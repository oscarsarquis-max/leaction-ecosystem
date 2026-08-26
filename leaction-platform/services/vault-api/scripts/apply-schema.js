'use strict';

/**
 * Cria role vault_api + banco leaction_vault e aplica database/init.sql.
 * Usa VAULT_BOOTSTRAP_DATABASE_URL (superuser local) só neste script.
 */

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

require('dotenv').config({
  path: path.join(__dirname, '..', '.env'),
  override: false,
});

const BOOTSTRAP_URL =
  process.env.VAULT_BOOTSTRAP_DATABASE_URL ||
  'postgresql://admin:password123@127.0.0.1:5434/leaction_hub';
const VAULT_DB = 'leaction_vault';
const VAULT_ROLE = 'vault_api';
const VAULT_PASS = process.env.VAULT_DB_PASSWORD || 'vault_local_change_me';
const sqlPath = path.join(__dirname, '..', 'database', 'init.sql');

function rewriteDbName(url, dbName) {
  const u = new URL(url);
  u.pathname = `/${dbName}`;
  return u.toString();
}

(async () => {
  const admin = new Client({ connectionString: BOOTSTRAP_URL });
  await admin.connect();

  const role = await admin.query(
    `SELECT 1 FROM pg_roles WHERE rolname = $1`,
    [VAULT_ROLE]
  );
  if (role.rowCount === 0) {
    await admin.query(
      `CREATE ROLE ${VAULT_ROLE} LOGIN PASSWORD '${VAULT_PASS.replace(/'/g, "''")}'`
    );
    console.log('role vault_api criada');
  } else {
    await admin.query(
      `ALTER ROLE ${VAULT_ROLE} WITH LOGIN PASSWORD '${VAULT_PASS.replace(/'/g, "''")}'`
    );
    console.log('role vault_api atualizada');
  }

  const db = await admin.query(
    `SELECT 1 FROM pg_database WHERE datname = $1`,
    [VAULT_DB]
  );
  if (db.rowCount === 0) {
    await admin.query(`CREATE DATABASE ${VAULT_DB} OWNER ${VAULT_ROLE}`);
    console.log('banco leaction_vault criado');
  } else {
    console.log('banco leaction_vault já existe');
  }

  await admin.query(`REVOKE CONNECT ON DATABASE ${VAULT_DB} FROM PUBLIC`);
  await admin.query(`GRANT CONNECT ON DATABASE ${VAULT_DB} TO ${VAULT_ROLE}`);
  await admin.query(`GRANT CONNECT ON DATABASE ${VAULT_DB} TO CURRENT_USER`);
  await admin.end();

  const vault = new Client({ connectionString: rewriteDbName(BOOTSTRAP_URL, VAULT_DB) });
  await vault.connect();
  const sql = fs.readFileSync(sqlPath, 'utf8');
  for (const stmt of sql.split(';').map((s) => s.trim()).filter(Boolean)) {
    await vault.query(stmt);
  }
  await vault.query(`GRANT ALL ON SCHEMA public TO ${VAULT_ROLE}`);
  await vault.query(`GRANT ALL ON ALL TABLES IN SCHEMA public TO ${VAULT_ROLE}`);
  await vault.query(`GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ${VAULT_ROLE}`);
  await vault.query(
    `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${VAULT_ROLE}`
  );
  await vault.query(
    `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${VAULT_ROLE}`
  );
  const tables = await vault.query(
    `SELECT table_name FROM information_schema.tables
     WHERE table_schema = 'public'
       AND table_name IN ('vault_admins', 'secrets', 'secrets_audit_log', 'sistemas_rotacao')
     ORDER BY table_name`
  );
  console.log('tabelas:', tables.rows.map((r) => r.table_name).join(', '));
  await vault.end();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
