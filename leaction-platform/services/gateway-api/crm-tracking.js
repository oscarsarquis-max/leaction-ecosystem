'use strict';

const crypto = require('crypto');

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function getCrmSecret() {
  return String(process.env.CRM_TRACKING_SECRET || '').trim();
}

function crmSecretAuthorized(req) {
  const expected = getCrmSecret();
  if (!expected) {
    // Sem secret configurado: bloqueia em produção; libera em local só se NODE_ENV=development
    if (process.env.NODE_ENV === 'production') return false;
    console.warn('⚠️ [crm] CRM_TRACKING_SECRET vazio — aceitando sem header (dev).');
    return true;
  }
  const got = String(req.headers['x-crm-secret'] || '').trim();
  return got.length > 0 && got === expected;
}

function hashIp(ipReal) {
  const raw = String(ipReal || '').trim() || 'unknown';
  const salt = String(process.env.CRM_IP_HASH_SALT || getCrmSecret() || 'crm-dev-salt').trim();
  return crypto.createHash('sha256').update(`${salt}|${raw}`).digest('hex');
}

function normalizeTipoEvento(value) {
  const t = String(value || '').trim().toLowerCase().slice(0, 128);
  return t || 'pageview';
}

function parseOptionalUserId(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number.parseInt(String(value), 10);
  return Number.isFinite(n) ? n : null;
}

/** Converte ratio em percentual com 1 casa decimal. */
function roundPct(part, total) {
  const p = Number(part) || 0;
  const t = Number(total) || 0;
  if (t <= 0) return 0;
  return Math.round((p / t) * 1000) / 10;
}

/** Percentual de conversão limitado a 0–100 (acesso direto pode superar CTAs). */
function convPct(part, total) {
  return Math.min(100, roundPct(part, total));
}

function dropoffPct(conv) {
  return Math.round((100 - Math.min(100, Math.max(0, Number(conv) || 0))) * 10) / 10;
}

function formatDuration(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return {
    segundos: s,
    minutos: Math.round((s / 60) * 10) / 10,
    label: mins > 0 ? `${mins}m ${secs}s` : `${secs}s`,
  };
}

