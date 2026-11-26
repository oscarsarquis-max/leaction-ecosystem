'use strict';

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const {
  BedrockRuntimeClient,
  ConverseCommand,
} = require('@aws-sdk/client-bedrock-runtime');
const {
  DAILY_CAP,
  LOOKBACK_DAYS,
  MIN_GROUNDED_CHARS,
  DEFAULT_KEYWORDS,
  WIKIPEDIA_COOLDOWN_DAYS,
  WIKIPEDIA_MAX_PER_ROUND,
  dateOnly,
  dedupeCandidates,
  expireAtFrom,
  extractReadableText,
  extractOgSiteName,
  isWithinLastDays,
  looksLikePaywall,
  matchesKeywords,
  normalizeUrl,
  parseBedrockJson,
  parseRssItems,
  slugFromTitleAndUrl,
  stripHtml,
  todaySaoPaulo,
  validateSuggestionDraft,
  buildBedrockPrompt,
  buildEditorialPrompt,
  normalizeEditorial,
  editorialPasses,
  resolveFonteNome,
  wikipediaApiUrl,
  wikipediaVerbeteUrl,
  wikipediaTitleFromLink,
  parseWikipediaExtract,
  pickWikipediaTitles,
  buildShortfallMessage,
  summarizeDiscarded,
} = require('./cms-sugestoes-lib');

const FONTES_PATH = path.join(__dirname, '../config/cms-sugestoes-fontes.json');
const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const PAGE_TIMEOUT_MS = 10000;
const BEDROCK_TIMEOUT_MS = 60000;
const BEDROCK_MAX_CONSECUTIVE_FAILS = 3;
const MAX_CANDIDATES_EXAMINED = 40;
const EDITORIAL_ITEMS_CAP = 60;

/** Erro com mensagem pronta para o gestor (a tela mostra `message` sem traduzir). */
class SugestoesError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'SugestoesError';
    this.code = code;
  }
}

const HUMAN_ERRORS = {
  bedrock_timeout:
    'O redator automático (Bedrock) demorou demais para responder. Tente de novo em alguns minutos.',
  sem_feeds:
    'Nenhuma fonte de notícias respondeu agora e não houve curiosidade disponível. Tente de novo em alguns minutos.',
  rodada_recente:
    'Uma rodada acabou de terminar. Aguarde 2 minutos antes de gerar de novo.',
  interrompida: 'A rodada foi interrompida (o servidor reiniciou). Gere de novo.',
  falha: 'Não foi possível gerar as sugestões agora. Tente de novo em alguns minutos.',
};

function humanError(code) {
  return HUMAN_ERRORS[code] || HUMAN_ERRORS.falha;
}

function withTimeout(promise, ms, code = 'BEDROCK_TIMEOUT') {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      const err = new Error(`timeout ${ms}ms`);
      err.code = code;
      reject(err);
    }, ms);
    if (typeof timer.unref === 'function') timer.unref();
  });
  return Promise.race([Promise.resolve(promise), timeout]).finally(() => clearTimeout(timer));
}

function isTimeoutError(err) {
  return err?.code === 'BEDROCK_TIMEOUT' || /timeout|timed out/i.test(String(err?.name || err?.message || ''));
}

function loadFontesConfig(filePath = FONTES_PATH) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const parsed = JSON.parse(raw);
  return {
    feeds: Array.isArray(parsed.feeds) ? parsed.feeds : [],
    keywords: Array.isArray(parsed.keywords) && parsed.keywords.length
      ? parsed.keywords
      : DEFAULT_KEYWORDS,
    wikipediaVerbetes: Array.isArray(parsed.wikipedia_verbetes) ? parsed.wikipedia_verbetes : [],
    fonteNomes:
      parsed.fonte_nomes && typeof parsed.fonte_nomes === 'object' ? parsed.fonte_nomes : {},
    feedsRemovidos: Array.isArray(parsed.feeds_removidos) ? parsed.feeds_removidos : [],
  };
}

function loadFontes(filePath = FONTES_PATH) {
  return loadFontesConfig(filePath).feeds;
}

function bedrockConfig() {
  const region =
    process.env.BEDROCK_REGION || process.env.AWS_REGION || 'us-east-1';
  const modelId =
    process.env.BEDROCK_MODEL_ID || 'us.anthropic.claude-sonnet-4-6';
  return { region, modelId };
}

