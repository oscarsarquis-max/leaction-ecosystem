'use strict';

/**
 * Sponge — uso por funcionalidade (prompt 138).
 * Derivado de crm_sessoes + crm_eventos. Sem tabela nova, sem job.
 */

const { computeUso } = require('./crm-funcionalidades');

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const USO_EVENTS_SQL = `
  SELECT
    e.id,
    e.id_sessao,
    e.tipo_evento,
    e.url_pagina,
    e.criado_em,
    s.sistema_origem,
    s.usuario_origem_ref,
    s.instituicao_id
  FROM crm_eventos e
  JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
 WHERE e.criado_em >= $1::timestamptz
   AND e.criado_em < $2::timestamptz
   AND e.tipo_evento <> 'conta_snapshot'
   AND ($3::text IS NULL OR s.sistema_origem = $3)
   AND ($4::uuid IS NULL OR s.instituicao_id = $4)
   AND ($5::text IS NULL OR s.usuario_origem_ref = $5)
 ORDER BY e.id_sessao, e.criado_em, e.id
`;

function parseIsoParam(raw, label) {
  const s = String(raw || '').trim();
  if (!s) return { value: null };
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) {
    return { error: `${label} deve ser ISO válido` };
  }
  return { value: d };
}

function defaultPeriodo(desde, ate) {
  const end = ate || new Date();
  const start = desde || new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000);
  return { start, end };
}

async function fetchUsoEvents(pool, filtros) {
  const { desde, ate, sistema, instituicaoId, usuarioOrigemRef } = filtros;
  const res = await pool.query(USO_EVENTS_SQL, [
    desde.toISOString(),
    ate.toISOString(),
    sistema || null,
    instituicaoId || null,
    usuarioOrigemRef || null,
  ]);
  return res.rows;
}

function shapeUso(computed, periodo, recorte, elapsedMs) {
  return {
    ok: true,
    periodo: {
      desde: periodo.desde.toISOString(),
      ate: periodo.ate.toISOString(),
    },
    recorte: {
      sistema: recorte.sistema || null,
      instituicao_id: recorte.instituicaoId || null,
      usuario_origem_ref: recorte.usuarioOrigemRef || null,
    },
    totais: computed.totais,
    funcionalidades: computed.funcionalidades,
    outros: computed.outros,
    ...(computed.serie ? { serie: computed.serie } : {}),
    meta: { elapsed_ms: elapsedMs },
  };
}

async function computeUsoFromDb(pool, filtros) {
  const t0 = Date.now();
  const rows = await fetchUsoEvents(pool, filtros);
  const computed = computeUso(rows, { agruparDia: Boolean(filtros.agruparDia) });
  return {
    payload: shapeUso(
      computed,
      { desde: filtros.desde, ate: filtros.ate },
      {
        sistema: filtros.sistema,
        instituicaoId: filtros.instituicaoId,
        usuarioOrigemRef: filtros.usuarioOrigemRef,
      },
      Date.now() - t0
    ),
    elapsedMs: Date.now() - t0,
  };
}

async function computeUso30dForInstituicao(pool, instituicaoId) {
  const ate = new Date();
  const desde = new Date(ate.getTime() - 30 * 24 * 60 * 60 * 1000);
  const { payload } = await computeUsoFromDb(pool, {
    desde,
    ate,
    sistema: null,
    instituicaoId,
    usuarioOrigemRef: null,
    agruparDia: false,
  });
  return {
    periodo: payload.periodo,
    totais: payload.totais,
    funcionalidades: (payload.funcionalidades || []).slice(0, 10),
    outros: payload.outros,
    meta: payload.meta,
  };
}

/**
 * @param {{ crmSecretAuthorized: (req: import('express').Request) => boolean }} auth
 */
function registerCrmUsoRoutes(app, pool, auth) {
  const crmSecretAuthorized = auth && auth.crmSecretAuthorized;
  if (typeof crmSecretAuthorized !== 'function') {
    throw new Error('crm-uso: crmSecretAuthorized é obrigatório');
  }

  app.get('/api/crm/uso', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }

    const desdeParsed = parseIsoParam(req.query.desde, 'desde');
    if (desdeParsed.error) {
      return res.status(400).json({ ok: false, error: desdeParsed.error });
    }
    const ateParsed = parseIsoParam(req.query.ate, 'ate');
    if (ateParsed.error) {
      return res.status(400).json({ ok: false, error: ateParsed.error });
    }

    const agruparRaw = String(req.query.agrupar || 'funcionalidade').trim().toLowerCase();
    if (agruparRaw && agruparRaw !== 'funcionalidade' && agruparRaw !== 'dia') {
      return res.status(400).json({ ok: false, error: 'agrupar deve ser funcionalidade ou dia' });
    }

    const sistema = String(req.query.sistema || '').trim() || null;
    const usuarioOrigemRef = String(req.query.usuario_origem_ref || '').trim() || null;
    const instRaw = String(req.query.instituicao_id || '').trim();
    let instituicaoId = null;
    if (instRaw) {
      if (!UUID_RE.test(instRaw)) {
        return res.status(400).json({ ok: false, error: 'instituicao_id deve ser UUID válido' });
      }
      instituicaoId = instRaw.toLowerCase();
    }

    const { start, end } = defaultPeriodo(desdeParsed.value, ateParsed.value);
    if (start.getTime() >= end.getTime()) {
      return res.status(400).json({ ok: false, error: 'desde deve ser anterior a ate' });
    }

    try {
      const { payload, elapsedMs } = await computeUsoFromDb(pool, {
        desde: start,
        ate: end,
        sistema,
        instituicaoId,
        usuarioOrigemRef,
        agruparDia: agruparRaw === 'dia',
      });
      if (elapsedMs > 1000) {
        console.warn(`⚠️ [crm/uso] consulta ${elapsedMs}ms (limiar 1s)`);
      }
      return res.json(payload);
    } catch (err) {
      console.error('❌ [crm/uso GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao agregar uso por funcionalidade' });
    }
  });
}

module.exports = {
  registerCrmUsoRoutes,
  computeUso30dForInstituicao,
  computeUsoFromDb,
};
