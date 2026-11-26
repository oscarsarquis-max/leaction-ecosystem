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

describe('grounding em camadas (offline)', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const {
    parseRssItems,
    matchesKeywords,
    extractReadableText,
    looksLikePaywall,
    MIN_GROUNDED_CHARS,
  } = require('./cms-sugestoes-lib');
  const fixtures = path.join(__dirname, 'fixtures', 'cms-sugestoes');

  it('camada 1: content:encoded do feed', () => {
    const xml = fs.readFileSync(
      path.join(fixtures, 'layer-content-encoded.rss.xml'),
      'utf8'
    );
    const [item] = parseRssItems(xml);
    assert.ok(item);
    assert.equal(matchesKeywords(item.title, item.description), true);
    const grounded = sugestoesJob.groundFromContentEncoded(item.contentEncoded);
    assert.equal(grounded.ok, true);
    assert.equal(grounded.layer, 'content_encoded');
    assert.ok(grounded.text.length >= MIN_GROUNDED_CHARS);
  });

  it('camada 2: HTML de página com extrator', async () => {
    const html = fs.readFileSync(path.join(fixtures, 'layer-page-article.html'), 'utf8');
    const text = extractReadableText(html, {
      readabilityExtract: () => {
        const stripped = html
          .replace(/<script[\s\S]*?<\/script>/gi, ' ')
          .replace(/<[^>]+>/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
        return stripped;
      },
    });
    assert.ok(text.length >= MIN_GROUNDED_CHARS);
    const http = {
      get: async () => ({ status: 200, data: html }),
    };
    const grounded = await sugestoesJob.groundFromPage(
      'https://example.com/farinha',
      http,
      { readabilityExtract: () => text }
    );
    assert.equal(grounded.ok, true);
    assert.equal(grounded.layer, 'page');
  });

  it('descarta paywall na camada de página', async () => {
    const html = fs.readFileSync(path.join(fixtures, 'layer-paywall.html'), 'utf8');
    assert.equal(looksLikePaywall(html, 'trecho'), true);
    const http = {
      get: async () => ({ status: 200, data: html }),
    };
    const grounded = await sugestoesJob.groundFromPage(
      'https://example.com/paywall',
      http,
      { readabilityExtract: () => 'Trecho livre curto.' }
    );
    assert.equal(grounded.ok, false);
    assert.equal(grounded.reason, 'paywall');
  });
});

// ---------------------------------------------------------------------------
// BLOG-024c / 024d
// ---------------------------------------------------------------------------
const lib = require('./cms-sugestoes-lib');
const lepainPurge = require('./lepain-purge');
const rodadas = require('./cms-sugestoes-rodadas');
const sugestoesRoutes = require('./cms-sugestoes');
const { registerCmsPostsRoutes } = require('./cms-posts');

describe('BLOG-024c — janela e link do Bing News', () => {
  it('olha só os últimos 14 dias', () => {
    assert.equal(lib.LOOKBACK_DAYS, 14);
    const now = new Date('2026-11-26T12:00:00Z');
    assert.equal(lib.isWithinLastDays('2026-11-15T12:00:00Z', lib.LOOKBACK_DAYS, now), true);
    assert.equal(lib.isWithinLastDays('2026-11-10T12:00:00Z', lib.LOOKBACK_DAYS, now), false);
  });

  it('decodeBingNewsUrl devolve a URL real do artigo', () => {
    const wrapped =
      'http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid=&tid=6b08&url=https%3a%2f%2fnoticias.uol.com.br%2fultimas%2fpadarias-historicas.htm%3fa%3d1%2520b&c=456&mkt=pt-br';
    assert.equal(
      lib.decodeBingNewsUrl(wrapped),
      'https://noticias.uol.com.br/ultimas/padarias-historicas.htm?a=1%20b'
    );
    // Não mexe em link comum, em Bing sem url= nem em url= que não é http(s).
    const plain = 'https://g1.globo.com/a?url=https%3a%2f%2fx.com';
    assert.equal(lib.decodeBingNewsUrl(plain), plain);
    const noUrl = 'http://www.bing.com/news/apiclick.aspx?aid=1';
    assert.equal(lib.decodeBingNewsUrl(noUrl), noUrl);
    const script = 'http://www.bing.com/news/apiclick.aspx?url=javascript%3aalert(1)';
    assert.equal(lib.decodeBingNewsUrl(script), script);
    assert.equal(lib.decodeBingNewsUrl(''), '');
  });

  it('parseRssItems troca o redirecionador do Bing pelo link real e lê News:Source', () => {
    const xml = `<?xml version="1.0"?><rss xmlns:News="x"><channel><item>
      <title>Padarias históricas</title>
      <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;aid=&amp;url=https%3a%2f%2fwww.exemplo.com.br%2fmateria&amp;c=1&amp;mkt=pt-br</link>
      <description>Texto</description>
      <pubDate>Sun, 24 Nov 2026 07:02:00 GMT</pubDate>
      <News:Source>UOL</News:Source>
    </item></channel></rss>`;
    const [item] = lib.parseRssItems(xml);
    assert.equal(item.link, 'https://www.exemplo.com.br/materia');
    assert.equal(item.sourceHint, 'UOL');
  });
});

