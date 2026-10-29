#!/usr/bin/env bash
# Analyze school.inove4us.com.br hits while potentially unlocked.
set -euo pipefail

OUT=/tmp/school-access-audit
mkdir -p "$OUT"

# Combine current + rotated uncompressed + gunzip recent
: > "$OUT/raw.txt"
sudo awk '$0 ~ /school\.inove4us\.com\.br/' /var/log/nginx/access.log >> "$OUT/raw.txt" || true
sudo awk '$0 ~ /school\.inove4us\.com\.br/' /var/log/nginx/access.log.1 >> "$OUT/raw.txt" || true
for f in /var/log/nginx/access.log.2.gz /var/log/nginx/access.log.3.gz /var/log/nginx/access.log.4.gz; do
  if [ -f "$f" ]; then
    sudo zcat "$f" | awk '$0 ~ /school\.inove4us\.com\.br/' >> "$OUT/raw.txt" || true
  fi
done

echo "=== total school host lines (Aug~ window in logs) ==="
wc -l "$OUT/raw.txt"

echo "=== lock file birth/mtime (UTC) ==="
stat /var/www/inove4us-school/data/system_locked || true
echo "current value:" $(cat /var/www/inove4us-school/data/system_locked)

echo "=== gatekeeper unlock/lock/bypass in access logs ==="
grep -E 'gatekeeper/(unlock|lock|bypass|status)' "$OUT/raw.txt" | tail -50 || true
echo "(count unlock)" $(grep -c 'gatekeeper/unlock' "$OUT/raw.txt" || true)
echo "(count lock)" $(grep -c 'gatekeeper/lock' "$OUT/raw.txt" || true)
echo "(count bypass)" $(grep -c 'gatekeeper/bypass' "$OUT/raw.txt" || true)

# Filter window: from 2026-08-12 to lock-restore 2026-08-14T15:28:01Z
# nginx time format: [14/Aug/2026:15:28:01 +0000]
python3 - <<'PY'
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

path = "/tmp/school-access-audit/raw.txt"
# unlocked window hypothesis: lock file birth Aug 13 21:13 with false, OR from Aug 12 launch.
# We know locked:false at inventory ~15:00 UTC Aug 14 and relocked 15:28 UTC Aug 14.
# Birth of file: 2026-08-13 21:13:33 — likely when unlock wrote the file as false.
start = datetime(2026, 8, 13, 21, 0, 0, tzinfo=timezone.utc)
end = datetime(2026, 8, 14, 15, 28, 1, tzinfo=timezone.utc)
# also report Aug 12 00:00 -> end for broader view
start_broad = datetime(2026, 8, 12, 0, 0, 0, tzinfo=timezone.utc)

pat = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+)[^"]*" (?P<status>\d+) (?P<size>\S+) "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"'
)

bot_re = re.compile(
    r'(bot|crawler|spider|slurp|bingpreview|facebookexternalhit|twitterbot|linkedinbot|'
    r'bytespider|semrush|ahrefs|mj12|petalbot|yandex|duckduck|applebot|gptbot|claudebot|'
    r'amazonbot|baiduspider|scrapy|python-requests|curl/|wget|Go-http|httpx|axios|'
    r'HealthChecker|ELB-HealthChecker|Google-Read-Aloud|AdsBot)',
    re.I,
)

def parse_ts(s):
    # 14/Aug/2026:15:28:01 +0000
    return datetime.strptime(s, "%d/%b/%Y:%H:%M:%S %z")

def analyze(label, t0, t1):
    total = 0
    human = 0
    bots = 0
    by_status = Counter()
    by_path = Counter()
    by_ip = Counter()
    human_ips = Counter()
    human_paths = Counter()
    human_uas = Counter()
    samples = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if not m:
            continue
        try:
            ts = parse_ts(m.group("ts"))
        except Exception:
            continue
        if not (t0 <= ts <= t1):
            continue
        total += 1
        ip = m.group("ip")
        pth = m.group("path").split("?")[0]
        st = m.group("status")
        ua = m.group("ua")
        by_status[st] += 1
        by_path[pth] += 1
        by_ip[ip] += 1
        is_bot = bool(bot_re.search(ua)) or pth in ("/api/health", "/favicon.ico")
        # treat gatekeeper/status probes as ops
        if "gatekeeper/status" in pth:
            is_bot = True
        if is_bot:
            bots += 1
        else:
            human += 1
            human_ips[ip] += 1
            human_paths[pth] += 1
            human_uas[ua[:120]] += 1
            if len(samples) < 25:
                samples.append(f"{ts.isoformat()} {ip} {st} {pth} | {ua[:80]}")
    print(f"\n=== WINDOW {label}: {t0.isoformat()} -> {t1.isoformat()} ===")
    print(f"total={total} bots/ops={bots} likely_human={human}")
    print("status top:", by_status.most_common(8))
    print("paths top:", by_path.most_common(15))
    print("ips top:", by_ip.most_common(10))
    if human:
        print("HUMAN ips:", human_ips.most_common(15))
        print("HUMAN paths:", human_paths.most_common(20))
        print("HUMAN ua samples:")
        for ua, n in human_uas.most_common(10):
            print(f"  {n}x {ua}")
        print("HUMAN request samples:")
        for s in samples:
            print(" ", s)
    else:
        print("No likely-human hits in this window (after bot/ops filter).")

analyze("unlock-file-birth-to-relock", start, end)
analyze("broad-Aug12-to-relock", start_broad, end)

# Also: first and last school hit overall in combined logs
first = last = None
for line in open(path, encoding="utf-8", errors="replace"):
    m = pat.search(line)
    if not m:
        continue
    try:
        ts = parse_ts(m.group("ts"))
    except Exception:
        continue
    if first is None or ts < first:
        first = ts
    if last is None or ts > last:
        last = ts
print(f"\nlog span school host: {first} .. {last}")
PY

echo "=== bash history unlock hints (ubuntu) ==="
grep -nE 'gatekeeper/(un)?lock|system_locked|SCHOOL_SYSTEM_LOCKED' /home/ubuntu/.bash_history 2>/dev/null | tail -30 || true
grep -nE 'gatekeeper/(un)?lock|system_locked' /var/www/inove4us-school/logs/*.log 2>/dev/null | tail -20 || true
pm2 logs inove4us-school --lines 5 --nostream 2>/dev/null | head -5 || true
