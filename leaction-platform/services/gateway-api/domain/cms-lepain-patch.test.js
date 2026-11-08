'use strict';

/**
 * O patch LePain roda duas vezes no mesmo banco vazio de cms_posts
 * e não altera a linha que já existia.
 *
 * node --test services/gateway-api/domain/cms-lepain-patch.test.js
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
  path.join(__dirname, '../../../shared/database/patch_cms_lepain.sql'),
  'utf8'
);

const BOOTSTRAP = `
CREATE TABLE cms_posts (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    resumo TEXT NULL,
    conteudo_html TEXT NULL,
    imagem_capa TEXT NULL,
    sistema_destino VARCHAR(50) NOT NULL DEFAULT 'todos',
    status VARCHAR(20) NOT NULL DEFAULT 'rascunho',
    publicado_em TIMESTAMPTZ NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cms_posts_slug UNIQUE (slug),
    CONSTRAINT chk_cms_posts_status CHECK (status IN ('rascunho', 'publicado')),
    CONSTRAINT chk_cms_posts_destino CHECK (
        sistema_destino IN ('hub-publico','actionhub','inove4us','paneldx','todos')
    )
);
INSERT INTO cms_posts (slug, titulo, sistema_destino, status)
VALUES ('ja-existia', 'Post antigo', 'paneldx', 'publicado');
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
  const container = `cms-lepain-patch-${process.pid}`;
  const port = 56000 + (process.pid % 1000);
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
    const dbName = `cms_lepain_patch_${process.pid}`;
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

describe('patch_cms_lepain.sql', () => {
  it('roda duas vezes e preserva a linha antiga', async () => {
    const client = new Client({ connectionString: scratch.adminUrl });
    await client.connect();
    try {
      await client.query(BOOTSTRAP);
      await client.query(PATCH);
      await client.query(PATCH);

      const row = await client.query(
        `SELECT slug, titulo, sistema_destino, status, secao, idioma, grupo_id,
                sentidos, resumo_instagram, right_now_tipo, data_evento, valido_ate,
                atualizado_em
         FROM cms_posts WHERE slug = 'ja-existia'`
      );
      assert.equal(row.rowCount, 1);
      assert.equal(row.rows[0].sistema_destino, 'paneldx');
      assert.equal(row.rows[0].status, 'publicado');
      assert.equal(row.rows[0].titulo, 'Post antigo');
      assert.equal(row.rows[0].secao, null);
      assert.equal(row.rows[0].atualizado_em, null);

      const check = await client.query(
        `SELECT pg_get_constraintdef(oid) AS def
         FROM pg_constraint WHERE conname = 'chk_cms_posts_destino'`
      );
      assert.match(check.rows[0].def, /lepain/);

      await client.query(
        `INSERT INTO cms_posts (slug, titulo, sistema_destino, status, secao, idioma, sentidos)
         VALUES ('ensaio', 'Ensaio', 'lepain', 'rascunho', 'insights', 'pt', ARRAY['olhar'])`
      );
      await client.query(
        `UPDATE cms_posts SET grupo_id = id WHERE slug = 'ensaio'`
      );
      const pt = await client.query(`SELECT id FROM cms_posts WHERE slug = 'ensaio'`);
      await client.query(
        `INSERT INTO cms_posts (slug, titulo, sistema_destino, status, secao, idioma, grupo_id, sentidos)
         VALUES ('essay', 'Essay', 'lepain', 'rascunho', 'insights', 'en', $1, ARRAY['olhar'])`,
        [pt.rows[0].id]
      );
      await assert.rejects(
        () =>
          client.query(
            `INSERT INTO cms_posts (slug, titulo, sistema_destino, status, secao, idioma, grupo_id, sentidos)
             VALUES ('essay-2', 'Essay 2', 'lepain', 'rascunho', 'insights', 'en', $1, ARRAY['som'])`,
            [pt.rows[0].id]
          ),
        (err) => err && err.code === '23505'
      );
    } finally {
      await client.end();
    }
  });
});