describe('BLOG-024c — nome da fonte', () => {
  const fonteNomes = {
    'mercadoeconsumo.com.br': 'Mercado & Consumo',
    'g1.globo.com': 'g1',
  };

  it('prefere og:site_name, depois o mapa, nunca o domínio cru quando há mapa', () => {
    const html = '<html><head><meta property="og:site_name" content="Folha &amp; Cia"></head></html>';
    assert.equal(lib.extractOgSiteName(html), 'Folha & Cia');
    assert.equal(lib.extractOgSiteName('<html></html>'), '');
    assert.equal(
      lib.resolveFonteNome('https://www.mercadoeconsumo.com.br/x', { ogSiteName: 'Folha', fonteNomes }),
      'Folha'
    );
    assert.equal(
      lib.resolveFonteNome('https://www.mercadoeconsumo.com.br/x', { fonteNomes }),
      'Mercado & Consumo'
    );
    assert.equal(lib.resolveFonteNome('https://g1.globo.com/sp/x', { fonteNomes, hint: 'g1.globo.com' }), 'g1');
    assert.equal(
      lib.resolveFonteNome('https://outro.com.br/x', { fonteNomes, hint: 'mercadoeconsumo.com.br' }),
      'Mercado & Consumo'
    );
    assert.equal(lib.resolveFonteNome('https://outro.com.br/x', { fonteNomes, hint: 'UOL' }), 'UOL');
    assert.equal(lib.resolveFonteNome('https://outro.com.br/x', { fonteNomes }), 'outro.com.br');
  });

  it('o config real traz wikipedia_verbetes, fonte_nomes e Bing', () => {
    const cfg = sugestoesJob.loadFontesConfig();
    assert.equal(cfg.wikipediaVerbetes.length, 10);
    assert.ok(cfg.wikipediaVerbetes.includes('Pão francês'));
    assert.equal(cfg.fonteNomes['mercadoeconsumo.com.br'], 'Mercado & Consumo');
    assert.equal(cfg.fonteNomes['g1.globo.com'], 'g1');
    assert.ok(cfg.feeds.some((f) => /bing\.com\/news\/search\?q=padaria/.test(f.url)));
    assert.ok(cfg.feeds.length >= 7);
    assert.ok(cfg.feedsRemovidos.every((f) => f.motivo));
  });
});

