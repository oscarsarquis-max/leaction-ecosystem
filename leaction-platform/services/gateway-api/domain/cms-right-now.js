'use strict';

/**
 * BLOG-022/025 — reações + enquetes (públicas via X-LePain-Key; admin via JWT).
 * BLOG-025: enquete lúdica (sugerir / publicar / histórico / encerrar → Fornada).
 */

const crypto = require('crypto');
const { saoPauloParts, expireAtFrom, TITLE_MAX, RESUMO_MAX } = require('./cms-sugestoes-lib');
const { converseJson, insertSuggestionPair } = require('./cms-sugestoes-job');
const lojaClient = require('./loja-integracoes-client');

const ENQUETE_DIAS = 7;
const PRODUTO_CAMPOS = ['produto_id', 'produto_nome', 'produto_url'];
const OPCAO_IDS = ['a', 'b', 'c'];

const WINDOW_MS = 60 * 1000;
const LIMIT = 30;
const hits = new Map();

let enqueteSchedulerStarted = false;
let lastEnqueteWeekKey = null;

function resetRateLimit() {
  hits.clear();
}

function keyOf() {
  return String(process.env.LEPAIN_CMS_KEY || '');
}

function keyMatches(req) {
  const expected = keyOf();
  const got = String(req.get('x-lepain-key') || '');
  if (!expected || !got) return false;
  const a = Buffer.from(expected);
  const b = Buffer.from(got);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

function socketIp(req) {
  return String(req.ip || req.socket?.remoteAddress || 'unknown');
}

function allow(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((at) => now - at < WINDOW_MS);
  if (recent.length >= LIMIT) {
    hits.set(ip, recent);
    return false;
  }
  recent.push(now);
  hits.set(ip, recent);
  return true;
}

function guard(req, res) {
  const trusted = keyMatches(req);
  const forwarded = String(req.get('x-forwarded-for') || '')
    .split(',')[0]
    .trim();
  const ip = trusted && forwarded ? forwarded : socketIp(req);
  if (!allow(ip)) {
    res.status(429).json({ error: 'muitas requisições' });
    return false;
  }
  if (!trusted) {
    res.status(401).json({ error: 'não autorizado' });
    return false;
  }
  return true;
}

function visitanteOf(value) {
  const text = String(value || '').trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(text)) return null;
  return text;
}

