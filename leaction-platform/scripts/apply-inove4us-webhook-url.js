'use strict';
const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';
const sqlPath = path.join(
  __dirname,
  '..',
  'shared',
  'database',
  'patch_inove4us_webhook_url.sql'
);

(async () => {
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  await client.query(fs.readFileSync(sqlPath, 'utf8'));
  const r = await client.query(
    `SELECT app_id, webhook_url FROM app_registry WHERE app_id = 'inove4us'`
  );
  console.log(r.rows[0]);
  await client.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