describe('BLOG-024c — filtro editorial', () => {
  it('normaliza a nota e aprova só com >= 7', () => {
    assert.deepEqual(lib.normalizeEditorial({ score: '8', motivo: 'preço do pão' }), {
      score: 8,
      motivo: 'preço do pão',
      descartarSempre: false,
    });
    assert.equal(lib.normalizeEditorial({}).score, 0);
    assert.equal(lib.normalizeEditorial({ score: 42 }).score, 10);
    assert.equal(lib.editorialPasses({ score: 6.9 }), false);
    assert.equal(lib.editorialPasses({ score: 7 }), true);
    assert.equal(lib.editorialPasses({ score: 9, descartarSempre: true }), false);
    assert.match(lib.buildEditorialPrompt('texto', { title: 'T' }), /cliente que ama p[ãa]o, no Brasil/);
  });

  /** Pool que responde só ao que gerarSugestoes consulta. */
  function generationPool() {
    let nextId = 100;
    const inserted = [];
    const pool = poolOf((sql, params) => {
      if (/SELECT count\(DISTINCT/.test(sql)) return { rows: [{ n: 0 }] };
      if (/SELECT titulo, link_url/.test(sql)) return { rows: [] };
      if (/SELECT link_url FROM cms_posts/.test(sql)) return { rows: [] };
      if (/INSERT INTO cms_posts/.test(sql)) {
        nextId += 1;
        inserted.push({ id: nextId, idioma: /'pt'/.test(sql) ? 'pt' : 'en', params });
        return { rows: [{ id: nextId }] };
      }
      return { rows: [] };
    });
    pool.inserted = inserted;
    return pool;
  }

  const NOW = new Date('2026-11-26T15:00:00Z');
  const rss = `<?xml version="1.0"?><rss><channel>
    <item><title>Preço do pãozinho sobe em São Paulo</title><link>https://www.exemplo.com.br/pao-preco</link>
      <description>Padarias reajustam o pão</description><pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate></item>
    <item><title>Fabricante de padaria lança forno industrial</title><link>https://www.exemplo.com.br/forno-b2b</link>
      <description>Equipamento para padaria</description><pubDate>Mon, 23 Nov 2026 10:00:00 GMT</pubDate></item>
  </channel></rss>`;
  const article = `<html><head><meta property="og:site_name" content="Exemplo Notícias"></head><body><article>${'Pão fresco todos os dias. '.repeat(40)}</article></body></html>`;
  const fakeHttp = {
    get: async (url) => {
      if (url === 'https://feed.test/rss') return { status: 200, data: rss };
      return { status: 200, data: article };
    },
  };
  const draft = (titulo) => ({
    tipo: 'noticia',
    titulo_pt: titulo,
    resumo_pt: 'Resumo curto da matéria.',
    markdown_pt: 'Parágrafo um.\n\nParágrafo dois.',
    titulo_en: `EN ${titulo}`.slice(0, 70),
    resumo_en: 'Short summary.',
    markdown_en: 'Paragraph one.\n\nParagraph two.',
    fonte: 'exemplo.com.br',
    sentidos: ['sabor'],
    trecho_base: 'Pão fresco todos os dias.',
  });
  const baseDeps = () => ({
    now: NOW,
    http: fakeHttp,
    fontesConfig: {
      feeds: [{ id: 't', url: 'https://feed.test/rss' }],
      keywords: ['pao', 'padaria'],
      wikipediaVerbetes: [],
      fonteNomes: { 'exemplo.com.br': 'Exemplo' },
    },
    readabilityExtract: () => 'Pão fresco todos os dias. '.repeat(40),
  });

  it('reprova nota 6, aprova nota 8, guarda score+motivo e avisa o que faltou', async () => {
    const pool = generationPool();
    const bedrockCalls = [];
    const progress = [];
    const result = await sugestoesJob.gerarSugestoes(pool, {
      ...baseDeps(),
      onProgress: (p) => progress.push(p),
      invokeEditorial: async (_text, meta) =>
        /forno-b2b/.test(meta.url)
          ? { score: 6, motivo: 'assunto B2B' }
          : { score: 8, motivo: 'preço do pãozinho' },
      invokeBedrock: async (_text, meta) => {
        bedrockCalls.push(meta);
        return draft('Pãozinho mais caro em SP');
      },
    });
    assert.equal(result.created, 1);
    assert.equal(result.stats.discarded.editorial, 1);
    assert.equal(result.stats.editorial.avaliadas, 2);
    const rejeitada = result.stats.editorial.itens.find((i) => !i.aprovado);
    assert.equal(rejeitada.score, 6);
    assert.equal(rejeitada.motivo, 'assunto B2B');
    assert.equal(result.items[0].editorial.score, 8);
    // O rascunho completo só foi pedido para a matéria aprovada.
    assert.equal(bedrockCalls.length, 1);
    assert.match(bedrockCalls[0].url, /pao-preco/);
    // og:site_name da página vence o mapa; o rascunho sai com esse nome.
    assert.equal(bedrockCalls[0].fonte, 'Exemplo Notícias');
    const ptInsert = pool.inserted.find((i) => i.idioma === 'pt');
    assert.ok(ptInsert.params.includes('Exemplo Notícias'));
    assert.equal(result.shortfall_message, '1 de 5: as outras matérias não passaram no filtro');
    assert.ok(result.discarded_summary.some((d) => d.motivo === 'editorial' && d.total === 1));
    const phases = progress.map((p) => p.phase);
    assert.ok(phases.includes('avaliando') && phases.includes('escrevendo'));
    assert.equal(progress.at(-1).phase, 'concluido');
    assert.equal(progress.at(-1).aprovadas, 1);
  });

  it('timeout do Bedrock sem nenhuma resposta vira mensagem humana', async () => {
    const pool = generationPool();
    await assert.rejects(
      sugestoesJob.gerarSugestoes(pool, {
        ...baseDeps(),
        bedrockTimeoutMs: 20,
        invokeEditorial: () => new Promise(() => {}),
      }),
      (err) =>
        err instanceof sugestoesJob.SugestoesError &&
        err.code === 'bedrock_timeout' &&
        /Bedrock/.test(err.message)
    );
  });

  it('sem feed respondendo e sem curiosidade: erro "sem_feeds"', async () => {
    const pool = generationPool();
    await assert.rejects(
      sugestoesJob.gerarSugestoes(pool, {
        ...baseDeps(),
        http: { get: async () => ({ status: 503, data: '' }) },
      }),
      (err) => err.code === 'sem_feeds' && /Nenhuma fonte/.test(err.message)
    );
  });
});

describe('BLOG-024c — curiosidades da Wikipédia', () => {
  it('lê o extrato e ignora verbete inexistente ou curto', () => {
    const long = 'Pão é um alimento básico. '.repeat(20);
    const ok = lib.parseWikipediaExtract({ query: { pages: { 12: { title: 'Pão', extract: long } } } });
    assert.equal(ok.titulo, 'Pão');
    assert.equal(lib.parseWikipediaExtract({ query: { pages: { '-1': { title: 'X', missing: '' } } } }), null);
    assert.equal(lib.parseWikipediaExtract({ query: { pages: { 3: { title: 'Y', extract: 'curto' } } } }), null);
    assert.match(lib.wikipediaApiUrl('Pão francês'), /prop=extracts.*explaintext=1/);
    assert.equal(lib.wikipediaVerbeteUrl('Pão francês'), 'https://pt.wikipedia.org/wiki/P%C3%A3o_franc%C3%AAs');
    assert.equal(lib.wikipediaTitleFromLink('https://pt.wikipedia.org/wiki/P%C3%A3o_franc%C3%AAs'), 'Pão francês');
  });

  it('pula verbetes dos últimos 30 dias e cria no máximo 2 curiosidades com link do verbete', async () => {
    const picked = lib.pickWikipediaTitles(
      ['Pão', 'Pão francês', 'Panetone', 'Croissant', 'Trigo'],
      ['Pão', 'Panetone'],
      { max: 10, random: () => 0.5 }
    );
    assert.deepEqual([...picked].sort(), ['Croissant', 'Pão francês', 'Trigo']);

    let id = 500;
    const pool = poolOf((sql) => {
      if (/SELECT link_url FROM cms_posts/.test(sql)) {
        assert.match(sql, /wikipedia\.org\/wiki/);
        return {
          rows: [
            { link_url: 'https://pt.wikipedia.org/wiki/P%C3%A3o' },
            { link_url: 'https://pt.wikipedia.org/wiki/Panetone' },
          ],
        };
      }
      if (/INSERT INTO cms_posts/.test(sql)) {
        id += 1;
        return { rows: [{ id }] };
      }
      return { rows: [] };
    });
    const stats = sugestoesJob.blankStats();
    const progress = sugestoesJob.createProgress(null);
    const asked = [];
    const created = await sugestoesJob.gerarCuriosidadesWikipedia(pool, {
      http: {},
      now: new Date('2026-11-26T15:00:00Z'),
      stats,
      progress,
      limit: 2,
      verbetes: ['Pão', 'Panetone', 'Croissant', 'Trigo', 'Baguete'],
      state: {},
      deps: {
        random: () => 0.5,
        fetchWikipediaExtract: async (titulo) => {
          asked.push(titulo);
          return { titulo, extract: `${titulo} é tradicional. `.repeat(30) };
        },
        invokeBedrock: async (_text, meta) => {
          assert.equal(meta.tipoForcado, 'curiosidade');
          return {
            tipo: 'noticia',
            titulo_pt: `Você sabia: ${meta.title}`,
            resumo_pt: 'Uma curiosidade do verbete.',
            markdown_pt: 'a\n\nb',
            titulo_en: `Did you know: ${meta.title}`,
            resumo_en: 'A curiosity from the entry.',
            markdown_en: 'a\n\nb',
            fonte: 'pt.wikipedia.org',
            sentidos: ['memoria'],
            trecho_base: 'é tradicional',
          };
        },
      },
    });
    assert.equal(created.length, 2);
    assert.ok(created.every((c) => c.tipo === 'curiosidade' && c.fonte === 'Wikipédia'));
    assert.ok(created.every((c) => /^https:\/\/pt\.wikipedia\.org\/wiki\//.test(c.link)));
    assert.ok(!asked.includes('Pão') && !asked.includes('Panetone'));
    assert.equal(stats.wikipedia.criadas, 2);
  });
});

describe('BLOG-024c — agrupamento e contagem do dia', () => {
  const now = new Date('2026-11-26T15:00:00Z'); // 12:00 em São Paulo
  const pairs = [
    { grupo_id: 3, criado_em: '2026-11-26T14:00:00Z' },
    { grupo_id: 2, criado_em: '2026-11-26T02:30:00Z' }, // 25/11 23:30 em SP
    { grupo_id: 1, criado_em: '2026-11-25T18:00:00Z' },
  ];

  it('conta "hoje" no fuso de São Paulo e agrupa do dia mais novo para o mais antigo', () => {
    assert.equal(lib.countPairsCreatedToday(pairs, now), 1);
    assert.deepEqual(lib.groupPairsByDay(pairs, now), [
      { data: '2026-11-26', hoje: true, total: 1, grupo_ids: [3] },
      { data: '2026-11-25', hoje: false, total: 2, grupo_ids: [2, 1] },
    ]);
  });

  it('mensagem de faltou e resumo de descartes', () => {
    assert.equal(lib.buildShortfallMessage(3, 5), '3 de 5: as outras matérias não passaram no filtro');
    assert.equal(lib.buildShortfallMessage(5, 5), null);
    assert.equal(lib.buildShortfallMessage(0, 0), null);
    const sum = lib.summarizeDiscarded({ editorial: 2, keyword: 9, paywall: 0 });
    assert.deepEqual(sum.map((s) => s.motivo), ['keyword', 'editorial']);
  });
});

describe('BLOG-024c/d — rodada assíncrona (202 + polling)', () => {
  let server;
  let base;
  let release;
  let gate;
  let runner;
  const calls = { generate: 0 };

  before(async () => {
    gate = new Promise((resolve) => {
      release = resolve;
    });
    const pool = poolOf((sql) => {
      if (/SELECT id, slug, titulo/.test(sql)) {
        return {
          rows: [
            { id: 1, idioma: 'pt', grupo_id: 1, right_now_tipo: 'noticia', criado_em: '2026-11-26T14:00:00Z', sugestao_expira_em: '2026-11-28T14:00:00Z', slug: 'a', titulo: 'A', resumo: 'a', conteudo_html: 'a', sentidos: ['sabor'] },
            { id: 2, idioma: 'en', grupo_id: 1, criado_em: '2026-11-26T14:00:00Z', slug: 'a-en', titulo: 'A', resumo: 'a', conteudo_html: 'a' },
            { id: 3, idioma: 'pt', grupo_id: 3, right_now_tipo: 'curiosidade', criado_em: '2026-11-25T14:00:00Z', sugestao_expira_em: '2026-11-27T14:00:00Z', slug: 'c', titulo: 'C', resumo: 'c', conteudo_html: 'c', sentidos: ['sabor'] },
          ],
        };
      }
      return { rows: [] };
    });
    runner = rodadas.createRodadaRunner(pool, {
      store: rodadas.createMemoryRodadasStore(),
      generate: async (_pool, deps) => {
        calls.generate += 1;
        deps.onProgress({ phase: 'lendo', materias: 8, com_texto: 3, aprovadas: 0, message: 'Lendo matéria 3 de 8…' });
        await gate;
        deps.onProgress({ phase: 'concluido', materias: 8, com_texto: 3, aprovadas: 3, message: 'ok' });
        return {
          created: 3,
          ids: [1, 2, 3],
          items: [],
          shortfall_message: '3 de 5: as outras matérias não passaram no filtro',
          discarded_summary: [{ motivo: 'editorial', rotulo: 'reprovadas no filtro editorial', total: 4 }],
          stats: { feeds: [] },
        };
      },
    });
    const app = express();
    app.use(express.json());
    const requireAdmin = createRequireAdminAuth('test-secret');
    registerCmsSugestoesRoutes(app, pool, requireAdmin, {
      runner,
      now: () => new Date('2026-11-26T15:00:00Z'),
    });
    server = await listen(app);
    base = `http://127.0.0.1:${server.address().port}`;
  });

  after(async () => {
    release();
    await runner.whenIdle();
    if (server) await new Promise((resolve) => server.close(resolve));
  });

  it('POST gerar responde 202 e o segundo POST reaproveita a mesma rodada', async () => {
    const first = await call(base, 'POST', '/api/cms/sugestoes/gerar');
    assert.equal(first.status, 202);
    assert.ok(first.data.rodada_id);
    assert.equal(first.data.status, 'running');
    const second = await call(base, 'POST', '/api/cms/sugestoes/gerar');
    assert.equal(second.status, 202);
    assert.equal(second.data.rodada_id, first.data.rodada_id);
    assert.equal(second.data.reused, true);
    assert.equal(calls.generate, 1);

    const poll = await call(base, 'GET', `/api/cms/sugestoes/rodadas/${first.data.rodada_id}`);
    assert.equal(poll.status, 200);
    assert.equal(poll.data.status, 'running');
    assert.equal(poll.data.progress.phase, 'lendo');
    assert.equal(poll.data.progress.materias, 8);
    assert.equal(poll.data.progress.com_texto, 3);
    assert.equal(poll.data.result, null);
    const atual = await call(base, 'GET', '/api/cms/sugestoes/rodadas/atual');
    assert.equal(atual.data.rodada.id, first.data.rodada_id);

    release();
    await runner.whenIdle();
    const done = await call(base, 'GET', `/api/cms/sugestoes/rodadas/${first.data.rodada_id}`);
    assert.equal(done.data.status, 'done');
    assert.equal(done.data.result.created, 3);
    assert.equal(done.data.result.shortfall_message, '3 de 5: as outras matérias não passaram no filtro');
    assert.equal(done.data.result.discarded_summary[0].motivo, 'editorial');
    assert.ok(done.data.finished_at);
    assert.equal((await call(base, 'GET', '/api/cms/sugestoes/rodadas/atual')).data.rodada, null);
    assert.equal((await call(base, 'GET', '/api/cms/sugestoes/rodadas/999')).status, 404);
  });

  it('rodada recente (< 2 min) é recusada com mensagem humana', async () => {
    const res = await call(base, 'POST', '/api/cms/sugestoes/gerar');
    assert.equal(res.status, 429);
    assert.equal(res.data.code, 'rodada_recente');
    assert.match(res.data.error, /2 minutos/);
  });

  it('erro do Bedrock aparece como texto legível na rodada', async () => {
    const pool = poolOf(() => ({ rows: [] }));
    const failing = rodadas.createRodadaRunner(pool, {
      store: rodadas.createMemoryRodadasStore(),
      minIntervalMs: 0,
      generate: async () => {
        throw new sugestoesJob.SugestoesError('bedrock_timeout', sugestoesJob.humanError('bedrock_timeout'));
      },
    });
    const out = await failing.start({ trigger: 'manual' });
    await failing.whenIdle();
    const row = rodadas.shapeRodada(await failing.get(out.rodada_id));
    assert.equal(row.status, 'error');
    assert.equal(row.error.code, 'bedrock_timeout');
    assert.match(row.error.message, /Bedrock/);
    assert.equal(row.result, null);

    const crash = rodadas.createRodadaRunner(pool, {
      store: rodadas.createMemoryRodadasStore(),
      generate: async () => {
        throw new Error('ECONNRESET 10.0.0.1');
      },
    });
    const out2 = await crash.start({});
    await crash.whenIdle();
    const row2 = rodadas.shapeRodada(await crash.get(out2.rodada_id));
    assert.equal(row2.status, 'error');
    assert.doesNotMatch(row2.error.message, /ECONNRESET/);
  });

  it('GET lista traz pending_today_count e grupos por dia (São Paulo)', async () => {
    const res = await call(base, 'GET', '/api/cms/sugestoes');
    assert.equal(res.status, 200);
    assert.equal(res.data.pending_count, 2);
    assert.equal(res.data.pending_today_count, 1);
    assert.deepEqual(
      res.data.grupos.map((g) => [g.data, g.hoje, g.total]),
      [
        ['2026-11-26', true, 1],
        ['2026-11-25', false, 1],
      ]
    );
  });
});

describe('BLOG-024c — rodada automática do dia (07:00 + catch-up)', () => {
  const emptyPool = () => poolOf(() => ({ rows: [] }));
  const quickGenerate = async () => ({ created: 0, ids: [], items: [], stats: {} });

  it('só a partir das 07:00 SP e no máximo uma por dia, mesmo reiniciando', async () => {
    sugestoesRoutes.resetSugestoesSchedulerForTests();
    const store = rodadas.createMemoryRodadasStore();
    const make = () => rodadas.createRodadaRunner(emptyPool(), { store, generate: quickGenerate });
    let runner = make();

    // 06:30 em SP: ainda não.
    const early = await sugestoesRoutes.maybeStartDailyRound(runner, new Date('2026-11-26T09:30:00Z'));
    assert.equal(early.started, false);
    assert.equal(store.rows.length, 0);

    // 07:00 em SP: dispara.
    const seven = await sugestoesRoutes.maybeStartDailyRound(runner, new Date('2026-11-26T10:00:00Z'));
    assert.equal(seven.started, true);
    await runner.whenIdle();
    assert.equal(store.rows.filter((r) => r.trigger === 'auto').length, 1);

    // Mesmo processo, minutos depois: não repete.
    const again = await sugestoesRoutes.maybeStartDailyRound(runner, new Date('2026-11-26T10:01:00Z'));
    assert.equal(again.started, false);

    // Reinício às 10:00 SP: o catch-up consulta o banco e não cria outra.
    sugestoesRoutes.resetSugestoesSchedulerForTests();
    runner = make();
    const restart = await sugestoesRoutes.maybeStartDailyRound(runner, new Date('2026-11-26T13:00:00Z'));
    assert.equal(restart.started, false);
    assert.equal(store.rows.filter((r) => r.trigger === 'auto').length, 1);

    // Dia seguinte: catch-up às 09:00 SP roda de novo.
    sugestoesRoutes.resetSugestoesSchedulerForTests();
    const next = await sugestoesRoutes.maybeStartDailyRound(make(), new Date('2026-11-27T12:00:00Z'));
    assert.equal(next.started, true);
    sugestoesRoutes.resetSugestoesSchedulerForTests();
  });

  it('rodada em andamento adia a automática, e manual do dia não a bloqueia', async () => {
    sugestoesRoutes.resetSugestoesSchedulerForTests();
    const store = rodadas.createMemoryRodadasStore();
    let release;
    const hold = new Promise((resolve) => {
      release = resolve;
    });
    const runner = rodadas.createRodadaRunner(emptyPool(), {
      store,
      minIntervalMs: 0,
      generate: async () => {
        await hold;
        return { created: 0, ids: [], items: [], stats: {} };
      },
    });
    const manual = await runner.start({ trigger: 'manual' });
    const waiting = await sugestoesRoutes.maybeStartDailyRound(runner, new Date('2026-11-26T11:00:00Z'));
    assert.equal(waiting.started, false);
    assert.equal(waiting.reason, 'rodada_em_andamento');
    assert.equal(waiting.rodada_id, manual.rodada_id);
    release();
    await runner.whenIdle();
    const auto = await sugestoesRoutes.maybeStartDailyRound(runner, new Date('2026-11-26T11:01:00Z'));
    assert.equal(auto.started, true);
    await runner.whenIdle();
    sugestoesRoutes.resetSugestoesSchedulerForTests();
  });

  it('rodada que ficou running num processo anterior vira erro "interrompida"', async () => {
    const store = rodadas.createMemoryRodadasStore();
    await store.create({ trigger: 'manual', startedAt: new Date() });
    assert.equal(await store.failOrphans(new Date()), 1);
    const row = rodadas.shapeRodada(await store.get(1));
    assert.equal(row.status, 'error');
    assert.equal(row.error.code, 'interrompida');
  });

  it('server.js liga o job diário', () => {
    const src = require('node:fs').readFileSync(require('node:path').join(__dirname, '../server.js'), 'utf8');
    assert.match(src, /startSugestoesScheduler\(pool,\s*\{\s*dailyEnabled:\s*true\s*\}\)/);
  });
});

describe('BLOG-024d — lista admin e purge do blog', () => {
  it('GET /api/cms/posts/admin exclui sugestao e descartado', async () => {
    const pool = poolOf(() => ({ rows: [] }));
    const app = express();
    app.use(express.json());
    registerCmsPostsRoutes(app, pool, { jwtSecret: 'test-secret' });
    const srv = await listen(app);
    try {
      const res = await call(`http://127.0.0.1:${srv.address().port}`, 'GET', '/api/cms/posts/admin');
      assert.equal(res.status, 200);
      const sql = pool.calls.find((c) => /FROM cms_posts/.test(c.sql)).sql;
      assert.match(sql, /WHERE status NOT IN \('sugestao', 'descartado'\)/);
    } finally {
      await new Promise((resolve) => srv.close(resolve));
    }
  });

  it('notifyLepainPurge envia X-LePain-Key, não lança e ignora quando falta a chave', async () => {
    lepainPurge.resetLepainPurgeWarningForTests();
    const logs = [];
    const logger = { warn: (m) => logs.push(m) };
    const seen = [];
    const ok = await lepainPurge.notifyLepainPurge({
      env: { LEPAIN_CMS_KEY: 'segredo-teste' },
      logger,
      http: {
        post: async (url, _body, cfg) => {
          seen.push({ url, key: cfg.headers['X-LePain-Key'] });
          return { status: 200 };
        },
      },
    });
    assert.equal(ok.ok, true);
    assert.deepEqual(seen, [{ url: 'https://lepain.lojadepaes.com.br/api/cms/purge', key: 'segredo-teste' }]);

    const failed = await lepainPurge.notifyLepainPurge({
      env: { LEPAIN_CMS_KEY: 'segredo-teste' },
      logger,
      http: {
        post: async () => {
          throw new Error('rede caiu');
        },
      },
    });
    assert.equal(failed.ok, false);
    const bad = await lepainPurge.notifyLepainPurge({
      env: { LEPAIN_CMS_KEY: 'segredo-teste' },
      logger,
      http: { post: async () => ({ status: 401 }) },
    });
    assert.equal(bad.ok, false);
    assert.ok(logs.some((l) => /rede caiu/.test(l)) && logs.some((l) => /401/.test(l)));
    assert.ok(logs.every((l) => !/segredo-teste/.test(l)));

    const none = await lepainPurge.notifyLepainPurge({
      env: {},
      logger,
      http: { post: async () => assert.fail('sem chave não chama o blog') },
    });
    assert.deepEqual(none, { ok: false, skipped: 'sem_chave' });
  });

  it('criar, editar, excluir (lepain) e publicar sugestão avisam o blog; outro destino não', async () => {
    const original = lepainPurge.notifyLepainPurge;
    let purges = 0;
    lepainPurge.notifyLepainPurge = async () => {
      purges += 1;
      return { ok: true };
    };
    const originalCheck = sugestoesJob.checkLinkOk;
    sugestoesJob.checkLinkOk = async () => true;
    const row = {
      id: 7,
      slug: 'levain',
      titulo: 'Levain',
      resumo: 'r',
      conteudo_html: '<p>x</p>',
      imagem_capa: null,
      sistema_destino: 'lepain',
      status: 'rascunho',
      secao: 'insights',
      idioma: 'pt',
      grupo_id: 7,
      sentidos: ['aroma'],
      right_now_tipo: 'noticia',
      link_url: 'https://a.com/x',
      criado_em: '2026-11-26T10:00:00Z',
    };
    const pool = poolOf((sql) => {
      if (/^INSERT INTO cms_posts/.test(sql)) return { rows: [{ ...row }] };
      if (/^UPDATE cms_posts SET grupo_id/.test(sql)) return { rows: [{ ...row }] };
      if (/^SELECT \* FROM cms_posts WHERE id = \$1$/.test(sql)) return { rows: [{ ...row }] };
      if (/^UPDATE cms_posts SET slug/.test(sql)) return { rows: [{ ...row, status: 'rascunho' }] };
      if (/^DELETE/.test(sql)) return { rows: [{ id: 7 }] };
      if (/idioma = 'pt' AND status = 'sugestao'/.test(sql)) {
        return { rows: [{ ...row, status: 'sugestao', data_evento: null }] };
      }
      if (/idioma = 'en' AND status = 'sugestao'/.test(sql)) {
        return { rows: [{ ...row, id: 8, idioma: 'en', status: 'sugestao' }] };
      }
      return { rows: [] };
    });
    const app = express();
    app.use(express.json());
    registerCmsPostsRoutes(app, pool, { jwtSecret: 'test-secret' });
    const srv = await listen(app);
    const b = `http://127.0.0.1:${srv.address().port}`;
    try {
      const body = {
        titulo: 'Levain',
        slug: 'levain',
        sistema_destino: 'lepain',
        status: 'publicado',
        secao: 'insights',
        idioma: 'pt',
        sentidos: ['aroma'],
      };
      assert.equal((await call(b, 'POST', '/api/cms/posts', body)).status, 201);
      assert.equal((await call(b, 'PUT', '/api/cms/posts/7', { status: 'rascunho' })).status, 200);
      assert.equal((await call(b, 'DELETE', '/api/cms/posts/7')).status, 200);
      assert.equal(purges, 3);

      const pub = await call(b, 'POST', '/api/cms/sugestoes/7/publicar', {});
      assert.equal(pub.status, 200);
      assert.equal(purges, 4);

      const other = await call(b, 'POST', '/api/cms/posts', {
        titulo: 'Hub',
        slug: 'hub',
        sistema_destino: 'paneldx',
        status: 'rascunho',
      });
      assert.equal(other.status, 201);
      assert.equal(purges, 4);
    } finally {
      lepainPurge.notifyLepainPurge = original;
      sugestoesJob.checkLinkOk = originalCheck;
      await new Promise((resolve) => srv.close(resolve));
    }
  });
});

describe('BLOG-024c — patch SQL', () => {
  it('cria a tabela de rodadas, os índices únicos e o descarte pontual sem tocar publicadas', () => {
    const sql = require('node:fs').readFileSync(
      require('node:path').join(__dirname, '../../../shared/database/patch_cms_sugestoes_rodadas.sql'),
      'utf8'
    );
    assert.match(sql, /CREATE TABLE IF NOT EXISTS cms_sugestoes_rodadas/);
    assert.match(sql, /uq_cms_sugestoes_rodadas_auto_dia/);
    assert.match(sql, /uq_cms_sugestoes_rodadas_running/);
    assert.match(sql, /WHERE status = 'sugestao'/);
    assert.doesNotMatch(sql, /status = 'publicado'/);
    assert.doesNotMatch(sql, /DELETE FROM/i);
    // O DDL embutido no gateway e o patch descrevem as mesmas estruturas.
    for (const name of [
      'uq_cms_sugestoes_rodadas_auto_dia',
      'uq_cms_sugestoes_rodadas_running',
      'chk_cms_sugestoes_rodadas_status',
    ]) {
      assert.ok(sql.includes(name) && rodadas.RODADAS_DDL.includes(name));
    }
  });
});