function createBedrockClient({ region } = {}) {
  const cfg = bedrockConfig();
  return new BedrockRuntimeClient({ region: region || cfg.region });
}

function readabilityExtract(html) {
  try {
    const { JSDOM } = require('jsdom');
    const { Readability } = require('@mozilla/readability');
    const dom = new JSDOM(String(html || ''), { url: 'https://example.invalid/' });
    const article = new Readability(dom.window.document).parse();
    return article?.textContent ? String(article.textContent).trim() : '';
  } catch {
    return '';
  }
}

async function fetchFeed(url, http = axios) {
  try {
    const res = await http.get(url, {
      timeout: 20000,
      responseType: 'text',
      headers: {
        'User-Agent': USER_AGENT,
        Accept: 'application/rss+xml, application/xml, text/xml, */*',
      },
      maxRedirects: 5,
      validateStatus: () => true,
    });
    if (res.status < 200 || res.status >= 400) {
      return { ok: false, status: res.status, xml: '', error: `http_${res.status}` };
    }
    return { ok: true, status: res.status, xml: String(res.data || '') };
  } catch (err) {
    const status = err.response?.status || null;
    return {
      ok: false,
      status,
      xml: '',
      error: status ? `http_${status}` : err.code === 'ECONNABORTED' ? 'timeout' : 'error',
    };
  }
}

async function fetchFeedXml(url, http = axios) {
  const got = await fetchFeed(url, http);
  if (!got.ok) throw new Error(`feed ${got.error || got.status}`);
  return got.xml;
}

/**
 * Grounding em camadas. Retorna texto >= MIN_GROUNDED_CHARS ou motivo de descarte.
 */
function groundFromContentEncoded(contentEncoded) {
  const text = stripHtml(contentEncoded || '');
  if (text.length >= MIN_GROUNDED_CHARS) {
    return { ok: true, text, layer: 'content_encoded' };
  }
  return { ok: false, reason: 'sem_texto', text, layer: null };
}

async function groundFromPage(url, http = axios, deps = {}) {
  const extract = deps.readabilityExtract || readabilityExtract;
  try {
    const res = await http.get(url, {
      timeout: deps.pageTimeoutMs || PAGE_TIMEOUT_MS,
      maxRedirects: 5,
      responseType: 'text',
      headers: {
        'User-Agent': USER_AGENT,
        Accept: 'text/html,application/xhtml+xml,*/*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
      },
      validateStatus: () => true,
    });
    if (res.status >= 400 && res.status < 500) {
      return { ok: false, reason: 'http_4xx', status: res.status };
    }
    if (res.status < 200 || res.status >= 300) {
      return { ok: false, reason: 'sem_texto', status: res.status };
    }
    const html = String(res.data || '');
    const text = extractReadableText(html, { readabilityExtract: extract });
    if (looksLikePaywall(html, text)) {
      return { ok: false, reason: 'paywall', status: res.status };
    }
    if (text.length >= MIN_GROUNDED_CHARS) {
      return {
        ok: true,
        text,
        layer: 'page',
        status: res.status,
        ogSiteName: extractOgSiteName(html),
      };
    }
    return { ok: false, reason: 'sem_texto', status: res.status, text };
  } catch (err) {
    if (err.code === 'ECONNABORTED' || /timeout/i.test(err.message || '')) {
      return { ok: false, reason: 'timeout' };
    }
    const status = err.response?.status;
    if (status >= 400 && status < 500) {
      return { ok: false, reason: 'http_4xx', status };
    }
    return { ok: false, reason: 'sem_texto' };
  }
}

async function groundItem(item, http = axios, deps = {}) {
  const fromFeed = groundFromContentEncoded(item.contentEncoded);
  if (fromFeed.ok) return fromFeed;
  return groundFromPage(item.link, http, deps);
}

async function checkLinkOk(url, http = axios) {
  try {
    const res = await http.get(url, {
      timeout: 15000,
      maxRedirects: 8,
      responseType: 'text',
      headers: { 'User-Agent': USER_AGENT },
      validateStatus: () => true,
    });
    return res.status === 200;
  } catch {
    return false;
  }
}

