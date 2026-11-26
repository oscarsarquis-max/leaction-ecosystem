#!/usr/bin/env bash
# Build imagem lepain no host e troca só o container lepain (Loja/Gestão intactas).
set -euo pipefail

TAG="${1:?tag}"
SRC_TAR="${2:?src tar}"
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
WORK=/tmp/blog025-lepain-src
IMAGE="lojadepaes-blog:${TAG}"

rm -rf "$WORK"
mkdir -p "$WORK"
tar -xzf "$SRC_TAR" -C "$WORK"
cd "$WORK"
ASSET=$(python3 - <<'PY'
import hashlib, pathlib
h=hashlib.sha256()
for p in sorted(pathlib.Path('app').rglob('*')):
    if p.is_file():
        h.update(p.read_bytes())
print(h.hexdigest()[:8])
PY
)
docker build --build-arg "LEPAIN_ASSET_VERSION=$ASSET" -t "$IMAGE" -f deploy/Dockerfile .
docker image inspect "$IMAGE" >/dev/null

ENV_FILE="$BLOG_HOME/deploy/.env"
previous=""
if [ -f "$ENV_FILE" ]; then
  previous=$(grep -E '^LEPAIN_IMAGE=' "$ENV_FILE" | cut -d= -f2- || true)
fi
printf 'LEPAIN_IMAGE=%s\n' "$IMAGE" > "$ENV_FILE"

MONITOR=/tmp/blog025-lepain-health.txt
: > "$MONITOR"
(
  for i in $(seq 1 60); do
    ts=$(date -Is)
    loja=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 https://lojadepaes.com.br/api/v1/health || echo 000)
    gestao=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 https://gestao.lojadepaes.com.br/ || echo 000)
    lepain=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 https://lepain.lojadepaes.com.br/api/v1/health || echo 000)
    echo "$ts loja=$loja gestao=$gestao lepain=$lepain" >> "$MONITOR"
    sleep 2
  done
) &
MON=$!

COMPOSE=(docker compose -f "$BLOG_HOME/deploy/docker-compose.prod.yml" --env-file "$ENV_FILE")
"${COMPOSE[@]}" up -d --force-recreate lepain

ok=0
for _ in $(seq 1 25); do
  if docker exec lepain python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8091/api/v1/health', timeout=4)" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 3
done

kill "$MON" 2>/dev/null || true
wait "$MON" 2>/dev/null || true
echo "HEALTH_TAIL=$(tail -n 3 "$MONITOR" | tr '\n' ';')"

if [ "$ok" != "1" ]; then
  echo "LEPAIN_HEALTH_FAIL"
  if [ -n "$previous" ] && docker image inspect "$previous" >/dev/null 2>&1; then
    printf 'LEPAIN_IMAGE=%s\n' "$previous" > "$ENV_FILE"
    "${COMPOSE[@]}" up -d --force-recreate lepain
  fi
  exit 1
fi

echo "IMAGE=$IMAGE ASSET=$ASSET PREVIOUS=${previous:-none}"
echo BLOG025_LEPAIN_OK
