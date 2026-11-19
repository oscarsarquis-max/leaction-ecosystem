'use strict';

const {
  dateOnly,
  isEventDatePast,
  saoPauloParts,
  TITLE_MAX,
  RESUMO_MAX,
} = require('./cms-sugestoes-lib');
const sugestoesJob = require('./cms-sugestoes-job');

let schedulerStarted = false;
let lastRunDay = null;

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
 */
function registerCmsSugestoesRoutes(app, pool, requireAdmin) {
  app.get('/api/cms/sugestoes', requireAdmin, async (req, res) => {
    try {
      const destino = String(req.query.destino || 'lepain').trim().toLowerCase();
      if (destino !== 'lepain') {
        return res.status(400).json({ error: 'destino inválido (use lepain)' });
      }
      await sugestoesJob.expireOverdueSugestoes(pool);
      const { pairs, pending_count } = await loadPendingPairs(pool, destino);
      return res.status(200).json({ sugestoes: pairs, pending_count });
    } catch (err) {
      console.error('[cms] GET /api/cms/sugestoes', err.message);
      return res.status(500).json({ error: 'Falha ao listar sugestões' });
    }
  });

  app.post('/api/cms/sugestoes/gerar', requireAdmin, async (_req, res) => {
    try {
      await sugestoesJob.expireOverdueSugestoes(pool);
      const result = await sugestoesJob.gerarSugestoes(pool);
      return res.status(200).json(result);
    } catch (err) {
      console.error('[cms] POST /api/cms/sugestoes/gerar', err.message);
      return res.status(500).json({ error: 'Falha ao gerar sugestões' });
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
 * Tick a cada minuto: só expira vencidas.
 * O job diário 07:00 fica desligado até o Oscar aprovar a qualidade;
 * a geração sob demanda usa a mesma função (`gerarSugestoes`).
 */
function startSugestoesScheduler(pool, opts = {}) {
  if (schedulerStarted && !opts.force) return { started: false, reason: 'already' };
  schedulerStarted = true;
  const dailyEnabled = opts.dailyEnabled === true;
  const tickMs = opts.tickMs || 60 * 1000;
  const run = async () => {
    try {
      await sugestoesJob.expireOverdueSugestoes(pool);
      if (!dailyEnabled) return;
      const parts = saoPauloParts(opts.now ? opts.now() : new Date());
      if (parts.hour === 7 && parts.minute === 0 && lastRunDay !== parts.date) {
        lastRunDay = parts.date;
        console.log(`[cms-sugestoes] job diário ${parts.date}`);
        await sugestoesJob.gerarSugestoes(pool);
      }
    } catch (err) {
      console.error('[cms-sugestoes] scheduler', err.message);
    }
  };
  const handle = setInterval(run, tickMs);
  if (typeof handle.unref === 'function') handle.unref();
  void run();
  return { started: true, handle, dailyEnabled };
}

function resetSugestoesSchedulerForTests() {
  schedulerStarted = false;
  lastRunDay = null;
}

module.exports = {
  registerCmsSugestoesRoutes,
  startSugestoesScheduler,
  resetSugestoesSchedulerForTests,
  loadPendingPairs,
  parsePublishBody,
  shapePair,
};