async function converseJson(prompt, { client, modelId, maxTokens = 1800, temperature = 0.2 } = {}) {
  const cfg = bedrockConfig();
  const bedrock = client || createBedrockClient();
  const command = new ConverseCommand({
    modelId: modelId || cfg.modelId,
    messages: [{ role: 'user', content: [{ text: prompt }] }],
    inferenceConfig: { maxTokens, temperature },
  });
  const out = await bedrock.send(command);
  const parts = out?.output?.message?.content || [];
  const text = parts.map((p) => p.text || '').join('').trim();
  return parseBedrockJson(text);
}

async function invokeBedrock(articleText, meta, { client, modelId } = {}) {
  return converseJson(buildBedrockPrompt(articleText, meta), { client, modelId });
}

/** Filtro editorial barato (nota 0-10) antes de gastar tokens no rascunho PT/EN. */
async function invokeEditorialBedrock(articleText, meta, { client, modelId } = {}) {
  return converseJson(buildEditorialPrompt(articleText, meta), {
    client,
    modelId,
    maxTokens: 300,
    temperature: 0,
  });
}

async function fetchWikipediaExtract(titulo, http = axios, { timeoutMs = 15000 } = {}) {
  try {
    const res = await http.get(wikipediaApiUrl(titulo), {
      timeout: timeoutMs,
      responseType: 'json',
      headers: { 'User-Agent': 'LePainRightNow/1.0 (lepain.lojadepaes.com.br)', Accept: 'application/json' },
      validateStatus: () => true,
    });
    if (res.status < 200 || res.status >= 300) return null;
    const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
    return parseWikipediaExtract(data);
  } catch {
    return null;
  }
}

async function countTodayAutoPairs(pool, now = new Date()) {
  const day = todaySaoPaulo(now);
  const result = await pool.query(
    `SELECT count(DISTINCT COALESCE(grupo_id, id))::int AS n
       FROM cms_posts
      WHERE origem = 'auto'
        AND secao = 'right_now'
        AND sistema_destino = 'lepain'
        AND idioma = 'pt'
        AND status IN ('sugestao', 'publicado')
        AND (criado_em AT TIME ZONE 'America/Sao_Paulo')::date = $1::date`,
    [day]
  );
  return Number(result.rows[0]?.n) || 0;
}

async function loadExistingForDedupe(pool) {
  const result = await pool.query(
    `SELECT titulo, link_url
       FROM cms_posts
      WHERE sistema_destino = 'lepain'
        AND secao = 'right_now'
        AND status IN ('sugestao', 'publicado', 'rascunho')
        AND criado_em >= now() - interval '30 days'`
  );
  return {
    existingUrls: result.rows.map((r) => r.link_url).filter(Boolean),
    existingTitles: result.rows.map((r) => r.titulo).filter(Boolean),
  };
}

async function insertSuggestionPair(pool, draft, meta, now = new Date()) {
  const link = meta.url;
  const slugPt = slugFromTitleAndUrl(draft.titulo_pt, link);
  const slugEn = `${slugPt}-en`;
  const sentidos = (draft.sentidos || []).map((s) => String(s).toLowerCase());
  const fonte = String(draft.fonte || meta.fonte || '').trim().slice(0, 80);
  const trecho = String(draft.trecho_base || '').trim().slice(0, 200);
  const dataMateria = dateOnly(meta.dataMateria) || dateOnly(now);
  const dataEvento =
    String(draft.tipo).toLowerCase() === 'evento' ? dateOnly(draft.data_evento) : null;
  const expira = expireAtFrom(now);
  const tipo = String(draft.tipo).toLowerCase();

  const pt = await pool.query(
    `INSERT INTO cms_posts
      (slug, titulo, resumo, conteudo_html, sistema_destino, status, secao, idioma,
       sentidos, right_now_tipo, data_evento, link_url, fonte, origem, sugestao_expira_em,
       trecho_base, data_materia)
     VALUES ($1,$2,$3,$4,'lepain','sugestao','right_now','pt',
             $5,$6,$7,$8,$9,'auto',$10,$11,$12)
     RETURNING id`,
    [
      slugPt,
      draft.titulo_pt.trim(),
      draft.resumo_pt.trim(),
      draft.markdown_pt.trim(),
      sentidos,
      tipo,
      dataEvento,
      link,
      fonte,
      expira,
      trecho,
      dataMateria,
    ]
  );
  const ptId = pt.rows[0].id;
  await pool.query(`UPDATE cms_posts SET grupo_id = id WHERE id = $1`, [ptId]);

  await pool.query(
    `INSERT INTO cms_posts
      (slug, titulo, resumo, conteudo_html, sistema_destino, status, secao, idioma, grupo_id,
       sentidos, right_now_tipo, data_evento, link_url, fonte, origem, sugestao_expira_em,
       trecho_base, data_materia)
     VALUES ($1,$2,$3,$4,'lepain','sugestao','right_now','en',$5,
             $6,$7,$8,$9,$10,'auto',$11,$12,$13)`,
    [
      slugEn,
      draft.titulo_en.trim(),
      draft.resumo_en.trim(),
      draft.markdown_en.trim(),
      ptId,
      sentidos,
      tipo,
      dataEvento,
      link,
      fonte,
      expira,
      trecho,
      dataMateria,
    ]
  );
  return ptId;
}

