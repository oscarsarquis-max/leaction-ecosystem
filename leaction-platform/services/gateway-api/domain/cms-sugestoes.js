'use strict';

const {
  dateOnly,
  isEventDatePast,
  saoPauloParts,
  groupPairsByDay,
  countPairsCreatedToday,
  TITLE_MAX,
  RESUMO_MAX,
} = require('./cms-sugestoes-lib');
const sugestoesJob = require('./cms-sugestoes-job');
const lepainPurge = require('./lepain-purge');
const { createRodadaRunner, shapeRodada } = require('./cms-sugestoes-rodadas');

// Hora (America/Sao_Paulo) a partir da qual a rodada automática do dia pode rodar.
const DAILY_HOUR = 7;

let schedulerStarted = false;
let lastRunDay = null;
const runners = new WeakMap();

/** Um runner por pool, compartilhado entre rotas e scheduler. */
function getRodadaRunner(pool, opts = {}) {
  if (opts.runner) return opts.runner;
  let runner = runners.get(pool);
  if (!runner) {
    runner = createRodadaRunner(pool, opts.runnerOptions || {});
    runners.set(pool, runner);
  }
  return runner;
}

function iso(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function shapePair(pt, en) {
  return {
    grupo_id: pt.id,
    tipo: pt.right_now_tipo,
    fonte: pt.fonte,
    link_url: pt.link_url,
    trecho_base: pt.trecho_base,
    data_materia: dateOnly(pt.data_materia),
    data_evento: dateOnly(pt.data_evento),
    sentidos: Array.isArray(pt.sentidos) ? pt.sentidos : [],
    sugestao_expira_em: iso(pt.sugestao_expira_em),
    criado_em: iso(pt.criado_em),
    pt: {
      id: pt.id,
      slug: pt.slug,
      titulo: pt.titulo,
      resumo: pt.resumo,
      conteudo_html: pt.conteudo_html,
    },
    en: en
      ? {
          id: en.id,
          slug: en.slug,
          titulo: en.titulo,
          resumo: en.resumo,
          conteudo_html: en.conteudo_html,
        }
      : null,
  };
}

async function loadPendingPairs(pool, destino = 'lepain') {
  const result = await pool.query(
    `SELECT id, slug, titulo, resumo, conteudo_html, right_now_tipo, sentidos,
            link_url, fonte, trecho_base, data_materia, data_evento,
            sugestao_expira_em, criado_em, idioma, grupo_id, status
       FROM cms_posts
      WHERE sistema_destino = $1
        AND secao = 'right_now'
        AND status = 'sugestao'
        AND (sugestao_expira_em IS NULL OR sugestao_expira_em > now())
      ORDER BY criado_em DESC, id DESC`,
    [destino]
  );
  const byId = new Map(result.rows.map((r) => [r.id, r]));
  const pairs = [];
  const used = new Set();
  for (const row of result.rows) {
    if (row.idioma !== 'pt') continue;
    if (used.has(row.id)) continue;
    const en =
      result.rows.find(
        (r) => r.idioma === 'en' && Number(r.grupo_id) === Number(row.id)
      ) || null;
    used.add(row.id);
    if (en) used.add(en.id);
    pairs.push(shapePair(row, en));
  }
  return { pairs, pending_count: pairs.length, byId };
}

/** Resumo para a tela: quantas pendentes foram criadas hoje (SP) e o agrupamento por dia. */
function summarizePending(pairs, now = new Date()) {
  return {
    pending_today_count: countPairsCreatedToday(pairs, now),
    grupos: groupPairsByDay(pairs, now),
  };
}

function parsePublishBody(body = {}) {
  const titulo_pt = String(body.titulo_pt ?? body.pt?.titulo ?? '').trim();
  const resumo_pt = String(body.resumo_pt ?? body.pt?.resumo ?? '').trim();
  const markdown_pt = String(body.markdown_pt ?? body.pt?.conteudo_html ?? '').trim();
  const titulo_en = String(body.titulo_en ?? body.en?.titulo ?? '').trim();
  const resumo_en = String(body.resumo_en ?? body.en?.resumo ?? '').trim();
  const markdown_en = String(body.markdown_en ?? body.en?.conteudo_html ?? '').trim();
  const erros = [];
  if (!titulo_pt || [...titulo_pt].length > TITLE_MAX) erros.push('titulo_pt');
  if (!resumo_pt || [...resumo_pt].length > RESUMO_MAX) erros.push('resumo_pt');
  if (!titulo_en || [...titulo_en].length > TITLE_MAX) erros.push('titulo_en');
  if (!resumo_en || [...resumo_en].length > RESUMO_MAX) erros.push('resumo_en');
  if (!markdown_pt || !markdown_en) erros.push('markdown');
  return {
    error: erros.length ? `campos inválidos: ${erros.join(', ')}` : null,
    titulo_pt,
    resumo_pt,
    markdown_pt,
    titulo_en,
    resumo_en,
    markdown_en,
  };
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {(req, res, next) => void} requireAdmin
 * @param {{ runner?: object, now?: () => Date }} [opts]
 */
function registerCmsSugestoesRoutes(app, pool, requireAdmin, opts = {}) {
  const runner = getRodadaRunner(pool, opts);
  const clock = opts.now || (() => new Date());

  app.get('/api/cms/sugestoes', requireAdmin, async (req, res) => {
    try {
      const destino = String(req.query.destino || 'lepain').trim().toLowerCase();
      if (destino !== 'lepain') {
        return res.status(400).json({ error: 'destino inválido (use lepain)' });
      }
      // Abrir a tela também expira o que venceu (o tick de 1 min cobre o resto).
      await sugestoesJob.expireOverdueSugestoes(pool);
      const { pairs, pending_count } = await loadPendingPairs(pool, destino);
      return res.status(200).json({
        sugestoes: pairs,
        pending_count,
        ...summarizePending(pairs, clock()),
      });
    } catch (err) {
      console.error('[cms] GET /api/cms/sugestoes', err.message);
      return res.status(500).json({ error: 'Falha ao listar sugestões' });
    }
  });

  // Gerar é assíncrono: responde 202 na hora e a tela acompanha em GET /rodadas/:id.
  app.post('/api/cms/sugestoes/gerar', requireAdmin, async (_req, res) => {
    try {
      await sugestoesJob.expireOverdueSugestoes(pool);
      const out = await runner.start({ trigger: 'manual' });
      if (!out.ok) {
        return res
          .status(out.status || 409)
          .json({ error: out.message || 'Não foi possível iniciar a rodada', code: out.code, rodada_id: out.rodada_id ?? null });
      }
      return res.status(202).json({ rodada_id: out.rodada_id, status: 'running', reused: Boolean(out.reused) });
    } catch (err) {
      console.error('[cms] POST /api/cms/sugestoes/gerar', err.message);
      return res.status(500).json({ error: 'Falha ao gerar sugestões' });
    }
  });

  // Rodada em andamento (a tela retoma o polling depois de recarregar).
  app.get('/api/cms/sugestoes/rodadas/atual', requireAdmin, async (_req, res) => {
    try {
      const running = await runner.store.latestRunning();
      return res.status(200).json({ rodada: running ? shapeRodada(running) : null });
    } catch (err) {
      console.error('[cms] GET /api/cms/sugestoes/rodadas/atual', err.message);
      return res.status(500).json({ error: 'Falha ao ler rodada' });
    }
  });

  app.get('/api/cms/sugestoes/rodadas/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });
      const row = await runner.get(id);
      if (!row) return res.status(404).json({ error: 'Rodada não encontrada' });
      return res.status(200).json(shapeRodada(row));
    } catch (err) {
      console.error('[cms] GET /api/cms/sugestoes/rodadas/:id', err.message);
      return res.status(500).json({ error: 'Falha ao ler rodada' });
    }
  });

  app.post('/api/cms/sugestoes/:id/publicar', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });

      const found = await pool.query(
        `SELECT * FROM cms_posts
          WHERE id = $1 AND idioma = 'pt' AND status = 'sugestao'
            AND sistema_destino = 'lepain' AND secao = 'right_now'`,
        [id]
      );
      const pt = found.rows[0];
      if (!pt) return res.status(404).json({ error: 'Sugestão não encontrada' });

      const enFound = await pool.query(
        `SELECT * FROM cms_posts
          WHERE grupo_id = $1 AND idioma = 'en' AND status = 'sugestao'`,
        [id]
      );
      const en = enFound.rows[0];
      if (!en) return res.status(404).json({ error: 'Versão EN não encontrada' });

      const parsed = parsePublishBody({
        titulo_pt: req.body?.titulo_pt ?? pt.titulo,
        resumo_pt: req.body?.resumo_pt ?? pt.resumo,
        markdown_pt: req.body?.markdown_pt ?? pt.conteudo_html,
        titulo_en: req.body?.titulo_en ?? en.titulo,
        resumo_en: req.body?.resumo_en ?? en.resumo,
        markdown_en: req.body?.markdown_en ?? en.conteudo_html,
        ...req.body,
      });
      if (parsed.error) return res.status(400).json({ error: parsed.error });

      const link = String(req.body?.link_url || pt.link_url || '').trim();
      if (!link || !(await sugestoesJob.checkLinkOk(link))) {
        return res.status(400).json({ error: 'link indisponível (HTTP ≠ 200)' });
      }
      if (pt.right_now_tipo === 'evento' && isEventDatePast(pt.data_evento)) {
        return res.status(400).json({ error: 'data do evento já passou' });
      }

      const nowIso = new Date().toISOString();
      await pool.query(
        `UPDATE cms_posts SET
            titulo = $1, resumo = $2, conteudo_html = $3,
            link_url = $4, status = 'publicado', publicado_em = $5, atualizado_em = now()
         WHERE id = $6`,
        [parsed.titulo_pt, parsed.resumo_pt, parsed.markdown_pt, link, nowIso, pt.id]
      );
      await pool.query(
        `UPDATE cms_posts SET
            titulo = $1, resumo = $2, conteudo_html = $3,
            link_url = $4, status = 'publicado', publicado_em = $5, atualizado_em = now()
         WHERE id = $6`,
        [parsed.titulo_en, parsed.resumo_en, parsed.markdown_en, link, nowIso, en.id]
      );

      // O blog guarda 60 s de cache; avisa para a publicação aparecer já.
      void lepainPurge.notifyLepainPurge();
      return res.status(200).json({ grupo_id: id, status: 'publicado', ids: [pt.id, en.id] });
    } catch (err) {
      console.error('[cms] POST /api/cms/sugestoes/:id/publicar', err.message);
      return res.status(500).json({ error: 'Falha ao publicar sugestão' });
    }
  });

  app.post('/api/cms/sugestoes/:id/descartar', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });

      const found = await pool.query(
        `SELECT id FROM cms_posts
          WHERE id = $1 AND idioma = 'pt' AND status = 'sugestao'
            AND sistema_destino = 'lepain'`,
        [id]
      );
      if (!found.rows[0]) return res.status(404).json({ error: 'Sugestão não encontrada' });

      const updated = await pool.query(
        `UPDATE cms_posts
            SET status = 'descartado', atualizado_em = now()
          WHERE status = 'sugestao'
            AND (id = $1 OR (idioma = 'en' AND grupo_id = $1))
          RETURNING id`,
        [id]
      );
      return res.status(200).json({
        grupo_id: id,
        status: 'descartado',
        ids: updated.rows.map((r) => r.id),
      });
    } catch (err) {
      console.error('[cms] POST /api/cms/sugestoes/:id/descartar', err.message);
      return res.status(500).json({ error: 'Falha ao descartar sugestão' });
    }
  });
}

