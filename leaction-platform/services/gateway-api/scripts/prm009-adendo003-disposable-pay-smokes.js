'use strict';

const http = require('http');
const { Pool } = require('pg');
const jwt = require('jsonwebtoken');
const { createContractService } = require('../domain/contract-service');
const { process_pending_outbox_events } = require('../domain/outbox-worker');

const url = process.env.DISPOSABLE_DATABASE_URL;
if (!url) {
  console.error('DISPOSABLE_DATABASE_URL ausente');
  process.exit(1);
}

const APP_A = 'smoke-app-a';
const APP_B = 'smoke-app-b';
const SECRET_A = 'smoke-secret-a';
const SECRET_B = 'smoke-secret-b';

function listen() {
  return new Promise((resolve) => {
    const hits = [];
    const server = http.createServer((req, res) => {
      let body = '';
      req.on('data', (chunk) => {
        body += chunk;
      });
      req.on('end', () => {
        const fail = String(req.url || '').includes('fail');
        hits.push({
          url: req.url,
          auth: req.headers.authorization || '',
          app: req.headers['x-hub-app-id'] || '',
          body: JSON.parse(body || '{}'),
        });
        res.writeHead(fail ? 500 : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: !fail }));
      });
    });
    server.listen(0, '127.0.0.1', () => resolve({ server, hits, port: server.address().port }));
  });
}

(async () => {
  const pool = new Pool({ connectionString: url });
  const { server, hits, port } = await listen();
  const urlA = `http://127.0.0.1:${port}/app-a`;
  const urlB = `http://127.0.0.1:${port}/app-b`;
  const failUrl = `http://127.0.0.1:${port}/fail`;
  try {
    await pool.query(
      `INSERT INTO app_registry (app_id, name, webhook_url, webhook_secret, active)
       VALUES ($1,'Smoke A',$2,$3,true), ($4,'Smoke B',$5,$6,true)
       ON CONFLICT (app_id) DO UPDATE SET webhook_url = EXCLUDED.webhook_url, webhook_secret = EXCLUDED.webhook_secret`,
      [APP_A, urlA, SECRET_A, APP_B, urlB, SECRET_B]
    );
    const user = await pool.query(
      `INSERT INTO users (email, full_name) VALUES ('smoke.contract@test.local','Smoke')
       ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name RETURNING id`
    );
    const product = await pool.query(
      `INSERT INTO products (sku, name, type, external_resource_id)
       VALUES ('SMOKE_CREDITS_10','Smoke créditos','PANELDX_SUBSCRIPTION','smoke')
       ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name RETURNING id`
    );
    const order = await pool.query(
      `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id, gateway_ref)
       VALUES ($1,$2,'PAID',NULL,$3,$4) RETURNING id`,
      [
        user.rows[0].id,
        product.rows[0].id,
        JSON.stringify({
          app_id: APP_A,
          credits: 10,
          subject_type: 'email',
          subject_id: 'smoke.contract@test.local',
          period_months: 12,
        }),
        'hub:smoke-app-a:pending',
      ]
    );
    const orderId = order.rows[0].id;
    await pool.query(`UPDATE orders SET gateway_ref = $1 WHERE id = $2`, [`hub:${APP_A}:${orderId}`, orderId]);

    const svc = createContractService(pool);
    const first = await svc.activateFromOrder(orderId);
    const second = await svc.activateFromOrder(orderId);
    if (!first.contract_id || first.contract_id !== second.contract_id || second.idempotent !== true) {
      throw new Error('contrato não foi idempotente');
    }
    const contracts = await pool.query(`SELECT count(*)::int AS n FROM contracts WHERE order_id = $1`, [orderId]);
    if (contracts.rows[0].n !== 1) throw new Error('contrato duplicado');
    await process_pending_outbox_events(pool);
    const afterContract = hits.filter((h) => h.url === '/app-a').length;
    if (afterContract < 1) throw new Error('contrato não entregou outbox ao app A');
    if (hits.some((h) => h.url === '/app-b')) throw new Error('contrato do app A vazou para o app B');

    const keyA = `smoke_a_${Date.now()}`;
    const keyB = `smoke_b_${Date.now()}`;
    await pool.query(
      `INSERT INTO webhook_outbox (app_id, event_type, payload_json, idempotency_key, status, attempts, next_retry_at)
       VALUES ($1,'CREDITS_GRANTED',$2::jsonb,$3,'pending',0,CURRENT_TIMESTAMP)`,
      [APP_A, JSON.stringify({ credits: 3, app: APP_A }), keyA]
    );
    await pool.query(
      `INSERT INTO webhook_outbox (app_id, event_type, payload_json, idempotency_key, status, attempts, next_retry_at)
       VALUES ($1,'CREDITS_GRANTED',$2::jsonb,$3,'pending',0,CURRENT_TIMESTAMP)`,
      [APP_B, JSON.stringify({ credits: 4, app: APP_B }), keyB]
    );
    await process_pending_outbox_events(pool);
    if (hits.filter((h) => h.url === '/app-a').length !== afterContract + 1) {
      throw new Error('app A não recebeu exactamente mais um evento isolado');
    }
    if (hits.filter((h) => h.url === '/app-b').length !== 1) throw new Error('app B não recebeu uma vez');
    jwt.verify(hits.find((h) => h.url === '/app-a').auth.slice(7), SECRET_A);
    jwt.verify(hits.find((h) => h.url === '/app-b').auth.slice(7), SECRET_B);

    await pool.query(
      `INSERT INTO webhook_outbox (app_id, event_type, payload_json, idempotency_key, status, attempts, next_retry_at)
       VALUES ($1,'CREDITS_GRANTED',$2::jsonb,$3,'pending',0,CURRENT_TIMESTAMP)
       ON CONFLICT (idempotency_key) DO NOTHING`,
      [APP_A, JSON.stringify({ credits: 3, app: APP_A }), keyA]
    );
    const beforeRetry = hits.length;
    await process_pending_outbox_events(pool);
    if (hits.length !== beforeRetry) throw new Error('retry duplicou entrega já delivered');

    await pool.query(`UPDATE app_registry SET webhook_url = $1 WHERE app_id = $2`, [failUrl, APP_A]);
    const keyFail = `smoke_fail_${Date.now()}`;
    await pool.query(
      `INSERT INTO webhook_outbox (app_id, event_type, payload_json, idempotency_key, status, attempts, next_retry_at)
       VALUES ($1,'CREDITS_GRANTED',$2::jsonb,$3,'pending',0,CURRENT_TIMESTAMP)`,
      [APP_A, JSON.stringify({ credits: 1 }), keyFail]
    );
    await process_pending_outbox_events(pool);
    const failed = await pool.query(`SELECT status, attempts FROM webhook_outbox WHERE idempotency_key = $1`, [keyFail]);
    if (failed.rows[0].status !== 'failed' && failed.rows[0].status !== 'pending') {
      throw new Error('falha não registada');
    }
    if (Number(failed.rows[0].attempts) < 1) throw new Error('retry não incrementou attempts');

    console.log('DISPOSABLE_SMOKE_OK', {
      contract_id: first.contract_id,
      outbox_delivered: 2,
      retry_no_duplicate: true,
      isolation: true,
    });
  } finally {
    server.close();
    await pool.end();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
