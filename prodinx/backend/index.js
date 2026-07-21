require("dotenv").config({ path: require("path").join(__dirname, "..", ".env") });

const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");
const {
  CONFIG_PESOS_IAPS,
  mapNomeGrupoParaPapel,
} = require("./config_pesos");
const { ensureDatabaseSchema } = require("./db_migrations");
const {
  buscarColaboradorPorId,
  resolverIdColaboradorFiltro,
  calcularIapsColaboradorComPesos,
} = require("./services/dashboard_iaps");
const { filtrarMedicoesElegiveis } = require("./services/iaps_calculator");
const {
  listarOpcoesConfiguracaoPesos,
  buscarConfiguracaoPesosPorPapel,
  salvarConfiguracaoPesos,
} = require("./services/configuracao_pesos_api");
const createIndicadoresRouter = require("./routes/indicadores");
const { calcularScoreIndicador } = require("./services/indicador_score_engine");
const {
  gerarAnaliseInteligente,
  montarContextoAnalise,
  calcularHashContexto,
} = require("./services/analise_inteligente_service");
const {
  buscarAnaliseArmazenada,
  salvarAnaliseArmazenada,
} = require("./services/analise_inteligente_repository");

const app = express();
const PORT = process.env.PORT || 3002;

const pool = new Pool({
  user: process.env.POSTGRES_USER || "postgres",
  password: process.env.POSTGRES_PASSWORD || "Cmgv6190!@",
  host: process.env.POSTGRES_HOST || "localhost",
  port: Number(process.env.POSTGRES_PORT) || 5432,
  database: process.env.POSTGRES_DB || "prodinx",
});

const corsOrigins = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(",").map((origin) => origin.trim())
  : [
      "http://localhost:3000",
      "http://localhost:5176",
      "http://127.0.0.1:5176",
    ];

