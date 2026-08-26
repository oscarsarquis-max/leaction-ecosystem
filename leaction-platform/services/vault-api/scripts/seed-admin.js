'use strict';

const path = require('path');
const { Client } = require('pg');
const { hashPassword } = require('../lib/passwords');
const { vaultDatabaseUrl } = require('../lib/db');

require('dotenv').config({
  path: path.join(__dirname, '..', '.env'),
  override: false,
});

(async () => {
  const email = String(process.env.VAULT_BOOTSTRAP_EMAIL || '')
    .trim()
    .toLowerCase();
  const senha = String(process.env.VAULT_BOOTSTRAP_PASSWORD || '');
  if (!email.includes('@') || senha.length < 8) {
    throw new Error(
      'Defina VAULT_BOOTSTRAP_EMAIL e VAULT_BOOTSTRAP_PASSWORD (>= 8) no .env do vault-api'
    );
  }

  const client = new Client({ connectionString: vaultDatabaseUrl() });
  await client.connect();
  const hash = hashPassword(senha);
  await client.query(
    `INSERT INTO vault_admins (email, senha_hash, ativo)
     VALUES ($1, $2, TRUE)
     ON CONFLICT (email) DO UPDATE SET
       senha_hash = EXCLUDED.senha_hash,
       ativo = TRUE`,
    [email, hash]
  );
  console.log('admin do cofre pronto:', email);
  await client.end();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
