'use strict';

/**
 * CMS LePain — validação, filtros públicos e recusa fora do destino.
 * node --test services/gateway-api/domain/cms-posts.test.js
 */
const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const express = require('express');
const {
  registerCmsPostsRoutes,
  buildPublicPostsQuery,
  validatePayload,
  parseBody,
} = require('./cms-posts');

process.env.HUB_ADMIN_API_KEY = process.env.HUB_ADMIN_API_KEY || 'cms-blog-003-test';

function listen(app) {
  return new Promise((resolve) => {
    const server = http.createServer(app);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

function start(pool) {
  const app = express();
  app.use(express.json());
  registerCmsPostsRoutes(app, pool, { jwtSecret: 'test-secret' });
  return listen(app);
}

async function call(base, method, path, body) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      'x-admin-api-key': process.env.HUB_ADMIN_API_KEY,
    },
    body: body == null ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data, headers: res.headers };
}

function poolOf(handler) {
  const calls = [];
  return {
    calls,
    query: async (sql, params) => {
      const text = String(sql).replace(/\s+/g, ' ').trim();
      calls.push({ sql: text, params });
      return handler(text, params, calls);
    },
  };
}

const lepainBase = {
  titulo: 'Crosta',
  slug: 'crosta',
  sistema_destino: 'lepain',
  status: 'rascunho',
  secao: 'insights',
  idioma: 'pt',
  sentidos: ['olhar', 'aroma'],
};

describe('consulta pública paneldx', () => {
  it('mantém o filtro todos e não aplica secao nem idioma', () => {
    const query = buildPublicPostsQuery({
      sistema: 'paneldx',
      secao: null,
      idioma: null,
      limit: 20,
      offset: 0,
    });
    assert.match(query.sql, /status = 'publicado'/);
    assert.match(
      query.sql,
      /sistema_destino = \$1 OR sistema_destino = 'todos'/
    );
    assert.doesNotMatch(query.sql, /AND secao =/);
    assert.doesNotMatch(query.sql, /AND idioma =/);
    assert.deepEqual(query.params, ['paneldx', 20, 0]);
    assert.match(query.sql, /ORDER BY publicado_em DESC NULLS LAST, criado_em DESC/);
  });
});

describe('validação LePain', () => {
  it('exige secao, idioma e sentidos', () => {
    const semSecao = parseBody({ ...lepainBase, secao: '' });
    assert.match(validatePayload(semSecao, { raw: { ...lepainBase, secao: '' } }), /secao/);
    const semIdioma = parseBody({ ...lepainBase, idioma: '' });
    assert.match(validatePayload(semIdioma, { raw: { ...lepainBase, idioma: '' } }), /idioma/);
    const semSentidos = parseBody({ ...lepainBase, sentidos: [] });
    assert.match(
      validatePayload(semSentidos, { raw: { ...lepainBase, sentidos: [] } }),
      /sentidos/
    );
  });

  it('recusa campos novos em paneldx', () => {
    const payload = parseBody({
      titulo: 'Painel',
      slug: 'painel',
      sistema_destino: 'paneldx',
      status: 'publicado',
      secao: 'insights',
    });
    assert.match(
      validatePayload(payload, { raw: { secao: 'insights' } }),
      /não se aplicam/
    );
    const limpo = parseBody({
      titulo: 'Painel',
      slug: 'painel',
      sistema_destino: 'paneldx',
      status: 'publicado',
    });
    assert.equal(validatePayload(limpo, { raw: { titulo: 'Painel' } }), null);
  });
});

