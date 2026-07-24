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
  'patch_cms_actionhub_destino.sql'
);

(async () => {
  const sql = fs.readFileSync(sqlPath, 'utf8');
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  await client.query(sql);
  const check = await client.query(
    `SELECT pg_get_constraintdef(oid) AS def
     FROM pg_constraint WHERE conname = 'chk_cms_posts_destino'`
  );
  console.log('chk_cms_posts_destino:', check.rows[0]?.def || '(missing)');
  await client.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
