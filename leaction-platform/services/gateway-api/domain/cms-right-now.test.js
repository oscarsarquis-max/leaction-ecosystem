'use strict';

/**
 * BLOG-022 — patch duas vezes, reação idempotente, voto 409, enquete fechada 410,
 * chave obrigatória e status fora do GET público.
 *
 * node --test domain/cms-right-now.test.js
 */
const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const express = require('express');
const { Client, Pool } = require('pg');
const { registerCmsPostsRoutes } = require('./cms-posts');

process.env.LEPAIN_CMS_KEY = 'blog-022-test';
process.env.HUB_ADMIN_API_KEY = process.env.HUB_ADMIN_API_KEY || 'cms-blog-003-test';

const PATCH = fs.readFileSync(
  path.join(__dirname, '../../../shared/database/patch_cms_right_now_v2.sql'),
  'utf8'
);
const VISITANTE = 'a'.repeat(64);
const LOCAL_URL =
  process.env.CMS_PATCH_TEST_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';

const BOOTSTRAP = `
CREATE TABLE cms_posts (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) NOT NULL UNIQUE,
    titulo VARCHAR(255) NOT NULL,
    resumo TEXT NULL,
    conteudo_html TEXT NULL,
    imagem_capa TEXT NULL,
    sistema_destino VARCHAR(50) NOT NULL DEFAULT 'todos',
    status VARCHAR(20) NOT NULL DEFAULT 'rascunho',
    publicado_em TIMESTAMPTZ NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    secao VARCHAR(20),
    idioma VARCHAR(2),
    grupo_id INTEGER,
    sentidos TEXT[],
    resumo_instagram TEXT,
    right_now_tipo VARCHAR(20),
    data_evento DATE,
    valido_ate DATE,
    instagram_url TEXT,
    atualizado_em TIMESTAMPTZ,
    CONSTRAINT chk_cms_posts_status CHECK (status IN ('rascunho', 'publicado')),
    CONSTRAINT chk_cms_posts_right_now_tipo CHECK (
        right_now_tipo IS NULL OR right_now_tipo IN ('promocao', 'evento', 'noticia')
    )
);
INSERT INTO cms_posts (slug, titulo, sistema_destino, status)
VALUES ('ja-existia', 'Post antigo', 'paneldx', 'publicado');
`;

let scratch;
let pool;
let server;
let base;

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
  const container = `cms-rn-v2-${process.pid}`;
  const port = 56100 + (process.pid % 800);
  const run = spawnSync(
    'docker',
    [
      'run', '-d', '--rm', '--name', container,
      '-e', 'POSTGRES_PASSWORD=cms_test',
      '-e', 'POSTGRES_DB=cms_patch',
      '-p', `${port}:5432`,
      'postgres:16-alpine',
    ],
    { encoding: 'utf8' }
  );
  if (run.status !== 0) throw new Error(run.stderr || 'docker run falhou');
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

