const { Pool } = require('pg');
require('dotenv').config({ path: '../../.env', override: true });

function stripSslModeFromDatabaseUrl(url) {
  if (!url) return '';
  let out = url.replace(/([?&])sslmode=[^&]*/gi, '$1');
  return out.replace(/\?&/, '?').replace(/[?&]$/, '');
}

(async () => {
  const raw = process.env.DATABASE_URL || '';
  const pool = new Pool({
    connectionString: stripSslModeFromDatabaseUrl(raw),
    ssl: { rejectUnauthorized: false },
  });
  const orders = await pool.query(
    `SELECT id, status, created_at FROM orders
     WHERE external_resource_id::text ILIKE '%LOJADEPAES_BIBLIOTECA%'
     ORDER BY created_at DESC LIMIT 20`
  );
  const contracts = await pool.query(
    `SELECT id, subject_id, status, started_at FROM contracts
     WHERE app_id = 'lojadepaes' LIMIT 20`
  );
  const snaps = await pool.query(
    `SELECT subject_id, valid_until FROM entitlement_snapshots WHERE app_id = 'lojadepaes' LIMIT 20`
  );
  console.log(JSON.stringify({
    biblioteca_orders: orders.rows,
    lojadepaes_contracts: contracts.rowCount,
    lojadepaes_snapshots: snaps.rowCount,
  }, null, 2));
  await pool.end();
})().catch((err) => {
  console.error('FAIL', err.message);
  process.exit(1);
});
