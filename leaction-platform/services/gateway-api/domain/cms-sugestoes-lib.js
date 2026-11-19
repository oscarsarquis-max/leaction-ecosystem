'use strict';

const crypto = require('crypto');

const SENTIDOS = new Set(['olhar', 'toque', 'aroma', 'sabor', 'som', 'memoria']);
const TIPOS = new Set(['noticia', 'curiosidade', 'evento']);
const TITLE_MAX = 70;
const RESUMO_MAX = 140;
const TRECHO_MAX = 200;
const FONTE_MAX = 80;
const SIMILARITY_THRESHOLD = 0.82;
const DAILY_CAP = 5;
const EXPIRE_HOURS = 48;
// Feeds diretos de padaria têm volume menor que o Google News; 21 dias cobre a fila útil.
const LOOKBACK_DAYS = 21;
const MIN_GROUNDED_CHARS = 600;
const DEFAULT_KEYWORDS = [
  'pao',
  'padaria',
  'panifica',
  'fermenta',
  'panetone',
  'trigo',
  'farinha',
  'confeitaria',
  'gastronom',
];

function normalizeUrl(raw) {
  if (raw == null || raw === '') return '';
  let text = String(raw).trim();
  try {
    const u = new URL(text);
    u.hash = '';
    let path = u.pathname || '/';
    if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
    u.pathname = path;
    const host = u.hostname.toLowerCase().replace(/^www\./, '');
    return `${u.protocol}//${host}${u.pathname}${u.search}`.toLowerCase();
  } catch {
    return text.toLowerCase().replace(/\/+$/, '');
  }
}

function normalizeTitle(raw) {
  return String(raw || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function titleTokens(raw) {
  const text = normalizeTitle(raw);
  if (!text) return [];
  return text.split(' ').filter((t) => t.length > 2);
}

function jaccard(a, b) {
  const setA = new Set(a);
  const setB = new Set(b);
  if (!setA.size && !setB.size) return 1;
  if (!setA.size || !setB.size) return 0;
  let inter = 0;
  for (const t of setA) if (setB.has(t)) inter += 1;
  return inter / (setA.size + setB.size - inter);
}

function titlesSimilar(a, b, threshold = SIMILARITY_THRESHOLD) {
  const score = jaccard(titleTokens(a), titleTokens(b));
  return score >= threshold;
}

function extractNumbers(text) {
  const found = String(text || '').match(/\d+(?:[.,]\d+)?/g) || [];
  return found.map((n) => n.replace(',', '.'));
}

function numbersInResumoAppearInArticle(resumo, articleText) {
  const nums = extractNumbers(resumo);
  if (!nums.length) return true;
  const hay = String(articleText || '');
  return nums.every((n) => {
    const plain = n.replace(/\./g, '');
    const withDot = n;
    const withComma = n.replace('.', ',');
    return (
      hay.includes(withDot) ||
      hay.includes(withComma) ||
      (plain !== withDot && hay.includes(plain))
    );
  });
}

function dateOnly(value) {
  if (value == null || value === '') return null;
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const y = value.getFullYear();
    const m = String(value.getMonth() + 1).padStart(2, '0');
    const d = String(value.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(String(value).trim());
  return match ? match[1] : null;
}

function todaySaoPaulo(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

function saoPauloParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(now);
  const get = (type) => parts.find((p) => p.type === type)?.value;
  return {
    year: Number(get('year')),
    month: Number(get('month')),
    day: Number(get('day')),
    hour: Number(get('hour') === '24' ? '0' : get('hour')),
    minute: Number(get('minute')),
    date: todaySaoPaulo(now),
  };
}

function isWithinLastDays(isoOrDate, days = LOOKBACK_DAYS, now = new Date()) {
  if (!isoOrDate) return false;
  const date = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate);
  if (Number.isNaN(date.getTime())) return false;
  const ms = days * 24 * 60 * 60 * 1000;
  return date.getTime() >= now.getTime() - ms && date.getTime() <= now.getTime() + 60 * 60 * 1000;
}

function isEventDatePast(value, now = new Date()) {
  const day = dateOnly(value);
  if (!day) return false;
  return day < todaySaoPaulo(now);
}

function expireAtFrom(now = new Date()) {
  return new Date(now.getTime() + EXPIRE_HOURS * 60 * 60 * 1000).toISOString();
}

function isExpired(sugestaoExpiraEm, now = new Date()) {
  if (!sugestaoExpiraEm) return false;
  const date = new Date(sugestaoExpiraEm);
  if (Number.isNaN(date.getTime())) return false;
  return date.getTime() <= now.getTime();
}

function slugify(input) {
  return String(input || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 200);
}

function shortHash(input, len = 6) {
  return crypto.createHash('sha1').update(String(input || '')).digest('hex').slice(0, len);
}

function slugFromTitleAndUrl(titulo, url) {
  const base = slugify(titulo) || 'sugestao';
  return `${base}-${shortHash(normalizeUrl(url) || url)}`;
}

function stripHtml(html) {
  let text = String(html || '');
  text = text.replace(/<script[\s\S]*?<\/script>/gi, ' ');
  text = text.replace(/<style[\s\S]*?<\/style>/gi, ' ');
  text = text.replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ');
  text = text.replace(/<!--[\s\S]*?-->/g, ' ');
  text = text.replace(/<\/(p|div|br|li|h[1-6]|tr)>/gi, '\n');
  text = text.replace(/<[^>]+>/g, ' ');
  text = text
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)));
  return text.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').replace(/[ \t]{2,}/g, ' ').trim();
}