function iso(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function parseStamp(value) {
  if (value == null || value === '') return { value: null, error: 'data obrigatória' };
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return { value: null, error: 'data inválida' };
  return { value: date.toISOString(), error: null };
}

function hasPreco(text) {
  return /\b(r\$|preço|preco|\$\s*\d)\b/i.test(String(text || ''));
}

function parseOpcoes(value) {
  if (!Array.isArray(value) || value.length < 2 || value.length > 4) {
    return { error: 'a enquete precisa de 2 a 4 opções' };
  }
  const opcoes = [];
  for (const item of value) {
    const pt = String(item?.pt || '').trim();
    const en = String(item?.en || '').trim();
    if (!pt || !en) return { error: 'cada opção precisa de texto em PT e EN' };
    const detalhe_pt = String(item?.detalhe_pt || item?.detalhe || '').trim();
    const detalhe_en = String(item?.detalhe_en || item?.detalhe || '').trim();
    const surface = `${pt} ${en} ${detalhe_pt} ${detalhe_en}`;
    if (hasPreco(surface)) {
      return { error: 'pergunta e opções não podem trazer preço' };
    }
    const id = String(item?.id || '').trim() || `o${opcoes.length + 1}`;
    if (!/^[A-Za-z0-9_-]{1,32}$/.test(id)) return { error: 'id de opção inválido' };
    const option = { id, pt, en };
    if (detalhe_pt) option.detalhe_pt = detalhe_pt;
    if (detalhe_en) option.detalhe_en = detalhe_en;
    if (item?.produto_id) option.produto_id = String(item.produto_id);
    if (item?.produto_nome) option.produto_nome = String(item.produto_nome).trim();
    if (item?.produto_url) option.produto_url = String(item.produto_url).trim();
    opcoes.push(option);
  }
  if (new Set(opcoes.map((item) => item.id)).size !== opcoes.length) {
    return { error: 'opções com id repetido' };
  }
  return { opcoes };
}

function resultadoDe(opcoes, rows) {
  const counts = new Map(rows.map((row) => [String(row.opcao_id), Number(row.n) || 0]));
  const total = [...counts.values()].reduce((sum, n) => sum + n, 0);
  const resultado = opcoes.map((opcao) => {
    const n = counts.get(opcao.id) || 0;
    return { id: opcao.id, pct: total ? Math.round((n * 100) / total) : 0 };
  });
  return { resultado, total };
}

async function contagem(pool, enqueteId) {
  const result = await pool.query(
    `SELECT opcao_id, count(*)::int AS n
       FROM cms_votos
      WHERE enquete_id = $1
      GROUP BY opcao_id`,
    [enqueteId]
  );
  return result.rows;
}

/** Produto só depois do voto (ou enquete fechada). Detalhe sempre pode ir. */
function opcoesPublicas(opcoes, { revelarProduto = false } = {}) {
  return opcoes.map((o) => {
    const copy = { ...o };
    if (!revelarProduto) {
      for (const campo of PRODUTO_CAMPOS) delete copy[campo];
    }
    return copy;
  });
}

function shapeEnquete(row, vote, counts) {
  const opcoes = Array.isArray(row.opcoes) ? row.opcoes : [];
  const fecha = new Date(row.fecha_em);
  const closed = !Number.isNaN(fecha.getTime()) && fecha.getTime() <= Date.now();
  const voted = Boolean(vote);
  const body = {
    id: row.id,
    pergunta_pt: row.pergunta_pt,
    pergunta_en: row.pergunta_en,
    opcoes: opcoesPublicas(opcoes, { revelarProduto: voted || closed }),
    fecha_em: iso(row.fecha_em),
    votou: voted,
  };
  if (voted || closed) {
    const tally = resultadoDe(opcoes, counts);
    body.resultado = tally.resultado;
    body.total = tally.total;
  }
  return body;
}

async function outraAberta(pool, selfId, abre, fecha) {
  const result = await pool.query(
    `SELECT id FROM cms_enquetes
      WHERE status = 'publicada'
        AND id <> $1
        AND abre_em < $3
        AND fecha_em > $2
      LIMIT 1`,
    [selfId || 0, abre, fecha]
  );
  return Boolean(result.rows[0]);
}

function parseEnquete(body) {
  const pergunta_pt = String(body.pergunta_pt || '').trim();
  const pergunta_en = String(body.pergunta_en || '').trim();
  if (!pergunta_pt || !pergunta_en) return { error: 'pergunta em PT e EN é obrigatória' };
  const parsed = parseOpcoes(body.opcoes);
  if (parsed.error) return parsed;
  const abre = parseStamp(body.abre_em);
  if (abre.error) return { error: `abre_em: ${abre.error}` };
  const fecha = parseStamp(body.fecha_em);
  if (fecha.error) return { error: `fecha_em: ${fecha.error}` };
  if (new Date(fecha.value) <= new Date(abre.value)) {
    return { error: 'fecha_em precisa ser depois de abre_em' };
  }
  const status = String(body.status || 'rascunho').trim().toLowerCase();
  if (!['rascunho', 'publicada', 'sugerida', 'encerrada'].includes(status)) {
    return { error: 'status inválido' };
  }
  if (hasPreco(`${pergunta_pt} ${pergunta_en}`)) {
    return { error: 'pergunta não pode trazer preço' };
  }
  return {
    pergunta_pt,
    pergunta_en,
    opcoes: parsed.opcoes,
    abre_em: abre.value,
    fecha_em: fecha.value,
    status,
  };
}

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function normalizeVitrineItem(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const id = String(raw.id || '').trim();
  const nome = String(raw.nome || raw.name || '').trim();
  const url = String(raw.url || raw.produto_url || '').trim();
  if (!id || !nome || !url) return null;
  return { id, nome, url };
}

function textMentionsProduct(text, produtos) {
  const lower = String(text || '').toLowerCase();
  return produtos.some((p) => {
    const nome = String(p.nome || '').trim().toLowerCase();
    return nome.length >= 3 && lower.includes(nome);
  });
}

function clip(text, max) {
  const chars = [...String(text || '').trim()];
  if (chars.length <= max) return chars.join('');
  return `${chars.slice(0, max - 1).join('').trimEnd()}…`;
}

function weekKeySaoPaulo(now = new Date()) {
  const parts = saoPauloParts(now);
  // ISO-ish week from SP calendar date (Mon-based).
  const utc = Date.UTC(parts.year, parts.month - 1, parts.day);
  const day = new Date(utc);
  const thursday = new Date(utc);
  thursday.setUTCDate(day.getUTCDate() + 4 - (day.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(thursday.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((thursday - yearStart) / 86400000 + 1) / 7);
  return `${thursday.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

function isMondaySaoPaulo(now = new Date()) {
  const weekday = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo',
    weekday: 'short',
  }).format(now);
  return weekday === 'Mon';
}

function semanaLabel(abre, fecha, idioma = 'pt') {
  const loc = idioma === 'en' ? 'en-US' : 'pt-BR';
  const opts = { timeZone: 'America/Sao_Paulo', day: 'numeric', month: 'short' };
  const a = new Date(abre);
  const f = new Date(fecha);
  if (Number.isNaN(a.getTime()) || Number.isNaN(f.getTime())) return '';
  const left = a.toLocaleDateString(loc, opts);
  const right = f.toLocaleDateString(loc, { ...opts, year: 'numeric' });
  return `${left} – ${right}`;
}

function pickVencedor(opcoes, tally, idioma = 'pt') {
  if (!tally.total || !Array.isArray(tally.resultado) || !tally.resultado.length) {
    return { texto: '', produto_nome: '', pct: 0, opcao: null };
  }
  const ranked = [...tally.resultado].sort((a, b) => b.pct - a.pct || String(a.id).localeCompare(String(b.id)));
  const best = ranked[0];
  const opcao = opcoes.find((o) => o.id === best.id) || null;
  const key = idioma === 'en' ? 'en' : 'pt';
  return {
    texto: opcao ? String(opcao[key] || '') : '',
    produto_nome: opcao ? String(opcao.produto_nome || '') : '',
    pct: best.pct,
    opcao,
  };
}

function buildEnquetePrompt(produtos) {
  const lista = produtos
    .map((p, i) => `${i + 1}. id=${p.id} nome="${p.nome}" url=${p.url}`)
    .join('\n');
  return `Você cria uma enquete lúdica sensorial para o blog LePain (padaria artesanal).

Produtos INTERNOS (nunca escreva nome, marca ou preço na pergunta nem nas opções):
${lista}

Responda APENAS JSON:
{
  "pergunta_pt": "",
  "pergunta_en": "",
  "opcoes": [
    { "id": "a", "pt": "", "en": "", "detalhe_pt": "", "detalhe_en": "", "produto_id": "" },
    { "id": "b", "pt": "", "en": "", "detalhe_pt": "", "detalhe_en": "", "produto_id": "" },
    { "id": "c", "pt": "", "en": "", "detalhe_pt": "", "detalhe_en": "", "produto_id": "" }
  ]
}

Regras:
- Tom brincalhão e sensorial (cheiro, crosta, miolo, domingo, pazes com o pão).
- Cada opção liga a exatamente um produto_id da lista (use os três).
- pergunta e textos pt/en/detalhe NÃO podem citar nome de produto nem preço.
- detalhe_pt/en: subtítulo curto sensorial (sem nome do produto).
- ids das opções: a, b, c.`;
}

async function gerarTextoEnquete(produtos, deps = {}) {
  const invoke = deps.converseJson || converseJson;
  const draft = await invoke(buildEnquetePrompt(produtos), {
    maxTokens: 1200,
    temperature: 0.7,
  });
  if (!draft || typeof draft !== 'object') throw new Error('bedrock_enquete_invalido');
  const pergunta_pt = String(draft.pergunta_pt || '').trim();
  const pergunta_en = String(draft.pergunta_en || '').trim();
  if (!pergunta_pt || !pergunta_en) throw new Error('bedrock_enquete_sem_pergunta');
  if (hasPreco(`${pergunta_pt} ${pergunta_en}`) || textMentionsProduct(`${pergunta_pt} ${pergunta_en}`, produtos)) {
    throw new Error('bedrock_enquete_vazou_produto');
  }
  const byId = new Map(produtos.map((p) => [String(p.id), p]));
  const rawOps = Array.isArray(draft.opcoes) ? draft.opcoes : [];
  const opcoes = [];
  for (let i = 0; i < 3; i += 1) {
    const raw = rawOps[i] || {};
    const produto =
      byId.get(String(raw.produto_id || '')) ||
      produtos[i];
    if (!produto) throw new Error('bedrock_enquete_produto');
    const pt = String(raw.pt || '').trim();
    const en = String(raw.en || '').trim();
    const detalhe_pt = String(raw.detalhe_pt || raw.detalhe || '').trim();
    const detalhe_en = String(raw.detalhe_en || raw.detalhe || '').trim();
    const surface = `${pt} ${en} ${detalhe_pt} ${detalhe_en}`;
    if (!pt || !en) throw new Error('bedrock_enquete_opcao');
    if (hasPreco(surface) || textMentionsProduct(surface, produtos)) {
      throw new Error('bedrock_enquete_vazou_produto');
    }
    opcoes.push({
      id: OPCAO_IDS[i],
      pt,
      en,
      detalhe_pt,
      detalhe_en,
      produto_id: String(produto.id),
      produto_nome: produto.nome,
      produto_url: produto.url,
    });
  }
  return { pergunta_pt, pergunta_en, opcoes };
}

function defaultWindow(now = new Date()) {
  const abre = now;
  const fecha = new Date(now.getTime() + ENQUETE_DIAS * 24 * 60 * 60 * 1000);
  return { abre_em: abre.toISOString(), fecha_em: fecha.toISOString() };
}

/**
 * Sorteia 3 produtos da vitrine + Bedrock → enquete status=sugerida.
 * @returns {{ ok: true, id: number } | { ok: false, status: number, error: string }}
 */
async function sugerirEnquete(pool, deps = {}) {
  const getVitrine = deps.getVitrine || lojaClient.getVitrine;
  const items = (await getVitrine()).map(normalizeVitrineItem).filter(Boolean);
  if (items.length < 3) {
    return { ok: false, status: 503, error: 'vitrine precisa de ao menos 3 produtos ativos' };
  }
  const produtos = shuffle(items).slice(0, 3);
  let draft;
  try {
    draft = await gerarTextoEnquete(produtos, deps);
  } catch (err) {
    console.warn('[cms-enquete] bedrock', err.message);
    return { ok: false, status: 502, error: 'falha ao gerar a enquete com IA' };
  }
  const window = defaultWindow(deps.now ? deps.now() : new Date());
  const result = await pool.query(
    `INSERT INTO cms_enquetes
       (pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status)
     VALUES ($1, $2, $3::jsonb, $4, $5, 'sugerida')
     RETURNING id`,
    [
      draft.pergunta_pt,
      draft.pergunta_en,
      JSON.stringify(draft.opcoes),
      window.abre_em,
      window.fecha_em,
    ]
  );
  return { ok: true, id: result.rows[0].id, opcoes: draft.opcoes, pergunta_pt: draft.pergunta_pt };
}

async function publicarEnquete(pool, id, deps = {}) {
  const found = await pool.query(`SELECT * FROM cms_enquetes WHERE id = $1`, [id]);
  const row = found.rows[0];
  if (!row) return { ok: false, status: 404, error: 'Enquete não encontrada' };
  if (row.status === 'publicada') return { ok: true, id, reused: true };
  if (row.status === 'encerrada') {
    return { ok: false, status: 409, error: 'enquete já encerrada' };
  }
  if (!['sugerida', 'rascunho'].includes(row.status)) {
    return { ok: false, status: 400, error: 'só rascunho ou sugerida podem ser publicadas' };
  }
  const now = deps.now ? deps.now() : new Date();
  const abre = now.toISOString();
  const fecha = new Date(now.getTime() + ENQUETE_DIAS * 24 * 60 * 60 * 1000).toISOString();
  if (await outraAberta(pool, id, abre, fecha)) {
    return { ok: false, status: 409, error: 'já existe uma enquete aberta nesse período' };
  }
  await pool.query(
    `UPDATE cms_enquetes
        SET status = 'publicada', abre_em = $2, fecha_em = $3
      WHERE id = $1`,
    [id, abre, fecha]
  );
  return { ok: true, id, abre_em: abre, fecha_em: fecha };
}

async function createFornadaSugestao(pool, { enquete, vencedor }) {
  const produtoNome = vencedor.produto_nome || vencedor.opcao?.produto_nome || 'pão da casa';
  const produtoUrl = vencedor.opcao?.produto_url || 'https://lojadepaes.com.br';
  const textoPt = vencedor.texto || vencedor.opcao?.pt || '';
  const textoEn = vencedor.opcao?.en || textoPt;
  const titulo_pt = clip(`Fornada: ${produtoNome}`, TITLE_MAX);
  const titulo_en = clip(`Bake day: ${produtoNome}`, TITLE_MAX);
  const resumo_pt = clip(
    `A enquete escolheu “${textoPt}”. Próxima fornada com ${produtoNome}.`,
    RESUMO_MAX
  );
  const resumo_en = clip(
    `The poll picked “${textoEn}”. Next bake features ${produtoNome}.`,
    RESUMO_MAX
  );
  const markdown_pt = [
    `A fornada da semana nasce da enquete: **${textoPt}**.`,
    '',
    `O pão da vez é **${produtoNome}**. Quem votou, sente o aroma; quem ainda não, encontra o link na loja.`,
  ].join('\n');
  const markdown_en = [
    `This week's bake comes from the poll: **${textoEn}**.`,
    '',
    `The loaf is **${produtoNome}**. Voters already know the scent; everyone else can meet it in the shop.`,
  ].join('\n');

  const postId = await insertSuggestionPair(
    pool,
    {
      tipo: 'promocao',
      titulo_pt,
      titulo_en,
      resumo_pt,
      resumo_en,
      markdown_pt,
      markdown_en,
      sentidos: ['sabor', 'aroma', 'memoria'],
      fonte: 'Enquete LePain',
      trecho_base: clip(textoPt, 200),
    },
    {
      url: produtoUrl,
      fonte: 'Enquete LePain',
      dataMateria: new Date(),
    }
  );

  // Garante expiração mesmo se insertSuggestionPair mudar assinatura.
  await pool.query(
    `UPDATE cms_posts
        SET sugestao_expira_em = COALESCE(sugestao_expira_em, $2::timestamptz),
            right_now_tipo = 'promocao'
      WHERE id = $1 OR grupo_id = $1`,
    [postId, expireAtFrom(new Date())]
  );

  await pool.query(`UPDATE cms_enquetes SET fornada_post_id = $2 WHERE id = $1`, [
    enquete.id,
    postId,
  ]);
  return postId;
}

/**
 * Encerra enquetes publicadas com fecha_em vencido e cria sugestão Fornada do vencedor.
 */
async function encerrarEnquetesVencidas(pool, deps = {}) {
  const now = deps.now ? deps.now() : new Date();
  const due = await pool.query(
    `SELECT * FROM cms_enquetes
      WHERE status = 'publicada'
        AND fecha_em <= $1
      ORDER BY fecha_em ASC
      LIMIT 20`,
    [now.toISOString()]
  );
  const closed = [];
  for (const row of due.rows) {
    const opcoes = Array.isArray(row.opcoes) ? row.opcoes : [];
    const tally = resultadoDe(opcoes, await contagem(pool, row.id));
    const vencedor = pickVencedor(opcoes, tally, 'pt');
    await pool.query(
      `UPDATE cms_enquetes
          SET status = 'encerrada', encerrada_em = $2
        WHERE id = $1 AND status = 'publicada'`,
      [row.id, now.toISOString()]
    );
    let fornadaId = row.fornada_post_id || null;
    if (!fornadaId && vencedor.opcao) {
      try {
        fornadaId = await createFornadaSugestao(pool, { enquete: row, vencedor });
      } catch (err) {
        console.error('[cms-enquete] fornada', err.message);
      }
    }
    closed.push({ id: row.id, fornada_post_id: fornadaId, total: tally.total });
  }
  return closed;
}

async function listHistorico(pool, { idioma = 'pt', limite = 3 } = {}) {
  const lim = Math.max(1, Math.min(Number(limite) || 3, 10));
  const lang = idioma === 'en' ? 'en' : 'pt';
  const result = await pool.query(
    `SELECT e.id, e.pergunta_pt, e.pergunta_en, e.opcoes, e.abre_em, e.fecha_em,
            e.fornada_post_id, p.slug AS fornada_slug, p.status AS fornada_status
       FROM cms_enquetes e
       LEFT JOIN cms_posts p ON p.id = e.fornada_post_id
      WHERE e.status = 'encerrada'
      ORDER BY e.fecha_em DESC, e.id DESC
      LIMIT $1`,
    [lim]
  );
  const items = [];
  for (const row of result.rows) {
    const opcoes = Array.isArray(row.opcoes) ? row.opcoes : [];
    const tally = resultadoDe(opcoes, await contagem(pool, row.id));
    const vencedor = pickVencedor(opcoes, tally, lang);
    const fornada_path =
      row.fornada_slug && row.fornada_status === 'publicado'
        ? `/${lang}/right-now/${row.fornada_slug}`
        : null;
    items.push({
      id: row.id,
      pergunta: lang === 'en' ? row.pergunta_en : row.pergunta_pt,
      semana: semanaLabel(row.abre_em, row.fecha_em, lang),
      vencedor: {
        texto: vencedor.texto,
        produto_nome: vencedor.produto_nome,
        pct: vencedor.pct,
      },
      total: tally.total,
      fornada_path,
    });
  }
  return items;
}

/**
 * Tick: encerra vencidas; segunda ≥ 07:00 SP → auto-sugerir (1× por semana).
 */
async function maybeAutoSugerir(pool, nowDate = new Date(), deps = {}) {
  const parts = saoPauloParts(nowDate);
  if (!isMondaySaoPaulo(nowDate)) return { started: false, reason: 'nao_segunda' };
  if (parts.hour < 7) return { started: false, reason: 'antes_das_7' };
  const key = weekKeySaoPaulo(nowDate);
  if (lastEnqueteWeekKey === key) return { started: false, reason: 'ja_tentou_semana' };
  const out = await sugerirEnquete(pool, { ...deps, now: () => nowDate });
  lastEnqueteWeekKey = key;
  if (!out.ok) {
    console.warn('[cms-enquete] auto-sugerir', out.error);
    return { started: false, reason: out.error, status: out.status };
  }
  console.log(`[cms-enquete] sugestão automática ${key} (#${out.id})`);
  return { started: true, id: out.id };
}

function startEnqueteScheduler(pool, opts = {}) {
  if (enqueteSchedulerStarted && !opts.force) return { started: false, reason: 'already' };
  enqueteSchedulerStarted = true;
  const tickMs = opts.tickMs || 60 * 1000;
  const clock = opts.now || (() => new Date());
  const deps = {
    getVitrine: opts.getVitrine,
    converseJson: opts.converseJson,
  };
  const autoEnabled = opts.autoSugerir !== false;

  const run = async () => {
    try {
      await encerrarEnquetesVencidas(pool, { now: clock });
      if (autoEnabled) await maybeAutoSugerir(pool, clock(), deps);
    } catch (err) {
      console.error('[cms-enquete] scheduler', err.message);
    }
  };
  const handle = setInterval(run, tickMs);
  if (typeof handle.unref === 'function') handle.unref();
  return { started: true, handle, first: run() };
}

function resetEnqueteSchedulerForTests() {
  enqueteSchedulerStarted = false;
  lastEnqueteWeekKey = null;
}

/**
 * Rotas privadas do Right Now e o cadastro de enquetes.
 * A chave fica em LEPAIN_CMS_KEY. O blog manda o IP do visitante em X-Forwarded-For.
 *
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {(req: import('express').Request, res: import('express').Response, next: Function) => void} requireAdmin
 * @param {object} [opts]
 */
function registerCmsRightNowRoutes(app, pool, requireAdmin, opts = {}) {
  const deps = {
    getVitrine: opts.getVitrine || lojaClient.getVitrine,
    converseJson: opts.converseJson || converseJson,
    now: opts.now || (() => new Date()),
  };

  app.post('/api/cms/posts/:id/quero', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      const id = parseInt(String(req.params.id), 10);
      const visitante = visitanteOf(req.body?.visitante);
      if (!Number.isFinite(id) || !visitante) {
        return res.status(400).json({ error: 'post e visitante são obrigatórios' });
      }
      const post = await pool.query(`SELECT id, status FROM cms_posts WHERE id = $1`, [id]);
      if (!post.rows[0] || post.rows[0].status !== 'publicado') {
        return res.status(404).json({ error: 'Post não encontrado' });
      }
      const inserted = await pool.query(
        `INSERT INTO cms_reacoes (post_id, visitante)
         VALUES ($1, $2)
         ON CONFLICT (post_id, visitante) DO NOTHING
         RETURNING id`,
        [id, visitante]
      );
      const count = await pool.query(
        `SELECT count(*)::int AS n FROM cms_reacoes WHERE post_id = $1`,
        [id]
      );
      return res.status(200).json({
        count: count.rows[0].n,
        novo: inserted.rows.length > 0,
      });
    } catch (err) {
      console.error('[cms] POST /api/cms/posts/:id/quero', err.message);
      return res.status(500).json({ error: 'Falha ao registrar reação' });
    }
  });

  app.get('/api/cms/enquetes/atual', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      // Fecha o que venceu antes de servir a aberta.
      await encerrarEnquetesVencidas(pool, deps);
      const visitante = visitanteOf(req.query.visitante);
      const open = await pool.query(
        `SELECT id, pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status
           FROM cms_enquetes
          WHERE status = 'publicada'
            AND abre_em <= now()
            AND fecha_em > now()
          ORDER BY abre_em DESC
          LIMIT 1`
      );
      const row = open.rows[0];
      if (!row) return res.status(200).json(null);
      let vote = null;
      if (visitante) {
        const found = await pool.query(
          `SELECT id FROM cms_votos WHERE enquete_id = $1 AND visitante = $2`,
          [row.id, visitante]
        );
        vote = found.rows[0] || null;
      }
      const counts =
        vote || new Date(row.fecha_em).getTime() <= Date.now()
          ? await contagem(pool, row.id)
          : [];
      return res.status(200).json(shapeEnquete(row, vote, counts));
    } catch (err) {
      console.error('[cms] GET /api/cms/enquetes/atual', err.message);
      return res.status(500).json({ error: 'Falha ao ler a enquete' });
    }
  });

  app.get('/api/cms/enquetes/historico', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      await encerrarEnquetesVencidas(pool, deps);
      const idioma = String(req.query.idioma || 'pt').trim().toLowerCase();
      const limite = parseInt(String(req.query.limite || '3'), 10);
      const historico = await listHistorico(pool, { idioma, limite });
      return res.status(200).json(historico);
    } catch (err) {
      console.error('[cms] GET /api/cms/enquetes/historico', err.message);
      return res.status(500).json({ error: 'Falha ao ler o histórico' });
    }
  });

  app.post('/api/cms/enquetes/:id/votos', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      const id = parseInt(String(req.params.id), 10);
      const visitante = visitanteOf(req.body?.visitante);
      const opcaoId = String(req.body?.opcao_id || '').trim();
      if (!Number.isFinite(id) || !visitante || !opcaoId) {
        return res.status(400).json({ error: 'enquete, opção e visitante são obrigatórios' });
      }
      const found = await pool.query(`SELECT * FROM cms_enquetes WHERE id = $1`, [id]);
      const row = found.rows[0];
      if (!row || row.status !== 'publicada') {
        return res.status(404).json({ error: 'Enquete não encontrada' });
      }
      const now = Date.now();
      if (new Date(row.fecha_em).getTime() <= now) {
        return res.status(410).json({ error: 'enquete fechada' });
      }
      if (new Date(row.abre_em).getTime() > now) {
        return res.status(404).json({ error: 'Enquete não encontrada' });
      }
      const opcoes = Array.isArray(row.opcoes) ? row.opcoes : [];
      if (!opcoes.some((item) => item.id === opcaoId)) {
        return res.status(400).json({ error: 'opção inválida' });
      }
      const inserted = await pool.query(
        `INSERT INTO cms_votos (enquete_id, opcao_id, visitante)
         VALUES ($1, $2, $3)
         ON CONFLICT (enquete_id, visitante) DO NOTHING
         RETURNING id`,
        [id, opcaoId, visitante]
      );
      if (!inserted.rows[0]) {
        return res.status(409).json({ error: 'voto já registrado' });
      }
      const tally = resultadoDe(opcoes, await contagem(pool, id));
      return res.status(200).json(tally);
    } catch (err) {
      console.error('[cms] POST /api/cms/enquetes/:id/votos', err.message);
      return res.status(500).json({ error: 'Falha ao registrar voto' });
    }
  });

  app.get('/api/cms/enquetes/admin', requireAdmin, async (_req, res) => {
    try {
      await encerrarEnquetesVencidas(pool, deps);
      const result = await pool.query(
        `SELECT id, pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status,
                fornada_post_id, encerrada_em
           FROM cms_enquetes
          ORDER BY abre_em DESC, id DESC
          LIMIT 100`
      );
      const enquetes = [];
      for (const row of result.rows) {
        const tally = resultadoDe(
          Array.isArray(row.opcoes) ? row.opcoes : [],
          await contagem(pool, row.id)
        );
        enquetes.push({
          id: row.id,
          pergunta_pt: row.pergunta_pt,
          pergunta_en: row.pergunta_en,
          opcoes: row.opcoes,
          abre_em: iso(row.abre_em),
          fecha_em: iso(row.fecha_em),
          status: row.status,
          fornada_post_id: row.fornada_post_id ?? null,
          encerrada_em: iso(row.encerrada_em),
          resultado: tally.resultado,
          total: tally.total,
        });
      }
      return res.status(200).json({ enquetes });
    } catch (err) {
      console.error('[cms] GET /api/cms/enquetes/admin', err.message);
      return res.status(500).json({ error: 'Falha ao listar enquetes' });
    }
  });

  app.post('/api/cms/enquetes/sugerir', requireAdmin, async (_req, res) => {
    try {
      const out = await sugerirEnquete(pool, deps);
      if (!out.ok) return res.status(out.status || 500).json({ error: out.error });
      return res.status(201).json({ id: out.id, status: 'sugerida' });
    } catch (err) {
      console.error('[cms] POST /api/cms/enquetes/sugerir', err.message);
      return res.status(500).json({ error: 'Falha ao sugerir enquete' });
    }
  });

  app.post('/api/cms/enquetes/:id/publicar', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });
      const out = await publicarEnquete(pool, id, deps);
      if (!out.ok) return res.status(out.status || 500).json({ error: out.error });
      return res.status(200).json(out);
    } catch (err) {
      console.error('[cms] POST /api/cms/enquetes/:id/publicar', err.message);
      return res.status(500).json({ error: 'Falha ao publicar enquete' });
    }
  });

  app.post('/api/cms/enquetes', requireAdmin, async (req, res) => {
    try {
      const parsed = parseEnquete(req.body || {});
      if (parsed.error) return res.status(400).json({ error: parsed.error });
      if (
        parsed.status === 'publicada' &&
        (await outraAberta(pool, 0, parsed.abre_em, parsed.fecha_em))
      ) {
        return res.status(409).json({ error: 'já existe uma enquete aberta nesse período' });
      }
      const result = await pool.query(
        `INSERT INTO cms_enquetes
           (pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status)
         VALUES ($1, $2, $3::jsonb, $4, $5, $6)
         RETURNING id`,
        [
          parsed.pergunta_pt,
          parsed.pergunta_en,
          JSON.stringify(parsed.opcoes),
          parsed.abre_em,
          parsed.fecha_em,
          parsed.status,
        ]
      );
      return res.status(201).json({ id: result.rows[0].id });
    } catch (err) {
      console.error('[cms] POST /api/cms/enquetes', err.message);
      return res.status(500).json({ error: 'Falha ao criar enquete' });
    }
  });

  app.put('/api/cms/enquetes/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });
      const existing = await pool.query(`SELECT id FROM cms_enquetes WHERE id = $1`, [id]);
      if (!existing.rows[0]) return res.status(404).json({ error: 'Enquete não encontrada' });
      const parsed = parseEnquete(req.body || {});
      if (parsed.error) return res.status(400).json({ error: parsed.error });
      if (
        parsed.status === 'publicada' &&
        (await outraAberta(pool, id, parsed.abre_em, parsed.fecha_em))
      ) {
        return res.status(409).json({ error: 'já existe uma enquete aberta nesse período' });
      }
      await pool.query(
        `UPDATE cms_enquetes SET
            pergunta_pt = $1,
            pergunta_en = $2,
            opcoes = $3::jsonb,
            abre_em = $4,
            fecha_em = $5,
            status = $6
         WHERE id = $7`,
        [
          parsed.pergunta_pt,
          parsed.pergunta_en,
          JSON.stringify(parsed.opcoes),
          parsed.abre_em,
          parsed.fecha_em,
          parsed.status,
          id,
        ]
      );
      return res.status(200).json({ id });
    } catch (err) {
      console.error('[cms] PUT /api/cms/enquetes/:id', err.message);
      return res.status(500).json({ error: 'Falha ao atualizar enquete' });
    }
  });
}

module.exports = {
  registerCmsRightNowRoutes,
  resetRateLimit,
  resultadoDe,
  parseOpcoes,
  opcoesPublicas,
  shapeEnquete,
  sugerirEnquete,
  publicarEnquete,
  encerrarEnquetesVencidas,
  listHistorico,
  startEnqueteScheduler,
  resetEnqueteSchedulerForTests,
  maybeAutoSugerir,
  weekKeySaoPaulo,
  textMentionsProduct,
  normalizeVitrineItem,
  ENQUETE_DIAS,
};