function blankStats() {
  return {
    feeds: [],
    layers: { content_encoded: 0, page: 0 },
    discarded: {
      keyword: 0,
      idade: 0,
      dedupe: 0,
      sem_texto: 0,
      http_4xx: 0,
      timeout: 0,
      paywall: 0,
      editorial: 0,
      validacao: 0,
      bedrock: 0,
      link: 0,
      wikipedia: 0,
    },
    // Filtro editorial: contagem em discarded.editorial; nota e motivo de cada matéria avaliada aqui.
    editorial: { avaliadas: 0, aprovadas: 0, rejeitadas: 0, itens: [] },
    wikipedia: { tentados: [], criadas: 0 },
    bedrock_timeouts: 0,
  };
}

function createProgress(onProgress) {
  const state = { phase: 'iniciando', materias: 0, com_texto: 0, aprovadas: 0, message: '' };
  return {
    state,
    set(patch) {
      Object.assign(state, patch);
      if (typeof onProgress !== 'function') return;
      try {
        onProgress({ ...state });
      } catch {
        /* progresso nunca derruba a rodada */
      }
    },
  };
}

async function loadWikipediaUsados(pool, now = new Date()) {
  const since = new Date(now.getTime() - WIKIPEDIA_COOLDOWN_DAYS * 24 * 60 * 60 * 1000);
  const result = await pool.query(
    `SELECT link_url
       FROM cms_posts
      WHERE sistema_destino = 'lepain'
        AND link_url ILIKE '%wikipedia.org/wiki/%'
        AND criado_em >= $1::timestamptz`,
    [since.toISOString()]
  );
  return result.rows.map((r) => wikipediaTitleFromLink(r.link_url)).filter(Boolean);
}

/**
 * Curiosidades da Wikipédia (sem limite de idade). Até `limit` pares; pula verbetes dos últimos 30 dias.
 * Retorna ids criados e atualiza stats/progress.
 */
async function gerarCuriosidadesWikipedia(pool, ctx) {
  const { http, now, stats, progress, limit, verbetes, deps, state } = ctx;
  const created = [];
  if (limit <= 0 || !verbetes.length) return created;

  let usados = [];
  try {
    usados = await loadWikipediaUsados(pool, now);
  } catch (err) {
    console.warn(`[cms-sugestoes] wikipedia usados: ${err.message}`);
  }
  const fila = pickWikipediaTitles(verbetes, usados, {
    max: verbetes.length,
    random: deps.random || Math.random,
  });
  progress.set({ phase: 'curiosidades', message: 'Buscando curiosidades na Wikipédia…' });

  for (const titulo of fila) {
    if (created.length >= limit || state.bedrockDown) break;
    const verbete = await (deps.fetchWikipediaExtract || fetchWikipediaExtract)(titulo, http);
    if (!verbete) {
      stats.discarded.wikipedia += 1;
      stats.wikipedia.tentados.push({ titulo, resultado: 'indisponivel' });
      continue;
    }
    const link = wikipediaVerbeteUrl(titulo);
    const meta = { title: verbete.titulo || titulo, url: link, fonte: 'Wikipédia', tipoForcado: 'curiosidade' };
    let draft;
    try {
      draft = await callBedrockGuarded(
        () =>
          deps.invokeBedrock
            ? deps.invokeBedrock(verbete.extract, meta)
            : invokeBedrock(verbete.extract, meta, {
                client: deps.bedrockClient,
                modelId: deps.modelId,
              }),
        { deps, stats, state }
      );
    } catch (err) {
      console.warn(`[cms-sugestoes] wikipedia bedrock: ${err.message}`);
      stats.discarded.bedrock += 1;
      stats.wikipedia.tentados.push({ titulo, resultado: 'bedrock' });
      continue;
    }
    draft.tipo = 'curiosidade';
    draft.link_url = link;
    draft.fonte = 'Wikipédia';
    const validated = validateSuggestionDraft(draft, verbete.extract, { now, skipLink: true });
    if (!validated.ok) {
      stats.discarded.validacao += 1;
      stats.wikipedia.tentados.push({ titulo, resultado: 'validacao', erros: validated.errors });
      continue;
    }
    try {
      const id = await insertSuggestionPair(
        pool,
        draft,
        { url: link, fonte: 'Wikipédia', dataMateria: now },
        now
      );
      created.push({ id, titulo: draft.titulo_pt, tipo: 'curiosidade', link, fonte: 'Wikipédia' });
      stats.wikipedia.criadas += 1;
      stats.wikipedia.tentados.push({ titulo, resultado: 'criada' });
    } catch (err) {
      console.warn(`[cms-sugestoes] wikipedia insert: ${err.message}`);
    }
  }
  return created;
}