app.use(
  cors({
    origin: corsOrigins,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);

app.use(express.json());

app.use("/api/indicadores", createIndicadoresRouter(pool));

function normalizeScoreParts(score) {
  if (score === null || score === undefined || Number.isNaN(Number(score))) {
    return { score: null, score_percentual: null };
  }

  const numeric = Number(score);
  if (numeric <= 1 && numeric >= 0) {
    return {
      score: numeric,
      score_percentual: Number((numeric * 100).toFixed(2)),
    };
  }

  return {
    score: numeric / 100,
    score_percentual: Number(numeric.toFixed(2)),
  };
}

function extractScore(payload) {
  const resumo = payload?.resumo;
  if (resumo?.score !== undefined && resumo?.score !== null) {
    return Number(resumo.score);
  }
  if (payload?.efficiency_score !== undefined && payload?.efficiency_score !== null) {
    return Number(payload.efficiency_score);
  }
  return null;
}

const ITENS_PREVIEW_LIMIT = 50;

function extractItens(payload, limit = ITENS_PREVIEW_LIMIT) {
  let itens = [];
  if (Array.isArray(payload?.itens)) {
    itens = payload.itens;
  } else if (Array.isArray(payload?.bugs_detalhes)) {
    itens = payload.bugs_detalhes;
  }

  if (itens.length <= limit) {
    return { itens, itens_total: itens.length, itens_truncados: false };
  }

  return {
    itens: itens.slice(0, limit),
    itens_total: itens.length,
    itens_truncados: true,
  };
}

function buildPeriodo(periodo, dataReferencia) {
  if (periodo && typeof periodo === "object") {
    return {
      inicio: periodo.inicio || dataReferencia || null,
      fim: periodo.fim || periodo.inicio || dataReferencia || null,
    };
  }

  if (dataReferencia) {
    return { inicio: dataReferencia, fim: dataReferencia };
  }

  return null;
}

function countItens(payload) {
  if (Array.isArray(payload?.itens)) {
    return payload.itens.length;
  }
  if (Array.isArray(payload?.bugs_detalhes)) {
    return payload.bugs_detalhes.length;
  }
  return 0;
}

const BASELINE_NIVEIS = new Set(["colaborador", "papel", "subpapel", "setor", "funcao"]);

const NIVEIS_FILTRO = {
  colaborador: "colaborador",
  papel: "papel",
  subpapel: "subpapel",
  setor: "setor",
  funcao: "subpapel",
};

const DASHBOARD_METRICAS_SQL = `
WITH medicoes_enriquecidas AS (
  SELECT m.id,
         m.nome_arquivo,
         m.data_importacao,
         m.data_referencia,
         m.status_import,
         m.id_colaborador,
         m.payload->'resumo' AS resumo,
         m.payload->'periodo' AS periodo,
         m.payload->'efficiency_score' AS efficiency_score,
         CASE
           WHEN jsonb_typeof(m.payload->'itens') = 'array'
             THEN jsonb_array_length(m.payload->'itens')
           WHEN jsonb_typeof(m.payload->'bugs_detalhes') = 'array'
             THEN jsonb_array_length(m.payload->'bugs_detalhes')
           ELSE 0
         END AS itens_total,
         i.id AS indicador_id,
         i.cod_indicador,
         i.nome_indicador,
         i.nome_grupo,
         i.dimensao,
         i.nivel_avaliacao,
         i.formula_original,
         i.formula_normalizada,
         i.parametros_configuraveis,
         i.subpapeis_aplicaveis,
         m.payload,
         d.explicacao,
         d.importancia,
         c.nome AS nome_colaborador,
         c.matricula AS matricula_colaborador,
         c.funcao AS funcao_colaborador,
         c.codsetor,
         c.papel AS papel_colaborador,
         c.subpapel AS subpapel_colaborador,
         COALESCE(
           NULLIF((m.payload->'resumo'->>'score_percentual')::numeric, NULL),
           CASE
             WHEN NULLIF(m.payload->'resumo'->>'score', '') IS NOT NULL
                  AND (m.payload->'resumo'->>'score')::numeric BETWEEN 0 AND 1
               THEN ROUND(((m.payload->'resumo'->>'score')::numeric * 100)::numeric, 2)
             WHEN NULLIF(m.payload->'resumo'->>'score', '') IS NOT NULL
               THEN ROUND((m.payload->'resumo'->>'score')::numeric, 2)
             WHEN NULLIF(m.payload->>'efficiency_score', '') IS NOT NULL
                  AND (m.payload->>'efficiency_score')::numeric BETWEEN 0 AND 1
               THEN ROUND(((m.payload->>'efficiency_score')::numeric * 100)::numeric, 2)
             WHEN NULLIF(m.payload->>'efficiency_score', '') IS NOT NULL
               THEN ROUND((m.payload->>'efficiency_score')::numeric, 2)
             ELSE NULL
           END
         ) AS score_percentual
  FROM medicoes m
  INNER JOIN indicadores i ON i.id = m.indicador_id
  LEFT JOIN descricao_indicador d ON d.cod_indicador = i.cod_indicador
  LEFT JOIN colaboradores c ON m.id_colaborador = c.id_colaborador
  WHERE m.status_import = 'SUCESSO'
    AND m.data_referencia >= (CURRENT_DATE - INTERVAL '12 months')
),
baseline_por_subpapel AS (
  SELECT cod_indicador,
         subpapel_colaborador,
         ROUND(AVG(score_percentual)::numeric, 2) AS baseline_score
  FROM medicoes_enriquecidas
  WHERE score_percentual IS NOT NULL
    AND subpapel_colaborador IS NOT NULL
  GROUP BY cod_indicador, subpapel_colaborador
),
baseline_por_papel AS (
  SELECT cod_indicador,
         papel_colaborador,
         ROUND(AVG(score_percentual)::numeric, 2) AS baseline_score
  FROM medicoes_enriquecidas
  WHERE score_percentual IS NOT NULL
    AND papel_colaborador IS NOT NULL
  GROUP BY cod_indicador, papel_colaborador
),
baseline_por_setor AS (
  SELECT cod_indicador,
         codsetor,
         ROUND(AVG(score_percentual)::numeric, 2) AS baseline_score
  FROM medicoes_enriquecidas
  WHERE score_percentual IS NOT NULL
    AND codsetor IS NOT NULL
  GROUP BY cod_indicador, codsetor
),
baseline_total AS (
  SELECT cod_indicador,
         ROUND(AVG(score_percentual)::numeric, 2) AS baseline_score
  FROM medicoes_enriquecidas
  WHERE score_percentual IS NOT NULL
  GROUP BY cod_indicador
)
SELECT me.*,
       CASE $1::text
         WHEN 'colaborador' THEN bpsub.baseline_score
         WHEN 'papel' THEN bpap.baseline_score
         WHEN 'subpapel' THEN bps.baseline_score
         WHEN 'setor' THEN bt.baseline_score
         ELSE bt.baseline_score
       END AS baseline_score
FROM medicoes_enriquecidas me
LEFT JOIN baseline_por_subpapel bpsub
  ON bpsub.cod_indicador = me.cod_indicador
 AND bpsub.subpapel_colaborador = me.subpapel_colaborador
LEFT JOIN baseline_por_papel bpap
  ON bpap.cod_indicador = me.cod_indicador
 AND bpap.papel_colaborador = me.papel_colaborador
LEFT JOIN baseline_por_setor bps
  ON bps.cod_indicador = me.cod_indicador
 AND bps.codsetor = me.codsetor
LEFT JOIN baseline_total bt
  ON bt.cod_indicador = me.cod_indicador
WHERE (
    $1::text = 'colaborador'
    AND (
      ($4::integer IS NOT NULL AND me.id_colaborador = $4::integer)
      OR (
        $4::integer IS NULL
        AND (
          $2::text IS NULL
          OR TRIM($2::text) = ''
          OR me.matricula_colaborador ILIKE '%' || TRIM($2::text) || '%'
          OR me.nome_colaborador ILIKE '%' || TRIM($2::text) || '%'
        )
      )
    )
  )
  OR (
    $1::text = 'papel'
    AND (
      $5::text IS NULL
      OR TRIM($5::text) = ''
      OR me.papel_colaborador ILIKE '%' || TRIM($5::text) || '%'
    )
  )
  OR (
    $1::text = 'subpapel'
    AND (
      $6::text IS NULL
      OR TRIM($6::text) = ''
      OR me.subpapel_colaborador ILIKE '%' || TRIM($6::text) || '%'
    )
  )
  OR (
    $1::text = 'setor'
    AND (
      $3::text IS NULL
      OR TRIM($3::text) = ''
      OR me.codsetor ILIKE '%' || TRIM($3::text) || '%'
    )
  )
ORDER BY me.data_referencia DESC, me.data_importacao DESC
`;

function parseDashboardQuery(query = {}) {
  const nivelRaw = String(query.nivel || query.filtro || "colaborador").toLowerCase();
  const nivelMapeado = NIVEIS_FILTRO[nivelRaw] ?? null;
  const nivel = nivelMapeado || "colaborador";

  const colaboradorBusca = query.colaborador_busca
    ? String(query.colaborador_busca).trim()
    : query.colaborador_valor
      ? String(query.colaborador_valor).trim()
      : null;
  const papel = query.papel ? String(query.papel).trim() : null;
  const subpapel = query.subpapel
    ? String(query.subpapel).trim()
    : query.funcao
      ? String(query.funcao).trim()
      : null;
  const codsetor = query.codsetor ? String(query.codsetor).trim() : null;
  const idColaboradorRaw = query.id_colaborador ?? query.colaborador_id ?? null;
  const idColaboradorParsed = idColaboradorRaw ? Number(idColaboradorRaw) : null;
  const idColaborador =
    Number.isInteger(idColaboradorParsed) && idColaboradorParsed > 0
      ? idColaboradorParsed
      : null;

  return {
    nivel,
    colaboradorBusca: colaboradorBusca || null,
    papel: papel || null,
    subpapel: subpapel || null,
    codsetor: codsetor || null,
    idColaborador,
  };
}

function resolverBuscaFiltro(filtros) {
  if (filtros.nivel === "colaborador") {
    return filtros.colaboradorBusca;
  }
  if (filtros.nivel === "papel") {
    return filtros.papel;
  }
  if (filtros.nivel === "subpapel") {
    return filtros.subpapel;
  }
  if (filtros.nivel === "setor") {
    return filtros.codsetor;
  }
  return null;
}

function mapDashboardMetrica(row, nivelBaseline = "colaborador") {
  const resumo = row.resumo && typeof row.resumo === "object" ? { ...row.resumo } : {};
  const score =
    resumo.score !== undefined && resumo.score !== null
      ? Number(resumo.score)
      : row.efficiency_score !== undefined && row.efficiency_score !== null
        ? Number(row.efficiency_score)
        : null;

  if (score !== null) {
    const normalized = normalizeScoreParts(score);
    resumo.score = normalized.score;
    resumo.score_percentual = normalized.score_percentual;
  } else if (row.score_percentual !== null && row.score_percentual !== undefined) {
    const normalized = normalizeScoreParts(Number(row.score_percentual));
    resumo.score = normalized.score;
    resumo.score_percentual = normalized.score_percentual;
  }

  const scoreDinamico = calcularScoreIndicador(
    {
      cod_indicador: row.cod_indicador,
      formula_normalizada: row.formula_normalizada,
      parametros_configuraveis: row.parametros_configuraveis,
      payload: row.payload && typeof row.payload === "object" ? row.payload : null,
      resumo,
      baseline_score: row.baseline_score,
    },
    "selecionado"
  );

  if (scoreDinamico !== null && !Number.isNaN(scoreDinamico)) {
    const normalizedDinamico = normalizeScoreParts(scoreDinamico);
    resumo.score = normalizedDinamico.score;
    resumo.score_percentual = normalizedDinamico.score_percentual;
    resumo.score_origem = row.formula_normalizada ? "formula_normalizada" : "armazenado";
  }

  const baselineScore =
    row.baseline_score !== null && row.baseline_score !== undefined
      ? Number(row.baseline_score)
      : null;

  if (baselineScore !== null && !Number.isNaN(baselineScore)) {
    resumo.baseline_score_percentual = baselineScore;
    resumo.baseline_score = Number((baselineScore / 100).toFixed(4));
  }

  const colaborador =
    row.id_colaborador || row.nome_colaborador || row.funcao_colaborador || row.codsetor
      ? {
          id_colaborador: row.id_colaborador ?? null,
          nome: row.nome_colaborador ?? null,
          matricula: row.matricula_colaborador ?? null,
          funcao: row.funcao_colaborador ?? null,
          codsetor: row.codsetor ?? null,
          papel: row.papel_colaborador ?? null,
          subpapel: row.subpapel_colaborador ?? null,
        }
      : null;

  const indicador = {
    id: row.indicador_id,
    cod_indicador: row.cod_indicador,
    nome_indicador: row.nome_indicador,
    nome_grupo: row.nome_grupo,
    dimensao: row.dimensao,
    nivel_avaliacao: row.nivel_avaliacao,
    formula_original: row.formula_original,
    formula_normalizada: row.formula_normalizada ?? null,
    parametros_configuraveis: row.parametros_configuraveis ?? null,
    subpapeis_aplicaveis: row.subpapeis_aplicaveis ?? null,
    nome_metrica: `${row.cod_indicador} - ${row.nome_indicador}`,
    explicacao: row.explicacao ?? null,
    importancia: row.importancia ?? null,
  };

  const medicao = {
    id: row.id,
    nome_arquivo: row.nome_arquivo,
    data_importacao: row.data_importacao,
    data_referencia: row.data_referencia,
    status_import: row.status_import,
  };

  const periodo = buildPeriodo(row.periodo || {}, row.data_referencia);
  const itens_total = Number(row.itens_total) || 0;

  return {
    id: row.id,
    id_colaborador: row.id_colaborador ?? colaborador?.id_colaborador ?? null,
    indicador,
    medicao,
    colaborador,
    nome_colaborador: colaborador?.nome ?? null,
    funcao_colaborador: colaborador?.funcao ?? null,
    codsetor: colaborador?.codsetor ?? null,
    papel_colaborador: colaborador?.papel ?? mapNomeGrupoParaPapel(row.nome_grupo),
    subpapel_colaborador: colaborador?.subpapel ?? null,
    baseline_score: baselineScore,
    nivel_baseline: nivelBaseline,
    nome_metrica: indicador.nome_metrica,
    nome_grupo: indicador.nome_grupo,
    cod_indicador: indicador.cod_indicador,
    nome_indicador: indicador.nome_indicador,
    dimensao: indicador.dimensao,
    nivel_avaliacao: indicador.nivel_avaliacao,
    subpapeis_aplicaveis: indicador.subpapeis_aplicaveis,
    formula_normalizada: indicador.formula_normalizada,
    parametros_configuraveis: indicador.parametros_configuraveis,
    payload: row.payload && typeof row.payload === "object" ? row.payload : null,
    explicacao: indicador.explicacao,
    importancia: indicador.importancia,
    data_importacao: medicao.data_importacao,
    data_referencia: medicao.data_referencia,
    data_referencia_inicio: periodo?.inicio ?? medicao.data_referencia,
    data_referencia_fim: periodo?.fim ?? medicao.data_referencia,
    resumo,
    itens_total,
    periodo,
  };
}

function extractItensFromPayload(payload) {
  if (Array.isArray(payload?.itens)) {
    return payload.itens;
  }
  if (Array.isArray(payload?.bugs_detalhes)) {
    return payload.bugs_detalhes;
  }
  return [];
}

function filterItens(itens, query) {
  const term = String(query || "").trim().toLowerCase();
  if (!term) {
    return itens;
  }

  return itens.filter((item) =>
    JSON.stringify(item).toLowerCase().includes(term)
  );
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.get("/api/dashboard/pesos-iaps", (_req, res) => {
  res.json(CONFIG_PESOS_IAPS);
});

app.get("/api/dashboard/filtros-opcoes", async (_req, res, next) => {
  try {
    const [colaboradoresResult, papeisResult, subpapeisResult, setoresResult] = await Promise.all([
      pool.query(
        `SELECT id_colaborador, matricula, nome, funcao, codsetor, papel, subpapel
         FROM colaboradores
         ORDER BY nome`
      ),
      pool.query(
        `SELECT DISTINCT papel
         FROM colaboradores
         WHERE papel IS NOT NULL AND TRIM(papel) <> ''
         ORDER BY papel`
      ),
      pool.query(
        `SELECT DISTINCT subpapel
         FROM colaboradores
         WHERE subpapel IS NOT NULL AND TRIM(subpapel) <> ''
         ORDER BY subpapel`
      ),
      pool.query(
        `SELECT DISTINCT codsetor
         FROM colaboradores
         WHERE codsetor IS NOT NULL AND TRIM(codsetor) <> ''
         ORDER BY codsetor`
      ),
    ]);

    res.json({
      colaboradores: colaboradoresResult.rows.map((row) => ({
        id_colaborador: row.id_colaborador,
        matricula: row.matricula,
        nome: row.nome,
        funcao: row.funcao,
        codsetor: row.codsetor,
        papel: row.papel,
        subpapel: row.subpapel,
        label: `${row.nome}${row.subpapel ? ` · ${row.subpapel}` : row.funcao ? ` · ${row.funcao}` : ""}`,
      })),
      papeis: papeisResult.rows.map((row) => row.papel),
      subpapeis: subpapeisResult.rows.map((row) => row.subpapel),
      setores: setoresResult.rows.map((row) => row.codsetor),
      niveis: [
        {
          valor: "colaborador",
          label: "Colaborador",
          baseline: "Média do subpapel",
        },
        {
          valor: "papel",
          label: "Papel",
          baseline: "Média do setor",
        },
        {
          valor: "subpapel",
          label: "Subpapel",
          baseline: "Média do papel",
        },
        {
          valor: "setor",
          label: "Setor",
          baseline: "Média total",
        },
      ],
    });
  } catch (error) {
    next(error);
  }
});

app.get("/api/configuracao-pesos/opcoes", async (_req, res, next) => {
  try {
    const opcoes = await listarOpcoesConfiguracaoPesos();
    res.json(opcoes);
  } catch (error) {
    next(error);
  }
});

app.get("/api/configuracao-pesos", async (req, res, next) => {
  try {
    const papel = String(req.query.papel || "").trim();
    const subpapel = String(req.query.subpapel || "").trim();

    if (!papel || !subpapel) {
      return res.status(400).json({
        erro: "Os parâmetros papel e subpapel são obrigatórios",
      });
    }

    const configuracao = await buscarConfiguracaoPesosPorPapel(pool, papel, subpapel);

    res.json({
      papel,
      subpapel,
      configuracao,
    });
  } catch (error) {
    next(error);
  }
});

app.put("/api/configuracao-pesos", async (req, res, next) => {
  try {
    const configuracao = await salvarConfiguracaoPesos(pool, req.body || {});
    res.json({
      mensagem: "Configurações salvas com sucesso",
      configuracao,
    });
  } catch (error) {
    next(error);
  }
});

app.post("/api/configuracao-pesos", async (req, res, next) => {
  try {
    const configuracao = await salvarConfiguracaoPesos(pool, req.body || {});
    res.json({
      mensagem: "Configurações salvas com sucesso",
      configuracao,
    });
  } catch (error) {
    next(error);
  }
});

app.get("/api/dashboard/metricas", async (req, res, next) => {
  try {
    const filtros = parseDashboardQuery(req.query);
    const idColaboradorResolvido = await resolverIdColaboradorFiltro(pool, filtros);
    const idColaboradorFiltro = filtros.idColaborador || idColaboradorResolvido;

    const { rows } = await pool.query(DASHBOARD_METRICAS_SQL, [
      filtros.nivel,
      filtros.nivel === "colaborador" ? filtros.colaboradorBusca : null,
      filtros.nivel === "setor" ? filtros.codsetor : null,
      idColaboradorFiltro,
      filtros.nivel === "papel" ? filtros.papel : null,
      filtros.nivel === "subpapel" ? filtros.subpapel : null,
    ]);

    const metricas = rows.map((row) => mapDashboardMetrica(row, filtros.nivel));

    let iaps_calculado = null;
    let scores_dimensoes = null;
    let memoria_calculo = null;
    let metricasResposta = metricas;

    if (idColaboradorFiltro) {
      const colaboradorDb = await buscarColaboradorPorId(pool, idColaboradorFiltro);
      const resultadoIaps = await calcularIapsColaboradorComPesos(
        pool,
        metricas,
        colaboradorDb
      );
      iaps_calculado = resultadoIaps.iaps_calculado;
      scores_dimensoes = resultadoIaps.scores_dimensoes;
      memoria_calculo = resultadoIaps.memoria_calculo;

      const codigosIaps = new Set(
        filtrarMedicoesElegiveis(
          metricas,
          resultadoIaps.contexto,
          resultadoIaps.pesos_config
        ).map((item) => item.cod_indicador)
      );
      metricasResposta = metricas.filter((item) => codigosIaps.has(item.cod_indicador));
    }

    res.json({
      total: metricasResposta.length,
      filtros: {
        nivel: filtros.nivel,
        busca: resolverBuscaFiltro(filtros),
        id_colaborador: idColaboradorFiltro,
      },
      iaps_calculado,
      scores_dimensoes,
      memoria_calculo,
      metricas: metricasResposta,
    });
  } catch (error) {
    next(error);
  }
});

app.get("/api/analise-inteligente/:id_colaborador", async (req, res, next) => {
  try {
    const idColaborador = Number(req.params.id_colaborador);
    const regenerar =
      req.query.regenerar === "1" ||
      req.query.regenerar === "true" ||
      req.query.regenerar === "sim";

    if (!Number.isInteger(idColaborador) || idColaborador <= 0) {
      return res.status(400).json({ erro: "id_colaborador inválido" });
    }

    const colaboradorDb = await buscarColaboradorPorId(pool, idColaborador);

    if (!colaboradorDb) {
      return res.status(404).json({ erro: "Colaborador não encontrado" });
    }

    const { rows } = await pool.query(DASHBOARD_METRICAS_SQL, [
      "colaborador",
      null,
      null,
      idColaborador,
      null,
      null,
    ]);

    const metricas = rows.map((row) => mapDashboardMetrica(row, "colaborador"));
    const resultadoIaps = await calcularIapsColaboradorComPesos(
      pool,
      metricas,
      colaboradorDb
    );

    if (!resultadoIaps.memoria_calculo?.length) {
      return res.status(404).json({
        erro: "Sem medições elegíveis para análise cruzada deste colaborador",
      });
    }

    const contexto = montarContextoAnalise({
      colaborador: colaboradorDb,
      iapsCalculado: resultadoIaps.iaps_calculado,
      scoresDimensoes: resultadoIaps.scores_dimensoes,
      memoriaCalculo: resultadoIaps.memoria_calculo,
    });
    const hashContexto = calcularHashContexto(contexto);

    if (!regenerar) {
      const armazenada = await buscarAnaliseArmazenada(pool, idColaborador);

      if (armazenada?.resultado && armazenada.hash_contexto === hashContexto) {
        const resultado =
          typeof armazenada.resultado === "string"
            ? JSON.parse(armazenada.resultado)
            : armazenada.resultado;

        return res.json({
          ...resultado,
          origem: "cache",
          gerado_em: armazenada.gerado_em,
          atualizado_em: armazenada.atualizado_em,
          hash_contexto: hashContexto,
        });
      }
    }

    const analise = await gerarAnaliseInteligente({
      colaborador: colaboradorDb,
      iapsCalculado: resultadoIaps.iaps_calculado,
      scoresDimensoes: resultadoIaps.scores_dimensoes,
      memoriaCalculo: resultadoIaps.memoria_calculo,
    });

    const persistencia = await salvarAnaliseArmazenada(
      pool,
      idColaborador,
      hashContexto,
      analise
    );

    res.json({
      ...analise,
      origem: regenerar ? "ia_regenerada" : "ia",
      gerado_em: persistencia?.gerado_em ?? analise.gerado_em,
      atualizado_em: persistencia?.atualizado_em ?? analise.gerado_em,
      hash_contexto: hashContexto,
    });
  } catch (error) {
    if (error.message?.includes("JSON") || error.name === "CredentialsProviderError") {
      error.statusCode = 503;
    }
    next(error);
  }
});

app.get("/api/medicoes/:id/itens", async (req, res, next) => {
  try {
    const medicaoId = Number(req.params.id);
    const limit = Math.min(Math.max(Number(req.query.limit) || 50, 1), 200);
    const offset = Math.max(Number(req.query.offset) || 0, 0);
    const query = req.query.q || "";

    const { rows } = await pool.query(
      `SELECT m.id,
              m.data_importacao,
              m.data_referencia,
              m.payload,
              i.cod_indicador,
              i.nome_indicador
       FROM medicoes m
       LEFT JOIN indicadores i ON i.id = m.indicador_id
       WHERE m.id = $1 AND m.status_import = 'SUCESSO'`,
      [medicaoId]
    );

    if (rows.length === 0) {
      return res.status(404).json({ erro: "Medição não encontrada" });
    }

    const row = rows[0];
    const payload = row.payload || {};
    const allItens = filterItens(extractItensFromPayload(payload), query);
    const itens = allItens.slice(offset, offset + limit);

    res.json({
      medicao_id: row.id,
      nome_metrica: row.cod_indicador
        ? `${row.cod_indicador} - ${row.nome_indicador}`
        : payload.metrica || null,
      data_importacao: row.data_importacao,
      data_referencia: row.data_referencia,
      total: allItens.length,
      limit,
      offset,
      itens,
    });
  } catch (error) {
    next(error);
  }
});

app.get("/api/importacoes", async (_req, res, next) => {
  try {
    const { rows } = await pool.query(
      `SELECT m.id, m.indicador_id, m.nome_arquivo, m.data_importacao,
              m.data_referencia, m.status_import, m.detalhe_status,
              i.cod_indicador, i.nome_indicador, i.nome_grupo,
              m.payload->'periodo'->>'inicio' AS periodo_inicio,
              m.payload->'periodo'->>'fim' AS periodo_fim,
              c.matricula AS colaborador_matricula,
              c.nome AS colaborador_nome
       FROM medicoes m
       LEFT JOIN indicadores i ON i.id = m.indicador_id
       LEFT JOIN colaboradores c ON c.id_colaborador = m.id_colaborador
       ORDER BY m.data_importacao DESC`
    );

    const importacoes = rows.map((row) => ({
      id: row.id,
      indicador_id: row.indicador_id,
      nome_arquivo: row.nome_arquivo,
      cod_indicador: row.cod_indicador ?? null,
      nome_indicador: row.nome_indicador ?? null,
      nome_metrica: row.cod_indicador
        ? `${row.cod_indicador} - ${row.nome_indicador}`
        : null,
      nome_grupo: row.nome_grupo ?? null,
      colaborador_matricula: row.colaborador_matricula ?? null,
      colaborador_nome: row.colaborador_nome ?? null,
      data_importacao: row.data_importacao,
      data_referencia: row.data_referencia ?? null,
      data_referencia_inicio: row.data_referencia || row.periodo_inicio,
      data_referencia_fim: row.periodo_fim,
      status: row.status_import?.toLowerCase(),
      mensagem_erro: row.detalhe_status,
    }));

    res.json({
      total: importacoes.length,
      importacoes,
    });
  } catch (error) {
    next(error);
  }
});

app.use((_req, res) => {
  res.status(404).json({ erro: "Rota não encontrada" });
});

app.use((error, _req, res, _next) => {
  console.error("Erro na API:", error.message);

  if (error instanceof SyntaxError && error.status === 400 && "body" in error) {
    return res.status(400).json({
      erro: "JSON malformado no corpo da requisição",
    });
  }

  if (error.statusCode) {
    return res.status(error.statusCode).json({
      erro: error.message,
      detalhes: error.detalhes,
    });
  }

  if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
    return res.status(503).json({
      erro: "Não foi possível ligar à base de dados PostgreSQL",
    });
  }

  if (error.code === "42P01") {
    return res.status(503).json({
      erro: "Tabelas indicadores/medicoes não encontradas. Execute o serviço Flask para criar o schema",
    });
  }

  if (error.code === "42703") {
    return res.status(503).json({
      erro: "Schema da base de dados desatualizado. Reinicie o backend para aplicar migrações.",
      detalhe: process.env.NODE_ENV === "development" ? error.message : undefined,
    });
  }

  if (error.statusCode) {
    return res.status(error.statusCode).json({
      erro: error.message || "Falha ao processar análise inteligente",
      detalhe: process.env.NODE_ENV === "development" ? error.stack : undefined,
    });
  }

  res.status(500).json({
    erro: "Erro interno do servidor",
    detalhe: process.env.NODE_ENV === "development" ? error.message : undefined,
  });
});

async function startServer() {
  try {
    await ensureDatabaseSchema(pool);
    console.log("Schema IAPS (papel/subpapel/configuracao_pesos) verificado.");
  } catch (error) {
    console.error("Falha ao aplicar migrações do schema:", error.message);
    process.exit(1);
  }

  const server = app.listen(PORT, "0.0.0.0", () => {
    console.log(`API Prodinx a correr em http://localhost:${PORT}`);
  });

  server.on("error", (error) => {
    if (error.code === "EADDRINUSE") {
      console.error(`Porta ${PORT} ja esta em uso — o backend provavelmente ja esta ativo.`);
      console.error(`Teste: http://127.0.0.1:${PORT}/api/dashboard/metricas`);
      process.exit(1);
    }
    throw error;
  });
}

startServer();
