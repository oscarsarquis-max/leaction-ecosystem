const { mapNomeGrupoParaPapel } = require("../config_pesos");
const {
  calcularScoreIndicador,
  calcularScoreIndicadorDetalhado,
} = require("./indicador_score_engine");
const { calcularIapsColaboradorComPesos, buscarColaboradorPorId } = require("./dashboard_iaps");
const { filtrarMedicoesElegiveis } = require("./iaps_calculator");

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

function buildPeriodo(periodo, dataReferencia) {
  if (periodo && typeof periodo === "object") {
    return {
      inicio: periodo.inicio || dataReferencia || null,
      fim: periodo.fim || periodo.inicio || dataReferencia || null,
    };
  }

  return {
    inicio: dataReferencia || null,
    fim: dataReferencia || null,
  };
}

/**
 * Última medição bem-sucedida por (colaborador, indicador) nos últimos 12 meses.
 */
const SQL_ULTIMAS_MEDICOES = `
  SELECT DISTINCT ON (m.id_colaborador, i.cod_indicador)
         m.id,
         m.nome_arquivo,
         m.data_importacao,
         m.data_referencia,
         m.status_import,
         m.id_colaborador,
         m.payload,
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
         d.explicacao,
         d.importancia,
         c.nome AS nome_colaborador,
         c.matricula AS matricula_colaborador,
         c.funcao AS funcao_colaborador,
         c.codsetor,
         c.papel AS papel_colaborador,
         c.subpapel AS subpapel_colaborador
  FROM medicoes m
  INNER JOIN indicadores i ON i.id = m.indicador_id
  LEFT JOIN descricao_indicador d ON d.cod_indicador = i.cod_indicador
  LEFT JOIN colaboradores c ON c.id_colaborador = m.id_colaborador
  WHERE m.status_import = 'SUCESSO'
    AND m.id_colaborador IS NOT NULL
    AND m.data_referencia >= (CURRENT_DATE - INTERVAL '12 months')
  ORDER BY m.id_colaborador, i.cod_indicador, m.data_referencia DESC, m.data_importacao DESC
`;

function media(valores) {
  const validos = valores.filter(
    (v) => v !== null && v !== undefined && !Number.isNaN(Number(v))
  );
  if (!validos.length) {
    return null;
  }
  return Number(
    (
      validos.reduce((acc, v) => acc + Number(v), 0) / validos.length
    ).toFixed(2)
  );
}

/**
 * Calcula baselines (média de scores mathjs) por indicador × nível de agregação.
 */
function construirMapasBaseline(rows) {
  const porSubpapel = new Map();
  const porPapel = new Map();
  const porSetor = new Map();
  const porTotal = new Map();

  const push = (mapa, chave, score) => {
    if (!chave || score === null || score === undefined) {
      return;
    }
    if (!mapa.has(chave)) {
      mapa.set(chave, []);
    }
    mapa.get(chave).push(score);
  };

  for (const row of rows) {
    const detalhe = calcularScoreIndicadorDetalhado({
      cod_indicador: row.cod_indicador,
      formula_normalizada: row.formula_normalizada,
      parametros_configuraveis: row.parametros_configuraveis,
      payload: row.payload,
    });

    if (detalhe.score === null) {
      continue;
    }

    const cod = row.cod_indicador;
    push(porTotal, cod, detalhe.score);
    push(porSubpapel, `${cod}||${row.subpapel_colaborador || ""}`, detalhe.score);
    push(porPapel, `${cod}||${row.papel_colaborador || ""}`, detalhe.score);
    push(porSetor, `${cod}||${row.codsetor || ""}`, detalhe.score);
  }

  const avgMap = (mapa) => {
    const out = new Map();
    for (const [chave, vals] of mapa.entries()) {
      out.set(chave, media(vals));
    }
    return out;
  };

  return {
    subpapel: avgMap(porSubpapel),
    papel: avgMap(porPapel),
    setor: avgMap(porSetor),
    total: avgMap(porTotal),
  };
}

function resolverBaselineScore(row, nivelBaseline, mapas) {
  const cod = row.cod_indicador;

  if (nivelBaseline === "colaborador" || nivelBaseline === "subpapel") {
    const chave = `${cod}||${row.subpapel_colaborador || ""}`;
    if (row.subpapel_colaborador && mapas.subpapel.has(chave)) {
      return mapas.subpapel.get(chave);
    }
  }

  if (nivelBaseline === "papel") {
    const chave = `${cod}||${row.papel_colaborador || ""}`;
    if (row.papel_colaborador && mapas.papel.has(chave)) {
      return mapas.papel.get(chave);
    }
  }

  if (nivelBaseline === "setor") {
    const chave = `${cod}||${row.codsetor || ""}`;
    if (row.codsetor && mapas.setor.has(chave)) {
      return mapas.setor.get(chave);
    }
  }

  return mapas.total.get(cod) ?? null;
}

