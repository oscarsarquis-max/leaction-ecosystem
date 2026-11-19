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
  dateOnly,
  dedupeCandidates,
  expireAtFrom,
  isWithinLastDays,
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
const BATCH_EXECUTE_URL = 'https://news.google.com/_/DotsSplashUi/data/batchexecute';

function loadFontes(filePath = FONTES_PATH) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const parsed = JSON.parse(raw);
  return Array.isArray(parsed.feeds) ? parsed.feeds : [];
}

function isGoogleNewsWrapper(url) {
  return /news\.google\.com\/(?:rss\/)?articles\//i.test(String(url || ''));
}

function googleNewsArticleId(url) {
  const match = String(url || '').match(/\/articles\/([A-Za-z0-9_\-]+)/);
  return match ? match[1] : null;
}

function parseBatchexecuteDestination(body) {
  let text = String(body || '');
  if (text.startsWith(")]}'")) {
    const nl = text.indexOf('\n');
    text = nl >= 0 ? text.slice(nl + 1) : text.slice(4);
  }
  text = text.trim();
  const firstNl = text.indexOf('\n');
  if (firstNl > 0 && /^\d+$/.test(text.slice(0, firstNl).trim())) {
    text = text.slice(firstNl + 1);
  }
  let envelopes;
  try {
    envelopes = JSON.parse(text);
  } catch {
    const m = text.match(/garturlres","(https?:\\\/\\\/[^"]+)"/);
    if (!m) return null;
    return m[1].replace(/\\\//g, '/').replace(/\\u003d/g, '=');
  }
  if (!Array.isArray(envelopes)) return null;
  for (const env of envelopes) {
    if (!Array.isArray(env) || env.length < 3) continue;
    if (env[0] !== 'wrb.fr' || env[1] !== 'Fbv4je') continue;
    try {
      const payload = JSON.parse(env[2]);
      if (Array.isArray(payload) && payload[0] === 'garturlres' && typeof payload[1] === 'string') {
        return payload[1];
      }
    } catch {
      /* next */
    }
  }
  return null;
}

/**
 * Resolve post-2024 Google News wrappers via signature + batchexecute.
 */
async function resolveGoogleNewsUrl(url, http = axios) {
  const articleId = googleNewsArticleId(url);
  if (!articleId) return null;
  const page = await http.get(String(url), {
    timeout: 20000,
    maxRedirects: 5,
    responseType: 'text',
    headers: {
      'User-Agent': USER_AGENT,
      Accept: 'text/html,application/xhtml+xml,*/*',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    },
    validateStatus: (s) => s >= 200 && s < 400,
  });
  const html = String(page.data || '');
  const signature = (html.match(/data-n-a-sg="([^"]+)"/) || [])[1];
  const timestamp = (html.match(/data-n-a-ts="([^"]+)"/) || [])[1];
  if (!signature || !timestamp) return null;

  const rpcInner = JSON.stringify([
    'garturlreq',
    [
      ['X', 'X', ['X', 'X'], null, null, 1, 1, 'BR:pt-419', null, 1, null, null, null, null, null, 0, 1],
      'pt-BR',
      'BR',
      1,
      [1, 1, 1],
      1,
      1,
      null,
      0,
      0,
      null,
      0,
    ],
    articleId,
    Number(timestamp),
    signature,
  ]);
  const fReq = JSON.stringify([[['Fbv4je', rpcInner, null, 'generic']]]);
  const post = await http.post(
    BATCH_EXECUTE_URL,
    new URLSearchParams({ 'f.req': fReq }).toString(),
    {
      timeout: 20000,
      responseType: 'text',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'User-Agent': USER_AGENT,
        Referer: 'https://news.google.com/',
        Origin: 'https://news.google.com',
      },
      validateStatus: (s) => s >= 200 && s < 500,
    }
  );
  const destination = parseBatchexecuteDestination(post.data);
  if (!destination || isGoogleNewsWrapper(destination)) return null;
  return destination;
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

async function fetchFeedXml(url, http = axios) {
  const res = await http.get(url, {
    timeout: 20000,
    responseType: 'text',
    headers: { 'User-Agent': USER_AGENT, Accept: 'application/rss+xml, application/xml, text/xml, */*' },
    maxRedirects: 5,
    validateStatus: (s) => s >= 200 && s < 400,
  });
  return String(res.data || '');
}

async function resolveFinalUrl(url, http = axios) {
  const start = String(url || '').trim();
  if (!start) return null;
  try {
    if (isGoogleNewsWrapper(start)) {
      const decoded = await resolveGoogleNewsUrl(start, http);
      if (decoded) return decoded;
    }
    const res = await http.get(start, {
      timeout: 20000,
      maxRedirects: 8,
      responseType: 'text',
      headers: { 'User-Agent': USER_AGENT, Accept: 'text/html,application/xhtml+xml,*/*' },
      validateStatus: (s) => s >= 200 && s < 400,
    });
    const finalUrl =
      res.request?.res?.responseUrl ||
      res.request?.responseURL ||
      res.config?.url ||
      start;
    const resolved = String(finalUrl);
    if (isGoogleNewsWrapper(resolved)) {
      return (await resolveGoogleNewsUrl(resolved, http)) || null;
    }
    return resolved;
  } catch {
    return null;
  }
}

async function downloadArticle(url, http = axios) {
  const res = await http.get(url, {
    timeout: 25000,
    maxRedirects: 8,
    responseType: 'text',
    headers: { 'User-Agent': USER_AGENT, Accept: 'text/html,application/xhtml+xml,*/*' },
    validateStatus: (s) => s >= 200 && s < 400,
  });
  const finalUrl =
    res.request?.res?.responseUrl ||
    res.request?.responseURL ||
    res.config?.url ||
    url;
  const html = String(res.data || '');
  const text = stripHtml(html);
  if (text.length < 280) return { ok: false, reason: 'texto curto', url: finalUrl, text: '' };
  return { ok: true, url: String(finalUrl), text, status: res.status };
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

async function collectCandidates({ feeds, http, now }) {
  const raw = [];
  for (const feed of feeds) {
    try {
      const xml = await fetchFeedXml(feed.url, http);
      const items = parseRssItems(xml);
      for (const item of items) {
        if (item.pubDate && !isWithinLastDays(item.pubDate, LOOKBACK_DAYS, now)) continue;
        if (!item.pubDate) {
          /* sem data: ainda tenta; filtro final no artigo */
        }
        raw.push({
          ...item,
          feedId: feed.id,
          fonteHint: feed.fonte || item.sourceHint || '',
        });
      }
    } catch (err) {
      console.warn(`[cms-sugestoes] feed ${feed.id}: ${err.message}`);
    }
  }
  return raw;
}

/**
 * Gera sugestões até o teto diário (5 pares PT+EN).
 * deps injetáveis para testes (http, bedrock, fontesPath).
 */
async function gerarSugestoes(pool, deps = {}) {
  const now = deps.now || new Date();
  const http = deps.http || axios;
  const feeds = deps.feeds || loadFontes(deps.fontesPath || FONTES_PATH);
  const already = await countTodayAutoPairs(pool, now);
  const slots = Math.max(0, (deps.cap ?? DAILY_CAP) - already);
  if (slots <= 0) {
    return { created: 0, skipped: 'cap_atingido', already };
  }

  const { existingUrls, existingTitles } = await loadExistingForDedupe(pool);
  const candidates = dedupeCandidates(await collectCandidates({ feeds, http, now }), {
    existingUrls,
    existingTitles,
  });

  const createdIds = [];
  const seen = new Set(existingUrls.map(normalizeUrl));

  for (const item of candidates) {
    if (createdIds.length >= slots) break;
    let finalUrl = item.link;
    try {
      if (/news\.google\.com/i.test(finalUrl)) {
        const resolved = await resolveFinalUrl(finalUrl, http);
        if (!resolved || /news\.google\.com/i.test(resolved)) continue;
        finalUrl = resolved;
      }
      const norm = normalizeUrl(finalUrl);
      if (!norm || seen.has(norm)) continue;

      const article = await downloadArticle(finalUrl, http);
      if (!article.ok) continue;
      finalUrl = article.url;
      if (seen.has(normalizeUrl(finalUrl))) continue;

      if (!(await checkLinkOk(finalUrl, http))) continue;

      let draft;
      try {
        draft = deps.invokeBedrock
          ? await deps.invokeBedrock(article.text, {
              title: item.title,
              url: finalUrl,
              fonte: fonteFromUrl(finalUrl, item.fonteHint),
            })
          : await invokeBedrock(article.text, {
              title: item.title,
              url: finalUrl,
              fonte: fonteFromUrl(finalUrl, item.fonteHint),
            }, { client: deps.bedrockClient, modelId: deps.modelId });
      } catch (err) {
        console.warn(`[cms-sugestoes] bedrock: ${err.message}`);
        continue;
      }

      draft.link_url = finalUrl;
      if (!draft.fonte) draft.fonte = fonteFromUrl(finalUrl, item.fonteHint);
      const validated = validateSuggestionDraft(draft, article.text, { now, skipLink: true });
      if (!validated.ok) continue;

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
      seen.add(normalizeUrl(finalUrl));
    } catch (err) {
      console.warn(`[cms-sugestoes] item: ${err.message}`);
    }
  }

  return { created: createdIds.length, ids: createdIds, already, slots };
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
  bedrockConfig,
  createBedrockClient,
  fetchFeedXml,
  resolveFinalUrl,
  resolveGoogleNewsUrl,
  parseBatchexecuteDestination,
  isGoogleNewsWrapper,
  downloadArticle,
  checkLinkOk,
  invokeBedrock,
  countTodayAutoPairs,
  insertSuggestionPair,
  gerarSugestoes,
  expireOverdueSugestoes,
  FONTES_PATH,
};
