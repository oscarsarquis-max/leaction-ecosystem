const {
  mapNomeGrupoParaPapel,
  normalizarPapel,
  indicadorAplicaAoSubpapel,
} = require("../config_pesos");
const {
  resolverPesosDimensoesComConfig,
  resolverPesosNiveisComConfig,
} = require("./config_pesos_db");
const { calcularScoreIndicador } = require("./indicador_score_engine");

/**
 * Regra estrita: quando uma nota de nível estiver ausente, zera a parcela
 * em vez de redistribuir o peso para o nível disponível.
 */
const MODO_ESTRITO_NIVEL = false;

const ORDEM_DIMENSOES = [
  "Satisfação",
  "Performance",
  "Atividade",
  "Comunicação",
  "Eficiência",
];

const SIMBOLOS_DIMENSAO = {
  Satisfação: "Vs",
  Performance: "Vd",
  Atividade: "Ve",
  Comunicação: "Vc",
  Eficiência: "Va",
};

function arredondar(valor, casas = 2) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return null;
  }

  return Number(Number(valor).toFixed(casas));
}

function extrairScorePercentual(metrica, campo = "selecionado") {
  return calcularScoreIndicador(metrica, campo);
}

function normalizarNivelAvaliacao(nivel) {
  return String(nivel || "").trim() === "Individual" ? "Individual" : "Equipe";
}

function mediaValores(valores) {
  const validos = valores.filter(
    (valor) => valor !== null && valor !== undefined && !Number.isNaN(Number(valor))
  );

  if (validos.length === 0) {
    return null;
  }

  const soma = validos.reduce((acumulado, valor) => acumulado + Number(valor), 0);
  return soma / validos.length;
}

function deduplicarMedicoesPorIndicador(metricas) {
  const porIndicador = new Map();

  metricas.forEach((metrica) => {
    const codIndicador = metrica.cod_indicador;
    if (!codIndicador) {
      return;
    }

    const dataReferencia = String(metrica.data_referencia || "");
    const existente = porIndicador.get(codIndicador);

    if (
      !existente ||
      dataReferencia.localeCompare(String(existente.data_referencia || "")) > 0
    ) {
      porIndicador.set(codIndicador, metrica);
    }
  });

  return Array.from(porIndicador.values());
}

function filtrarMedicoesElegiveis(metricas, contexto, pesosConfig = null) {
  const { subpapel } = contexto;
  const pesosDimensoes = resolverPesosDimensoesComConfig(pesosConfig);

  return deduplicarMedicoesPorIndicador(metricas).filter((metrica) => {
    if (!metrica.dimensao || pesosDimensoes[metrica.dimensao] === undefined) {
      return false;
    }

    return indicadorAplicaAoSubpapel(metrica.subpapeis_aplicaveis, subpapel);
  });
}

function combinarNotasPorNivel(notaIndividual, notaEquipe, pesosNiveis) {
  const pesoIndividual = pesosNiveis.Individual;
  const pesoEquipe = pesosNiveis.Equipe;

  if (MODO_ESTRITO_NIVEL) {
    const individual = notaIndividual ?? 0;
    const equipe = notaEquipe ?? 0;
    return arredondar(individual * pesoIndividual + equipe * pesoEquipe);
  }

  let total = 0;
  let pesoAplicado = 0;

  if (notaIndividual !== null && notaIndividual !== undefined) {
    total += Number(notaIndividual) * pesoIndividual;
    pesoAplicado += pesoIndividual;
  }

  if (notaEquipe !== null && notaEquipe !== undefined) {
    total += Number(notaEquipe) * pesoEquipe;
    pesoAplicado += pesoEquipe;
  }

  if (pesoAplicado === 0) {
    return null;
  }

  return arredondar(total / pesoAplicado);
}

function agruparIndicadoresPorDimensao(medicoesElegiveis, campoScore = "selecionado") {
  const porDimensao = new Map();

  medicoesElegiveis.forEach((metrica) => {
    const dimensao = metrica.dimensao;
    const nivel = normalizarNivelAvaliacao(metrica.nivel_avaliacao);
    const score = extrairScorePercentual(metrica, campoScore);

    if (!porDimensao.has(dimensao)) {
      porDimensao.set(dimensao, { Individual: [], Equipe: [] });
    }

    porDimensao.get(dimensao)[nivel].push({
      cod_indicador: metrica.cod_indicador,
      nome_indicador: metrica.nome_indicador ?? null,
      explicacao: metrica.explicacao ?? null,
      importancia: metrica.importancia ?? null,
      score: arredondar(score),
    });
  });

  return porDimensao;
}