function mapRowToMetrica(row, nivelBaseline, baselineScore) {
  const detalhe = calcularScoreIndicadorDetalhado({
    cod_indicador: row.cod_indicador,
    formula_normalizada: row.formula_normalizada,
    parametros_configuraveis: row.parametros_configuraveis,
    payload: row.payload,
  });

  const normalized = normalizeScoreParts(detalhe.score);
  const resumo = {
    score: normalized.score,
    score_percentual: normalized.score_percentual,
    score_origem: detalhe.origem,
    formula_normalizada: detalhe.formula_normalizada,
    variaveis: detalhe.variaveis,
    expressao_substituida: detalhe.expressao_substituida,
    resultado_bruto: detalhe.resultado_bruto,
    erro_calculo: detalhe.erro,
  };

  if (baselineScore !== null && baselineScore !== undefined) {
    resumo.baseline_score_percentual = baselineScore;
    resumo.baseline_score = Number((baselineScore / 100).toFixed(4));
  }

  const colaborador =
    row.id_colaborador || row.nome_colaborador
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

  const periodoPayload =
    row.payload && typeof row.payload === "object" ? row.payload.periodo : null;
  const periodo = buildPeriodo(periodoPayload || {}, row.data_referencia);

  return {
    id: row.id,
    id_colaborador: row.id_colaborador ?? null,
    indicador,
    medicao: {
      id: row.id,
      nome_arquivo: row.nome_arquivo,
      data_importacao: row.data_importacao,
      data_referencia: row.data_referencia,
      status_import: row.status_import,
    },
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
    data_importacao: row.data_importacao,
    data_referencia: row.data_referencia,
    data_referencia_inicio: periodo?.inicio ?? row.data_referencia,
    data_referencia_fim: periodo?.fim ?? row.data_referencia,
    resumo,
    itens_total: 0,
    periodo,
    calculo: {
      formula_normalizada: detalhe.formula_normalizada,
      variaveis: detalhe.variaveis,
      expressao_substituida: detalhe.expressao_substituida,
      resultado_bruto: detalhe.resultado_bruto,
      score_percentual: detalhe.score,
      origem: detalhe.origem,
      erro: detalhe.erro,
      baseline_score: baselineScore,
    },
  };
}

function montarPassosMemoriaIndicadores(metricas) {
  return metricas.map((metrica) => {
    const calc = metrica.calculo || {};
    const score = calc.score_percentual ?? metrica.resumo?.score_percentual ?? null;
    const baseline = metrica.baseline_score ?? null;
    const gap =
      score !== null && baseline !== null
        ? Number((score - baseline).toFixed(2))
        : null;

    return {
      cod_indicador: metrica.cod_indicador,
      nome_indicador: metrica.nome_indicador,
      dimensao: metrica.dimensao,
      nivel_avaliacao: metrica.nivel_avaliacao,
      formula_normalizada: calc.formula_normalizada ?? metrica.formula_normalizada,
      payload: metrica.payload,
      variaveis: calc.variaveis || {},
      expressao_substituida: calc.expressao_substituida,
      resultado_bruto: calc.resultado_bruto,
      score_individual: score,
      score_equipe_baseline: baseline,
      gap_vs_baseline: gap,
      peso_ind_eq: "40/60",
      origem: calc.origem,
      erro: calc.erro,
      passo_a_passo: [
        {
          etapa: 1,
          descricao: "Payload limpo (variáveis)",
          valor: calc.variaveis || metrica.payload || {},
        },
        {
          etapa: 2,
          descricao: "Fórmula normalizada (mathjs)",
          valor: calc.formula_normalizada ?? metrica.formula_normalizada ?? null,
        },
        {
          etapa: 3,
          descricao: "Substituição",
          valor: calc.expressao_substituida,
        },
        {
          etapa: 4,
          descricao: "Resultado math.evaluate",
          valor: calc.resultado_bruto,
          erro: calc.erro,
        },
        {
          etapa: 5,
          descricao: "Score percentual normalizado",
          valor: score,
        },
        {
          etapa: 6,
          descricao: "Baseline equipe (média peers mathjs)",
          valor: baseline,
        },
      ],
    };
  });
}