describe('rotas CMS', () => {
  /** @type {import('node:http').Server[]} */
  const servers = [];

  after(async () => {
    await Promise.all(
      servers.map(
        (server) =>
          new Promise((resolve, reject) => {
            server.close((err) => (err ? reject(err) : resolve()));
          })
      )
    );
  });

  it('GET paneldx devolve a mesma cláusula todos', async () => {
    const pool = poolOf(async () => ({ rows: [] }));
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const res = await call(base, 'GET', '/api/cms/posts?sistema_destino=paneldx');
    assert.equal(res.status, 200);
    assert.equal(res.headers.get('cache-control'), 'public, max-age=60');
    assert.equal(res.data.count, 0);
    const sql = pool.calls[0].sql;
    assert.match(sql, /sistema_destino = \$1 OR sistema_destino = 'todos'/);
    assert.doesNotMatch(sql, /AND secao =/);
    assert.doesNotMatch(sql, /AND idioma =/);
    assert.deepEqual(pool.calls[0].params[0], 'paneldx');
    assert.equal(pool.calls[0].params.at(-1), 0);
  });

  it('filtra secao, idioma e offset e lê por slug publicado', async () => {
    const row = {
      id: 4,
      slug: 'crosta',
      titulo: 'Crosta',
      resumo: 'curto',
      conteudo_html: '<p>oi</p>',
      imagem_capa: null,
      sistema_destino: 'lepain',
      status: 'publicado',
      publicado_em: '2026-11-08T12:00:00.000Z',
      criado_em: '2026-11-08T12:00:00.000Z',
      secao: 'insights',
      idioma: 'pt',
      grupo_id: 4,
      sentidos: ['sabor'],
      resumo_instagram: 'card',
      right_now_tipo: null,
      data_evento: null,
      valido_ate: null,
      atualizado_em: null,
    };
    const pool = poolOf(async (sql) => {
      if (sql.includes('WHERE slug =')) return { rows: [row] };
      return { rows: [row] };
    });
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const list = await call(
      base,
      'GET',
      '/api/cms/posts?sistema_destino=lepain&secao=insights&idioma=pt&offset=5&limit=10'
    );
    assert.equal(list.status, 200);
    assert.equal(list.headers.get('cache-control'), 'public, max-age=60');
    assert.deepEqual(pool.calls[0].params, ['lepain', 'insights', 'pt', 10, 5]);
    assert.equal(list.data.posts[0].secao, 'insights');
    assert.equal(list.data.posts[0].idioma, 'pt');
    assert.deepEqual(list.data.posts[0].sentidos, ['sabor']);

    const one = await call(base, 'GET', '/api/cms/posts/crosta');
    assert.equal(one.status, 200);
    assert.equal(one.data.post.slug, 'crosta');
    assert.match(pool.calls[1].sql, /status = 'publicado'/);
    assert.equal(one.headers.get('cache-control'), 'public, max-age=60');
  });

  it('recusa LePain incompleto, segunda EN e campo novo em paneldx', async () => {
    const pool = poolOf(async (sql) => {
      if (sql.includes("idioma = 'pt'")) return { rows: [{ id: 7 }] };
      if (sql.includes("idioma = 'en'")) return { rows: [{ id: 8 }] };
      return { rows: [] };
    });
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;

    const semSecao = await call(base, 'POST', '/api/cms/posts', {
      ...lepainBase,
      secao: undefined,
    });
    assert.equal(semSecao.status, 400);
    assert.match(semSecao.data.error, /secao/);

    const semIdioma = await call(base, 'POST', '/api/cms/posts', {
      ...lepainBase,
      idioma: '',
    });
    assert.equal(semIdioma.status, 400);
    assert.match(semIdioma.data.error, /idioma/);

    const semSentidos = await call(base, 'POST', '/api/cms/posts', {
      ...lepainBase,
      sentidos: [],
    });
    assert.equal(semSentidos.status, 400);
    assert.match(semSentidos.data.error, /sentidos/);

    const segundaEn = await call(base, 'POST', '/api/cms/posts', {
      titulo: 'Crust',
      slug: 'crust',
      sistema_destino: 'lepain',
      status: 'rascunho',
      secao: 'insights',
      idioma: 'en',
      grupo_id: 7,
      sentidos: ['olhar'],
    });
    assert.equal(segundaEn.status, 409);
    assert.match(segundaEn.data.error, /versão EN/);
    assert.equal(
      pool.calls.some((call) => call.sql.startsWith('INSERT')),
      false
    );

    const painel = await call(base, 'POST', '/api/cms/posts', {
      titulo: 'Painel',
      slug: 'painel',
      sistema_destino: 'paneldx',
      status: 'rascunho',
      secao: 'insights',
    });
    assert.equal(painel.status, 400);
    assert.match(painel.data.error, /não se aplicam/);
  });

  it('grava grupo_id do PT depois do insert e atualizado_em no PUT', async () => {
    const pool = poolOf(async (sql, params) => {
      if (sql.startsWith('INSERT')) {
        return {
          rows: [
            {
              id: 15,
              slug: params[0],
              titulo: params[1],
              sistema_destino: params[5],
              status: params[6],
              secao: params[8],
              idioma: params[9],
              grupo_id: params[10],
              sentidos: params[11],
            },
          ],
        };
      }
      if (sql.startsWith('UPDATE') && sql.includes('grupo_id = id')) {
        return {
          rows: [
            {
              id: 15,
              slug: 'crosta',
              titulo: 'Crosta',
              sistema_destino: 'lepain',
              status: 'rascunho',
              secao: 'insights',
              idioma: 'pt',
              grupo_id: 15,
              sentidos: ['olhar', 'aroma'],
            },
          ],
        };
      }
      if (sql.startsWith('SELECT')) {
        return {
          rows: [
            {
              id: 3,
              slug: 'painel',
              titulo: 'Painel',
              resumo: null,
              conteudo_html: null,
              imagem_capa: null,
              sistema_destino: 'paneldx',
              status: 'rascunho',
              publicado_em: null,
              criado_em: '2026-01-01T00:00:00.000Z',
            },
          ],
        };
      }
      if (sql.includes('atualizado_em = now()')) {
        return {
          rows: [
            {
              id: 3,
              slug: 'painel',
              titulo: 'Painel novo',
              sistema_destino: 'paneldx',
              status: 'rascunho',
              secao: null,
              idioma: null,
              grupo_id: null,
              sentidos: null,
              atualizado_em: '2026-11-08T15:00:00.000Z',
            },
          ],
        };
      }
      return { rows: [] };
    });
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const created = await call(base, 'POST', '/api/cms/posts', lepainBase);
    assert.equal(created.status, 201);
    assert.equal(created.data.post.grupo_id, 15);
    assert.equal(
      pool.calls.some((item) => item.sql.includes('grupo_id = id')),
      true
    );

    const updated = await call(base, 'PUT', '/api/cms/posts/3', {
      titulo: 'Painel novo',
    });
    assert.equal(updated.status, 200);
    const update = pool.calls.find((item) => item.sql.includes('atualizado_em = now()'));
    assert.ok(update);
    assert.equal(update.params[5], 'paneldx');
    assert.equal(update.params[8], null);
  });
});

