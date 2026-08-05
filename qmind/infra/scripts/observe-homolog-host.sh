#!/usr/bin/env bash
# Coleta host-side diaria (worker, jobs, disco, memoria) + metricas CloudWatch QMind/Homolog.
# Cron: 20 11 * * * /opt/qmind/bin/observe-homolog-host.sh
# Usa credencial backup-uploader apenas para PutMetricData (namespace QMind/Homolog).
set -euo pipefail

META="${QMIND_META:-/opt/qmind/INSTANCE_META.env}"
# shellcheck disable=SC1090
source "$META"

COMPOSE_DIR="${COMPOSE_DIR:-/opt/qmind/infra/compose}"
OUT_DIR="${QMIND_OPS_DIR:-/opt/qmind/ops/observe}"
STAMP_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DAY_UTC="$(date -u +%Y-%m-%d)"
mkdir -p "$OUT_DIR"
chmod 750 "$OUT_DIR" || true

unset AWS_SESSION_TOKEN AWS_SECURITY_TOKEN AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY || true
set -a
# shellcheck disable=SC1091
source /opt/qmind/secrets/backup-uploader.env
set +a

REGION="${QMIND_AWS_REGION:-us-east-2}"
cd "$COMPOSE_DIR"

disk_pct="$(df -P / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')"
mem_pct="$(awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} END{ if(t>0) printf "%.1f", (t-a)*100/t; else print "0" }' /proc/meminfo)"

worker_health=0
worker_status="down"
# Health port is internal to the container (not published on the host).
if docker compose -f docker-compose.homolog.yml exec -T worker \
  curl -fsS --max-time 3 http://127.0.0.1:8010/health >/dev/null 2>&1; then
  worker_health=1
  worker_status="healthy"
fi

api_container="$(docker compose -f docker-compose.homolog.yml ps -q api 2>/dev/null || true)"
worker_container="$(docker compose -f docker-compose.homolog.yml ps -q worker 2>/dev/null || true)"
db_container="$(docker compose -f docker-compose.homolog.yml ps -q db 2>/dev/null || true)"

cpu_api="null"; mem_api="null"; cpu_worker="null"; mem_worker="null"; cpu_db="null"; mem_db="null"
if [[ -n "$api_container" ]]; then
  read -r cpu_api mem_api < <(docker stats --no-stream --format "{{.CPUPerc}} {{.MemPerc}}" "$api_container" | sed 's/%//g')
fi
if [[ -n "$worker_container" ]]; then
  read -r cpu_worker mem_worker < <(docker stats --no-stream --format "{{.CPUPerc}} {{.MemPerc}}" "$worker_container" | sed 's/%//g')
fi
if [[ -n "$db_container" ]]; then
  read -r cpu_db mem_db < <(docker stats --no-stream --format "{{.CPUPerc}} {{.MemPerc}}" "$db_container" | sed 's/%//g')
fi

job_sql=$(cat <<'SQL'
SELECT
  count(*) FILTER (WHERE status='queued') AS queued,
  count(*) FILTER (WHERE status='running') AS running,
  count(*) FILTER (WHERE status='failed' AND finished_at > now() - interval '24 hours') AS failed_24h,
  count(*) FILTER (WHERE status='succeeded' AND finished_at > now() - interval '24 hours') AS succeeded_24h,
  coalesce(
    extract(epoch from avg(finished_at - started_at) FILTER (
      WHERE status='succeeded'
        AND finished_at > now() - interval '24 hours'
        AND started_at IS NOT NULL
    )),
    0
  )::int AS avg_success_seconds_24h,
  count(*) FILTER (
    WHERE status='running' AND locked_at IS NOT NULL AND locked_at < now() - interval '15 minutes'
  ) AS stuck_running
FROM jobs
WHERE job_type='report_pdf_export';
SQL
)

job_line="$(
  docker compose -f docker-compose.homolog.yml exec -T db \
    psql -U qmind_admin -d qmind -tA -F ',' -c "$job_sql" 2>/dev/null || echo "0,0,0,0,0,0"
)"
IFS=',' read -r queued running failed_24h succeeded_24h avg_sec stuck <<<"$job_line"
queued="${queued:-0}"; running="${running:-0}"; failed_24h="${failed_24h:-0}"
succeeded_24h="${succeeded_24h:-0}"; avg_sec="${avg_sec:-0}"; stuck="${stuck:-0}"

OUT_FILE="$OUT_DIR/${DAY_UTC}.json"
cat >"$OUT_FILE" <<JSON
{
  "day_utc": "$DAY_UTC",
  "collected_at": "$STAMP_UTC",
  "source": "host",
  "disk_used_percent": $disk_pct,
  "mem_used_percent": $mem_pct,
  "worker_health": $worker_health,
  "worker_status": "$worker_status",
  "containers": {
    "api_cpu_percent": $cpu_api,
    "api_mem_percent": $mem_api,
    "worker_cpu_percent": $cpu_worker,
    "worker_mem_percent": $mem_worker,
    "db_cpu_percent": $cpu_db,
    "db_mem_percent": $mem_db
  },
  "jobs": {
    "queued": $queued,
    "running": $running,
    "failed_24h": $failed_24h,
    "succeeded_24h": $succeeded_24h,
    "avg_success_seconds_24h": $avg_sec,
    "stuck_running": $stuck
  }
}
JSON
chmod 640 "$OUT_FILE" || true

put_metric() {
  local name="$1" value="$2" unit="${3:-None}"
  aws cloudwatch put-metric-data \
    --region "$REGION" \
    --namespace "QMind/Homolog" \
    --metric-data "MetricName=${name},Value=${value},Unit=${unit},Dimensions=[{Name=Environment,Value=homolog}]" \
    >/dev/null
}

put_metric "WorkerHealthy" "$worker_health" "None"
put_metric "DiskUsedPercent" "$disk_pct" "Percent"
put_metric "MemUsedPercent" "$mem_pct" "Percent"
put_metric "JobQueuedCount" "$queued" "Count"
put_metric "JobRunningCount" "$running" "Count"
put_metric "JobFailed24h" "$failed_24h" "Count"
put_metric "JobSucceeded24h" "$succeeded_24h" "Count"
put_metric "JobStuckRunning" "$stuck" "Count"
put_metric "JobAvgSuccessSeconds24h" "$avg_sec" "Seconds"

# Gatilhos locais (log only; operator script consolida)
triggers=()
if (( disk_pct > 80 )); then triggers+=("disk_above_80"); fi
if (( worker_health == 0 )); then triggers+=("worker_unhealthy"); fi
if (( stuck > 0 )); then triggers+=("jobs_stuck"); fi
if (( queued > 20 )); then triggers+=("queue_growth"); fi

echo "OBSERVE_HOST_OK day=$DAY_UTC disk=$disk_pct mem=$mem_pct worker=$worker_status queued=$queued stuck=$stuck triggers=${triggers[*]:-none}"
