'use strict';

/**
 * Smoke do OutboxWorker: sobe HTTP local, entrega 1 evento, confere delivered.
 */

const http = require('http');
const { Pool } = require('pg');
const jwt = require('jsonwebtoken');
const { process_pending_outbox_events } = require('../domain/outbox-worker');
require('dotenv').config({ path: '../../../.env', override: true });

const SECRET = 'smoke-outbox-secret-' + Date.now().toString(16);
const APP_ID = 'inove4us';
const KEY = `smoke_outbox_${Date.now()}`;

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5433),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
});

(async () => {
  let received = null;
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => {
      body += c;
    });
    req.on('end', () => {
      received = {
        auth: req.headers.authorization || '',
        signature: req.headers['x-hub-signature'] || '',
        body: JSON.parse(body || '{}'),
      };
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
    });
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address();
  const webhookUrl = `http://127.0.0.1:${port}/hub-webhook`;

  const prev = await pool.query(
    `SELECT webhook_url, webhook_secret FROM app_registry WHERE app_id = $1`,
    [APP_ID]
  );
  const prevUrl = prev.rows[0]?.webhook_url ?? null;
  const prevSecret = prev.rows[0]?.webhook_secret ?? null;

  await pool.query(
    `UPDATE app_registry
     SET webhook_url = $1, webhook_secret = $2, active = TRUE
     WHERE app_id = $3`,
    [webhookUrl, SECRET, APP_ID]
  );

  try {
    await pool.query(
      `INSERT INTO webhook_outbox (
         app_id, event_type, payload_json, idempotency_key,
         status, attempts, next_retry_at
       ) VALUES (
         $1, 'CREDITS_GRANTED', $2::jsonb, $3,
         'pending', 0, CURRENT_TIMESTAMP
       )
       ON CONFLICT (idempotency_key) DO NOTHING`,
      [APP_ID, JSON.stringify({ credits: 7, smoke: true }), KEY]
    );

    const stats = await process_pending_outbox_events(pool);
    console.log('stats', stats);

    if (!received) throw new Error('webhook não recebido');
    if (!String(received.auth).startsWith('Bearer ')) {
      throw new Error('Authorization Bearer ausente');
    }
    const token = received.auth.slice(7);
    const decoded = jwt.verify(token, SECRET);
    if (decoded.event_type !== 'CREDITS_GRANTED') {
      throw new Error('JWT event_type inválido');
    }

    const row = await pool.query(
      `SELECT status, attempts FROM webhook_outbox WHERE idempotency_key = $1`,
      [KEY]
    );
    if (row.rows[0]?.status !== 'delivered') {
      throw new Error(`status esperado delivered, got ${row.rows[0]?.status}`);
    }

    console.log('SMOKE_OK', {
      decoded_event: decoded.event_type,
      body_event: received.body.event_type,
    });
  } finally {
    await pool.query(
      `UPDATE app_registry
       SET webhook_url = $1, webhook_secret = $2
       WHERE app_id = $3`,
      [prevUrl, prevSecret, APP_ID]
    );
    server.close();
    await pool.end();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
