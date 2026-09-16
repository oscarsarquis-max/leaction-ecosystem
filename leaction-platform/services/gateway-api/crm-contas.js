'use strict';

/**
 * Sponge — ficha de conta (prompt 131).
 * Leitura de crm_* + SELECT em contracts / contract_items / entitlement_snapshots / orders.
 * Não altera ingestão nem o funil PLG.
 */

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function iso(value) {
  if (value == null || value === '') return null;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function asInt(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

function asSistemas(value) {
  if (Array.isArray(value)) {
    return [...new Set(value.filter(Boolean).map((s) => String(s)))].sort();
  }
  return [];
}

function parseComContrato(raw) {
  if (raw === undefined || raw === null || String(raw).trim() === '') return null;
  const s = String(raw).trim().toLowerCase();
  if (s === 'true' || s === '1') return true;
  if (s === 'false' || s === '0') return false;
  return undefined;
}

function nomeFromMeta(meta, orderJson) {
  const m = meta && typeof meta === 'object' ? meta : {};
  const hub = m.hub_payload && typeof m.hub_payload === 'object' ? m.hub_payload : {};
  const order =
    orderJson && typeof orderJson === 'object'
      ? orderJson
      : {};
  const candidates = [
    hub.razao_social,
    m.razao_social,
    order.razao_social,
    order.hub_payload && order.hub_payload.razao_social,
  ];
  for (const c of candidates) {
    const t = String(c || '').trim();
    if (t) return t.slice(0, 240);
  }
  return null;
}

const USO_CTE = `
uso AS (
  SELECT
    s.instituicao_id,
    MIN(s.criado_em) AS primeiro_acesso,
    MAX(e.criado_em) AS ultimo_acesso,
    MAX(e.criado_em) FILTER (WHERE e.tipo_evento = 'login_sucesso') AS ultimo_login,
    COUNT(DISTINCT s.id_sessao) FILTER (
      WHERE e.criado_em >= NOW() - INTERVAL '7 days'
    )::int AS sessoes_7d,
    COUNT(DISTINCT s.id_sessao) FILTER (
      WHERE e.criado_em >= NOW() - INTERVAL '30 days'
    )::int AS sessoes_30d,
    COUNT(*) FILTER (WHERE e.criado_em >= NOW() - INTERVAL '7 days')::int AS eventos_7d,
    COUNT(*) FILTER (WHERE e.criado_em >= NOW() - INTERVAL '30 days')::int AS eventos_30d,
    COUNT(DISTINCT s.usuario_origem_ref) FILTER (
      WHERE e.criado_em >= NOW() - INTERVAL '30 days'
        AND s.usuario_origem_ref IS NOT NULL
        AND BTRIM(s.usuario_origem_ref) <> ''
    )::int AS usuarios_30d,
    ARRAY_REMOVE(ARRAY_AGG(DISTINCT s.sistema_origem), NULL) AS sistemas
  FROM crm_sessoes s
  LEFT JOIN crm_eventos e ON e.id_sessao = s.id_sessao
  WHERE s.instituicao_id IS NOT NULL
  GROUP BY s.instituicao_id
)`;

const COMER_CTE = `
comer AS (
  SELECT DISTINCT ON (lower(c.subject_id))
    c.subject_id::uuid AS instituicao_id,
    c.id AS contract_id,
    c.app_id,
    c.status AS contrato_status,
    c.created_at,
    c.meta_json,
    c.order_id,
    (
      SELECT ci.sku
        FROM contract_items ci
       WHERE ci.contract_id = c.id
         AND ci.item_type IN ('plan', 'seat')
       ORDER BY CASE WHEN ci.item_type = 'plan' THEN 0 ELSE 1 END, ci.sku
       LIMIT 1
    ) AS plano
  FROM contracts c
  WHERE c.subject_type = 'instituicao'
    AND c.subject_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  ORDER BY lower(c.subject_id), c.created_at DESC
)`;

const IDS_CTE = `
ids AS (
  SELECT instituicao_id FROM uso
  UNION
  SELECT instituicao_id FROM comer
)`;

function mapContaRow(row) {
  const instituicaoId = String(row.instituicao_id);
  const nome = nomeFromMeta(row.meta_json, row.order_payload) || instituicaoId;
  return {
    instituicao_id: instituicaoId,
    nome,
    sistemas: asSistemas(row.sistemas),
    primeiro_acesso: iso(row.primeiro_acesso),
    ultimo_acesso: iso(row.ultimo_acesso),
    ultimo_login: iso(row.ultimo_login),
    sessoes_7d: asInt(row.sessoes_7d),
    sessoes_30d: asInt(row.sessoes_30d),
    usuarios_30d: asInt(row.usuarios_30d),
    tem_contrato: Boolean(row.contract_id),
    contrato_status: row.contrato_status || null,
    plano: row.plano || null,
  };
}

function shapeEntitlement(row) {
  if (!row) return null;
  const p =
    row.payload_json && typeof row.payload_json === 'object' ? row.payload_json : {};
  return {
    app_id: row.app_id || null,
    seats: p.seats ?? p.seats_balance ?? p.licencas ?? p.licenses ?? null,
    creditos: p.credits ?? p.creditos ?? p.credits_balance ?? p.creditos_saldo ?? null,
    plano: p.plan ?? p.sku ?? null,
    valid_until: iso(row.valid_until || p.valid_until),
    updated_at: iso(row.updated_at),
  };
}

function countsByTipo(rows) {
  return (rows || []).map((r) => ({
    tipo_evento: String(r.tipo_evento),
    count: asInt(r.count),
  }));
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ crmSecretAuthorized: (req: import('express').Request) => boolean }} auth
 */
function registerCrmContasRoutes(app, pool, auth) {
  const crmSecretAuthorized = auth && auth.crmSecretAuthorized;
  if (typeof crmSecretAuthorized !== 'function') {
    throw new Error('crm-contas: crmSecretAuthorized é obrigatório');
  }

  app.get('/api/crm/contas', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }

    const sistema = String(req.query.sistema || '').trim().toLowerCase();
    const comContrato = parseComContrato(req.query.com_contrato);
    if (comContrato === undefined) {
      return res.status(400).json({ ok: false, error: 'com_contrato deve ser true ou false' });
    }
    const semRaw = String(req.query.sem_acesso_desde || '').trim();
    let semDias = null;
    if (semRaw) {
      if (!/^\d+$/.test(semRaw) || Number(semRaw) < 1) {
        return res.status(400).json({
          ok: false,
          error: 'sem_acesso_desde deve ser um inteiro positivo (dias)',
        });
      }
      semDias = Number(semRaw);
    }

    const params = [];
    const filters = [];
    if (sistema) {
      params.push(sistema);
      filters.push(
        `($${params.length}::text = ANY (COALESCE(u.sistemas, ARRAY[]::text[])) OR c.app_id = $${params.length}::text)`
      );
    }
    if (comContrato === true) {
      filters.push('c.contract_id IS NOT NULL');
    } else if (comContrato === false) {
      filters.push('c.contract_id IS NULL');
    }
    if (semDias != null) {
      params.push(semDias);
      filters.push(
        `(u.ultimo_acesso IS NULL OR u.ultimo_acesso < NOW() - ($${params.length}::int * INTERVAL '1 day'))`
      );
    }
    const where = filters.length ? `WHERE ${filters.join(' AND ')}` : '';

    const sql = `
      WITH ${USO_CTE},
      ${COMER_CTE},
      ${IDS_CTE}
      SELECT
        i.instituicao_id,
        u.primeiro_acesso,
        u.ultimo_acesso,
        u.ultimo_login,
        COALESCE(u.sessoes_7d, 0) AS sessoes_7d,
        COALESCE(u.sessoes_30d, 0) AS sessoes_30d,
        COALESCE(u.usuarios_30d, 0) AS usuarios_30d,
        u.sistemas,
        c.contract_id,
        c.contrato_status,
        c.plano,
        c.meta_json,
        CASE
          WHEN o.external_resource_id IS NOT NULL
           AND left(btrim(o.external_resource_id), 1) = '{'
          THEN o.external_resource_id::jsonb
          ELSE NULL
        END AS order_payload
      FROM ids i
      LEFT JOIN uso u ON u.instituicao_id = i.instituicao_id
      LEFT JOIN comer c ON c.instituicao_id = i.instituicao_id
      LEFT JOIN orders o ON o.id = c.order_id
      ${where}
      ORDER BY u.ultimo_acesso DESC NULLS LAST, i.instituicao_id ASC
    `;

    const t0 = Date.now();
    try {
      const result = await pool.query(sql, params);
      const ms = Date.now() - t0;
      return res.json({
        ok: true,
        contas: result.rows.map(mapContaRow),
        meta: { count: result.rows.length, elapsed_ms: ms },
      });
    } catch (err) {
      console.error('❌ [crm/contas GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao listar contas' });
    }
  });

  app.get('/api/crm/contas/:instituicao_id', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }

    const raw = String(req.params.instituicao_id || '').trim();
    if (!UUID_RE.test(raw)) {
      return res.status(400).json({ ok: false, error: 'instituicao_id deve ser UUID válido' });
    }
    const instituicaoId = raw.toLowerCase();

    const existsSql = `
      SELECT 1 AS ok
       WHERE EXISTS (
         SELECT 1 FROM crm_sessoes WHERE instituicao_id = $1::uuid
       )
          OR EXISTS (
         SELECT 1 FROM contracts
          WHERE subject_type = 'instituicao' AND lower(subject_id) = $1
       )
    `;

    const contaSql = `
      WITH ${USO_CTE},
      ${COMER_CTE}
      SELECT
        $1::uuid AS instituicao_id,
        u.primeiro_acesso,
        u.ultimo_acesso,
        u.ultimo_login,
        COALESCE(u.sessoes_7d, 0) AS sessoes_7d,
        COALESCE(u.sessoes_30d, 0) AS sessoes_30d,
        COALESCE(u.eventos_7d, 0) AS eventos_7d,
        COALESCE(u.eventos_30d, 0) AS eventos_30d,
        COALESCE(u.usuarios_30d, 0) AS usuarios_30d,
        u.sistemas,
        c.contract_id,
        c.contrato_status,
        c.plano,
        c.meta_json,
        c.app_id,
        CASE
          WHEN o.external_resource_id IS NOT NULL
           AND left(btrim(o.external_resource_id), 1) = '{'
          THEN o.external_resource_id::jsonb
          ELSE NULL
        END AS order_payload
      FROM (SELECT $1::uuid AS instituicao_id) seed
      LEFT JOIN uso u ON u.instituicao_id = seed.instituicao_id
      LEFT JOIN comer c ON c.instituicao_id = seed.instituicao_id
      LEFT JOIN orders o ON o.id = c.order_id
    `;

    const contratosSql = `
      SELECT
        c.id,
        c.app_id,
        c.status,
        c.created_at,
        COALESCE(
          json_agg(
            json_build_object(
              'sku', ci.sku,
              'tipo', ci.item_type,
              'quantidade', ci.quantity
            ) ORDER BY ci.item_type, ci.sku
          ) FILTER (WHERE ci.id IS NOT NULL),
          '[]'::json
        ) AS itens
      FROM contracts c
      LEFT JOIN contract_items ci ON ci.contract_id = c.id
      WHERE c.subject_type = 'instituicao'
        AND lower(c.subject_id) = $1
      GROUP BY c.id
      ORDER BY c.created_at DESC
    `;

    const tiposSql = `
      SELECT e.tipo_evento, COUNT(*)::int AS count
        FROM crm_eventos e
        JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
       WHERE s.instituicao_id = $1::uuid
         AND e.criado_em >= NOW() - INTERVAL '30 days'
       GROUP BY e.tipo_evento
       ORDER BY count DESC, e.tipo_evento ASC
    `;

    const usuariosSql = `
      SELECT
        s.usuario_origem_ref,
        (ARRAY_AGG(s.sistema_origem ORDER BY COALESCE(e.criado_em, s.criado_em) DESC))[1]
          AS sistema_origem,
        MIN(s.criado_em) AS primeiro_acesso,
        MAX(e.criado_em) AS ultimo_acesso,
        COUNT(DISTINCT s.id_sessao) FILTER (
          WHERE e.criado_em >= NOW() - INTERVAL '30 days'
        )::int AS sessoes_30d
      FROM crm_sessoes s
      LEFT JOIN crm_eventos e ON e.id_sessao = s.id_sessao
      WHERE s.instituicao_id = $1::uuid
        AND s.usuario_origem_ref IS NOT NULL
        AND BTRIM(s.usuario_origem_ref) <> ''
      GROUP BY s.usuario_origem_ref
      ORDER BY MAX(e.criado_em) DESC NULLS LAST
    `;

    const usuariosTiposSql = `
      SELECT s.usuario_origem_ref, e.tipo_evento, COUNT(*)::int AS count
        FROM crm_eventos e
        JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
       WHERE s.instituicao_id = $1::uuid
         AND e.criado_em >= NOW() - INTERVAL '30 days'
         AND s.usuario_origem_ref IS NOT NULL
         AND BTRIM(s.usuario_origem_ref) <> ''
       GROUP BY s.usuario_origem_ref, e.tipo_evento
    `;

    const creditosSql = `
      SELECT COALESCE(SUM(
        CASE
          WHEN (e.dados->>'quantidade') ~ '^-?[0-9]+(\\.[0-9]+)?$'
          THEN (e.dados->>'quantidade')::numeric
          ELSE 0
        END
      ), 0)::float AS total
        FROM crm_eventos e
        JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
       WHERE s.instituicao_id = $1::uuid
         AND e.tipo_evento = 'credito_consumir'
         AND e.criado_em >= NOW() - INTERVAL '30 days'
    `;

    const sessoesSql = `
      SELECT
        s.id_sessao,
        s.sistema_origem,
        s.usuario_origem_ref,
        s.criado_em AS inicio,
        MAX(e.criado_em) AS ultimo_evento,
        COUNT(e.id)::int AS n_eventos
      FROM crm_sessoes s
      LEFT JOIN crm_eventos e ON e.id_sessao = s.id_sessao
      WHERE s.instituicao_id = $1::uuid
      GROUP BY s.id_sessao, s.sistema_origem, s.usuario_origem_ref, s.criado_em
      ORDER BY COALESCE(MAX(e.criado_em), s.criado_em) DESC
      LIMIT 20
    `;

    const entitlementSql = `
      SELECT app_id, subject_id, payload_json, valid_until, updated_at
        FROM entitlement_snapshots
       WHERE lower(subject_id) = $1
       ORDER BY updated_at DESC NULLS LAST
       LIMIT 1
    `;

    try {
      const found = await pool.query(existsSql, [instituicaoId]);
      if (!found.rows.length) {
        return res.status(404).json({ ok: false, error: 'Conta não encontrada' });
      }

      const [
        contaRes,
        contratosRes,
        tiposRes,
        usuariosRes,
        usuariosTiposRes,
        creditosRes,
        sessoesRes,
        entRes,
      ] = await Promise.all([
        pool.query(contaSql, [instituicaoId]),
        pool.query(contratosSql, [instituicaoId]),
        pool.query(tiposSql, [instituicaoId]),
        pool.query(usuariosSql, [instituicaoId]),
        pool.query(usuariosTiposSql, [instituicaoId]),
        pool.query(creditosSql, [instituicaoId]),
        pool.query(sessoesSql, [instituicaoId]),
        pool.query(entitlementSql, [instituicaoId]),
      ]);

      const base = mapContaRow(contaRes.rows[0] || { instituicao_id: instituicaoId });
      const tiposPorUsuario = new Map();
      for (const r of usuariosTiposRes.rows) {
        const key = String(r.usuario_origem_ref);
        if (!tiposPorUsuario.has(key)) tiposPorUsuario.set(key, []);
        tiposPorUsuario.get(key).push({
          tipo_evento: String(r.tipo_evento),
          count: asInt(r.count),
        });
      }

      return res.json({
        ok: true,
        conta: {
          ...base,
          eventos_30d: asInt(contaRes.rows[0] && contaRes.rows[0].eventos_30d),
          eventos_por_tipo_30d: countsByTipo(tiposRes.rows),
          contratos: contratosRes.rows.map((c) => ({
            id: c.id,
            app_id: c.app_id,
            status: c.status,
            created_at: iso(c.created_at),
            itens: Array.isArray(c.itens) ? c.itens : [],
          })),
          entitlement: shapeEntitlement(entRes.rows[0] || null),
          usuarios: usuariosRes.rows.map((u) => ({
            usuario_origem_ref: u.usuario_origem_ref,
            sistema_origem: u.sistema_origem || null,
            primeiro_acesso: iso(u.primeiro_acesso),
            ultimo_acesso: iso(u.ultimo_acesso),
            sessoes_30d: asInt(u.sessoes_30d),
            eventos_por_tipo_30d: (tiposPorUsuario.get(String(u.usuario_origem_ref)) || [])
              .slice()
              .sort((a, b) => b.count - a.count || a.tipo_evento.localeCompare(b.tipo_evento)),
          })),
          creditos_consumidos_30d: Number(creditosRes.rows[0] && creditosRes.rows[0].total) || 0,
          ultimas_sessoes: sessoesRes.rows.map((s) => ({
            id_sessao: s.id_sessao,
            sistema_origem: s.sistema_origem,
            usuario_origem_ref: s.usuario_origem_ref || null,
            inicio: iso(s.inicio),
            ultimo_evento: iso(s.ultimo_evento),
            n_eventos: asInt(s.n_eventos),
          })),
        },
      });
    } catch (err) {
      console.error('❌ [crm/contas/:id GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao carregar ficha de conta' });
    }
  });
}

module.exports = {
  registerCrmContasRoutes,
};
