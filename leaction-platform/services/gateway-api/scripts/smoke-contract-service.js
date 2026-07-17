const { Pool } = require('pg');
const { createContractService } = require('../domain/contract-service');
require('dotenv').config({ path: '../../../.env', override: true });

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5433),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
});

(async () => {
  const svc = createContractService(pool);
  const u = await pool.query(
    `INSERT INTO users (email, full_name) VALUES ($1, $2)
     ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
     RETURNING id`,
    ['contract.smoke@test.local', 'Smoke']
  );

  let p = await pool.query(
    `SELECT id, sku FROM products WHERE type = 'PANELDX_SUBSCRIPTION' LIMIT 1`
  );
  if (!p.rows[0]) {
    p = await pool.query(
      `INSERT INTO products (sku, name, type, external_resource_id)
       VALUES ('INOVE4US_CREDITS_100', 'Pacote 100 créditos', 'PANELDX_SUBSCRIPTION', 'inove')
       RETURNING id, sku`
    );
  }

  const payload = JSON.stringify({
    app_id: 'inove4us',
    credits: 100,
    subject_type: 'email',
    subject_id: 'contract.smoke@test.local',
    period_months: 12,
  });

  const o = await pool.query(
    `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id, gateway_ref)
     VALUES ($1, $2, 'PAID', NULL, $3, $4)
     RETURNING id`,
    [u.rows[0].id, p.rows[0].id, payload, 'hub:inove4us:pending']
  );
  const orderId = o.rows[0].id;
  await pool.query(`UPDATE orders SET gateway_ref = $1 WHERE id = $2`, [
    `hub:inove4us:${orderId}`,
    orderId,
  ]);

  const r1 = await svc.activateFromOrder(orderId);
  console.log('first', JSON.stringify(r1));
  const r2 = await svc.activateFromOrder(orderId);
  console.log('second', JSON.stringify(r2));

  const snap = await pool.query(
    `SELECT payload_json FROM entitlement_snapshots
     WHERE app_id = 'inove4us' AND subject_id = 'contract.smoke@test.local'`
  );
  console.log('snap', JSON.stringify(snap.rows[0]?.payload_json));

  const out = await pool.query(
    `SELECT event_type, status, idempotency_key FROM webhook_outbox
     WHERE idempotency_key = $1`,
    [`order_${orderId}_activation`]
  );
  console.log('outbox', JSON.stringify(out.rows));
  await pool.end();
})().catch(async (e) => {
  console.error(e);
  try {
    await pool.end();
  } catch (_) {
    /* ignore */
  }
  process.exit(1);
});