function normalizeOrigemSlug(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

async function ensureCrmOrigensTable(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS crm_origens (
      slug VARCHAR(64) PRIMARY KEY,
      nome VARCHAR(160) NOT NULL,
      descricao TEXT NULL,
      ativo BOOLEAN NOT NULL DEFAULT TRUE,
      criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
  `);
  await pool.query(
    `INSERT INTO crm_origens (slug, nome, descricao)
     VALUES
       ('paneldx', 'PanelDX', 'Transformação Digital Educacional'),
       ('inove4us', 'inove4us', 'Mesa do Inovador (freemium)')
     ON CONFLICT (slug) DO NOTHING`
  );
}

/**
 * Rotas CRM Tracking — ingestão S2S + dashboard funil freemium.
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 */
function registerCrmTrackingRoutes(app, pool) {
  // bootstrap idempotente (não bloqueia registro de rotas se falhar)
  ensureCrmOrigensTable(pool).catch((err) => {
    console.warn('⚠️ [crm] ensureCrmOrigensTable:', err.message);
  });

  /**
   * GET /api/crm/origens — catálogo + origens já vistas em sessões
   */
  app.get('/api/crm/origens', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }
    try {
      await ensureCrmOrigensTable(pool);
      const [catalog, seen] = await Promise.all([
        pool.query(
          `SELECT slug, nome, descricao, ativo, criado_em, atualizado_em
           FROM crm_origens
           ORDER BY nome ASC`
        ),
        pool.query(
          `SELECT sistema_origem AS slug, COUNT(*)::int AS sessoes
           FROM crm_sessoes
           GROUP BY sistema_origem
           ORDER BY sessoes DESC`
        ),
      ]);
      const seenMap = new Map(seen.rows.map((r) => [r.slug, r.sessoes]));
      const items = catalog.rows.map((r) => ({
        slug: r.slug,
        nome: r.nome,
        descricao: r.descricao,
        ativo: r.ativo,
        criado_em: r.criado_em,
        atualizado_em: r.atualizado_em,
        sessoes: seenMap.get(r.slug) || 0,
        fonte: 'catalogo',
      }));
      for (const row of seen.rows) {
        if (!items.some((i) => i.slug === row.slug)) {
          items.push({
            slug: row.slug,
            nome: row.slug,
            descricao: null,
            ativo: true,
            criado_em: null,
            atualizado_em: null,
            sessoes: row.sessoes,
            fonte: 'detectada',
          });
        }
      }
      items.sort((a, b) => String(a.nome).localeCompare(String(b.nome), 'pt-BR'));
      return res.json({ ok: true, origens: items });
    } catch (err) {
      console.error('❌ [crm/origens GET]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao listar origens' });
    }
  });

  /**
   * POST /api/crm/origens — cadastra origem analisável
   * Body: { slug, nome, descricao? }
   */
  app.post('/api/crm/origens', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }
    const body = req.body || {};
    const slug = normalizeOrigemSlug(body.slug || body.sistema_origem || body.nome);
    const nome = String(body.nome || slug || '').trim().slice(0, 160);
    const descricao = String(body.descricao || '').trim().slice(0, 500) || null;

    if (!slug || slug.length < 2) {
      return res.status(400).json({
        ok: false,
        error: 'Informe um slug válido (letras, números, _ ou -).',
      });
    }
    if (!nome) {
      return res.status(400).json({ ok: false, error: 'Informe o nome da origem.' });
    }

    try {
      await ensureCrmOrigensTable(pool);
      const inserted = await pool.query(
        `INSERT INTO crm_origens (slug, nome, descricao)
         VALUES ($1, $2, $3)
         ON CONFLICT (slug) DO UPDATE
           SET nome = EXCLUDED.nome,
               descricao = COALESCE(EXCLUDED.descricao, crm_origens.descricao),
               ativo = TRUE,
               atualizado_em = CURRENT_TIMESTAMP
         RETURNING slug, nome, descricao, ativo, criado_em, atualizado_em`,
        [slug, nome, descricao]
      );
      return res.status(201).json({ ok: true, origem: inserted.rows[0] });
    } catch (err) {
      console.error('❌ [crm/origens POST]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao cadastrar origem' });
    }
  });

  /**
   * POST /api/crm/tracking/receber
   * Body: sistema_origem, id_sessao, id_usuario?, tipo_evento, url_pagina, ip_real?, user_agent?
   * Header: x-crm-secret
   */
  app.post('/api/crm/tracking/receber', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }

    const body = req.body || {};
    const sistemaOrigem = String(body.sistema_origem || '').trim().toLowerCase().slice(0, 64);
    const idSessao = String(body.id_sessao || '').trim();
    const tipoEvento = normalizeTipoEvento(body.tipo_evento);
    const urlPagina = String(body.url_pagina || '').trim().slice(0, 2048) || null;
    const idUsuario = parseOptionalUserId(body.id_usuario ?? body.id_usuario_origem);
    const tempoGasto = Number.parseInt(String(body.tempo_gasto_segundos ?? 0), 10);
    const tempoSegundos = Number.isFinite(tempoGasto) && tempoGasto >= 0 ? tempoGasto : 0;
    const userAgent = String(body.user_agent || req.headers['user-agent'] || '').slice(0, 4000) || null;
    const ipHash = hashIp(body.ip_real);

    if (!sistemaOrigem) {
      return res.status(400).json({ ok: false, error: 'sistema_origem obrigatório' });
    }
    if (!UUID_RE.test(idSessao)) {
      return res.status(400).json({ ok: false, error: 'id_sessao deve ser UUID válido' });
    }

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      await client.query(
        `INSERT INTO crm_sessoes (id_sessao, sistema_origem, id_usuario_origem, ip_hash, user_agent)
         VALUES ($1::uuid, $2, $3, $4, $5)
         ON CONFLICT (id_sessao) DO NOTHING`,
        [idSessao, sistemaOrigem, idUsuario, ipHash, userAgent]
      );

      // Se a sessão já existia sem usuário e agora veio id_usuario, atualiza.
      if (idUsuario != null) {
        await client.query(
          `UPDATE crm_sessoes
           SET id_usuario_origem = COALESCE(id_usuario_origem, $2)
           WHERE id_sessao = $1::uuid`,
          [idSessao, idUsuario]
        );
      }

      const inserted = await client.query(
        `INSERT INTO crm_eventos (id_sessao, tipo_evento, url_pagina, tempo_gasto_segundos)
         VALUES ($1::uuid, $2, $3, $4)
         RETURNING id, criado_em`,
        [idSessao, tipoEvento, urlPagina, tempoSegundos]
      );

      await client.query('COMMIT');

      return res.status(201).json({
        ok: true,
        id_evento: inserted.rows[0].id,
        id_sessao: idSessao,
        criado_em: inserted.rows[0].criado_em,
      });
    } catch (err) {
      await client.query('ROLLBACK').catch(() => {});
      console.error('❌ [crm/tracking/receber]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao registrar evento CRM' });
    } finally {
      client.release();
    }
  });

  /**
   * GET /api/crm/dashboard/funil-freemium?sistema=paneldx
   * Agrega funil PLG, conversão, engajamento, retenção 24h, dispositivos + sessões recentes.
   * Header: x-crm-secret (ou CRM_TRACKING_SECRET configurado).
   */
  app.get('/api/crm/dashboard/funil-freemium', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }

    const sistema = String(req.query.sistema || 'paneldx').trim().toLowerCase() || 'paneldx';
    const isInove4us = sistema === 'inove4us';

    try {
      const funilSql = isInove4us
        ? `WITH base AS (
               SELECT
                 e.tipo_evento,
                 e.id_sessao,
                 split_part(
                   regexp_replace(COALESCE(e.url_pagina, ''), '^https?://[^/]+', ''),
                   '?',
                   1
                 ) AS path
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               WHERE s.sistema_origem = $1
             )
             SELECT
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview'
                   AND (
                     path = '/' OR path = '' OR path LIKE '/acesso%'
                     OR path LIKE '/mesa-do-inovador%'
                   )
               ) AS visitas_home,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento IN ('desafio_estruturar', 'desafio_estruturar_fallback')
               ) AS cliques_mesa_inovador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'caminho_selecionar'
               ) AS cliques_solucionador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento IN (
                   'desafio_estruturar',
                   'desafio_estruturar_fallback',
                   'caminho_selecionar'
                 )
               ) AS cliques_ferramentas,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview' AND path LIKE '/desafio%'
               ) AS acesso_mesa_inovador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'plano_gerar'
               ) AS acesso_solucionador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'plano_gerar'
                    OR (tipo_evento = 'pageview' AND path LIKE '/desafio%')
               ) AS acesso_ferramentas,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento IN ('desafio_estruturar', 'desafio_estruturar_fallback')
               ) AS desafios_estruturados,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'plano_gerar'
               ) AS planos_gerados,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'desafio_estruturar_erro'
               ) AS desafios_erro,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'desafio_estruturar_fallback'
               ) AS desafios_fallback,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'checkout_iniciar'
               ) AS checkouts_iniciados,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pagamento_aprovado'
               ) AS pagamentos_aprovados,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pagamento_pendente'
               ) AS pagamentos_pendentes,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pagamento_erro'
               ) AS pagamentos_erro,
               COUNT(*) AS total_eventos,
               COUNT(DISTINCT id_sessao) AS total_sessoes
             FROM base`
        : `WITH base AS (
               SELECT
                 e.tipo_evento,
                 e.id_sessao,
                 split_part(
                   regexp_replace(COALESCE(e.url_pagina, ''), '^https?://[^/]+', ''),
                   '?',
                   1
                 ) AS path
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               WHERE s.sistema_origem = $1
             )
             SELECT
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview' AND (path = '/' OR path = '')
               ) AS visitas_home,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'click_cta_mesa_inovador'
               ) AS cliques_mesa_inovador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'click_cta_solucionador'
               ) AS cliques_solucionador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento IN ('click_cta_mesa_inovador', 'click_cta_solucionador')
               ) AS cliques_ferramentas,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview' AND path LIKE '/mesa-do-inovador%'
               ) AS acesso_mesa_inovador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview'
                   AND (
                     path LIKE '/solucionador-de-problemas%'
                     OR path LIKE '/consultor-leaction%'
                   )
               ) AS acesso_solucionador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview'
                   AND (
                     path LIKE '/mesa-do-inovador%'
                     OR path LIKE '/solucionador-de-problemas%'
                     OR path LIKE '/consultor-leaction%'
                   )
               ) AS acesso_ferramentas,
               0::int AS desafios_estruturados,
               0::int AS planos_gerados,
               0::int AS desafios_erro,
               0::int AS desafios_fallback,
               0::int AS checkouts_iniciados,
               0::int AS pagamentos_aprovados,
               0::int AS pagamentos_pendentes,
               0::int AS pagamentos_erro,
               COUNT(*) AS total_eventos,
               COUNT(DISTINCT id_sessao) AS total_sessoes
             FROM base`;

      const [funilResult, engagementResult, retentionResult, devicesResult, recentesResult, evolucaoResult] =
        await Promise.all([
          pool.query(funilSql, [sistema]),

          // Tempo médio de engajamento (usa tempo_gasto_segundos > 0)
          pool.query(
            isInove4us
              ? `WITH ev AS (
               SELECT
                 split_part(
                   regexp_replace(COALESCE(e.url_pagina, ''), '^https?://[^/]+', ''),
                   '?',
                   1
                 ) AS path,
                 e.tempo_gasto_segundos
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               WHERE s.sistema_origem = $1
                 AND e.tempo_gasto_segundos > 0
             )
             SELECT
               COALESCE(AVG(tempo_gasto_segundos) FILTER (
                 WHERE path LIKE '/mesa-do-inovador%' OR path LIKE '/acesso%'
               ), 0) AS avg_mesa_segundos,
               COALESCE(AVG(tempo_gasto_segundos) FILTER (
                 WHERE path LIKE '/desafio%'
               ), 0) AS avg_solucionador_segundos,
               COUNT(*) FILTER (
                 WHERE path LIKE '/mesa-do-inovador%' OR path LIKE '/acesso%'
               ) AS amostras_mesa,
               COUNT(*) FILTER (WHERE path LIKE '/desafio%') AS amostras_solucionador
             FROM ev`
              : `WITH ev AS (
               SELECT
                 split_part(
                   regexp_replace(COALESCE(e.url_pagina, ''), '^https?://[^/]+', ''),
                   '?',
                   1
                 ) AS path,
                 e.tempo_gasto_segundos
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               WHERE s.sistema_origem = $1
                 AND e.tempo_gasto_segundos > 0
             )
             SELECT
               COALESCE(AVG(tempo_gasto_segundos) FILTER (
                 WHERE path LIKE '/mesa-do-inovador%'
               ), 0) AS avg_mesa_segundos,
               COALESCE(AVG(tempo_gasto_segundos) FILTER (
                 WHERE path LIKE '/solucionador-de-problemas%'
                   OR path LIKE '/consultor-leaction%'
               ), 0) AS avg_solucionador_segundos,
               COUNT(*) FILTER (WHERE path LIKE '/mesa-do-inovador%') AS amostras_mesa,
               COUNT(*) FILTER (
                 WHERE path LIKE '/solucionador-de-problemas%'
                   OR path LIKE '/consultor-leaction%'
               ) AS amostras_solucionador
             FROM ev`,
            [sistema]
          ),

          /**
           * Retenção 24h com session UUID sticky (localStorage 30d):
           * - novas: sessões com criado_em nas últimas 24h
           * - ativas: tiveram evento nas últimas 24h
           * - recorrentes: ativas cujo criado_em é anterior a 24h (UUID já existia)
           */
          pool.query(
            `WITH params AS (
               SELECT NOW() - INTERVAL '24 hours' AS desde
             ),
             novas AS (
               SELECT s.id_sessao
               FROM crm_sessoes s, params p
               WHERE s.sistema_origem = $1
                 AND s.criado_em >= p.desde
             ),
             ativas AS (
               SELECT DISTINCT e.id_sessao
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               CROSS JOIN params p
               WHERE s.sistema_origem = $1
                 AND e.criado_em >= p.desde
             ),
             recorrentes AS (
               SELECT a.id_sessao
               FROM ativas a
               INNER JOIN crm_sessoes s ON s.id_sessao = a.id_sessao
               CROSS JOIN params p
               WHERE s.criado_em < p.desde
             )
             SELECT
               (SELECT COUNT(*)::int FROM novas) AS sessoes_criadas_24h,
               (SELECT COUNT(*)::int FROM ativas) AS sessoes_ativas_24h,
               (SELECT COUNT(*)::int FROM recorrentes) AS sessoes_recorrentes_24h,
               (
                 SELECT COUNT(*)::int
                 FROM ativas a
                 WHERE a.id_sessao IN (SELECT id_sessao FROM novas)
               ) AS sessoes_novas_ativas_24h`,
            [sistema]
          ),

          pool.query(
            `SELECT
               COUNT(*) FILTER (
                 WHERE user_agent ~* '(mobile|android|iphone|ipod|ipad|webos|blackberry|iemobile|opera mini)'
               )::int AS mobile,
               COUNT(*) FILTER (
                 WHERE COALESCE(user_agent, '') <> ''
                   AND user_agent !~* '(mobile|android|iphone|ipod|ipad|webos|blackberry|iemobile|opera mini)'
               )::int AS desktop,
               COUNT(*) FILTER (
                 WHERE COALESCE(user_agent, '') = ''
               )::int AS desconhecido,
               COUNT(*)::int AS total
             FROM crm_sessoes
             WHERE sistema_origem = $1`,
            [sistema]
          ),

          pool.query(
            `SELECT s.id_sessao,
                    s.sistema_origem,
                    s.id_usuario_origem,
                    s.criado_em,
                    (
                      SELECT e2.tipo_evento
                      FROM crm_eventos e2
                      WHERE e2.id_sessao = s.id_sessao
                      ORDER BY e2.criado_em DESC
                      LIMIT 1
                    ) AS ultimo_evento,
                    (
                      SELECT e2.url_pagina
                      FROM crm_eventos e2
                      WHERE e2.id_sessao = s.id_sessao
                      ORDER BY e2.criado_em DESC
                      LIMIT 1
                    ) AS ultima_url,
                    (
                      SELECT COUNT(*)::int
                      FROM crm_eventos e3
                      WHERE e3.id_sessao = s.id_sessao
                    ) AS qtd_eventos
             FROM crm_sessoes s
             WHERE s.sistema_origem = $1
             ORDER BY s.criado_em DESC
             LIMIT 50`,
            [sistema]
          ),

          pool.query(
            `WITH dias AS (
               SELECT generate_series(
                 (CURRENT_DATE - INTERVAL '29 days')::date,
                 CURRENT_DATE::date,
                 '1 day'::interval
               )::date AS dia
             ),
             ev AS (
               SELECT
                 e.criado_em::date AS dia,
                 COUNT(*)::int AS eventos,
                 COUNT(*) FILTER (WHERE e.tipo_evento = 'pageview')::int AS pageviews
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               WHERE s.sistema_origem = $1
                 AND e.criado_em >= CURRENT_DATE - INTERVAL '29 days'
               GROUP BY e.criado_em::date
             )
             SELECT
               to_char(d.dia, 'DD/MM') AS dia,
               COALESCE(ev.pageviews, 0)::int AS pageviews,
               COALESCE(ev.eventos, 0)::int AS eventos
             FROM dias d
             LEFT JOIN ev ON ev.dia = d.dia
             ORDER BY d.dia ASC`,
            [sistema]
          ),
        ]);

      const row = funilResult.rows[0] || {};
      const eng = engagementResult.rows[0] || {};
      const ret = retentionResult.rows[0] || {};
      const dev = devicesResult.rows[0] || {};

      const visitasHome = Number(row.visitas_home || 0);
      const cliquesFerramentas = Number(row.cliques_ferramentas || 0);
      const acessoFerramentas = Number(row.acesso_ferramentas || 0);
      const cliquesMesa = Number(row.cliques_mesa_inovador || 0);
      const cliquesSol = Number(row.cliques_solucionador || 0);
      const acessoMesa = Number(row.acesso_mesa_inovador || 0);
      const acessoSol = Number(row.acesso_solucionador || 0);
      const desafiosEstruturados = Number(row.desafios_estruturados || 0);
      const planosGerados = Number(row.planos_gerados || 0);
      const desafiosErro = Number(row.desafios_erro || 0);
      const desafiosFallback = Number(row.desafios_fallback || 0);
      const checkoutsIniciados = Number(row.checkouts_iniciados || 0);
      const pagamentosAprovados = Number(row.pagamentos_aprovados || 0);
      const pagamentosPendentes = Number(row.pagamentos_pendentes || 0);
      const pagamentosErro = Number(row.pagamentos_erro || 0);

      // inove4us: Acesso → Criou desafio → Elaborou plano → Pagou/assinou
      const etapaInteresse = isInove4us ? desafiosEstruturados : cliquesFerramentas;
      const etapaUso = isInove4us ? planosGerados : acessoFerramentas;
      const etapaPagamento = isInove4us ? pagamentosAprovados : 0;
      const convHomeCliques = convPct(etapaInteresse, visitasHome);
      const convCliquesUso = convPct(etapaUso, etapaInteresse);
      const convHomeUso = convPct(
        isInove4us ? etapaPagamento || etapaUso : etapaUso,
        visitasHome
      );
      const convPlanoPagamento = convPct(etapaPagamento, etapaUso);

      const avgMesa = Number(eng.avg_mesa_segundos || 0);
      const avgSol = Number(eng.avg_solucionador_segundos || 0);

      const criadas24h = Number(ret.sessoes_criadas_24h || 0);
      const ativas24h = Number(ret.sessoes_ativas_24h || 0);
      const recorrentes24h = Number(ret.sessoes_recorrentes_24h || 0);
      const novasAtivas24h = Number(ret.sessoes_novas_ativas_24h || 0);

      const mobile = Number(dev.mobile || 0);
      const desktop = Number(dev.desktop || 0);
      const desconhecido = Number(dev.desconhecido || 0);
      const dispositivosTotal = Number(dev.total || 0);
      const dispositivosClassificados = mobile + desktop;

      return res.json({
        ok: true,
        sistema_origem: sistema,
        funil_modelo: isInove4us ? 'inove4us_desafio_plano_pagamento' : 'paneldx_freemium',
        funil: {
          visitas_home: visitasHome,
          cliques_mesa_inovador: cliquesMesa,
          cliques_solucionador: cliquesSol,
          cliques_ferramentas: isInove4us ? etapaInteresse : cliquesFerramentas,
          acesso_mesa_inovador: acessoMesa,
          acesso_solucionador: acessoSol,
          acesso_ferramentas: isInove4us ? etapaUso : acessoFerramentas,
          desafios_estruturados: desafiosEstruturados,
          planos_gerados: planosGerados,
          desafios_erro: desafiosErro,
          desafios_fallback: desafiosFallback,
          checkouts_iniciados: checkoutsIniciados,
          pagamentos_aprovados: pagamentosAprovados,
          pagamentos_pendentes: pagamentosPendentes,
          pagamentos_erro: pagamentosErro,
          total_eventos: Number(row.total_eventos || 0),
          total_sessoes: Number(row.total_sessoes || 0),
          taxas_conversao: {
            home_para_cliques_pct: convHomeCliques,
            cliques_para_uso_pct: convCliquesUso,
            home_para_uso_pct: convHomeUso,
            plano_para_pagamento_pct: isInove4us ? convPlanoPagamento : null,
            dropoff_home_para_cliques_pct: dropoffPct(convHomeCliques),
            dropoff_cliques_para_uso_pct: dropoffPct(convCliquesUso),
            dropoff_plano_para_pagamento_pct: isInove4us
              ? dropoffPct(convPlanoPagamento)
              : null,
          },
        },
        engajamento: {
          mesa_do_inovador: {
            ...formatDuration(avgMesa),
            amostras: Number(eng.amostras_mesa || 0),
          },
          solucionador: {
            ...formatDuration(avgSol),
            amostras: Number(eng.amostras_solucionador || 0),
          },
        },
        funcionalidades: isInove4us
          ? {
              desafio_estruturar: desafiosEstruturados,
              plano_gerar: planosGerados,
              caminho_selecionar: cliquesSol,
              desafio_estruturar_erro: desafiosErro,
              desafio_estruturar_fallback: desafiosFallback,
              checkout_iniciar: checkoutsIniciados,
              pagamento_aprovado: pagamentosAprovados,
              pagamento_pendente: pagamentosPendentes,
              pagamento_erro: pagamentosErro,
            }
          : null,
        retencao: {
          janela_horas: 24,
          sessoes_criadas_24h: criadas24h,
          sessoes_ativas_24h: ativas24h,
          sessoes_novas_ativas_24h: novasAtivas24h,
          sessoes_recorrentes_24h: recorrentes24h,
          taxa_retencao_pct: roundPct(recorrentes24h, ativas24h),
        },
        dispositivos: {
          mobile,
          desktop,
          desconhecido,
          total: dispositivosTotal,
          mobile_pct: roundPct(mobile, dispositivosClassificados),
          desktop_pct: roundPct(desktop, dispositivosClassificados),
        },
        sessoes_recentes: recentesResult.rows.map((r) => ({
          id_sessao: r.id_sessao,
          sistema_origem: r.sistema_origem,
          id_usuario_origem: r.id_usuario_origem,
          criado_em: r.criado_em,
          ultimo_evento: r.ultimo_evento,
          ultima_url: r.ultima_url,
          qtd_eventos: r.qtd_eventos,
        })),
        evolucao_acessos: evolucaoResult.rows.map((r) => ({
          dia: r.dia,
          pageviews: Number(r.pageviews || 0),
          eventos: Number(r.eventos || 0),
        })),
      });
    } catch (err) {
      console.error('❌ [crm/dashboard/funil-freemium]', err.message);
      return res.status(500).json({ ok: false, error: 'Falha ao agregar funil freemium' });
    }
  });
}

module.exports = {
  registerCrmTrackingRoutes,
  crmSecretAuthorized,
  hashIp,
};