function agruparNotasPorDimensao(medicoesElegiveis, campoScore) {
  const porDimensao = new Map();

  medicoesElegiveis.forEach((metrica) => {
    const dimensao = metrica.dimensao;
    const nivel = normalizarNivelAvaliacao(metrica.nivel_avaliacao);
    const nota = extrairScorePercentual(metrica, campoScore);

    if (!porDimensao.has(dimensao)) {
      porDimensao.set(dimensao, { Individual: [], Equipe: [] });
    }

    if (nota !== null) {
      porDimensao.get(dimensao)[nivel].push(nota);
    }
  });

  return porDimensao;
}

function formatarProporcaoIndEq(pesosNiveis) {
  const pesoInd = Math.round((pesosNiveis.Individual || 0) * 100);
  const pesoEq = Math.round((pesosNiveis.Equipe || 0) * 100);
  return `${pesoInd}/${pesoEq}`;
}

function montarIndicadorLinha(indicadores = []) {
  if (!indicadores.length) {
    return null;
  }

  if (indicadores.length === 1) {
    return indicadores[0];
  }

  return {
    cod_indicador: indicadores.map((item) => item.cod_indicador).join(", "),
    nome_indicador: indicadores.map((item) => item.nome_indicador).filter(Boolean).join(" · "),
    score: arredondar(mediaValores(indicadores.map((item) => item.score))),
    indicadores: indicadores,
  };
}

function paraEscalaUnitaria(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return null;
  }

  const numero = Number(valor);
  return numero > 1 ? arredondar(numero / 100, 4) : arredondar(numero, 4);
}

function montarMemoriaCalculo(medicoesElegiveis, pesosConfig, scoresDimensoes, contexto = null) {
  const pesosDimensoes = resolverPesosDimensoesComConfig(pesosConfig);
  const pesosNiveis = resolverPesosNiveisComConfig(pesosConfig);
  const indicadoresPorDimensao = agruparIndicadoresPorDimensao(medicoesElegiveis);
  const scoresPorDimensao = new Map(
    (scoresDimensoes || []).map((item) => [item.dimensao, item])
  );

  return ORDEM_DIMENSOES.filter((dimensao) => pesosDimensoes[dimensao] !== undefined).map(
    (dimensao) => {
      const pesoDimensao = pesosDimensoes[dimensao];
      const indicadoresNivel = indicadoresPorDimensao.get(dimensao) || {
        Individual: [],
        Equipe: [],
      };
      const scoreLinha = scoresPorDimensao.get(dimensao) || {};

      const indicadorIndividual = montarIndicadorLinha(indicadoresNivel.Individual);
      const indicadorEquipe = montarIndicadorLinha(indicadoresNivel.Equipe);

      return {
        dimensao,
        simbolo: SIMBOLOS_DIMENSAO[dimensao] ?? null,
        subpapel_linha:
          dimensao === "Satisfação" ? "Todos" : contexto?.subpapel ?? null,
        peso_dimensao: pesoDimensao,
        indicador_individual: indicadorIndividual,
        indicador_equipe: indicadorEquipe,
        score_individual: scoreLinha.nota_individual ?? null,
        score_equipe: scoreLinha.nota_equipe ?? null,
        score_individual_unidade: paraEscalaUnitaria(scoreLinha.nota_individual),
        score_equipe_unidade: paraEscalaUnitaria(scoreLinha.nota_equipe),
        peso_individual: pesosNiveis.Individual,
        peso_equipe: pesosNiveis.Equipe,
        proporcao_ind_eq: formatarProporcaoIndEq(pesosNiveis),
        score_final: scoreLinha.score_dimensao ?? null,
        score_final_unidade: paraEscalaUnitaria(scoreLinha.score_dimensao),
        contribuicao_iaps: scoreLinha.contribuicao ?? null,
        contribuicao_iaps_unidade: paraEscalaUnitaria(scoreLinha.contribuicao),
      };
    }
  );
}

function calcularScoresDimensoes(
  medicoesElegiveis,
  pesosConfig,
  campoScore = "selecionado"
) {
  const pesosDimensoes = resolverPesosDimensoesComConfig(pesosConfig);
  const pesosNiveis = resolverPesosNiveisComConfig(pesosConfig);
  const notasPorDimensao = agruparNotasPorDimensao(medicoesElegiveis, campoScore);

  return ORDEM_DIMENSOES.filter((dimensao) => pesosDimensoes[dimensao] !== undefined).map(
    (dimensao) => {
      const pesoDimensao = pesosDimensoes[dimensao];
      const notasNivel = notasPorDimensao.get(dimensao) || { Individual: [], Equipe: [] };
      const notaIndividual = arredondar(mediaValores(notasNivel.Individual));
      const notaEquipe = arredondar(mediaValores(notasNivel.Equipe));
      const scoreDimensao = combinarNotasPorNivel(notaIndividual, notaEquipe, pesosNiveis);
      const contribuicao =
        scoreDimensao !== null ? arredondar(scoreDimensao * pesoDimensao) : null;

      return {
        dimensao,
        nota_individual: notaIndividual,
        nota_equipe: notaEquipe,
        score_dimensao: scoreDimensao,
        peso_dimensao: pesoDimensao,
        contribuicao,
        indicadores_individual: notasNivel.Individual.length,
        indicadores_equipe: notasNivel.Equipe.length,
      };
    }
  );
}

