/**
 * Micro-CMS — export / compare / pull (conteúdo independente de deploy).
 *
 * Uso:
 *   node scripts/promote-cms-site.js --key=inove4us --export=./tmp/cms-inove4us.json
 *   node scripts/promote-cms-site.js --key=inove4us --compare-only
 *   node scripts/promote-cms-site.js --key=inove4us --pull-from-prod --apply-local
 *
 * Env:
 *   DATABASE_URL          — Hub local (ou destino do --apply-local)
 *   CMS_PROMOTE_PROD_URL  — default https://api.actionhub.com.br
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

// Não sobrescreve DATABASE_URL já exportada pelo wrapper (local :5433).
require('dotenv').config({ path: path.join(__dirname, '..', '.env'), override: false });
require('dotenv').config({
  path: path.join(__dirname, '..', 'services', 'gateway-api', '.env'),
  override: false,
});
if (process.env.CMS_PROMOTE_LOCAL_DATABASE_URL) {
  process.env.DATABASE_URL = process.env.CMS_PROMOTE_LOCAL_DATABASE_URL;
}

const ALLOWED = new Set(['default', 'inove4us', 'inove4us-school', 'panne-demo', 'panne']);

function argValue(name) {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3).trim() : null;
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`);
}

function resolveKey() {
  const key = String(argValue('key') || '')
    .trim()
    .toLowerCase();
  if (!ALLOWED.has(key)) {
    console.error(`--key obrigatório (use: ${[...ALLOWED].join(', ')})`);
    process.exit(1);
  }
  return key;
}

function pgClient(url) {
  const databaseUrl =
    url ||
    process.env.DATABASE_URL ||
    'postgresql://admin:password123@localhost:5433/leaction_hub';
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca|no-verify|prefer)/i.test(databaseUrl) ||
    databaseUrl.includes('rds.amazonaws.com');
  // pg v8+ trata sslmode=require como verify-full; SSL fica no objeto ssl.
  const connectionString = databaseUrl
    .replace(/([?&])sslmode=[^&]*/gi, '$1')
    .replace(/[?&]$/, '')
    .replace(/\?&/, '?');
  return new Client({
    connectionString,
    ssl: forceSsl ? { rejectUnauthorized: false } : false,
  });
}

function prodBase() {
  return (
    process.env.CMS_PROMOTE_PROD_URL ||
    process.env.HUB_GATEWAY_PUBLIC_URL ||
    'https://api.actionhub.com.br'
  ).replace(/\/$/, '');
}

async function fetchProdCms(configKey) {
  const url = `${prodBase()}/api/public/cms?config_key=${encodeURIComponent(configKey)}`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    throw new Error(`Prod CMS HTTP ${res.status} ${url}`);
  }
  const data = await res.json();
  return {
    config_key: data.config_key || configKey,
    landing_page_data: data.landing_page_data || {},
    instructions_data: data.instructions_data ?? null,
    updated_at: data.updated_at || null,
    source: 'prod-api',
  };
}

async function fetchLocalCms(configKey) {
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
    const { rows } = await client.query(
      `SELECT config_key, landing_page_data, instructions_data, updated_at
       FROM cms_site_config WHERE config_key = $1 LIMIT 1`,
      [configKey]
    );
    if (!rows.length) {
      return null;
    }
    const row = rows[0];
    return {
      config_key: row.config_key,
      landing_page_data: row.landing_page_data || {},
      instructions_data: row.instructions_data ?? null,
      updated_at:
        row.updated_at && typeof row.updated_at.toISOString === 'function'
          ? row.updated_at.toISOString()
          : row.updated_at || null,
      source: 'local-db',
    };
  } finally {
    await client.end();
  }
}

function sortKeysDeep(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeysDeep);
  }
  if (value && typeof value === 'object') {
    const out = {};
    for (const k of Object.keys(value).sort()) {
      out[k] = sortKeysDeep(value[k]);
    }
    return out;
  }
  return value;
}

function fingerprint(payload) {
  const body = {
    landing_page_data: sortKeysDeep(payload?.landing_page_data || {}),
    instructions_data: payload?.instructions_data ?? null,
  };
  return JSON.stringify(body);
}

function summarizeLanding(landing) {
  const cols = Array.isArray(landing?.columns) ? landing.columns : [];
  const c0 = cols[0] || landing?.coluna1 || {};
  const c1 = cols[1] || {};
  return {
    columns: cols.length,
    col0_title: c0.title || c0.pill_text || '',
    col0_visible: c0.visible !== false && c0.visibility !== false,
    col1_title: c1.title || '',
    col1_visible: c1.visible !== false,
    hero: landing?.hero?.leaction_title || landing?.hero?.paneldx_title || '',
  };
}

function writeExport(filePath, payload) {
  const abs = path.resolve(filePath);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  const out = {
    config_key: payload.config_key,
    landing_page_data: payload.landing_page_data,
    instructions_data: payload.instructions_data,
    updated_at: payload.updated_at,
    exported_at: new Date().toISOString(),
    schema_version: 1,
  };
  fs.writeFileSync(abs, JSON.stringify(out, null, 2), 'utf8');
  return abs;
}

async function main() {
  const key = resolveKey();
  const compareOnly = hasFlag('compare-only');
  const pullFromProd = hasFlag('pull-from-prod');
  const applyLocal = hasFlag('apply-local');
  const exportPath =
    argValue('export') ||
    (compareOnly || pullFromProd
      ? null
      : path.join(__dirname, '..', '.deploy-secrets', `cms-${key}.json`));

  if (pullFromProd) {
    const prod = await fetchProdCms(key);
    console.log(`Prod ${key} updated_at=${prod.updated_at || '?'}`);
    console.log('Prod summary:', summarizeLanding(prod.landing_page_data));
    const out =
      exportPath ||
      path.join(__dirname, '..', '.deploy-secrets', `cms-${key}-from-prod.json`);
    const abs = writeExport(out, prod);
    console.log(`Exported prod → ${abs}`);
    if (applyLocal) {
      const { spawnSync } = require('child_process');
      const r = spawnSync(
        process.execPath,
        [path.join(__dirname, 'apply-cms-site-json.js'), `--file=${abs}`, '--skip-s3'],
        { stdio: 'inherit', env: process.env }
      );
      process.exit(r.status || 0);
    }
    return;
  }

  const local = await fetchLocalCms(key);
  if (!local) {
    console.error(`Local sem cms_site_config para config_key=${key}`);
    process.exit(1);
  }
  console.log(`Local ${key} updated_at=${local.updated_at || '?'}`);
  console.log('Local summary:', summarizeLanding(local.landing_page_data));

  let prod = null;
  try {
    prod = await fetchProdCms(key);
    console.log(`Prod  ${key} updated_at=${prod.updated_at || '?'}`);
    console.log('Prod summary:', summarizeLanding(prod.landing_page_data));
  } catch (err) {
    console.warn(`WARN não foi possível ler prod: ${err.message}`);
  }

  const same = prod ? fingerprint(local) === fingerprint(prod) : null;
  if (prod) {
    console.log(same ? 'DIFF: local == prod (conteúdo equivalente)' : 'DIFF: local != prod');
  }

  if (exportPath) {
    const abs = writeExport(exportPath, local);
    console.log(`Exported local → ${abs}`);
  }

  if (compareOnly) {
    process.exit(same === false ? 3 : 0);
  }

  if (!exportPath) {
    console.log('Nada a fazer (use --export=... ou o wrapper promote-cms-site.ps1 -Force).');
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
