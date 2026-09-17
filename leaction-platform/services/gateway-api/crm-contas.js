'use strict';

/**
 * Sponge — ficha de conta (prompt 131) e visão de atividade (prompt 136).
 * Leitura de crm_* + SELECT em contracts / contract_items / entitlement_snapshots / orders.
 * Não altera ingestão nem o funil PLG.
 */

const { computeUso30dForInstituicao } = require('./crm-uso');

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

function papelDe(sistema) {
  const s = String(sistema || '');
  if (s === 'inove4us-school') return 'gestor';
  if (s === 'inove4us') return 'professor';
  return s || null;
}

function parseIsoParam(raw, label) {
  const s = String(raw || '').trim();
  if (!s) return { value: null };
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) {
    return { error: `${label} deve ser ISO válido` };
  }
  return { value: d };
}

function parseLimite(raw) {
  if (raw === undefined || raw === null || String(raw).trim() === '') return 200;
  if (!/^\d+$/.test(String(raw).trim())) return null;
  const n = Number(String(raw).trim());
  if (n < 1) return null;
  return Math.min(1000, n);
}

function parseParadoDias(raw) {
  if (raw === undefined || raw === null || String(raw).trim() === '') return 3;
  if (!/^\d+$/.test(String(raw).trim())) return null;
  return Number(String(raw).trim());
}

function pessoaKey(ref, sistema) {
  return `${String(ref || '')}\u0000${String(sistema || '')}`;
}

function conviteIdOf(dados) {
  if (!dados || typeof dados !== 'object') return null;
  const raw = dados.convite_id;
  if (raw === null || raw === undefined || raw === '') return null;
  return String(raw);
}

function isUsoAposAceite(tipo) {
  const t = String(tipo || '');
  return t !== '' && t !== 'pageview' && t !== 'login_sucesso' && t !== 'convite_escola_aceitar' && t !== 'professor_convidar';
}

const EXISTS_CONTA_SQL = `
      SELECT 1 AS ok
       WHERE EXISTS (
         SELECT 1 FROM crm_sessoes WHERE instituicao_id = $1::uuid
       )
          OR EXISTS (
         SELECT 1 FROM contracts
          WHERE subject_type = 'instituicao'
            AND lower(subject_id) = lower($1::text)
       )
    `;

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

