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
  dateOnly,
  dedupeCandidates,
  expireAtFrom,
  extractReadableText,
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
} = require('./cms-sugestoes-lib');

const FONTES_PATH = path.join(__dirname, '../config/cms-sugestoes-fontes.json');
const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const PAGE_TIMEOUT_MS = 10000;

function loadFontesConfig(filePath = FONTES_PATH) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const parsed = JSON.parse(raw);
  return {
    feeds: Array.isArray(parsed.feeds) ? parsed.feeds : [],
    keywords: Array.isArray(parsed.keywords) && parsed.keywords.length
      ? parsed.keywords
      : DEFAULT_KEYWORDS,
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
      return { ok: true, text, layer: 'page', status: res.status };
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

async function invokeBedrock(articleText, meta, { client, modelId } = {}) {
  const cfg = bedrockConfig();
  const bedrock = client || createBedrockClient();
  const prompt = buildBedrockPrompt(articleText, meta);
  const command = new ConverseCommand({
    modelId: modelId || cfg.modelId,
    messages: [{ role: 'user', content: [{ text: prompt }] }],
    inferenceConfig: { maxTokens: 1800, temperature: 0.2 },
  });
  const out = await bedrock.send(command);
  const parts = out?.output?.message?.content || [];
  const text = parts.map((p) => p.text || '').join('').trim();
  return parseBedrockJson(text);
}

function fonteFromUrl(url, hint) {
  if (hint) return String(hint).trim().slice(0, 80);
  try {
    return new URL(url).hostname.replace(/^www\./, '').slice(0, 80);
  } catch {
    return 'fonte';
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
      validacao: 0,
      bedrock: 0,
      link: 0,
    },
  };
}

/**
 * Gera sugestões sob demanda (botão Gerar sugestões). Job 07:00 desligado.
 */
async function gerarSugestoes(pool, deps = {}) {
  const now = deps.now || new Date();
  const http = deps.http || axios;
  const cfg = deps.fontesConfig || loadFontesConfig(deps.fontesPath || FONTES_PATH);
  const feeds = deps.feeds || cfg.feeds;
  const keywords = deps.keywords || cfg.keywords;
  const stats = blankStats();

  const already = await countTodayAutoPairs(pool, now);
  const slots = Math.max(0, (deps.cap ?? DAILY_CAP) - already);
  if (slots <= 0) {
    return { created: 0, skipped: 'cap_atingido', already, slots: 0, stats };
  }

  const { existingUrls, existingTitles } = await loadExistingForDedupe(pool);
  const raw = [];

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
  const candidates = dedupeCandidates(raw, { existingUrls, existingTitles });
  stats.discarded.dedupe += Math.max(0, beforeDedupe - candidates.length);

  const createdIds = [];
  const seen = new Set(existingUrls.map(normalizeUrl));

  for (const item of candidates) {
    if (createdIds.length >= slots) break;
    const finalUrl = String(item.link || '').trim();
    const norm = normalizeUrl(finalUrl);
    if (!norm || seen.has(norm)) {
      stats.discarded.dedupe += 1;
      continue;
    }

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

    if (!(await checkLinkOk(finalUrl, http))) {
      stats.discarded.link += 1;
      continue;
    }

    let draft;
    try {
      draft = deps.invokeBedrock
        ? await deps.invokeBedrock(grounded.text, {
            title: item.title,
            url: finalUrl,
            fonte: fonteFromUrl(finalUrl, item.fonteHint),
          })
        : await invokeBedrock(
            grounded.text,
            {
              title: item.title,
              url: finalUrl,
              fonte: fonteFromUrl(finalUrl, item.fonteHint),
            },
            { client: deps.bedrockClient, modelId: deps.modelId }
          );
    } catch (err) {
      console.warn(`[cms-sugestoes] bedrock: ${err.message}`);
      stats.discarded.bedrock += 1;
      continue;
    }

    draft.link_url = finalUrl;
    if (!draft.fonte) draft.fonte = fonteFromUrl(finalUrl, item.fonteHint);
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
          fonte: draft.fonte,
          dataMateria: item.pubDate || now,
        },
        now
      );
      createdIds.push(id);
      seen.add(norm);
    } catch (err) {
      console.warn(`[cms-sugestoes] insert: ${err.message}`);
    }
  }

  return {
    created: createdIds.length,
    ids: createdIds,
    already,
    slots,
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
  fetchFeed,
  fetchFeedXml,
  groundFromContentEncoded,
  groundFromPage,
  groundItem,
  checkLinkOk,
  invokeBedrock,
  countTodayAutoPairs,
  insertSuggestionPair,
  gerarSugestoes,
  expireOverdueSugestoes,
  readabilityExtract,
  FONTES_PATH,
  PAGE_TIMEOUT_MS,
  USER_AGENT,
};