function calcularIapsFinal(scoresDimensoes) {
  const contribuicoes = scoresDimensoes
    .map((item) => item.contribuicao)
    .filter((valor) => valor !== null && valor !== undefined);

  if (contribuicoes.length === 0) {
    return null;
  }

  return arredondar(contribuicoes.reduce((acumulado, valor) => acumulado + valor, 0));
}

function descobrirContextoColaborador(metricas, colaboradorDb = null) {
  if (colaboradorDb) {
    const papel =
      normalizarPapel(colaboradorDb.papel) ||
      mapNomeGrupoParaPapel(metricas[0]?.nome_grupo) ||
      "Técnica";

    return {
      id_colaborador: colaboradorDb.id_colaborador,
      nome: colaboradorDb.nome ?? null,
      matricula: colaboradorDb.matricula ?? null,
      papel,
      subpapel: colaboradorDb.subpapel ?? null,
    };
  }

  const metricaComColaborador = metricas.find(
    (metrica) => metrica.papel_colaborador || metrica.subpapel_colaborador
  );

  if (metricaComColaborador) {
    return {
      id_colaborador: metricaComColaborador.colaborador?.id_colaborador ?? null,
      nome: metricaComColaborador.nome_colaborador ?? null,
      matricula: metricaComColaborador.colaborador?.matricula ?? null,
      papel:
        normalizarPapel(metricaComColaborador.papel_colaborador) ||
        mapNomeGrupoParaPapel(metricaComColaborador.nome_grupo) ||
        "Técnica",
      subpapel: metricaComColaborador.subpapel_colaborador ?? null,
    };
  }

  return {
    id_colaborador: null,
    nome: null,
    matricula: null,
    papel: mapNomeGrupoParaPapel(metricas[0]?.nome_grupo) || "Técnica",
    subpapel: null,
  };
}

function calcularIapsColaborador(metricas, colaboradorDb = null, pesosConfig = null) {
  const contexto = descobrirContextoColaborador(metricas, colaboradorDb);
  const medicoesElegiveis = filtrarMedicoesElegiveis(metricas, contexto, pesosConfig);

  if (medicoesElegiveis.length === 0) {
    return {
      iaps_calculado: null,
      scores_dimensoes: [],
      memoria_calculo: [],
      contexto,
      pesos_config: pesosConfig,
      medicoes_elegiveis: 0,
    };
  }

  const scoresDimensoesSelecionado = calcularScoresDimensoes(
    medicoesElegiveis,
    pesosConfig,
    "selecionado"
  );
  const scoresDimensoesBaseline = calcularScoresDimensoes(
    medicoesElegiveis,
    pesosConfig,
    "baseline"
  );

  const iapsSelecionado = calcularIapsFinal(scoresDimensoesSelecionado);
  const iapsBaseline = calcularIapsFinal(scoresDimensoesBaseline);
  const memoriaCalculo = montarMemoriaCalculo(
    medicoesElegiveis,
    pesosConfig,
    scoresDimensoesSelecionado,
    contexto
  );

  return {
    iaps_calculado: {
      valor: iapsSelecionado,
      iaps_baseline: iapsBaseline,
      id_colaborador: contexto.id_colaborador,
      nome_colaborador: contexto.nome,
      matricula: contexto.matricula,
      papel: contexto.papel,
      subpapel: contexto.subpapel,
      medicoes_consideradas: medicoesElegiveis.length,
      modo_nivel_estrito: MODO_ESTRITO_NIVEL,
      configuracao_pesos_id: pesosConfig?.id ?? null,
    },
    scores_dimensoes: scoresDimensoesSelecionado.map((item, index) => ({
      ...item,
      baseline: {
        nota_individual: scoresDimensoesBaseline[index]?.nota_individual ?? null,
        nota_equipe: scoresDimensoesBaseline[index]?.nota_equipe ?? null,
        score_dimensao: scoresDimensoesBaseline[index]?.score_dimensao ?? null,
        contribuicao: scoresDimensoesBaseline[index]?.contribuicao ?? null,
      },
    })),
    memoria_calculo: memoriaCalculo,
    contexto,
    pesos_config: pesosConfig,
    medicoes_elegiveis: medicoesElegiveis.length,
  };
}

module.exports = {
  MODO_ESTRITO_NIVEL,
  ORDEM_DIMENSOES,
  arredondar,
  extrairScorePercentual,
  normalizarNivelAvaliacao,
  deduplicarMedicoesPorIndicador,
  filtrarMedicoesElegiveis,
  combinarNotasPorNivel,
  montarMemoriaCalculo,
  calcularScoresDimensoes,
  calcularIapsFinal,
  descobrirContextoColaborador,
  calcularIapsColaborador,
};
