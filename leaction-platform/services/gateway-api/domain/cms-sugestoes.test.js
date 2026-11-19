'use strict';

/**
 * BLOG-024 — validação, dedupe, expiração, publicar PT+EN, GET público.
 * node --test domain/cms-sugestoes.test.js
 */
const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const express = require('express');
const {
  validateSuggestionDraft,
  numbersInResumoAppearInArticle,
  dedupeCandidates,
  normalizeUrl,
  titlesSimilar,
} = require('./cms-sugestoes-lib');
const {
  expireOverdueSugestoes,
  checkLinkOk,
} = require('./cms-sugestoes-job');
const sugestoesJob = require('./cms-sugestoes-job');
const { registerCmsSugestoesRoutes } = require('./cms-sugestoes');
const { buildPublicPostsQuery } = require('./cms-posts');
const { createRequireAdminAuth } = require('../admin/auth');

process.env.HUB_ADMIN_API_KEY = process.env.HUB_ADMIN_API_KEY || 'cms-blog-024-test';

function listen(app) {
  return new Promise((resolve) => {
    const server = http.createServer(app);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
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
  return { status: res.status, data };
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

describe('validação de sugestão', () => {
  it('exige limites e números do resumo no texto do artigo', () => {
    const article = 'O mercado de panetones chegou a R$ 1,36 bilhão em 2026.';
    assert.equal(numbersInResumoAppearInArticle('Mercado de R$ 1,36 bilhão', article), true);
    assert.equal(numbersInResumoAppearInArticle('Mercado de R$ 9,99 bilhão', article), false);

    const ok = validateSuggestionDraft(
      {
        tipo: 'noticia',
        titulo_pt: 'Panetone em alta',
        resumo_pt: 'O mercado chegou a R$ 1,36 bilhão.',
        markdown_pt: 'a\n\nb',
        titulo_en: 'Panettone rising',
        resumo_en: 'The market reached R$ 1,36 billion.',
        markdown_en: 'a\n\nb',
        fonte: 'gironews.com',
        sentidos: ['sabor'],
        trecho_base: 'R$ 1,36 bilhão',
      },
      article
    );
    assert.equal(ok.ok, true);

    const longTitle = validateSuggestionDraft(
      {
        tipo: 'curiosidade',
        titulo_pt: 'x'.repeat(71),
        resumo_pt: 'ok',
        markdown_pt: 'a',
        titulo_en: 'ok',
        resumo_en: 'ok',
        markdown_en: 'a',
        fonte: 'a.com',
        sentidos: ['olhar'],
        trecho_base: 'trecho',
      },
      'sem numero'
    );
    assert.equal(longTitle.ok, false);
    assert.match(longTitle.errors.join(' '), /titulo_pt/);
  });
});

describe('dedupe', () => {
  it('remove URL normalizada e títulos parecidos', () => {
    assert.equal(
      normalizeUrl('https://WWW.Example.com/path/?q=1#frag'),
      'https://example.com/path?q=1'
    );
    assert.equal(
      titlesSimilar(
        'A massa madre chegou ao pão francês',
        'A massa madre chegou ao pao frances'
      ),
      true
    );
    const kept = dedupeCandidates(
      [
        { title: 'A massa madre chegou ao pão francês', link: 'https://a.com/1' },
        { title: 'A massa madre chegou ao pao frances', link: 'https://a.com/outro' },
        { title: 'Farinha de trigo sobe no atacado', link: 'https://b.com/2' },
        { title: 'Feira Alimenta Sebrae em Brasília', link: 'https://c.com/feira' },
      ],
      {
        existingUrls: ['https://www.b.com/2'],
        existingTitles: ['A massa madre chegou ao pão francês ontem'],
      }
    );
    assert.equal(kept.length, 1);
    assert.equal(kept[0].link, 'https://c.com/feira');
  });
});

describe('expiração', () => {
  it('marca sugestões vencidas como descartado', async () => {
    const pool = poolOf((sql) => {
      assert.match(sql, /status = 'descartado'/);
      assert.match(sql, /sugestao_expira_em/);
      return { rows: [{ id: 11 }, { id: 12 }] };
    });
    const ids = await expireOverdueSugestoes(pool, new Date('2026-11-19T12:00:00Z'));
    assert.deepEqual(ids, [11, 12]);
  });
});

describe('publicar atualiza PT e EN', () => {
  let server;
  let base;
  let originalCheck;
  const updates = [];

  before(async () => {
    originalCheck = sugestoesJob.checkLinkOk;
    sugestoesJob.checkLinkOk = async () => true;

    const pool = poolOf((sql, params) => {
      if (/idioma = 'pt' AND status = 'sugestao'/.test(sql) && /SELECT \*/.test(sql)) {
        return {
          rows: [
            {
              id: 101,
              titulo: 'Titulo PT',
              resumo: 'Resumo PT',
              conteudo_html: 'md pt',
              link_url: 'https://gironews.com/a',
              right_now_tipo: 'noticia',
              data_evento: null,
              status: 'sugestao',
            },
          ],
        };
      }
      if (/idioma = 'en' AND status = 'sugestao'/.test(sql)) {
        return {
          rows: [
            {
              id: 102,
              titulo: 'Title EN',
              resumo: 'Summary EN',
              conteudo_html: 'md en',
              status: 'sugestao',
            },
          ],
        };
      }
      if (/UPDATE cms_posts SET/.test(sql) && /status = 'publicado'/.test(sql)) {
        updates.push({ id: params[5], status: 'publicado', titulo: params[0] });
        return { rows: [{ id: params[5] }] };
      }
      return { rows: [] };
    });

    const app = express();
    app.use(express.json());
    const requireAdmin = createRequireAdminAuth('test-secret');
    registerCmsSugestoesRoutes(app, pool, requireAdmin);
    server = await listen(app);
    base = `http://127.0.0.1:${server.address().port}`;
  });

  after(async () => {
    sugestoesJob.checkLinkOk = originalCheck;
    if (server) await new Promise((resolve) => server.close(resolve));
  });

  it('publica o par nos dois idiomas', async () => {
    updates.length = 0;
    const res = await call(base, 'POST', '/api/cms/sugestoes/101/publicar', {
      titulo_pt: 'Novo PT',
      resumo_pt: 'Resumo novo PT',
      markdown_pt: 'corpo pt',
      titulo_en: 'New EN',
      resumo_en: 'New summary EN',
      markdown_en: 'body en',
    });
    assert.equal(res.status, 200);
    assert.equal(res.data.status, 'publicado');
    assert.deepEqual(res.data.ids, [101, 102]);
    assert.equal(updates.length, 2);
    assert.deepEqual(
      updates.map((u) => u.id).sort(),
      [101, 102]
    );
    assert.ok(updates.every((u) => u.status === 'publicado'));
  });
});

describe('consulta pública', () => {
  it('continua filtrando só status=publicado', () => {
    const query = buildPublicPostsQuery({
      sistema: 'lepain',
      secao: 'right_now',
      idioma: 'pt',
      limit: 20,
      offset: 0,
    });
    assert.match(query.sql, /WHERE status = 'publicado'/);
    assert.doesNotMatch(query.sql, /status = 'sugestao'/);
    assert.doesNotMatch(query.sql, /status = 'descartado'/);
    assert.doesNotMatch(query.sql, /status IN \(/);
  });
});

describe('checkLinkOk mockável', () => {
  it('não chama Bedrock real neste arquivo', () => {
    assert.equal(typeof checkLinkOk, 'function');
    assert.equal(typeof sugestoesJob.invokeBedrock, 'function');
  });
});

describe('Google News batchexecute', () => {
  it('extrai a URL final do envelope Fbv4je', () => {
    const body =
      ")]}'\n" +
      '18\n' +
      JSON.stringify([
        [
          'wrb.fr',
          'Fbv4je',
          JSON.stringify(['garturlres', 'https://www.estadao.com.br/economia/padaria/']),
        ],
      ]);
    assert.equal(
      sugestoesJob.parseBatchexecuteDestination(body),
      'https://www.estadao.com.br/economia/padaria/'
    );
    assert.equal(sugestoesJob.isGoogleNewsWrapper('https://news.google.com/rss/articles/CBMiabc'), true);
    assert.equal(sugestoesJob.isGoogleNewsWrapper('https://www.estadao.com.br/x'), false);
  });
});
