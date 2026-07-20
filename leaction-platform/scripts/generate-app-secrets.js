/**
 * Gera webhook_secret seguro para apps em app_registry com secret NULL.
 *
 * Uso:
 *   node scripts/generate-app-secrets.js
 *   DATABASE_URL=postgresql://... node scripts/generate-app-secrets.js
 */
'use strict';

const crypto = require('crypto');
const { Client } = require('pg');
const path = require('path');

try {
  require('dotenv').config({ path: path.join(__dirname, '..', '.env'), override: true });
} catch (_) {
  /* dotenv opcional */
}

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';

async function main() {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca)/i.test(DATABASE_URL) ||
    DATABASE_URL.includes('rds.amazonaws.com');
  const client = new Client({
    connectionString: DATABASE_URL,
    ssl: forceSsl ? { rejectUnauthorized: false } : false,
  });

  await client.connect();

  const { rows } = await client.query(
    `SELECT app_id, name
     FROM app_registry
     WHERE webhook_secret IS NULL
        OR btrim(webhook_secret) = ''
     ORDER BY app_id`
  );

  if (rows.length === 0) {
    console.log('Nenhum app_registry sem webhook_secret. Nada a fazer.');
    await client.end();
    return;
  }

  console.log(`Encontrados ${rows.length} app(s) sem secret. Gerando...\n`);

  for (const row of rows) {
    const secret = crypto.randomBytes(32).toString('hex');
    await client.query(
      `UPDATE app_registry
       SET webhook_secret = $1
       WHERE app_id = $2
         AND (webhook_secret IS NULL OR btrim(webhook_secret) = '')`,
      [secret, row.app_id]
    );

    console.log('────────────────────────────────────────');
    console.log(`app_id:         ${row.app_id}`);
    console.log(`name:           ${row.name}`);
    console.log(`webhook_secret: ${secret}`);
    console.log('COPIE ESTE SECRET PARA O ARQUIVO .env DO APLICATIVO CORRESPONDENTE');
    console.log('────────────────────────────────────────\n');
  }

  await client.end();
  console.log('Concluído.');
}

main().catch(async (err) => {
  console.error('Erro ao gerar secrets:', err.message);
  process.exit(1);
});
