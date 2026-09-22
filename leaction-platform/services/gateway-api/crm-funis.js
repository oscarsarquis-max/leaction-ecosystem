/**
 * Mapa de funil do Action-Sponge, uma entrada por sistema.
 * O PanelDX e o fallback nomeado: origem desconhecida usa o modelo dele,
 * filtrando os eventos pelo sistema pedido ($1), como a ingestao ja fazia.
 *
 * inove4us, inove4us-school e paneldx estao transcritos do SQL anterior.
 * Nenhuma etapa, rotulo, evento ou ordem desses tres foi alterada.
 */

const FUNIS = {
  inove4us: {
    sistema: 'inove4us',
    modelo: 'inove4us_desafio_plano_pagamento',
    funilSql: `WITH base AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
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
             FROM base`,
    engagementSql: `WITH ev AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
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
             FROM ev`,
    etapas: [
      { chave: 'acesso', rotulo: 'Acesso / Mesa', regra: 'pageview em /, vazio, /acesso ou /mesa-do-inovador' },
      { chave: 'desafio', rotulo: 'Criou desafio', regra: 'desafio_estruturar ou desafio_estruturar_fallback' },
      { chave: 'plano', rotulo: 'Elaborou plano', tipo_evento: 'plano_gerar' },
      { chave: 'pagamento', rotulo: 'Pagou / assinou', tipo_evento: 'pagamento_aprovado' },
    ],
    ramos: [],
  },
  'inove4us-school': {
    sistema: 'inove4us-school',
    modelo: 'inove4us_school_b2b',
    funilSql: `WITH base AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
             )
             SELECT
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview'
                   AND (path = '/' OR path = '' OR path LIKE '/acesso%')
               ) AS visitas_home,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'login_sucesso'
               ) AS cliques_mesa_inovador,
               0::int AS cliques_solucionador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'login_sucesso'
               ) AS cliques_ferramentas,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'pageview' AND path LIKE '/equipe%'
               ) AS acesso_mesa_inovador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'checkout_iniciar'
               ) AS acesso_solucionador,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'checkout_iniciar'
               ) AS acesso_ferramentas,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'login_sucesso'
               ) AS desafios_estruturados,
               COUNT(DISTINCT id_sessao) FILTER (
                 WHERE tipo_evento = 'checkout_iniciar'
               ) AS planos_gerados,
               0::int AS desafios_erro,
               0::int AS desafios_fallback,
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
             FROM base`,
    engagementSql: `WITH ev AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
                 AND e.tempo_gasto_segundos > 0
             )
             SELECT
               COALESCE(AVG(tempo_gasto_segundos) FILTER (
                 WHERE path LIKE '/acesso%' OR path = '/' OR path = ''
               ), 0) AS avg_mesa_segundos,
               COALESCE(AVG(tempo_gasto_segundos) FILTER (
                 WHERE path LIKE '/equipe%'
               ), 0) AS avg_solucionador_segundos,
               COUNT(*) FILTER (
                 WHERE path LIKE '/acesso%' OR path = '/' OR path = ''
               ) AS amostras_mesa,
               COUNT(*) FILTER (WHERE path LIKE '/equipe%') AS amostras_solucionador
             FROM ev`,
    etapas: [
      { chave: 'acesso', rotulo: 'Acesso', regra: 'pageview em /, vazio ou /acesso' },
      { chave: 'login', rotulo: 'Login', tipo_evento: 'login_sucesso' },
      { chave: 'checkout', rotulo: 'Checkout', tipo_evento: 'checkout_iniciar' },
      { chave: 'pagamento', rotulo: 'Pagou', tipo_evento: 'pagamento_aprovado' },
    ],
    ramos: [],
  },
  paneldx: {
    sistema: 'paneldx',
    modelo: 'paneldx_freemium',
    fallback: true,
    funilSql: `WITH base AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
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
             FROM base`,
    engagementSql: `WITH ev AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
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
    etapas: [
      { chave: 'home', rotulo: 'Home', regra: 'pageview em / ou vazio' },
      { chave: 'interesse', rotulo: 'Interesse (Clique)', regra: 'click_cta_mesa_inovador ou click_cta_solucionador' },
      { chave: 'uso', rotulo: 'Uso Real', regra: 'pageview em /mesa-do-inovador, /solucionador-de-problemas ou /consultor-leaction' },
    ],
    ramos: [],
  },
  lojadepaes: {
    sistema: 'lojadepaes',
    modelo: 'lojadepaes_fornada',
    funilSql: `WITH base AS (
               SELECT
                 e.tipo_evento,
                 e.id_sessao
               FROM crm_eventos e
               INNER JOIN crm_sessoes s ON s.id_sessao = e.id_sessao
               WHERE s.sistema_origem = $1
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
             )
             SELECT
               COUNT(DISTINCT id_sessao) FILTER (WHERE tipo_evento = 'pageview') AS visitas_home,
               0::int AS cliques_mesa_inovador,
               0::int AS cliques_solucionador,
               0::int AS cliques_ferramentas,
               0::int AS acesso_mesa_inovador,
               0::int AS acesso_solucionador,
               0::int AS acesso_ferramentas,
               COUNT(DISTINCT id_sessao) FILTER (WHERE tipo_evento = 'fornada_escolher') AS etapa_escolha,
               COUNT(DISTINCT id_sessao) FILTER (WHERE tipo_evento = 'pedido_enviar') AS etapa_pedido,
               COUNT(DISTINCT id_sessao) FILTER (WHERE tipo_evento = 'pedido_aceitar') AS etapa_aceite,
               COUNT(DISTINCT id_sessao) FILTER (WHERE tipo_evento = 'pagamento_registrar') AS etapa_pagamento,
               COUNT(DISTINCT id_sessao) FILTER (WHERE tipo_evento = 'data_solicitar') AS ramo_outra_data,
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
             FROM base`,
    engagementSql: `WITH ev AS (
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
                 AND ($2::uuid IS NULL OR s.instituicao_id = $2::uuid)
                 AND e.tipo_evento <> 'conta_snapshot'
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
    nota: 'Pedido enviado não reserva a fornada. O aceite da padaria é que ocupa a data. O pagamento é registro financeiro, fora da reserva.',
    etapas: [
      { chave: 'visita', rotulo: 'Visita', tipo_evento: 'pageview' },
      { chave: 'escolha', rotulo: 'Escolha', tipo_evento: 'fornada_escolher' },
      { chave: 'pedido', rotulo: 'Pedido enviado', tipo_evento: 'pedido_enviar' },
      { chave: 'aceite', rotulo: 'Aceite da padaria', tipo_evento: 'pedido_aceitar' },
      { chave: 'pagamento', rotulo: 'Pagamento', tipo_evento: 'pagamento_registrar' },
    ],
    ramos: [
      {
        chave: 'outra_data',
        rotulo: 'Outra data',
        tipo_evento: 'data_solicitar',
        sobre: 'escolha',
        nota: 'Pediu para avaliar outra data. Não confirma encomenda e não entra na cadeia de conversão.',
      },
    ],
  },
};

const FALLBACK_SISTEMA = 'paneldx';

function resolveFunil(sistema) {
  if (sistema && FUNIS[sistema]) {
    return { ...FUNIS[sistema], solicitado: sistema, fallbackDe: null };
  }
  const base = FUNIS[FALLBACK_SISTEMA];
  return { ...base, solicitado: sistema || null, fallbackDe: FALLBACK_SISTEMA };
}

function convPct(part, total) {
  const p = Number(part) || 0;
  const t = Number(total) || 0;
  if (t <= 0) return 0;
  return Math.min(100, Math.round((p / t) * 1000) / 10);
}

function montarFunilLoja(row) {
  const def = FUNIS.lojadepaes;
  const porChave = {
    visita: Number(row.visitas_home || 0),
    escolha: Number(row.etapa_escolha || 0),
    pedido: Number(row.etapa_pedido || 0),
    aceite: Number(row.etapa_aceite || 0),
    pagamento: Number(row.etapa_pagamento || 0),
  };
  const etapas = def.etapas.map((etapa, index) => {
    const sessoes = porChave[etapa.chave] || 0;
    const anterior = index === 0 ? null : porChave[def.etapas[index - 1].chave] || 0;
    const conv = index === 0 ? null : convPct(sessoes, anterior);
    return {
      chave: etapa.chave,
      rotulo: etapa.rotulo,
      tipo_evento: etapa.tipo_evento,
      sessoes,
      conv_anterior_pct: conv,
      dropoff_pct: conv == null ? null : Math.round((100 - conv) * 10) / 10,
    };
  });
  const escolha = porChave.escolha;
  const outra = Number(row.ramo_outra_data || 0);
  const ramos = def.ramos.map((ramo) => ({
    chave: ramo.chave,
    rotulo: ramo.rotulo,
    tipo_evento: ramo.tipo_evento,
    sobre: ramo.sobre,
    nota: ramo.nota,
    sessoes: outra,
    sobre_sessoes: escolha,
    pct: convPct(outra, escolha),
  }));
  return {
    modelo: def.modelo,
    nota: def.nota,
    etapas,
    ramos,
    conversao_visita_aceite_pct: convPct(porChave.aceite, porChave.visita),
  };
}

module.exports = { FUNIS, FALLBACK_SISTEMA, resolveFunil, montarFunilLoja };
