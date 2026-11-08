'use strict';

/**
 * O patch do link do Instagram roda duas vezes e só acrescenta a coluna.
 *
 * node --test services/gateway-api/domain/cms-lepain-instagram-patch.test.js
 *
 * Usa Postgres local (localhost:5433 / leaction_hub) só para abrir
 * um banco descartável. Se ele não estiver no ar, sobe um Postgres
 * temporário no Docker. Não grava em produção.
 */
const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Client } = require('pg');

const PATCH = fs.readFileSync(
  path.join(__dirname, '../../../shared/database/patch_cms_lepain_instagram.sql'),
  'utf8'
);

const BOOTSTRAP = `
CREATE TABLE cms_posts (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    sistema_destino VARCHAR(32) NOT NULL
);
INSERT INTO cms_posts (slug, titulo, sistema_destino)
VALUES ('ja-existia', 'Post antigo', 'paneldx');
`;

const LOCAL_URL =
  process.env.CMS_PATCH_TEST_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';

/** @type {{ kind: 'local' | 'docker', adminUrl: string, dbName: string, container?: string }} */
let scratch;

function canConnect(url) {
  const client = new Client({ connectionString: url, connectionTimeoutMillis: 2000 });
  return client
    .connect()
    .then(async () => {
      await client.end();
      return true;
    })
    .catch(async () => {
      try {
        await client.end();
      } catch {
        /* já fechado */
      }
      return false;
    });
}

async function startDocker() {
  const container = `cms-ig-patch-${process.pid}`;
  const port = 57000 + (process.pid % 1000);
  const run = spawnSync(
    'docker',
    [
      'run',
      '-d',
      '--rm',
      '--name',
      container,
      '-e',
      'POSTGRES_PASSWORD=cms_test',
      '-e',
      'POSTGRES_DB=cms_patch',
      '-p',
      `${port}:5432`,
      'postgres:16-alpine',
    ],
    { encoding: 'utf8' }
  );
  if (run.status !== 0) {
    throw new Error(run.stderr || run.stdout || 'docker run falhou');
  }
  const adminUrl = `postgresql://postgres:cms_test@127.0.0.1:${port}/cms_patch`;
  const deadline = Date.now() + 40000;
  while (Date.now() < deadline) {
    if (await canConnect(adminUrl)) {
      return { kind: 'docker', adminUrl, dbName: 'cms_patch', container };
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  spawnSync('docker', ['rm', '-f', container]);
  throw new Error('Postgres temporário não ficou pronto');
}

before(async () => {
  if (await canConnect(LOCAL_URL)) {
    const admin = new Client({ connectionString: LOCAL_URL });
    await admin.connect();
    const dbName = `cms_ig_patch_${process.pid}`;
    await admin.query(`DROP DATABASE IF EXISTS ${dbName}`);
    await admin.query(`CREATE DATABASE ${dbName}`);
    await admin.end();
    const url = new URL(LOCAL_URL);
    url.pathname = `/${dbName}`;
    scratch = { kind: 'local', adminUrl: url.toString(), dbName };
    return;
  }
  scratch = await startDocker();
});

after(async () => {
  if (!scratch) return;
  if (scratch.kind === 'docker' && scratch.container) {
    spawnSync('docker', ['rm', '-f', scratch.container]);
    return;
  }
  const admin = new Client({ connectionString: LOCAL_URL });
  await admin.connect();
  await admin.query(
    `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()`,
    [scratch.dbName]
  );
  await admin.query(`DROP DATABASE IF EXISTS ${scratch.dbName}`);
  await admin.end();
});

describe('patch_cms_lepain_instagram.sql', () => {
  it('roda duas vezes e deixa a linha antiga sem link', async () => {
    const client = new Client({ connectionString: scratch.adminUrl });
    await client.connect();
    try {
      await client.query(BOOTSTRAP);
      await client.query(PATCH);
      await client.query(PATCH);

      const column = await client.query(
        `SELECT data_type, is_nullable
           FROM information_schema.columns
          WHERE table_name = 'cms_posts' AND column_name = 'instagram_url'`
      );
      assert.equal(column.rows.length, 1);
      assert.equal(column.rows[0].data_type, 'text');
      assert.equal(column.rows[0].is_nullable, 'YES');

      const row = await client.query(
        `SELECT slug, titulo, sistema_destino, instagram_url FROM cms_posts`
      );
      assert.equal(row.rows.length, 1);
      assert.equal(row.rows[0].slug, 'ja-existia');
      assert.equal(row.rows[0].titulo, 'Post antigo');
      assert.equal(row.rows[0].sistema_destino, 'paneldx');
      assert.equal(row.rows[0].instagram_url, null);
    } finally {
      await client.end();
    }
  });
});