function nomeOuCodigo(nome, codigo) {
  const n = String(nome || '').trim();
  if (n) return n;
  const c = String(codigo || '').trim();
  return c || null;
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
    AND e.tipo_evento <> 'conta_snapshot'
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

function assentosFromSchoolSnap(dados) {
  if (!dados || typeof dados !== 'object') return null;
  const lic = dados.licencas && typeof dados.licencas === 'object' ? dados.licencas : null;
  if (!lic) return null;
  if (lic.em_uso == null && lic.total_assentos == null) return null;
  return `${asInt(lic.em_uso)}/${asInt(lic.total_assentos)}`;
}

function shapeSnapshotEvent(row) {
  if (!row) return null;
  const dados = row.dados && typeof row.dados === 'object' ? row.dados : {};
  return {
    data_ref: dados.data_ref ? String(dados.data_ref) : null,
    criado_em: iso(row.criado_em),
    dados,
  };
}

function mapContaRow(row) {
  const instituicaoId = String(row.instituicao_id);
  const nome =
    String(row.identidade_nome || '').trim() ||
    nomeFromMeta(row.meta_json, row.order_payload) ||
    instituicaoId;
  return {
    instituicao_id: instituicaoId,
    instituicao_nome: nome,
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
    assentos: assentosFromSchoolSnap(row.snap_school),
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
        ident_i.nome AS identidade_nome,
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
        snap.snap_school,
        CASE
          WHEN o.external_resource_id IS NOT NULL
           AND left(btrim(o.external_resource_id), 1) = '{'
          THEN o.external_resource_id::jsonb
          ELSE NULL
        END AS order_payload
      FROM ids i
      LEFT JOIN crm_identidades ident_i
        ON ident_i.tipo = 'instituicao'
       AND ident_i.chave = i.instituicao_id::text
      LEFT JOIN uso u ON u.instituicao_id = i.instituicao_id
      LEFT JOIN comer c ON c.instituicao_id = i.instituicao_id
      LEFT JOIN orders o ON o.id = c.order_id
      LEFT JOIN LATERAL (
        SELECT e.dados AS snap_school
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
         WHERE s.instituicao_id = i.instituicao_id
           AND e.tipo_evento = 'conta_snapshot'
           AND s.sistema_origem = 'inove4us-school'
           AND COALESCE(e.dados->>'escopo', '') <> 'professor'
         ORDER BY e.criado_em DESC
         LIMIT 1
      ) snap ON TRUE
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

  app.get('/api/crm/contas/:instituicao_id/atividade', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }

    const raw = String(req.params.instituicao_id || '').trim();
    if (!UUID_RE.test(raw)) {
      return res.status(400).json({ ok: false, error: 'instituicao_id deve ser UUID válido' });
    }
    const instituicaoId = raw.toLowerCase();

    const limite = parseLimite(req.query.limite);
    if (limite == null) {
      return res.status(400).json({ ok: false, error: 'limite deve ser um inteiro entre 1 e 1000' });
    }
    const paradoDias = parseParadoDias(req.query.parado_dias);
    if (paradoDias == null) {
      return res.status(400).json({ ok: false, error: 'parado_dias deve ser um inteiro >= 0' });
    }
    const desdeParsed = parseIsoParam(req.query.desde, 'desde');
    if (desdeParsed.error) {
      return res.status(400).json({ ok: false, error: desdeParsed.error });
    }
    const ateParsed = parseIsoParam(req.query.ate, 'ate');
    if (ateParsed.error) {
      return res.status(400).json({ ok: false, error: ateParsed.error });
    }
    const pessoa = String(req.query.pessoa || '').trim();
    const sistema = String(req.query.sistema || '').trim();
    const tipo = String(req.query.tipo || '').trim();

    const t0 = Date.now();
    try {
      const found = await pool.query(EXISTS_CONTA_SQL, [instituicaoId]);
      if (!found.rows.length) {
        return res.status(404).json({ ok: false, error: 'Conta não encontrada' });
      }

      const primeiroRes = await pool.query(
        `SELECT MIN(criado_em) AS primeiro
           FROM crm_sessoes
          WHERE instituicao_id = $1::uuid`,
        [instituicaoId]
      );
      const primeiroAcesso = primeiroRes.rows[0] && primeiroRes.rows[0].primeiro
        ? new Date(primeiroRes.rows[0].primeiro)
        : null;
      const desde = desdeParsed.value || primeiroAcesso || new Date(0);
      const ate = ateParsed.value || null;

      const pessoasSql = `
        SELECT
          s.usuario_origem_ref,
          s.sistema_origem,
          MAX(ident_u.nome) AS usuario_nome,
          MIN(s.criado_em) AS primeiro_acesso,
          MAX(COALESCE(e.criado_em, s.criado_em)) AS ultimo_acesso,
          MAX(e.criado_em) FILTER (WHERE e.tipo_evento = 'login_sucesso') AS ultimo_login,
          COUNT(DISTINCT s.id_sessao)::int AS sessoes
        FROM crm_sessoes s
        LEFT JOIN crm_eventos e ON e.id_sessao = s.id_sessao
          AND e.tipo_evento <> 'conta_snapshot'
        LEFT JOIN crm_identidades ident_u
          ON ident_u.tipo = 'usuario'
         AND ident_u.chave = s.sistema_origem || ':' || s.usuario_origem_ref
        WHERE s.instituicao_id = $1::uuid
          AND s.usuario_origem_ref IS NOT NULL
          AND BTRIM(s.usuario_origem_ref) <> ''
          AND s.usuario_origem_ref <> 'sistema:snapshot'
        GROUP BY s.usuario_origem_ref, s.sistema_origem
        ORDER BY MAX(COALESCE(e.criado_em, s.criado_em)) DESC NULLS LAST
      `;

      const tiposPessoaSql = `
        SELECT s.usuario_origem_ref, s.sistema_origem, e.tipo_evento, COUNT(*)::int AS count
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
         WHERE s.instituicao_id = $1::uuid
           AND e.tipo_evento <> 'conta_snapshot'
           AND e.criado_em >= $2::timestamptz
           AND ($3::timestamptz IS NULL OR e.criado_em <= $3::timestamptz)
           AND s.usuario_origem_ref IS NOT NULL
           AND BTRIM(s.usuario_origem_ref) <> ''
           AND s.usuario_origem_ref <> 'sistema:snapshot'
         GROUP BY s.usuario_origem_ref, s.sistema_origem, e.tipo_evento
      `;

      const ultimoEventoSql = `
        SELECT DISTINCT ON (s.usuario_origem_ref, s.sistema_origem)
          s.usuario_origem_ref,
          s.sistema_origem,
          e.tipo_evento,
          e.criado_em
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
         WHERE s.instituicao_id = $1::uuid
           AND e.tipo_evento <> 'conta_snapshot'
           AND e.criado_em >= $2::timestamptz
           AND ($3::timestamptz IS NULL OR e.criado_em <= $3::timestamptz)
           AND s.usuario_origem_ref IS NOT NULL
           AND BTRIM(s.usuario_origem_ref) <> ''
           AND s.usuario_origem_ref <> 'sistema:snapshot'
         ORDER BY s.usuario_origem_ref, s.sistema_origem, e.criado_em DESC
      `;

      const timelineSql = `
        SELECT
          e.criado_em AS quando,
          s.sistema_origem AS sistema,
          s.usuario_origem_ref,
          ident_u.nome AS usuario_nome,
          e.tipo_evento AS tipo,
          e.dados,
          e.id_sessao
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
          LEFT JOIN crm_identidades ident_u
            ON ident_u.tipo = 'usuario'
           AND ident_u.chave = s.sistema_origem || ':' || s.usuario_origem_ref
         WHERE s.instituicao_id = $1::uuid
           AND e.tipo_evento <> 'conta_snapshot'
           AND e.criado_em >= $2::timestamptz
           AND ($3::timestamptz IS NULL OR e.criado_em <= $3::timestamptz)
           AND ($4::text = '' OR s.usuario_origem_ref = $4::text)
           AND ($5::text = '' OR s.sistema_origem = $5::text)
           AND ($6::text = '' OR e.tipo_evento = $6::text)
         ORDER BY e.criado_em DESC
         LIMIT $7::int
      `;

      const porDiaSql = `
        SELECT
          ((e.criado_em AT TIME ZONE 'America/Sao_Paulo')::date) AS data,
          COUNT(*)::int AS eventos,
          COUNT(DISTINCT s.usuario_origem_ref) FILTER (
            WHERE s.usuario_origem_ref IS NOT NULL
              AND BTRIM(s.usuario_origem_ref) <> ''
              AND s.usuario_origem_ref <> 'sistema:snapshot'
          )::int AS pessoas_ativas
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
         WHERE s.instituicao_id = $1::uuid
           AND e.tipo_evento <> 'conta_snapshot'
           AND e.criado_em >= $2::timestamptz
           AND ($3::timestamptz IS NULL OR e.criado_em <= $3::timestamptz)
         GROUP BY 1
         ORDER BY 1
      `;

      const porDiaTipoSql = `
        SELECT
          ((e.criado_em AT TIME ZONE 'America/Sao_Paulo')::date) AS data,
          e.tipo_evento,
          COUNT(*)::int AS count
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
         WHERE s.instituicao_id = $1::uuid
           AND e.tipo_evento <> 'conta_snapshot'
           AND e.criado_em >= $2::timestamptz
           AND ($3::timestamptz IS NULL OR e.criado_em <= $3::timestamptz)
         GROUP BY 1, e.tipo_evento
      `;

      const sinaisEventosSql = `
        SELECT
          e.tipo_evento,
          e.dados,
          e.criado_em,
          s.usuario_origem_ref,
          s.sistema_origem,
          ident_u.nome AS usuario_nome
          FROM crm_eventos e
          JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
          LEFT JOIN crm_identidades ident_u
            ON ident_u.tipo = 'usuario'
           AND ident_u.chave = s.sistema_origem || ':' || s.usuario_origem_ref
         WHERE s.instituicao_id = $1::uuid
           AND e.tipo_evento <> 'conta_snapshot'
           AND e.tipo_evento IN (
             'professor_convidar',
             'convite_escola_aceitar',
             'aula_criar',
             'aula_fechar',
             'wizard_gerar',
             'desafio_criar',
             'desafio_encerrar',
             'pei_aplicar',
             'credito_consumir',
             'turma_criar',
             'aluno_matricular',
             'alocacao_criar',
             'comunicado_publicar',
             'pei_criar',
             'pei_atualizar'
           )
         ORDER BY e.criado_em ASC
      `;

      const identInstSql = `
        SELECT nome FROM crm_identidades
         WHERE tipo = 'instituicao' AND chave = $1
      `;

      const range = [instituicaoId, desde.toISOString(), ate ? ate.toISOString() : null];
      const [
        pessoasRes,
        tiposRes,
        ultimoRes,
        timelineRes,
        porDiaRes,
        porDiaTipoRes,
        sinaisRes,
        identInstRes,
      ] = await Promise.all([
        pool.query(pessoasSql, [instituicaoId]),
        pool.query(tiposPessoaSql, range),
        pool.query(ultimoEventoSql, range),
        pool.query(timelineSql, [...range, pessoa, sistema, tipo, limite]),
        pool.query(porDiaSql, range),
        pool.query(porDiaTipoSql, range),
        pool.query(sinaisEventosSql, [instituicaoId]),
        pool.query(identInstSql, [instituicaoId]),
      ]);

      const tiposMap = new Map();
      for (const r of tiposRes.rows) {
        const key = pessoaKey(r.usuario_origem_ref, r.sistema_origem);
        if (!tiposMap.has(key)) tiposMap.set(key, {});
        tiposMap.get(key)[String(r.tipo_evento)] = asInt(r.count);
      }
      const ultimoMap = new Map();
      for (const r of ultimoRes.rows) {
        ultimoMap.set(pessoaKey(r.usuario_origem_ref, r.sistema_origem), {
          tipo: String(r.tipo_evento),
          quando: iso(r.criado_em),
        });
      }

      const pessoas = pessoasRes.rows.map((p) => {
        const key = pessoaKey(p.usuario_origem_ref, p.sistema_origem);
        const eventosPorTipo = tiposMap.get(key) || {};
        const eventosTotal = Object.values(eventosPorTipo).reduce((acc, n) => acc + n, 0);
        return {
          usuario_origem_ref: p.usuario_origem_ref,
          usuario_nome: nomeOuCodigo(p.usuario_nome, p.usuario_origem_ref),
          sistema_origem: p.sistema_origem || null,
          papel: papelDe(p.sistema_origem),
          primeiro_acesso: iso(p.primeiro_acesso),
          ultimo_acesso: iso(p.ultimo_acesso),
          ultimo_login: iso(p.ultimo_login),
          sessoes: asInt(p.sessoes),
          eventos_total: eventosTotal,
          eventos_por_tipo: eventosPorTipo,
          ultimo_evento: ultimoMap.get(key) || null,
        };
      });

      const linhaDoTempo = timelineRes.rows.map((row) => ({
        quando: iso(row.quando),
        sistema: row.sistema || null,
        usuario_origem_ref: row.usuario_origem_ref || null,
        usuario_nome: nomeOuCodigo(row.usuario_nome, row.usuario_origem_ref),
        papel: papelDe(row.sistema),
        tipo: String(row.tipo),
        dados: row.dados && typeof row.dados === 'object' ? row.dados : {},
        id_sessao: row.id_sessao,
      }));

      const tiposPorDia = new Map();
      for (const r of porDiaTipoRes.rows) {
        const day = iso(r.data) ? iso(r.data).slice(0, 10) : String(r.data);
        if (!tiposPorDia.has(day)) tiposPorDia.set(day, {});
        tiposPorDia.get(day)[String(r.tipo_evento)] = asInt(r.count);
      }
      const porDiaHits = new Map();
      for (const r of porDiaRes.rows) {
        const day =
          r.data instanceof Date
            ? r.data.toISOString().slice(0, 10)
            : String(r.data).slice(0, 10);
        porDiaHits.set(day, {
          data: day,
          eventos: asInt(r.eventos),
          pessoas_ativas: asInt(r.pessoas_ativas),
          por_tipo: tiposPorDia.get(day) || {},
        });
      }
      const porDia = [];
      const dayStart = new Date(`${desde.toISOString().slice(0, 10)}T12:00:00Z`);
      const dayEnd = ate
        ? new Date(`${ate.toISOString().slice(0, 10)}T12:00:00Z`)
        : new Date(`${new Date().toISOString().slice(0, 10)}T12:00:00Z`);
      for (let t = dayStart.getTime(); t <= dayEnd.getTime(); t += 86400000) {
        const day = new Date(t).toISOString().slice(0, 10);
        porDia.push(
          porDiaHits.get(day) || { data: day, eventos: 0, pessoas_ativas: 0, por_tipo: {} }
        );
      }

      const enviados = [];
      const aceitos = [];
      const usosPorPessoa = new Map();
      for (const ev of sinaisRes.rows) {
        const ref = ev.usuario_origem_ref ? String(ev.usuario_origem_ref) : '';
        if (ev.tipo_evento === 'professor_convidar') {
          enviados.push({
            convite_id: conviteIdOf(ev.dados),
            quando: iso(ev.criado_em),
            usuario_origem_ref: ref || null,
            usuario_nome: nomeOuCodigo(ev.usuario_nome, ref),
          });
        } else if (ev.tipo_evento === 'convite_escola_aceitar') {
          aceitos.push({
            convite_id: conviteIdOf(ev.dados),
            quando: iso(ev.criado_em),
            usuario_origem_ref: ref || null,
            usuario_nome: nomeOuCodigo(ev.usuario_nome, ref),
            sistema_origem: ev.sistema_origem || null,
          });
        } else if (ref && isUsoAposAceite(ev.tipo_evento)) {
          if (!usosPorPessoa.has(ref)) usosPorPessoa.set(ref, []);
          usosPorPessoa.get(ref).push({ tipo: String(ev.tipo_evento), quando: iso(ev.criado_em) });
        }
      }
      const aceitosIds = new Set(aceitos.map((a) => a.convite_id).filter(Boolean));
      const convitesSemAceite = [
        ...new Set(
          enviados
            .map((e) => e.convite_id)
            .filter((id) => id && !aceitosIds.has(id))
        ),
      ];

      const professoresSemAtividade = [];
      const horasAceite = [];
      for (const aceito of aceitos) {
        const ref = aceito.usuario_origem_ref;
        if (!ref) continue;
        const usos = (usosPorPessoa.get(ref) || []).filter((u) => {
          if (!u.quando || !aceito.quando) return false;
          return new Date(u.quando).getTime() > new Date(aceito.quando).getTime();
        });
        if (!usos.length) {
          professoresSemAtividade.push({
            usuario_origem_ref: ref,
            usuario_nome: nomeOuCodigo(aceito.usuario_nome, ref),
            sistema_origem: aceito.sistema_origem,
            papel: papelDe(aceito.sistema_origem),
            aceite_em: aceito.quando,
          });
        } else {
          const primeiro = usos[0];
          const horas =
            (new Date(primeiro.quando).getTime() - new Date(aceito.quando).getTime()) / 3600000;
          horasAceite.push({
            usuario_origem_ref: ref,
            usuario_nome: nomeOuCodigo(aceito.usuario_nome, ref),
            sistema_origem: aceito.sistema_origem,
            papel: papelDe(aceito.sistema_origem),
            aceite_em: aceito.quando,
            primeiro_uso_em: primeiro.quando,
            primeiro_uso_tipo: primeiro.tipo,
            horas: Math.round(horas * 10) / 10,
          });
        }
      }

      const corte = Date.now() - paradoDias * 86400000;
      const parados = pessoas
        .filter((p) => {
          const stamp = p.ultimo_acesso || p.primeiro_acesso;
          if (!stamp) return paradoDias === 0;
          return new Date(stamp).getTime() < corte;
        })
        .map((p) => ({
          usuario_origem_ref: p.usuario_origem_ref,
          usuario_nome: p.usuario_nome,
          sistema_origem: p.sistema_origem,
          papel: p.papel,
          ultimo_acesso: p.ultimo_acesso,
        }));

      const instituicaoNome = nomeOuCodigo(
        identInstRes.rows[0] && identInstRes.rows[0].nome,
        instituicaoId
      );

      return res.json({
        ok: true,
        instituicao_id: instituicaoId,
        instituicao_nome: instituicaoNome,
        pessoas,
        linha_do_tempo: linhaDoTempo,
        por_dia: porDia,
        sinais: {
          convites: {
            enviados: enviados.length,
            aceitos: aceitos.length,
            convite_id: convitesSemAceite,
          },
          professores_sem_atividade_apos_aceite: professoresSemAtividade,
          horas_aceite_ate_primeiro_uso: horasAceite,
          parados_ha_dias: parados,
        },
        meta: {
          desde: desde.toISOString(),
          ate: ate ? ate.toISOString() : null,
          limite,
          retornados: linhaDoTempo.length,
          tem_mais: linhaDoTempo.length === limite,
          parado_dias: paradoDias,
          elapsed_ms: Date.now() - t0,
        },
      });
    } catch (err) {
      console.error('❌ [crm/contas/:id/atividade GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao carregar atividade da conta' });
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
          WHERE subject_type = 'instituicao'
            AND lower(subject_id) = lower($1::text)
       )
    `;

    const contaSql = `
      WITH ${USO_CTE},
      ${COMER_CTE}
      SELECT
        $1::uuid AS instituicao_id,
        ident_i.nome AS identidade_nome,
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
      LEFT JOIN crm_identidades ident_i
        ON ident_i.tipo = 'instituicao'
       AND ident_i.chave = $1::text
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
        AND lower(c.subject_id) = lower($1::text)
      GROUP BY c.id
      ORDER BY c.created_at DESC
    `;

    const tiposSql = `
      SELECT e.tipo_evento, COUNT(*)::int AS count
        FROM crm_eventos e
        JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
       WHERE s.instituicao_id = $1::uuid
         AND e.criado_em >= NOW() - INTERVAL '30 days'
         AND e.tipo_evento <> 'conta_snapshot'
       GROUP BY e.tipo_evento
       ORDER BY count DESC, e.tipo_evento ASC
    `;

    const usuariosSql = `
      SELECT
        s.usuario_origem_ref,
        (ARRAY_AGG(s.sistema_origem ORDER BY COALESCE(e.criado_em, s.criado_em) DESC))[1]
          AS sistema_origem,
        MAX(ident_u.nome) AS usuario_nome,
        MIN(s.criado_em) AS primeiro_acesso,
        MAX(e.criado_em) AS ultimo_acesso,
        COUNT(DISTINCT s.id_sessao) FILTER (
          WHERE e.criado_em >= NOW() - INTERVAL '30 days'
        )::int AS sessoes_30d
      FROM crm_sessoes s
      LEFT JOIN crm_eventos e ON e.id_sessao = s.id_sessao
        AND e.tipo_evento <> 'conta_snapshot'
      LEFT JOIN crm_identidades ident_u
        ON ident_u.tipo = 'usuario'
       AND ident_u.chave = s.sistema_origem || ':' || s.usuario_origem_ref
      WHERE s.instituicao_id = $1::uuid
        AND s.usuario_origem_ref IS NOT NULL
        AND BTRIM(s.usuario_origem_ref) <> ''
        AND s.usuario_origem_ref <> 'sistema:snapshot'
      GROUP BY s.usuario_origem_ref
      ORDER BY MAX(e.criado_em) DESC NULLS LAST
    `;

    const usuariosTiposSql = `
      SELECT s.usuario_origem_ref, e.tipo_evento, COUNT(*)::int AS count
        FROM crm_eventos e
        JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
       WHERE s.instituicao_id = $1::uuid
         AND e.criado_em >= NOW() - INTERVAL '30 days'
         AND e.tipo_evento <> 'conta_snapshot'
         AND s.usuario_origem_ref IS NOT NULL
         AND BTRIM(s.usuario_origem_ref) <> ''
         AND s.usuario_origem_ref <> 'sistema:snapshot'
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
        COALESCE(ident_u.nome, s.usuario_nome) AS usuario_nome,
        s.criado_em AS inicio,
        MAX(e.criado_em) AS ultimo_evento,
        COUNT(e.id)::int AS n_eventos
      FROM crm_sessoes s
      LEFT JOIN crm_eventos e ON e.id_sessao = s.id_sessao
        AND e.tipo_evento <> 'conta_snapshot'
      LEFT JOIN crm_identidades ident_u
        ON ident_u.tipo = 'usuario'
       AND ident_u.chave = s.sistema_origem || ':' || s.usuario_origem_ref
      WHERE s.instituicao_id = $1::uuid
        AND COALESCE(s.usuario_origem_ref, '') <> 'sistema:snapshot'
      GROUP BY s.id_sessao, s.sistema_origem, s.usuario_origem_ref, s.usuario_nome, ident_u.nome, s.criado_em
      ORDER BY COALESCE(MAX(e.criado_em), s.criado_em) DESC
      LIMIT 20
    `;

    const entitlementSql = `
      SELECT app_id, subject_id, payload_json, valid_until, updated_at
        FROM entitlement_snapshots
       WHERE lower(subject_id) = lower($1::text)
       ORDER BY updated_at DESC NULLS LAST
       LIMIT 1
    `;

    const snapshotsSql = `
      SELECT DISTINCT ON (
        s.sistema_origem,
        CASE
          WHEN COALESCE(e.dados->>'escopo', '') = 'professor'
          THEN COALESCE(e.dados->>'id_clie', '')
          ELSE ''
        END
      )
        s.sistema_origem,
        e.dados,
        e.criado_em,
        COALESCE(e.dados->>'escopo', '') AS escopo,
        e.dados->>'id_clie' AS id_clie
      FROM crm_eventos e
      JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
      WHERE s.instituicao_id = $1::uuid
        AND e.tipo_evento = 'conta_snapshot'
      ORDER BY
        s.sistema_origem,
        CASE
          WHEN COALESCE(e.dados->>'escopo', '') = 'professor'
          THEN COALESCE(e.dados->>'id_clie', '')
          ELSE ''
        END,
        e.criado_em DESC
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
        snapRes,
        uso30d,
      ] = await Promise.all([
        pool.query(contaSql, [instituicaoId]),
        pool.query(contratosSql, [instituicaoId]),
        pool.query(tiposSql, [instituicaoId]),
        pool.query(usuariosSql, [instituicaoId]),
        pool.query(usuariosTiposSql, [instituicaoId]),
        pool.query(creditosSql, [instituicaoId]),
        pool.query(sessoesSql, [instituicaoId]),
        pool.query(entitlementSql, [instituicaoId]),
        pool.query(snapshotsSql, [instituicaoId]),
        computeUso30dForInstituicao(pool, instituicaoId),
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

      let snapshotSchool = null;
      let snapshotInove = null;
      const snapshotsProfessores = [];
      for (const row of snapRes.rows) {
        const escopo = String(row.escopo || '');
        const shaped = shapeSnapshotEvent(row);
        if (escopo === 'professor') {
          snapshotsProfessores.push({
            id_clie: row.id_clie != null && row.id_clie !== '' ? String(row.id_clie) : null,
            ...shaped,
          });
          continue;
        }
        if (row.sistema_origem === 'inove4us-school' && !snapshotSchool) {
          snapshotSchool = shaped;
        } else if (row.sistema_origem === 'inove4us' && !snapshotInove) {
          snapshotInove = shaped;
        }
      }

      return res.json({
        ok: true,
        conta: {
          ...base,
          assentos: assentosFromSchoolSnap(snapshotSchool && snapshotSchool.dados),
          snapshot_school: snapshotSchool,
          snapshot_inove: snapshotInove,
          snapshots_professores: snapshotsProfessores,
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
            usuario_nome: nomeOuCodigo(u.usuario_nome, u.usuario_origem_ref),
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
            usuario_nome: nomeOuCodigo(s.usuario_nome, s.usuario_origem_ref),
            inicio: iso(s.inicio),
            ultimo_evento: iso(s.ultimo_evento),
            n_eventos: asInt(s.n_eventos),
          })),
          uso_30d: uso30d,
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
