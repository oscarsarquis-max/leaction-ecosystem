'use strict';

const { Pool } = require('pg');

function vaultDatabaseUrl() {
  const url = String(process.env.VAULT_DATABASE_URL || '').trim();
  if (!url) {
    throw new Error(
      'VAULT_DATABASE_URL obrigatória (banco leaction_vault — não use o DATABASE_URL do Hub)'
    );
  }
  if (/\/leaction_hub(\?|$)/i.test(url)) {
    throw new Error(
      'VAULT_DATABASE_URL aponta para leaction_hub — o cofre exige o banco leaction_vault'
    );
  }
  return url;
}

function createPool() {
  return new Pool({ connectionString: vaultDatabaseUrl() });
}

module.exports = { createPool, vaultDatabaseUrl };
