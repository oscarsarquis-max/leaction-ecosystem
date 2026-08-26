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

try {
  require('dotenv').config({
    path: path.join(__dirname, '..', '.env'),
    override: false,
  });
} catch {
  try {
    require(path.join(
      __dirname,
      '..',
      'services',
      'gateway-api',
      'node_modules',
      'dotenv'
    )).config({
      path: path.join(__dirname, '..', '.env'),
      override: false,
    });
  } catch {
    /* dotenv opcional */
  }
}

const { Client } = loadPg();

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5434/leaction_hub';
const sqlPath = path.join(__dirname, '..', 'shared', 'database', 'patch_identidade.sql');

function pgClientConfig(databaseUrl) {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca|no-verify)/i.test(databaseUrl) ||
    databaseUrl.includes('rds.amazonaws.com');
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
    `SELECT table_name FROM information_schema.tables
     WHERE table_schema = 'public'
       AND table_name IN (
         'identidade_usuarios',
         'identidade_funcoes',
         'identidade_permissoes'
       )
     ORDER BY table_name`
  );
  console.log(
    'identidade tables:',
    check.rows.map((r) => r.table_name).join(', ') || '(none)'
  );
  await client.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
