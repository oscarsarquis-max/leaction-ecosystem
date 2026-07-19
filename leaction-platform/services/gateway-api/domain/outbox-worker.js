'use strict';

/**
 * Worker do webhook_outbox — entrega eventos pendentes às apps satélites.
 *
 * Uso:
 *   const { startOutboxWorker, process_pending_outbox_events } = require('./domain/outbox-worker');
 *   startOutboxWorker(pool); // setInterval no boot do gateway
 */

const axios = require('axios');
const jwt = require('jsonwebtoken');

const LOG = '[OutboxWorker]';
const BATCH_LIMIT = 50;
const MAX_ATTEMPTS = 5;
const BACKOFF_MINUTES = 5;
const DEFAULT_INTERVAL_MS = 5_000;
const HTTP_TIMEOUT_MS = 15_000;

function backoffMinutes(attempts) {
  const n = Math.max(1, Number(attempts) || 1);
  return n * BACKOFF_MINUTES;
}

/**
 * Claim seguro: SELECT … FOR UPDATE SKIP LOCKED + marca processing.
 * @param {import('pg').Pool} pool
 * @returns {Promise<object[]>}
 */
async function claimPendingEvents(pool) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const selected = await client.query(
      `SELECT o.id
       FROM webhook_outbox o
       JOIN app_registry a ON a.app_id = o.app_id
       WHERE o.status IN ('pending', 'failed')
         AND o.attempts < $1
         AND (o.next_retry_at IS NULL OR o.next_retry_at <= NOW())
       ORDER BY o.created_at ASC
       LIMIT $2
       FOR UPDATE OF o SKIP LOCKED`,
      [MAX_ATTEMPTS, BATCH_LIMIT]
    );

    if (selected.rows.length === 0) {
      await client.query('COMMIT');
      return [];
    }

    const ids = selected.rows.map((r) => r.id);
    const claimed = await client.query(
      `UPDATE webhook_outbox o
       SET status = 'processing',
           last_error = NULL
       FROM app_registry a
       WHERE o.id = ANY($1::uuid[])
         AND a.app_id = o.app_id
       RETURNING
         o.id,
         o.app_id,
         o.event_type,
         o.payload_json,
         o.idempotency_key,
         o.status,
         o.attempts,
         o.next_retry_at,
         o.last_error,
         o.created_at,
         a.webhook_url,
         a.webhook_secret`,
      [ids]
    );

    await client.query('COMMIT');
    return claimed.rows;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

async function markDelivered(pool, id) {
  await pool.query(
    `UPDATE webhook_outbox
     SET status = 'delivered',
         last_error = NULL,
         next_retry_at = NULL
     WHERE id = $1`,
    [id]
  );
}

async function markFailed(pool, id, attemptsBefore, errorMessage, permanent = false) {
  const nextAttempts = Number(attemptsBefore || 0) + 1;
  const giveUp = permanent || nextAttempts >= MAX_ATTEMPTS;
  const minutes = backoffMinutes(nextAttempts);

  await pool.query(
    `UPDATE webhook_outbox
     SET status = 'failed',
         attempts = $2,
         last_error = $3,
         next_retry_at = CASE
           WHEN $4::boolean THEN NULL
           ELSE NOW() + ($5::int * INTERVAL '1 minute')
         END
     WHERE id = $1`,
    [id, nextAttempts, String(errorMessage || 'unknown error').slice(0, 2000), giveUp, minutes]
  );

  return { nextAttempts, giveUp };
}

function buildJwt(row) {
  const payload =
    row.payload_json && typeof row.payload_json === 'object'
      ? row.payload_json
      : {};

  return jwt.sign(
    {
      iss: 'leaction-hub',
      event_type: row.event_type,
      app_id: row.app_id,
      outbox_id: row.id,
      idempotency_key: row.idempotency_key,
      payload,
    },
    String(row.webhook_secret),
    { expiresIn: '1h' }
  );
}

/**
 * Entrega um evento claimado (já em status processing).
 * @param {import('pg').Pool} pool
 * @param {object} row
 */
/**
 * URL efetiva do webhook: env de produção tem prioridade sobre app_registry.
 * Ex.: APP_WEBHOOK_URL_INOVE4US=https://inove4us.com.br/api/webhooks/actionhub
 */
function resolveWebhookUrl(appId, dbUrl) {
  const key = `APP_WEBHOOK_URL_${String(appId || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '_')}`;
  const fromEnv = String(process.env[key] || '').trim();
  if (fromEnv) return fromEnv;
  return String(dbUrl || '').trim();
}