describe('right now', () => {
  it('exige o tipo', () => {
    const payload = parseBody({
      ...lepainBase,
      secao: 'right_now',
      right_now_tipo: '',
    });
    assert.match(validatePayload(payload, { raw: payload }), /right_now_tipo/);
  });
});

function publishedRow(overrides = {}) {
  return {
    id: 1,
    slug: 'levain',
    titulo: 'Levain',
    resumo: 'cultura',
    conteudo_html: '<p>massa</p>',
    imagem_capa: null,
    sistema_destino: 'lepain',
    status: 'publicado',
    publicado_em: '2026-11-01T12:00:00.000Z',
    criado_em: '2026-11-01T12:00:00.000Z',
    secao: 'insights',
    idioma: 'pt',
    grupo_id: 1,
    sentidos: ['aroma', 'sabor'],
    resumo_instagram: 'card',
    right_now_tipo: null,
    data_evento: null,
    valido_ate: null,
    atualizado_em: '2026-11-01T12:00:00.000Z',
    ...overrides,
  };
}

function memoryPool(seed) {
  const rows = seed.map((row) => ({ ...row }));
  return poolOf(async (sql, params) => {
    if (sql.startsWith('SELECT') && sql.includes('WHERE id =')) {
      return { rows: rows.filter((row) => row.id === params[0]) };
    }
    if (sql.startsWith('SELECT') && sql.includes('WHERE slug =')) {
      return {
        rows: rows.filter((row) => row.slug === params[0] && row.status === 'publicado'),
      };
    }
    if (sql.startsWith('SELECT') && sql.includes("status = 'publicado'")) {
      return {
        rows: rows.filter(
          (row) =>
            row.status === 'publicado' &&
            (row.sistema_destino === params[0] || row.sistema_destino === 'todos')
        ),
      };
    }
    if (sql.includes('atualizado_em = now()')) {
      const id = params.at(-1);
      const row = rows.find((item) => item.id === id);
      if (!row) return { rows: [] };
      row.slug = params[0];
      row.titulo = params[1];
      row.resumo = params[2];
      row.conteudo_html = params[3];
      row.imagem_capa = params[4];
      row.sistema_destino = params[5];
      row.status = params[6];
      row.publicado_em = params[7];
      row.secao = params[8];
      row.idioma = params[9];
      row.grupo_id = params[10];
      row.sentidos = params[11];
      row.resumo_instagram = params[12];
      row.right_now_tipo = params[13];
      row.data_evento = params[14];
      row.valido_ate = params[15];
      row.instagram_url = params[16];
      row.atualizado_em = '2026-11-08T18:00:00.000Z';
      return { rows: [{ ...row }] };
    }
    if (sql.startsWith('DELETE')) {
      const id = params[0];
      const pair = params[1] === true;
      const gone = rows.filter(
        (row) => row.id === id || (pair && row.idioma === 'en' && row.grupo_id === id)
      );
      for (const row of gone) rows.splice(rows.indexOf(row), 1);
      return { rows: gone.map((row) => ({ id: row.id })) };
    }
    if (sql.includes("idioma = 'pt'")) return { rows: [{ id: 1 }] };
    if (sql.includes("idioma = 'en'")) return { rows: [] };
    return { rows: [] };
  });
}