/**
 * Chama o Bedrock com timeout e conta falhas seguidas. Após 3 falhas seguidas marca
 * `state.bedrockDown` para a rodada parar de gastar tempo.
 */
async function callBedrockGuarded(fn, { deps, stats, state }) {
  const ms = deps.bedrockTimeoutMs || BEDROCK_TIMEOUT_MS;
  try {
    const out = await withTimeout(fn(), ms);
    state.bedrockFails = 0;
    state.bedrockSucceeded = true;
    return out;
  } catch (err) {
    state.bedrockFails = (state.bedrockFails || 0) + 1;
    if (isTimeoutError(err)) {
      stats.bedrock_timeouts += 1;
      state.bedrockTimedOut = true;
    }
    if (state.bedrockFails >= BEDROCK_MAX_CONSECUTIVE_FAILS) state.bedrockDown = true;
    throw err;
  }
}

/**
 * Gera sugestões (botão Gerar sugestões e job diário).
 * Fluxo: feeds -> keyword/idade/dedupe -> texto -> filtro editorial (nota >= 7) -> rascunho PT/EN;
 * depois completa com até 2 curiosidades da Wikipédia.
 *
 * deps.onProgress({phase, materias, com_texto, aprovadas, message}) acompanha a rodada.
 * Erros com texto para o gestor saem como SugestoesError (code + message).
 */
