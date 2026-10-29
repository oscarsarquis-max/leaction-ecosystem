#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
cd "$INFRA"
echo "collected_utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "collected_brt $(TZ=America/Sao_Paulo date +%Y-%m-%dT%H:%M:%S%z)"
API=$(sudo docker compose -f "$COMPOSE" ps -q api)
echo "api_image $(sudo docker inspect -f '{{.Config.Image}}' "$API")"
sudo docker compose -f "$COMPOSE" exec -T db psql -U lojadepaes -d lojadepaes -v ON_ERROR_STOP=1 -c "
SELECT o.public_reference, o.status, p.method, p.financial_status,
       p.expected_cents, p.amount_paid_cents, p.amount_refunded_cents,
       p.external_reference, p.mp_payment_id,
       left(coalesce(p.sanitized_error,''), 80) AS err,
       p.last_synced_at
FROM payment_records p
JOIN orders o ON o.id = p.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY o.public_reference, p.created_at;
"
sudo docker compose -f "$COMPOSE" exec -T db psql -U lojadepaes -d lojadepaes -v ON_ERROR_STOP=1 -c "
SELECT o.public_reference, o.status, m.kind, m.status AS mail_status, m.attempts, m.sent_at
FROM email_outbox m
JOIN orders o ON o.id = m.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
  AND m.kind IN ('order_accepted','order_auto_accepted_admin','payment_approved','order_submitted')
ORDER BY o.public_reference, m.created_at;
"
sudo docker compose -f "$COMPOSE" exec -T db psql -U lojadepaes -d lojadepaes -tAc "
SELECT count(*) FROM orders o
WHERE o.status IN ('confirmed','in_production','ready')
  AND EXISTS (
    SELECT 1 FROM payment_records p
    WHERE p.order_id = o.id AND p.financial_status = 'pending' AND p.external_reference IS NOT NULL
  );
"
