/**
 * Publica o CMS site config do Postgres local/prod para S3 (snapshot durável).
 *
 * Uso:
 *   cd leaction-platform
 *   # com CMS_S3_BUCKET no .env do gateway
 *   node scripts/push-cms-site-to-s3.js
 *   node scripts/push-cms-site-to-s3.js --key=inove4us
 *
 * Não faz deploy. Só garante que o conteúdo atual do DB exista no S3
 * para sobreviver a wipe/redeploy do banco.
 */
'use strict';

const path = require('path');
const { Client } = require('pg');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
require('dotenv').config({
  path: path.join(__dirname, '..', 'services', 'gateway-api', '.env'),
  override: true,
});

const cmsS3 = require('../services/gateway-api/lib/cms-s3-storage');

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5434/leaction_hub';

function parseKeyArg() {
  const arg = process.argv.find((a) => a.startsWith('--key='));
  if (!arg) return null;
  return arg.slice('--key='.length).trim().toLowerCase() || null;
}

async function main() {
  if (!cmsS3.isCmsS3Enabled()) {
    console.error('Defina CMS_S3_BUCKET (e opcionalmente CMS_S3_PREFIX / CMS_S3_REGION).');
    process.exit(1);
  }

  const onlyKey = parseKeyArg();
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  try {
    const q = onlyKey
      ? {
          text: `SELECT config_key, landing_page_data, instructions_data, updated_at
                 FROM cms_site_config WHERE config_key = $1`,
          values: [onlyKey],
        }
      : {
          text: `SELECT config_key, landing_page_data, instructions_data, updated_at
                 FROM cms_site_config ORDER BY config_key`,
          values: [],
        };
    const { rows } = await client.query(q.text, q.values);
    if (!rows.length) {
      console.log('Nenhuma linha em cms_site_config.');
      return;
    }
    for (const row of rows) {
      const saved = await cmsS3.putCmsSiteConfig(row.config_key, {
        landing_page_data: row.landing_page_data,
        instructions_data: row.instructions_data,
      });
      console.log(
        `OK ${row.config_key} → s3://${process.env.CMS_S3_BUCKET}/${saved.objectKey}`
      );
    }
  } finally {
    await client.end();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