function enriquecerMemoriaCalculoComPassos(memoriaCalculo, metricas) {
  const porCodigo = new Map(
    metricas.map((m) => [m.cod_indicador, m.calculo || null])
  );

  const enriquecerIndicador = (indicador) => {
    if (!indicador) {
      return null;
    }

    if (Array.isArray(indicador.indicadores)) {
      return {
        ...indicador,
        indicadores: indicador.indicadores.map((item) => {
          const calc = porCodigo.get(item.cod_indicador);
          return calc
            ? {
                ...item,
                formula_normalizada: calc.formula_normalizada,
                variaveis: calc.variaveis,
                expressao_substituida: calc.expressao_substituida,
                resultado_bruto: calc.resultado_bruto,
                erro: calc.erro,
              }
            : item;
        }),
      };
    }

    const calc = porCodigo.get(indicador.cod_indicador);
    if (!calc) {
      return indicador;
    }

    return {
      ...indicador,
      formula_normalizada: calc.formula_normalizada,
      variaveis: calc.variaveis,
      expressao_substituida: calc.expressao_substituida,
      resultado_bruto: calc.resultado_bruto,
      erro: calc.erro,
    };
  };

  return (memoriaCalculo || []).map((linha) => ({
    ...linha,
    indicador_individual: enriquecerIndicador(linha.indicador_individual),
    indicador_equipe: enriquecerIndicador(linha.indicador_equipe),
  }));
}

async function carregarUltimasMedicoes(pool) {
  const { rows } = await pool.query(SQL_ULTIMAS_MEDICOES);
  return rows;
}

async function montarRespostaMetricas(pool, rowsFiltradas, {
  nivelBaseline = "colaborador",
  idColaborador = null,
  todasRows = null,
} = {}) {
  const universo = todasRows || rowsFiltradas;
  const mapasBaseline = construirMapasBaseline(universo);

  const metricas = rowsFiltradas.map((row) => {
    const baselineScore = resolverBaselineScore(row, nivelBaseline, mapasBaseline);
    return mapRowToMetrica(row, nivelBaseline, baselineScore);
  });

  let iaps_calculado = null;
  let scores_dimensoes = null;
  let memoria_calculo = null;
  let memoria_calculo_indicadores = null;
  let metricasResposta = metricas;

  if (idColaborador) {
    const colaboradorDb = await buscarColaboradorPorId(pool, idColaborador);
    const resultadoIaps = await calcularIapsColaboradorComPesos(
      pool,
      metricas,
      colaboradorDb
    );

    iaps_calculado = resultadoIaps.iaps_calculado;
    scores_dimensoes = resultadoIaps.scores_dimensoes;
    memoria_calculo = enriquecerMemoriaCalculoComPassos(
      resultadoIaps.memoria_calculo,
      metricas
    );
    memoria_calculo_indicadores = montarPassosMemoriaIndicadores(
      filtrarMedicoesElegiveis(
        metricas,
        resultadoIaps.contexto,
        resultadoIaps.pesos_config
      )
    );

    const codigosIaps = new Set(
      filtrarMedicoesElegiveis(
        metricas,
        resultadoIaps.contexto,
        resultadoIaps.pesos_config
      ).map((item) => item.cod_indicador)
    );
    metricasResposta = metricas.filter((item) => codigosIaps.has(item.cod_indicador));
  }

  return {
    total: metricasResposta.length,
    iaps_calculado,
    scores_dimensoes,
    memoria_calculo,
    memoria_calculo_indicadores,
    metricas: metricasResposta,
  };
}

async function obterMetricasPorColaborador(pool, idColaborador) {
  const id = Number(idColaborador);
  if (!Number.isInteger(id) || id <= 0) {
    const error = new Error("id_colaborador inválido");
    error.statusCode = 400;
    throw error;
  }

  const colaborador = await buscarColaboradorPorId(pool, id);
  if (!colaborador) {
    const error = new Error("Colaborador não encontrado");
    error.statusCode = 404;
    throw error;
  }

  const todas = await carregarUltimasMedicoes(pool);
  const doColaborador = todas.filter((row) => row.id_colaborador === id);

  const resposta = await montarRespostaMetricas(pool, doColaborador, {
    nivelBaseline: "colaborador",
    idColaborador: id,
    todasRows: todas,
  });

  return {
    ...resposta,
    filtros: {
      nivel: "colaborador",
      id_colaborador: id,
      busca: colaborador.matricula || colaborador.nome,
    },
    colaborador: {
      id_colaborador: colaborador.id_colaborador,
      matricula: colaborador.matricula,
      nome: colaborador.nome,
      papel: colaborador.papel,
      subpapel: colaborador.subpapel,
      codsetor: colaborador.codsetor,
    },
  };
}

module.exports = {
  obterMetricasPorColaborador,
  montarRespostaMetricas,
  carregarUltimasMedicoes,
  mapRowToMetrica,
  calcularScoreIndicador,
};
