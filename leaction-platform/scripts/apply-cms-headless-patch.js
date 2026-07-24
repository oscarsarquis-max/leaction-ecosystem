'use strict';

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';
const sqlPath = path.join(__dirname, '..', 'shared', 'database', 'patch_cms_headless.sql');

(async () => {
  const sql = fs.readFileSync(sqlPath, 'utf8');
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  await client.query(sql);
  const check = await client.query(
    `SELECT COUNT(*)::int AS n FROM information_schema.tables
     WHERE table_schema = 'public' AND table_name = 'cms_posts'`
  );
  console.log('cms_posts ready:', check.rows[0].n === 1);
  await client.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
