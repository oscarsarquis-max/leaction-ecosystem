#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
cd "$INFRA"
echo "collected_utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "collected_brt $(TZ=America/Sao_Paulo date +%Y-%m-%dT%H:%M:%S%z)"
API=$(sudo docker compose -f "$COMPOSE" ps -q api)
echo "api_image $(sudo docker inspect -f '{{.Config.Image}}' "$API")"
echo "api_started $(sudo docker inspect -f '{{.State.StartedAt}}' "$API")"
sudo docker compose -f "$COMPOSE" exec -T db psql -U lojadepaes -d lojadepaes -c "SELECT version_num FROM alembic_version;"
sudo docker compose -f "$COMPOSE" exec -T db psql -U lojadepaes -d lojadepaes -v ON_ERROR_STOP=1 -f - <<'SQL'
\pset pager off
SELECT public_reference, status, total_cents, currency, fulfillment_modality,
       created_at, confirmed_at, production_local_date, preferred_time::text,
       holds_capacity, order_kind,
       (source_date_request_id IS NOT NULL) AS from_date_request,
       left(customer_name, 1) || '***' AS name_mask,
       regexp_replace(coalesce(customer_email,''), '(^.).*(@.*$)', '\1***\2') AS email_mask,
       (customer_phone IS NOT NULL AND customer_phone <> '') AS has_phone,
       (delivery_street IS NOT NULL AND delivery_street <> '') AS has_street
FROM orders
WHERE public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY created_at;

SELECT o.public_reference, i.quantity, i.physical_units, i.unit_price_cents, i.line_total_cents,
       i.net_weight_grams,
       coalesce(i.dough_name_snapshot,'') AS dough,
       coalesce(i.shape_name_snapshot,'') AS shape
FROM order_items i
JOIN orders o ON o.id = i.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY o.public_reference, i.created_at;

SELECT o.public_reference, h.from_status, h.to_status, h.reason, h.actor_ref, h.created_at
FROM order_status_history h
JOIN orders o ON o.id = h.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY o.public_reference, h.created_at;

SELECT o.public_reference, p.id, p.method, p.financial_status, p.external_status_raw,
       p.expected_cents, p.amount_paid_cents, p.amount_refunded_cents,
       p.external_reference, p.mp_payment_id,
       left(coalesce(p.idempotency_key,''), 8) || '…' AS idem_prefix,
       left(coalesce(p.sanitized_error,''), 180) AS err,
       p.created_at, p.confirmed_at, p.last_synced_at, p.updated_at
FROM payment_records p
JOIN orders o ON o.id = p.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY o.public_reference, p.created_at;

SELECT o.public_reference, e.external_event_id, e.external_type, e.process_status,
       left(coalesce(e.sanitized_error,''), 160) AS err,
       e.received_at, e.provider_occurred_at, e.payment_record_id
FROM payment_integration_events e
JOIN payment_records p ON p.id = e.payment_record_id
JOIN orders o ON o.id = p.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY e.received_at;

SELECT o.public_reference, m.kind, m.status, m.attempts,
       regexp_replace(m.to_address, '(^.).*(@.*$)', '\1***\2') AS to_mask,
       m.subject, m.created_at, m.sent_at,
       left(coalesce(m.last_error,''), 120) AS err,
       (position(o.public_reference in m.body) > 0) AS body_has_own_ref,
       (position('/pedido/' in m.body) > 0) AS has_order_path,
       (position('http' in m.body) > 0) AS has_http
FROM email_outbox m
JOIN orders o ON o.id = m.order_id
WHERE o.public_reference IN ('LPA8FC361791','LP91E9C35D1B')
ORDER BY o.public_reference, m.created_at;
SQL