async function call(method, path, { body, key = process.env.LEPAIN_CMS_KEY, admin = false } = {}) {
  const headers = { 'content-type': 'application/json' };
  if (admin) headers['x-admin-api-key'] = process.env.HUB_ADMIN_API_KEY;
  if (key) headers['x-lepain-key'] = key;
  const res = await fetch(`${base}${path}`, {
    method,
    headers,
    body: body == null ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  return { status: res.status, data };
}

before(async () => {
  if (await canConnect(LOCAL_URL)) {
    const admin = new Client({ connectionString: LOCAL_URL });
    await admin.connect();
    const dbName = `cms_rn_v2_${process.pid}`;
    await admin.query(`DROP DATABASE IF EXISTS ${dbName}`);
    await admin.query(`CREATE DATABASE ${dbName}`);
    await admin.end();
    const url = new URL(LOCAL_URL);
    url.pathname = `/${dbName}`;
    scratch = { kind: 'local', adminUrl: url.toString(), dbName };
  } else {
    scratch = await startDocker();
  }
  const client = new Client({ connectionString: scratch.adminUrl });
  await client.connect();
  await client.query(BOOTSTRAP);
  await client.query(PATCH);
  await client.query(PATCH);
  await client.end();

  pool = new Pool({ connectionString: scratch.adminUrl });
  const app = express();
  app.use(express.json());
  registerCmsPostsRoutes(app, pool, { jwtSecret: 'test-secret' });
  server = await new Promise((resolve) => {
    const httpServer = http.createServer(app);
    httpServer.listen(0, '127.0.0.1', () => resolve(httpServer));
  });
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) {
    await new Promise((resolve) => server.close(resolve));
  }
  if (pool) await pool.end();
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

describe('patch_cms_right_now_v2.sql', () => {
  it('roda duas vezes e a linha antiga fica manual, sem link', async () => {
    const row = await pool.query(
      `SELECT status, origem, link_url, fonte FROM cms_posts WHERE slug = 'ja-existia'`
    );
    assert.equal(row.rows[0].status, 'publicado');
    assert.equal(row.rows[0].origem, 'manual');
    assert.equal(row.rows[0].link_url, null);
    assert.equal(row.rows[0].fonte, null);
    const tables = await pool.query(
      `SELECT table_name FROM information_schema.tables
        WHERE table_name IN ('cms_reacoes', 'cms_enquetes', 'cms_votos')
        ORDER BY table_name`
    );
    assert.deepEqual(
      tables.rows.map((item) => item.table_name),
      ['cms_enquetes', 'cms_reacoes', 'cms_votos']
    );
  });
});

describe('API Right Now v2', () => {
  it('deixa sugestao e descartado fora do GET público', async () => {
    await pool.query(
      `INSERT INTO cms_posts (slug, titulo, sistema_destino, status, secao, idioma, right_now_tipo)
       VALUES
         ('no-ar', 'No ar', 'lepain', 'publicado', 'right_now', 'pt', 'curiosidade'),
         ('ideia', 'Ideia', 'lepain', 'sugestao', 'right_now', 'pt', 'noticia'),
         ('fora', 'Fora', 'lepain', 'descartado', 'right_now', 'pt', 'parceiro')`
    );
    const listed = await call('GET', '/api/cms/posts?sistema_destino=lepain&limit=20');
    assert.equal(listed.status, 200);
    const slugs = listed.data.posts.map((post) => post.slug);
    assert.deepEqual(slugs, ['no-ar']);
    assert.equal(listed.data.posts[0].quero_count, 0);
    assert.equal(listed.data.posts[0].origem, 'manual');
    assert.equal(listed.data.count, 1);
  });

  it('exige a chave e não soma a mesma reação duas vezes', async () => {
    const post = await pool.query(`SELECT id FROM cms_posts WHERE slug = 'no-ar'`);
    const id = post.rows[0].id;
    const denied = await call('POST', `/api/cms/posts/${id}/quero`, {
      key: '',
      body: { visitante: VISITANTE },
    });
    assert.equal(denied.status, 401);

    const first = await call('POST', `/api/cms/posts/${id}/quero`, {
      body: { visitante: VISITANTE },
    });
    assert.equal(first.status, 200);
    assert.equal(first.data.novo, true);
    assert.equal(first.data.count, 1);

    const second = await call('POST', `/api/cms/posts/${id}/quero`, {
      body: { visitante: VISITANTE },
    });
    assert.equal(second.status, 200);
    assert.equal(second.data.novo, false);
    assert.equal(second.data.count, 1);
  });

  it('recusa o segundo voto com 409 e a enquete fechada com 410', async () => {
    const open = await pool.query(
      `INSERT INTO cms_enquetes (pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status)
       VALUES ('Qual?', 'Which?', $1::jsonb, now() - interval '1 hour', now() + interval '1 day', 'publicada')
       RETURNING id`,
      [JSON.stringify([{ id: 'a', pt: 'Um', en: 'One' }, { id: 'b', pt: 'Dois', en: 'Two' }])]
    );
    const id = open.rows[0].id;
    const vote = await call('POST', `/api/cms/enquetes/${id}/votos`, {
      body: { opcao_id: 'a', visitante: VISITANTE },
    });
    assert.equal(vote.status, 200);
    assert.equal(vote.data.total, 1);
    assert.deepEqual(vote.data.resultado, [
      { id: 'a', pct: 100 },
      { id: 'b', pct: 0 },
    ]);
    const again = await call('POST', `/api/cms/enquetes/${id}/votos`, {
      body: { opcao_id: 'b', visitante: VISITANTE },
    });
    assert.equal(again.status, 409);

    const current = await call('GET', `/api/cms/enquetes/atual?visitante=${VISITANTE}`);
    assert.equal(current.status, 200);
    assert.equal(current.data.votou, true);
    assert.equal(current.data.total, 1);

    const closed = await pool.query(
      `INSERT INTO cms_enquetes (pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status)
       VALUES ('Acabou?', 'Over?', $1::jsonb, now() - interval '2 days', now() - interval '1 hour', 'rascunho')
       RETURNING id`,
      [JSON.stringify([{ id: 'a', pt: 'Sim', en: 'Yes' }, { id: 'b', pt: 'Não', en: 'No' }])]
    );
    await pool.query(`UPDATE cms_enquetes SET status = 'publicada' WHERE id = $1`, [
      closed.rows[0].id,
    ]);
    const late = await call('POST', `/api/cms/enquetes/${closed.rows[0].id}/votos`, {
      body: { opcao_id: 'a', visitante: VISITANTE },
    });
    assert.equal(late.status, 410);
  });
});