describe('editar, despublicar e excluir', () => {
  /** @type {import('node:http').Server[]} */
  const servers = [];

  after(async () => {
    await Promise.all(
      servers.map(
        (server) =>
          new Promise((resolve, reject) => {
            server.close((err) => (err ? reject(err) : resolve()));
          })
      )
    );
  });

  it('GET admin por id devolve rascunho', async () => {
    const pool = memoryPool([
      publishedRow({ id: 9, slug: 'no-forno', status: 'rascunho', publicado_em: null }),
    ]);
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const admin = await call(base, 'GET', '/api/cms/posts/admin/9');
    assert.equal(admin.status, 200);
    assert.equal(admin.data.post.status, 'rascunho');
    assert.equal(admin.data.post.slug, 'no-forno');
    assert.equal(
      pool.calls.some((item) => item.sql.includes("status = 'publicado'") && item.sql.includes('WHERE id =')),
      false
    );
    const pub = await call(base, 'GET', '/api/cms/posts/no-forno');
    assert.equal(pub.status, 404);
  });

  it('PUT grava campos LePain e a validação de antes continua', async () => {
    const pool = memoryPool([publishedRow()]);
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const ok = await call(base, 'PUT', '/api/cms/posts/1', {
      titulo: 'Levain',
      slug: 'levain',
      resumo: 'cultura.',
      sistema_destino: 'lepain',
      status: 'publicado',
      secao: 'insights',
      idioma: 'pt',
      sentidos: ['aroma', 'toque'],
      resumo_instagram: 'legenda',
    });
    assert.equal(ok.status, 200);
    assert.deepEqual(ok.data.post.sentidos, ['aroma', 'toque']);
    assert.equal(ok.data.post.resumo_instagram, 'legenda');
    assert.equal(ok.data.post.secao, 'insights');
    const update = pool.calls.find((item) => item.sql.includes('atualizado_em = now()'));
    assert.equal(update.params[5], 'lepain');
    assert.deepEqual(update.params[11], ['aroma', 'toque']);

    const before = pool.calls.length;
    const bad = await call(base, 'PUT', '/api/cms/posts/1', {
      titulo: 'Levain',
      slug: 'levain',
      sistema_destino: 'lepain',
      status: 'publicado',
      secao: 'insights',
      idioma: 'pt',
      sentidos: [],
    });
    assert.equal(bad.status, 400);
    assert.match(bad.data.error, /sentidos/);
    assert.equal(
      pool.calls.slice(before).some((item) => item.sql.includes('atualizado_em = now()')),
      false
    );

    const painel = memoryPool([
      publishedRow({
        id: 4,
        slug: 'painel',
        titulo: 'Painel',
        sistema_destino: 'paneldx',
        secao: null,
        idioma: null,
        grupo_id: null,
        sentidos: null,
        resumo_instagram: null,
      }),
    ]);
    const painelServer = await start(painel);
    servers.push(painelServer);
    const painelBase = `http://127.0.0.1:${painelServer.address().port}`;
    const refused = await call(painelBase, 'PUT', '/api/cms/posts/4', {
      titulo: 'Painel',
      secao: 'insights',
    });
    assert.equal(refused.status, 400);
    assert.match(refused.data.error, /não se aplicam/);
  });

  it('despublicar some do GET público', async () => {
    const pool = memoryPool([publishedRow()]);
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const before = await call(base, 'GET', '/api/cms/posts/levain');
    assert.equal(before.status, 200);
    const hidden = await call(base, 'PUT', '/api/cms/posts/1', { status: 'rascunho' });
    assert.equal(hidden.status, 200);
    assert.equal(hidden.data.post.status, 'rascunho');
    const after = await call(base, 'GET', '/api/cms/posts/levain');
    assert.equal(after.status, 404);
    const list = await call(base, 'GET', '/api/cms/posts?sistema_destino=lepain');
    assert.equal(list.status, 200);
    assert.equal(list.data.count, 0);
    const still = await call(base, 'GET', '/api/cms/posts/admin/1');
    assert.equal(still.status, 200);
    assert.equal(still.data.post.status, 'rascunho');
  });

  it('excluir uma PT com EN apaga as duas e deixa os outros destinos', async () => {
    const pool = memoryPool([
      publishedRow(),
      publishedRow({
        id: 2,
        slug: 'levain-en',
        titulo: 'Levain EN',
        idioma: 'en',
        grupo_id: 1,
      }),
      publishedRow({
        id: 4,
        slug: 'painel',
        titulo: 'Painel',
        sistema_destino: 'paneldx',
        idioma: null,
        grupo_id: null,
        sentidos: null,
        secao: null,
      }),
    ]);
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    const removed = await call(base, 'DELETE', '/api/cms/posts/1');
    assert.equal(removed.status, 200);
    assert.deepEqual(removed.data.deleted.sort(), [1, 2]);
    assert.equal((await call(base, 'GET', '/api/cms/posts/admin/1')).status, 404);
    assert.equal((await call(base, 'GET', '/api/cms/posts/admin/2')).status, 404);
    const painel = await call(base, 'GET', '/api/cms/posts/painel');
    assert.equal(painel.status, 200);
    assert.equal(painel.data.post.sistema_destino, 'paneldx');

    const onlyPainel = await call(base, 'DELETE', '/api/cms/posts/4');
    assert.equal(onlyPainel.status, 200);
    assert.deepEqual(onlyPainel.data.deleted, [4]);
    const del = pool.calls.filter((item) => item.sql.startsWith('DELETE'));
    assert.equal(del[1].params[1], false);
  });
});

