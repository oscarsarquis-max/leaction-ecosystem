'use strict';

const fs = require('fs');
const path = require('path');

function loadPg() {
  try {
    return require('pg');
  } catch {
    return require(path.join(
      __dirname,
      '..',
      'services',
      'gateway-api',
      'node_modules',
      'pg'
    ));
  }
}

const { Client } = loadPg();

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';
const sqlPath = path.join(__dirname, '..', 'shared', 'database', 'patch_cms_assistente_chat.sql');

function pgClientConfig(databaseUrl) {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca|no-verify)/i.test(databaseUrl) ||
    databaseUrl.includes('rds.amazonaws.com');
  // pg v8+ trata sslmode=require como verify-full; SSL fica no objeto ssl.
  const connectionString = databaseUrl
    .replace(/([?&])sslmode=[^&]*/gi, '$1')
    .replace(/[?&]$/, '')
    .replace(/\?&/, '?');
  return {
    connectionString,
    ssl: forceSsl ? { rejectUnauthorized: false } : false,
  };
}

(async () => {
  const sql = fs.readFileSync(sqlPath, 'utf8');
  const client = new Client(pgClientConfig(DATABASE_URL));
  await client.connect();
  await client.query(sql);
  const check = await client.query(
    `SELECT COUNT(*)::int AS n FROM information_schema.tables
     WHERE table_schema = 'public' AND table_name = 'cms_assistente_chat'`
  );
  console.log('cms_assistente_chat ready:', check.rows[0].n === 1);
  await client.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