function pickRssTag(body, tag) {
  const cdata = new RegExp(
    `<${tag}[^>]*><!\\[CDATA\\[([\\s\\S]*?)\\]\\]><\\/${tag}>`,
    'i'
  ).exec(body);
  if (cdata) return cdata[1].trim();
  const plain = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i').exec(body);
  return plain ? plain[1].trim() : '';
}

function parseRssItems(xml) {
  const items = [];
  const chunks = String(xml || '').split(/<item[\s>]/i).slice(1);
  for (const chunk of chunks) {
    const body = chunk.split(/<\/item>/i)[0] || '';
    const titleHtml = pickRssTag(body, 'title');
    const title = stripHtml(titleHtml).trim();
    let link = stripHtml(pickRssTag(body, 'link')).trim();
    if (!link) {
      const guid = stripHtml(pickRssTag(body, 'guid')).trim();
      if (/^https?:\/\//i.test(guid)) link = guid;
    }
    const pubDate =
      pickRssTag(body, 'pubDate') ||
      pickRssTag(body, 'published') ||
      pickRssTag(body, 'dc:date');
    const descriptionHtml =
      pickRssTag(body, 'description') || pickRssTag(body, 'summary') || '';
    const contentEncoded =
      pickRssTag(body, 'content:encoded') ||
      pickRssTag(body, 'content') ||
      '';
    if (!title || !link) continue;
    items.push({
      title,
      link,
      pubDate: pubDate ? new Date(pubDate) : null,
      sourceHint: stripHtml(pickRssTag(body, 'source') || '').trim(),
      description: stripHtml(descriptionHtml).trim(),
      contentEncoded,
    });
  }
  return items;
}

function matchesKeywords(title, summary, keywords = DEFAULT_KEYWORDS) {
  const hay = normalizeTitle(`${title || ''} ${summary || ''}`);
  if (!hay) return false;
  return (keywords || DEFAULT_KEYWORDS).some((kw) =>
    hay.includes(normalizeTitle(kw))
  );
}

function looksLikePaywall(html, text) {
  const blob = `${String(html || '')}\n${String(text || '')}`.toLowerCase();
  if (
    /\b(?:metered-|piano-|hard[-\s]?)?paywall\b|assine para continuar|subscribe to continue/.test(
      blob
    )
  ) {
    return true;
  }
  if (/para continuar lendo|conteúdo exclusivo para assinantes|faça login para ler/.test(blob)) {
    return true;
  }
  return false;
}

/**
 * Extrai texto legível de HTML (camada página). Preferir Readability quando disponível.
 */
function extractReadableText(html, { readabilityExtract } = {}) {
  const raw = String(html || '');
  if (!raw.trim()) return '';
  if (typeof readabilityExtract === 'function') {
    try {
      const got = readabilityExtract(raw);
      if (got && String(got).trim()) return String(got).trim();
    } catch {
      /* fallback */
    }
  }
  const article = raw.match(/<article[\s\S]*?<\/article>/i);
  const main = raw.match(/<main[\s\S]*?<\/main>/i);
  return stripHtml(article?.[0] || main?.[0] || raw);
}

function dedupeCandidates(candidates, { existingUrls = [], existingTitles = [] } = {}) {
  const seenUrls = new Set(existingUrls.map(normalizeUrl).filter(Boolean));
  const keptTitles = existingTitles.map((t) => String(t || ''));
  const out = [];
  for (const item of candidates) {
    const url = normalizeUrl(item.link || item.url);
    if (!url || seenUrls.has(url)) continue;
    const title = item.title || item.titulo || '';
    if (keptTitles.some((t) => titlesSimilar(t, title))) continue;
    seenUrls.add(url);
    keptTitles.push(title);
    out.push({ ...item, link: item.link || item.url, _normUrl: url });
  }
  return out;
}

function validateDraftLengths(draft) {
  const errors = [];
  const tipo = String(draft?.tipo || '').trim().toLowerCase();
  if (!TIPOS.has(tipo)) errors.push('tipo inválido');
  const tituloPt = String(draft?.titulo_pt || '').trim();
  const resumoPt = String(draft?.resumo_pt || '').trim();
  const tituloEn = String(draft?.titulo_en || '').trim();
  const resumoEn = String(draft?.resumo_en || '').trim();
  const markdownPt = String(draft?.markdown_pt || '').trim();
  const markdownEn = String(draft?.markdown_en || '').trim();
  const fonte = String(draft?.fonte || '').trim();
  const trecho = String(draft?.trecho_base || '').trim();
  if (!tituloPt || [...tituloPt].length > TITLE_MAX) errors.push('titulo_pt inválido');
  if (!resumoPt || [...resumoPt].length > RESUMO_MAX) errors.push('resumo_pt inválido');
  if (!tituloEn || [...tituloEn].length > TITLE_MAX) errors.push('titulo_en inválido');
  if (!resumoEn || [...resumoEn].length > RESUMO_MAX) errors.push('resumo_en inválido');
  if (!markdownPt || !markdownEn) errors.push('markdown obrigatório');
  if (!fonte || [...fonte].length > FONTE_MAX) errors.push('fonte inválida');
  if (!trecho || [...trecho].length > TRECHO_MAX) errors.push('trecho_base inválido');
  const sentidos = Array.isArray(draft?.sentidos) ? draft.sentidos : [];
  if (!sentidos.length || sentidos.some((s) => !SENTIDOS.has(String(s).toLowerCase()))) {
    errors.push('sentidos inválidos');
  }
  if (tipo === 'evento') {
    const de = dateOnly(draft?.data_evento);
    if (!de) errors.push('data_evento obrigatória para evento');
  }
  return errors;
}

function validateSuggestionDraft(draft, articleText, { now = new Date(), skipLink = true } = {}) {
  const errors = validateDraftLengths(draft);
  if (!numbersInResumoAppearInArticle(draft?.resumo_pt, articleText)) {
    errors.push('números do resumo_pt ausentes no texto');
  }
  if (!numbersInResumoAppearInArticle(draft?.resumo_en, articleText)) {
    errors.push('números do resumo_en ausentes no texto');
  }
  if (String(draft?.tipo || '').toLowerCase() === 'evento' && isEventDatePast(draft?.data_evento, now)) {
    errors.push('data_evento no passado');
  }
  if (!skipLink) {
    const link = String(draft?.link_url || draft?.link || '').trim();
    if (!/^https?:\/\//i.test(link)) errors.push('link inválido');
  }
  return { ok: errors.length === 0, errors };
}

function buildBedrockPrompt(articleText, meta = {}) {
  return [
    'Você é editor do blog LePain Right Now.',
    'Escreva APENAS a partir do texto extraído abaixo. Não invente fatos, números ou datas.',
    'Responda SOMENTE com JSON válido (sem markdown) no schema:',
    JSON.stringify({
      tipo: 'noticia|curiosidade|evento',
      titulo_pt: '<=70',
      resumo_pt: '<=140',
      markdown_pt: '2-3 paragrafos',
      titulo_en: '<=70',
      resumo_en: '<=140',
      markdown_en: '2-3 paragrafos',
      fonte: 'dominio curto <=80',
      sentidos: ['olhar|toque|aroma|sabor|som|memoria'],
      data_evento: 'AAAA-MM-DD ou null',
      trecho_base: 'citacao curta do texto <=200',
    }),
    `Fonte hint: ${meta.fonte || ''}`,
    `Título RSS: ${meta.title || ''}`,
    `URL: ${meta.url || ''}`,
    'TEXTO:',
    String(articleText || '').slice(0, 12000),
  ].join('\n');
}

function parseBedrockJson(raw) {
  const text = String(raw || '').trim();
  const fenced = /^```(?:json)?\s*([\s\S]*?)```$/i.exec(text);
  const body = fenced ? fenced[1].trim() : text;
  const start = body.indexOf('{');
  const end = body.lastIndexOf('}');
  if (start < 0 || end <= start) throw new Error('JSON Bedrock inválido');
  return JSON.parse(body.slice(start, end + 1));
}

module.exports = {
  SENTIDOS,
  TIPOS,
  TITLE_MAX,
  RESUMO_MAX,
  TRECHO_MAX,
  FONTE_MAX,
  SIMILARITY_THRESHOLD,
  DAILY_CAP,
  EXPIRE_HOURS,
  LOOKBACK_DAYS,
  MIN_GROUNDED_CHARS,
  DEFAULT_KEYWORDS,
  normalizeUrl,
  normalizeTitle,
  titlesSimilar,
  extractNumbers,
  numbersInResumoAppearInArticle,
  dateOnly,
  todaySaoPaulo,
  saoPauloParts,
  isWithinLastDays,
  isEventDatePast,
  expireAtFrom,
  isExpired,
  slugify,
  shortHash,
  slugFromTitleAndUrl,
  stripHtml,
  pickRssTag,
  parseRssItems,
  matchesKeywords,
  looksLikePaywall,
  extractReadableText,
  dedupeCandidates,
  validateDraftLengths,
  validateSuggestionDraft,
  buildBedrockPrompt,
  parseBedrockJson,
};
