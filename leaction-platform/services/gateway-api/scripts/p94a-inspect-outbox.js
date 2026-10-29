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
  const outbox = await pool.query(
    `SELECT id, event_type, app_id, status, idempotency_key, payload_json
     FROM webhook_outbox
     WHERE app_id = 'lojadepaes'
       AND created_at > NOW() - INTERVAL '15 minutes'
     ORDER BY created_at DESC
     LIMIT 8`
  );
  const snaps = await pool.query(
    `SELECT subject_id, valid_until, payload_json
     FROM entitlement_snapshots
     WHERE app_id = 'lojadepaes'
       AND subject_id LIKE 'biblioteca.94a.%'`
  );
  console.log(
    JSON.stringify(
      {
        outbox: outbox.rows.map((row) => ({
          event_type: row.event_type,
          status: row.status,
          keys: Object.keys(row.payload_json || {}),
          subject: row.payload_json?.subject_id || row.payload_json?.subject,
          credits: row.payload_json?.credits ?? row.payload_json?.credits_added,
        })),
        snaps: snaps.rows,
      },
      null,
      2
    )
  );
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