describe('instagram_url', () => {
  /** @type {import('node:http').Server[]} */
  const servers = [];

  after(async () => {
    await Promise.all(
      servers.map(
        (server) =>
          new Promise((resolve, reject) => {
            server.close((err) => (err ? reject(err) : resolve()));
          })
      )
    );
  });

  it('aceita só no LePain e só no domínio do Instagram', () => {
    const www = parseBody({
      ...lepainBase,
      instagram_url: 'https://www.instagram.com/p/AbC123/',
    });
    assert.equal(www.instagram_url, 'https://www.instagram.com/p/AbC123/');
    assert.equal(validatePayload(www, { raw: www }), null);

    const bare = parseBody({
      ...lepainBase,
      instagram_url: 'https://instagram.com/loja.de.paes/p/AbC123/',
    });
    assert.equal(validatePayload(bare, { raw: bare }), null);

    const empty = parseBody({ ...lepainBase, instagram_url: '  ' });
    assert.equal(empty.instagram_url, null);
    assert.equal(validatePayload(empty, { raw: { ...lepainBase, instagram_url: '' } }), null);

    for (const bad of [
      'http://www.instagram.com/p/abc',
      'https://instagram.com.evil.com/p/abc',
      'https://evil.instagram.com/p/abc',
      'https://www.instagram.com',
      'https://example.com/p/abc',
    ]) {
      const payload = parseBody({ ...lepainBase, instagram_url: bad });
      assert.match(validatePayload(payload, { raw: payload }), /instagram_url/);
    }

    const other = parseBody({
      titulo: 'Painel',
      slug: 'painel',
      sistema_destino: 'paneldx',
      status: 'publicado',
      instagram_url: 'https://www.instagram.com/p/abc/',
    });
    assert.match(
      validatePayload(other, {
        raw: { instagram_url: 'https://www.instagram.com/p/abc/' },
      }),
      /LePain/
    );
  });

  it('recusa o link fora do LePain e devolve o aceito no GET público', async () => {
    const pool = memoryPool([
      publishedRow({ instagram_url: 'https://www.instagram.com/p/ja-salvo/' }),
      publishedRow({
        id: 4,
        slug: 'painel',
        titulo: 'Painel',
        sistema_destino: 'paneldx',
        secao: null,
        idioma: null,
        grupo_id: null,
        sentidos: null,
      }),
    ]);
    const server = await start(pool);
    servers.push(server);
    const base = `http://127.0.0.1:${server.address().port}`;

    const refused = await call(base, 'PUT', '/api/cms/posts/4', {
      instagram_url: 'https://www.instagram.com/p/abc/',
    });
    assert.equal(refused.status, 400);

    const bad = await call(base, 'PUT', '/api/cms/posts/1', {
      instagram_url: 'https://example.com/post',
    });
    assert.equal(bad.status, 400);

    const saved = await call(base, 'PUT', '/api/cms/posts/1', {
      instagram_url: 'https://instagram.com/p/novo/',
    });
    assert.equal(saved.status, 200);
    assert.equal(saved.data.post.instagram_url, 'https://instagram.com/p/novo/');

    const pub = await call(base, 'GET', '/api/cms/posts/levain');
    assert.equal(pub.status, 200);
    assert.equal(pub.data.post.instagram_url, 'https://instagram.com/p/novo/');
  });
});