async function gerarSugestoes(pool, deps = {}) {
  const now = deps.now || new Date();
  const http = deps.http || axios;
  const cfg = deps.fontesConfig || loadFontesConfig(deps.fontesPath || FONTES_PATH);
  const feeds = deps.feeds || cfg.feeds;
  const keywords = deps.keywords || cfg.keywords;
  const fonteNomes = deps.fonteNomes || cfg.fonteNomes || {};
  const verbetes = deps.wikipediaVerbetes || cfg.wikipediaVerbetes || [];
  const stats = blankStats();
  const progress = createProgress(deps.onProgress);
  const state = { bedrockFails: 0, bedrockDown: false, bedrockTimedOut: false };

  progress.set({ phase: 'iniciando', message: 'Conferindo o que já foi gerado hoje…' });
  const already = await countTodayAutoPairs(pool, now);
  const slots = Math.max(0, (deps.cap ?? DAILY_CAP) - already);
  if (slots <= 0) {
    progress.set({ phase: 'concluido', message: 'Limite diário de sugestões já atingido.' });
    return {
      created: 0,
      ids: [],
      items: [],
      skipped: 'cap_atingido',
      already,
      slots: 0,
      shortfall_message: null,
      discarded_summary: [],
      stats,
    };
  }

  const { existingUrls, existingTitles } = await loadExistingForDedupe(pool);
  const raw = [];
  let feedsOk = 0;

  progress.set({ phase: 'buscando', message: 'Buscando matérias nos feeds…' });
  for (const feed of feeds) {
    const got = await fetchFeed(feed.url, http);
    const feedStat = {
      id: feed.id,
      url: feed.url,
      http: got.status,
      items: 0,
      kept: 0,
      error: got.ok ? null : got.error,
    };
    if (!got.ok) {
      console.warn(`[cms-sugestoes] feed ${feed.id}: ${got.error || got.status}`);
      stats.feeds.push(feedStat);
      continue;
    }
    feedsOk += 1;
    const items = parseRssItems(got.xml);
    feedStat.items = items.length;
    for (const item of items) {
      if (item.pubDate && !isWithinLastDays(item.pubDate, LOOKBACK_DAYS, now)) {
        stats.discarded.idade += 1;
        continue;
      }
      if (!matchesKeywords(item.title, item.description, keywords)) {
        stats.discarded.keyword += 1;
        continue;
      }
      raw.push({
        ...item,
        feedId: feed.id,
        fonteHint: feed.fonte || item.sourceHint || '',
      });
      feedStat.kept += 1;
    }
    stats.feeds.push(feedStat);
  }

  const beforeDedupe = raw.length;
  const candidates = dedupeCandidates(raw, { existingUrls, existingTitles }).sort((a, b) => {
    const ta = a.pubDate instanceof Date && !Number.isNaN(a.pubDate.getTime()) ? a.pubDate.getTime() : 0;
    const tb = b.pubDate instanceof Date && !Number.isNaN(b.pubDate.getTime()) ? b.pubDate.getTime() : 0;
    return tb - ta;
  });
  stats.discarded.dedupe += Math.max(0, beforeDedupe - candidates.length);
  progress.set({
    materias: candidates.length,
    message: `${candidates.length} matérias encontradas.`,
  });

  const created = [];
  const seen = new Set(existingUrls.map(normalizeUrl));
  const wikiReserve = Math.min(WIKIPEDIA_MAX_PER_ROUND, Math.floor(slots * 0.4));
  const newsLimit = Math.max(0, slots - wikiReserve);
  const maxExaminar = deps.maxCandidatos ?? MAX_CANDIDATES_EXAMINED;
  let examined = 0;

  for (const item of candidates) {
    if (created.length >= newsLimit || state.bedrockDown || examined >= maxExaminar) break;
    const finalUrl = String(item.link || '').trim();
    const norm = normalizeUrl(finalUrl);
    if (!norm || seen.has(norm)) {
      stats.discarded.dedupe += 1;
      continue;
    }
    examined += 1;

    progress.set({ phase: 'lendo', message: `Lendo matéria ${examined} de ${Math.min(candidates.length, maxExaminar)}…` });
    let grounded;
    try {
      grounded = await groundItem(item, http, {
        readabilityExtract: deps.readabilityExtract || readabilityExtract,
        pageTimeoutMs: deps.pageTimeoutMs || PAGE_TIMEOUT_MS,
      });
    } catch (err) {
      console.warn(`[cms-sugestoes] ground: ${err.message}`);
      stats.discarded.sem_texto += 1;
      continue;
    }
    if (!grounded.ok) {
      const reason = grounded.reason || 'sem_texto';
      stats.discarded[reason] = (stats.discarded[reason] || 0) + 1;
      console.warn(`[cms-sugestoes] descarte ${reason} ${finalUrl.slice(0, 80)}`);
      continue;
    }
    if (grounded.layer === 'content_encoded') stats.layers.content_encoded += 1;
    if (grounded.layer === 'page') stats.layers.page += 1;
    progress.set({ com_texto: progress.state.com_texto + 1 });

    if (!(await checkLinkOk(finalUrl, http))) {
      stats.discarded.link += 1;
      continue;
    }

    const fonte = resolveFonteNome(finalUrl, {
      ogSiteName: grounded.ogSiteName,
      fonteNomes,
      hint: item.fonteHint,
    });
    const meta = { title: item.title, url: finalUrl, fonte };

    // Filtro editorial ANTES do rascunho completo.
    progress.set({ phase: 'avaliando', message: 'Avaliando se um amante de pão leria isto…' });
    let editorial;
    try {
      const rawEditorial = await callBedrockGuarded(
        () =>
          deps.invokeEditorial
            ? deps.invokeEditorial(grounded.text, meta)
            : invokeEditorialBedrock(grounded.text, meta, {
                client: deps.bedrockClient,
                modelId: deps.modelId,
              }),
        { deps, stats, state }
      );
      editorial = normalizeEditorial(rawEditorial);
    } catch (err) {
      console.warn(`[cms-sugestoes] editorial: ${err.message}`);
      stats.discarded.bedrock += 1;
      continue;
    }
    stats.editorial.avaliadas += 1;
    const aprovado = editorialPasses(editorial);
    if (stats.editorial.itens.length < EDITORIAL_ITEMS_CAP) {
      stats.editorial.itens.push({
        titulo: item.title,
        url: finalUrl,
        fonte,
        score: editorial.score,
        motivo: editorial.motivo,
        aprovado,
      });
    }
    if (!aprovado) {
      stats.discarded.editorial += 1;
      stats.editorial.rejeitadas += 1;
      continue;
    }
    stats.editorial.aprovadas += 1;

    progress.set({ phase: 'escrevendo', message: 'Escrevendo o rascunho em PT e EN…' });
    let draft;
    try {
      draft = await callBedrockGuarded(
        () =>
          deps.invokeBedrock
            ? deps.invokeBedrock(grounded.text, meta)
            : invokeBedrock(grounded.text, meta, {
                client: deps.bedrockClient,
                modelId: deps.modelId,
              }),
        { deps, stats, state }
      );
    } catch (err) {
      console.warn(`[cms-sugestoes] bedrock: ${err.message}`);
      stats.discarded.bedrock += 1;
      continue;
    }

    draft.link_url = finalUrl;
    draft.fonte = fonte;
    const validated = validateSuggestionDraft(draft, grounded.text, {
      now,
      skipLink: true,
    });
    if (!validated.ok) {
      stats.discarded.validacao += 1;
      continue;
    }

    try {
      const id = await insertSuggestionPair(
        pool,
        draft,
        {
          url: finalUrl,
          fonte,
          dataMateria: item.pubDate || now,
        },
        now
      );
      created.push({
        id,
        titulo: draft.titulo_pt,
        tipo: String(draft.tipo).toLowerCase(),
        link: finalUrl,
        fonte,
        editorial: { score: editorial.score, motivo: editorial.motivo },
      });
      seen.add(norm);
      progress.set({ aprovadas: created.length });
    } catch (err) {
      console.warn(`[cms-sugestoes] insert: ${err.message}`);
    }
  }

  // Curiosidades da Wikipédia: completam a rodada (até 2), mesmo se as notícias falharem.
  const wikiLimit = Math.min(WIKIPEDIA_MAX_PER_ROUND, slots - created.length);
  const wiki = await gerarCuriosidadesWikipedia(pool, {
    http,
    now,
    stats,
    progress,
    limit: wikiLimit,
    verbetes,
    deps,
    state,
  });
  created.push(...wiki);
  progress.set({ aprovadas: created.length });

  if (!created.length) {
    // Nada criado e o Bedrock nunca respondeu (só estourou o tempo): o gestor precisa saber.
    if (state.bedrockTimedOut && !state.bedrockSucceeded) {
      throw new SugestoesError('bedrock_timeout', humanError('bedrock_timeout'));
    }
    if (feedsOk === 0) {
      throw new SugestoesError('sem_feeds', humanError('sem_feeds'));
    }
  }

  const shortfall = buildShortfallMessage(created.length, slots);
  progress.set({
    phase: 'concluido',
    message: shortfall || `${created.length} de ${slots} sugestões criadas.`,
  });
  return {
    created: created.length,
    ids: created.map((c) => c.id),
    items: created,
    already,
    slots,
    shortfall_message: shortfall,
    discarded_summary: summarizeDiscarded(stats.discarded),
    stats,
  };
}

async function expireOverdueSugestoes(pool, now = new Date()) {
  const result = await pool.query(
    `UPDATE cms_posts
        SET status = 'descartado', atualizado_em = now()
      WHERE status = 'sugestao'
        AND sugestao_expira_em IS NOT NULL
        AND sugestao_expira_em <= $1
      RETURNING id`,
    [now.toISOString()]
  );
  return result.rows.map((r) => r.id);
}

module.exports = {
  loadFontes,
  loadFontesConfig,
  bedrockConfig,
  createBedrockClient,
  converseJson,
  fetchFeed,
  fetchFeedXml,
  groundFromContentEncoded,
  groundFromPage,
  groundItem,
  checkLinkOk,
  invokeBedrock,
  invokeEditorialBedrock,
  fetchWikipediaExtract,
  loadWikipediaUsados,
  gerarCuriosidadesWikipedia,
  countTodayAutoPairs,
  insertSuggestionPair,
  blankStats,
  createProgress,
  withTimeout,
  SugestoesError,
  HUMAN_ERRORS,
  humanError,
  gerarSugestoes,
  expireOverdueSugestoes,
  readabilityExtract,
  FONTES_PATH,
  PAGE_TIMEOUT_MS,
  USER_AGENT,
};