/**
 * Dispara a rodada automática do dia (trigger 'auto').
 * Vale a partir das 07:00 (SP): às 07:00 é o job; depois disso é o catch-up de quem
 * subiu tarde ou reiniciou. No máximo 1 por dia: o índice único em cms_sugestoes_rodadas
 * garante mesmo após restart. Rodada manual em andamento adia o auto para o próximo tick.
 */
async function maybeStartDailyRound(runner, nowDate = new Date()) {
  const parts = saoPauloParts(nowDate);
  if (parts.hour < DAILY_HOUR) return { started: false, reason: 'antes_das_7' };
  if (lastRunDay === parts.date) return { started: false, reason: 'ja_tentou_hoje' };
  const out = await runner.start({ trigger: 'auto', at: nowDate });
  if (out.ok && !out.reused) {
    lastRunDay = parts.date;
    console.log(`[cms-sugestoes] rodada automática ${parts.date} (#${out.rodada_id})`);
    return { started: true, rodada_id: out.rodada_id };
  }
  if (out.skipped) {
    lastRunDay = parts.date;
    return { started: false, reason: 'auto_ja_rodou' };
  }
  return { started: false, reason: 'rodada_em_andamento', rodada_id: out.rodada_id };
}

/**
 * Tick a cada minuto:
 *  - expira sugestões vencidas (48 h) — a cada minuto cobre o requisito "de hora em hora";
 *  - com dailyEnabled, dispara a rodada automática do dia (07:00 SP ou catch-up depois).
 * Na partida, rodadas que ficaram `running` de um processo anterior viram erro "interrompida".
 */
