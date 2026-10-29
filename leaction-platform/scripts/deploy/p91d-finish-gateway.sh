#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform/services/gateway-api
node <<'NODE'
const { Pool } = require('pg');
const fs = require('fs');
require('dotenv').config({ path: '../../.env', override: true });
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
});
pool
  .query(fs.readFileSync('../../shared/database/patch_subscription_cycles.sql', 'utf8'))
  .then(async () => {
    console.log('cycles_table=ok');
    await pool.end();
  })
  .catch(async (err) => {
    console.error('cycles_table', err.message);
    try { await pool.end(); } catch {}
    process.exit(1);
  });
NODE
pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "subs=%{http_code}\n" "http://127.0.0.1:4001/v1/subscriptions"
curl -s -o /dev/null -w "credits=%{http_code}\n" -X POST http://127.0.0.1:4001/v1/credits/reserve -H 'Content-Type: application/json' -d '{}'
echo gateway_finish_ok
