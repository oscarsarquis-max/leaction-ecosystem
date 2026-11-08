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
