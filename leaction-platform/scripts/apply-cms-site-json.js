/**
 * Aplica um JSON de Micro-CMS (landing + instructions) no Postgres + S3.
 *
 * Uso (no EC2 ou local, com .env do Hub):
 *   node scripts/apply-cms-site-json.js --file=/tmp/cms-inove4us.json
 *   node scripts/apply-cms-site-json.js --file=./export.json --skip-s3
 *
 * Formato do arquivo:
 *   { "config_key": "inove4us", "landing_page_data": {...}, "instructions_data": "..." }
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

require('dotenv').config({ path: path.join(__dirname, '..', '.env'), override: false });
require('dotenv').config({
  path: path.join(__dirname, '..', 'services', 'gateway-api', '.env'),
  override: false,
});

const {
  defaultsForConfigKey,
  normalizeCmsLanding,
} = require('../services/gateway-api/domain/cms-landing');
const { stripBlogColumnsFromLanding } = require('../services/gateway-api/domain/cms-blog-sync');
const cmsS3 = require('../services/gateway-api/lib/cms-s3-storage');

const ALLOWED = new Set(['default', 'inove4us', 'inove4us-school', 'panne-demo', 'panne']);

function argValue(name) {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3).trim() : null;
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`);
}

function pgClientConfig(databaseUrl) {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca|no-verify|prefer)/i.test(databaseUrl) ||
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

function pgClient() {
  const databaseUrl =
    process.env.DATABASE_URL ||
    'postgresql://admin:password123@localhost:5433/leaction_hub';
  return new Client(pgClientConfig(databaseUrl));
}

async function main() {
  const file = argValue('file');
  if (!file) {
    console.error('Uso: node scripts/apply-cms-site-json.js --file=path.json [--skip-s3]');
    process.exit(1);
  }
  const abs = path.resolve(file);
  if (!fs.existsSync(abs)) {
    console.error(`Arquivo não encontrado: ${abs}`);
    process.exit(1);
  }

  const payload = JSON.parse(fs.readFileSync(abs, 'utf8'));
  const configKey = String(payload.config_key || argValue('key') || '')
    .trim()
    .toLowerCase();
  if (!ALLOWED.has(configKey)) {
    console.error(`config_key inválido: ${configKey} (use: ${[...ALLOWED].join(', ')})`);
    process.exit(1);
  }

  const { landing: defaultLanding } = defaultsForConfigKey(configKey);
  let landing = normalizeCmsLanding(payload.landing_page_data || {}, defaultLanding);
  if (configKey === 'default') {
    landing = stripBlogColumnsFromLanding(landing);
  }
  const instructions =
    payload.instructions_data == null ? null : String(payload.instructions_data);

  const client = pgClient();
  await client.connect();
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS cms_site_config (
        id_cms SERIAL PRIMARY KEY,
        config_key VARCHAR(50) NOT NULL DEFAULT 'default',
        landing_page_data JSONB NOT NULL DEFAULT '{}'::jsonb,
        instructions_data TEXT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_cms_site_config_key UNIQUE (config_key)
      )
    `);
    await client.query(
      `INSERT INTO cms_site_config (config_key, landing_page_data, instructions_data, updated_at)
       VALUES ($1, $2::jsonb, $3, CURRENT_TIMESTAMP)
       ON CONFLICT (config_key) DO UPDATE
         SET landing_page_data = EXCLUDED.landing_page_data,
             instructions_data = EXCLUDED.instructions_data,
             updated_at = CURRENT_TIMESTAMP`,
      [configKey, JSON.stringify(landing), instructions]
    );
    console.log(`OK Postgres cms_site_config config_key=${configKey}`);
  } finally {
    await client.end();
  }

  if (!hasFlag('skip-s3') && cmsS3.isCmsS3Enabled()) {
    try {
      const saved = await cmsS3.putCmsSiteConfig(configKey, {
        landing_page_data: landing,
        instructions_data: instructions,
      });
      console.log(`OK S3 s3://${process.env.CMS_S3_BUCKET}/${saved.objectKey}`);
    } catch (err) {
      console.error(`WARN S3 falhou (Postgres já aplicado): ${err.message}`);
      process.exitCode = 2;
    }
  } else if (!cmsS3.isCmsS3Enabled()) {
    console.log('S3 skip (CMS_S3_BUCKET ausente)');
  } else {
    console.log('S3 skip (--skip-s3)');
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
