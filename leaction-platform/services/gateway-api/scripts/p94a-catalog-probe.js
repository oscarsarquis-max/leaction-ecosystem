'use strict';

const { Pool } = require('pg');
require('dotenv').config({ path: '../../../.env', override: true });

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5433),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
});

(async () => {
  const r = await pool.query(
    `SELECT sku, type, price, active, meta_json
     FROM catalog_plans
     WHERE app_id = 'lojadepaes'
       AND sku IN ('LOJADEPAES_BIBLIOTECA_MENSAL', 'LOJADEPAES_BIBLIOTECA_CREDITOS')`
  );
  console.log(JSON.stringify(r.rows, null, 2));
  await pool.end();
})().catch(async (err) => {
  console.error(err.message);
  try {
    await pool.end();
  } catch {
    /* ignore */
  }
  process.exit(1);
});
