'use strict';

/**
 * Notificação isolada de planos da Loja. Não usa o webhook de pedidos/Pay.
 */

const { kickOutboxNow } = require('./outbox-worker');

const APP_ID = 'lojadepaes';

async function enqueueLojaPlansEvent(pool, { eventType, idempotencyKey, payload }) {
  if (!pool || !eventType || !idempotencyKey) return { ok: false, reason: 'invalid' };
  const body = payload && typeof payload === 'object' ? { ...payload } : {};
  delete body.card;
  delete body.token;
  delete body.mp_card;
  await pool.query(
    `INSERT INTO webhook_outbox (
       app_id, event_type, payload_json, idempotency_key,
       status, attempts, next_retry_at, created_at
     ) VALUES (
       $1, $2, $3::jsonb, $4,
       'pending', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
     )
     ON CONFLICT (idempotency_key) DO NOTHING`,
    [APP_ID, eventType, JSON.stringify(body), String(idempotencyKey).slice(0, 180)]
  );
  kickOutboxNow(pool);
  return { ok: true };
}

module.exports = {
  APP_ID,
  enqueueLojaPlansEvent,
};