async function deliverEvent(pool, row) {
  const webhookUrl = resolveWebhookUrl(row.app_id, row.webhook_url);
  const webhookSecret = String(row.webhook_secret || '').trim();

  if (!webhookUrl || !webhookSecret) {
    await markFailed(
      pool,
      row.id,
      row.attempts,
      'webhook_url ou webhook_secret ausente em app_registry',
      true
    );
    console.warn(
      `${LOG} skip app=${row.app_id} id=${row.id}: url/secret ausente → failed permanente`
    );
    return { ok: false, reason: 'misconfigured' };
  }

  let token;
  try {
    token = buildJwt(row);
  } catch (signErr) {
    await markFailed(pool, row.id, row.attempts, `JWT sign: ${signErr.message}`, true);
    return { ok: false, reason: 'jwt' };
  }

  const body = {
    event_type: row.event_type,
    app_id: row.app_id,
    idempotency_key: row.idempotency_key,
    payload: row.payload_json,
    token,
  };

  try {
    const res = await axios.post(webhookUrl, body, {
      timeout: HTTP_TIMEOUT_MS,
      headers: {
        Authorization: `Bearer ${token}`,
        'X-Hub-Signature': token,
        'Content-Type': 'application/json',
        'X-Hub-Event-Type': String(row.event_type || ''),
        'X-Hub-Idempotency-Key': String(row.idempotency_key || ''),
      },
      validateStatus: () => true,
    });

    if (res.status >= 200 && res.status < 300) {
      await markDelivered(pool, row.id);
      console.log(
        `${LOG} delivered id=${row.id} app=${row.app_id} event=${row.event_type} http=${res.status}`
      );
      return { ok: true };
    }

    const errMsg = `HTTP ${res.status}: ${typeof res.data === 'string' ? res.data : JSON.stringify(res.data || {}).slice(0, 500)}`;
    const fail = await markFailed(pool, row.id, row.attempts, errMsg, false);
    console.warn(
      `${LOG} fail id=${row.id} app=${row.app_id} attempts=${fail.nextAttempts}${fail.giveUp ? ' (give up)' : ''}: ${errMsg}`
    );
    return { ok: false, reason: 'http' };
  } catch (httpErr) {
    const errMsg = httpErr.message || String(httpErr);
    const fail = await markFailed(pool, row.id, row.attempts, errMsg, false);
    console.warn(
      `${LOG} error id=${row.id} app=${row.app_id} attempts=${fail.nextAttempts}${fail.giveUp ? ' (give up)' : ''}: ${errMsg}`
    );
    return { ok: false, reason: 'network' };
  }
}

/**
 * Processa um lote de eventos pendentes/failed elegíveis a retry.
 * @param {import('pg').Pool} pool
 */
async function process_pending_outbox_events(pool) {
  let rows;
  try {
    rows = await claimPendingEvents(pool);
  } catch (err) {
    console.error(`${LOG} claim error:`, err.message);
    return { claimed: 0, delivered: 0, failed: 0 };
  }

  if (!rows.length) {
    return { claimed: 0, delivered: 0, failed: 0 };
  }

  let delivered = 0;
  let failed = 0;

  for (const row of rows) {
    const result = await deliverEvent(pool, row);
    if (result.ok) delivered += 1;
    else failed += 1;
  }

  return { claimed: rows.length, delivered, failed };
}

const processPendingOutboxEvents = process_pending_outbox_events;

/**
 * Agenda o worker no processo do gateway.
 * @param {import('pg').Pool} pool
 * @param {{ intervalMs?: number }} [options]
 */
function startOutboxWorker(pool, options = {}) {
  if (String(process.env.OUTBOX_WORKER_DISABLED || '').trim() === '1') {
    console.warn(`${LOG} desabilitado (OUTBOX_WORKER_DISABLED=1)`);
    return { stop() {} };
  }

  const intervalMs = Number(options.intervalMs || process.env.OUTBOX_WORKER_INTERVAL_MS) || DEFAULT_INTERVAL_MS;
  let running = false;

  const tick = async () => {
    if (running) return;
    running = true;
    try {
      const stats = await process_pending_outbox_events(pool);
      if (stats.claimed > 0) {
        console.log(
          `${LOG} batch claimed=${stats.claimed} delivered=${stats.delivered} failed=${stats.failed}`
        );
      }
    } catch (err) {
      console.error(`${LOG} tick error:`, err.message);
    } finally {
      running = false;
    }
  };

  const timer = setInterval(tick, intervalMs);
  if (typeof timer.unref === 'function') timer.unref();

  // primeira passagem sem esperar o intervalo
  setTimeout(tick, 2_000).unref?.();

  console.log(`${LOG} agendado a cada ${intervalMs}ms`);

  return {
    stop() {
      clearInterval(timer);
    },
  };
}

/**
 * Dispara entrega imediata (após fulfill / inject) sem esperar o intervalo.
 * Fire-and-forget — erros só vão para o log.
 * @param {import('pg').Pool} pool
 */
function kickOutboxNow(pool) {
  setImmediate(() => {
    process_pending_outbox_events(pool)
      .then((stats) => {
        if (stats.claimed > 0) {
          console.log(
            `${LOG} kick claimed=${stats.claimed} delivered=${stats.delivered} failed=${stats.failed}`
          );
        }
      })
      .catch((err) => {
        console.error(`${LOG} kick error:`, err.message);
      });
  });
}

module.exports = {
  process_pending_outbox_events,
  processPendingOutboxEvents,
  startOutboxWorker,
  kickOutboxNow,
  claimPendingEvents,
  deliverEvent,
  MAX_ATTEMPTS,
  BACKOFF_MINUTES,
};
