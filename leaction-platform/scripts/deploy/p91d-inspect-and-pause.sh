#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform/services/gateway-api
node <<'NODE'
const { Pool } = require('pg');
require('dotenv').config({ path: '../../.env', override: true });

(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });
  const skus = ['LOJADEPAES_BIBLIOTECA_MENSAL', 'LOJADEPAES_BIBLIOTECA_CREDITOS'];
  const plans = await pool.query(
    `SELECT id, sku, price, active, meta_json
     FROM catalog_plans WHERE app_id = 'lojadepaes' AND sku = ANY($1)`,
    [skus]
  );
  const orders = await pool.query(
    `SELECT o.id, o.status, o.created_at, o.external_resource_id
     FROM orders o
     WHERE o.external_resource_id ILIKE '%LOJADEPAES_BIBLIOTECA%'
     ORDER BY o.created_at DESC
     LIMIT 20`
  );
  const contracts = await pool.query(
    `SELECT c.id, c.app_id, c.subject_id, c.status, c.started_at, c.ends_at, c.order_id
     FROM contracts c
     WHERE c.app_id = 'lojadepaes'
       AND (c.meta_json::text ILIKE '%BIBLIOTECA%' OR c.external_ref ILIKE '%BIBLIOTECA%')
     LIMIT 20`
  );
  const snaps = await pool.query(
    `SELECT subject_id, payload_json, valid_until
     FROM entitlement_snapshots
     WHERE app_id = 'lojadepaes'
     LIMIT 20`
  );
  const paused = await pool.query(
    `UPDATE catalog_plans
     SET active = FALSE, updated_at = CURRENT_TIMESTAMP
     WHERE app_id = 'lojadepaes' AND sku = ANY($1)
     RETURNING id, sku, active`,
    [skus]
  );
  console.log(JSON.stringify({
    plans_before: plans.rows.map((r) => ({ id: r.id, sku: r.sku, price: Number(r.price), active: r.active })),
    orders: orders.rows.map((r) => ({ id: r.id, status: r.status, created_at: r.created_at })),
    contracts: contracts.rows,
    snapshots: snaps.rows.map((r) => ({
      subject_id: r.subject_id,
      credits: r.payload_json && r.payload_json.credits,
      plan: r.payload_json && r.payload_json.plan && r.payload_json.plan.sku,
      valid_until: r.valid_until,
    })),
    paused: paused.rows,
  }, null, 2));
  await pool.end();
})().catch((err) => {
  console.error('FAIL', err.message);
  process.exit(1);
});
NODE