function startSugestoesScheduler(pool, opts = {}) {
  if (schedulerStarted && !opts.force) return { started: false, reason: 'already' };
  schedulerStarted = true;
  const dailyEnabled = opts.dailyEnabled === true;
  const tickMs = opts.tickMs || 60 * 1000;
  const runner = getRodadaRunner(pool, opts);
  const clock = opts.now || (() => new Date());

  const ready = (async () => {
    try {
      await runner.store.ensureSchema();
      const orphans = await runner.store.failOrphans(clock());
      if (orphans) console.warn(`[cms-sugestoes] ${orphans} rodada(s) interrompida(s) marcadas como erro`);
    } catch (err) {
      console.error('[cms-sugestoes] rodadas (schema/orphans)', err.message);
    }
  })();

  const run = async () => {
    try {
      await ready;
      await sugestoesJob.expireOverdueSugestoes(pool, clock());
      if (!dailyEnabled) return;
      await maybeStartDailyRound(runner, clock());
    } catch (err) {
      console.error('[cms-sugestoes] scheduler', err.message);
    }
  };
  const handle = setInterval(run, tickMs);
  if (typeof handle.unref === 'function') handle.unref();
  const first = run();
  return { started: true, handle, dailyEnabled, ready, first };
}

function resetSugestoesSchedulerForTests() {
  schedulerStarted = false;
  lastRunDay = null;
}

module.exports = {
  registerCmsSugestoesRoutes,
  startSugestoesScheduler,
  maybeStartDailyRound,
  getRodadaRunner,
  resetSugestoesSchedulerForTests,
  loadPendingPairs,
  summarizePending,
  parsePublishBody,
  shapePair,
  DAILY_HOUR,
};
