import {
  mapNomeGrupoParaPapel,
  resolverPesosDimensoes,
  resolverPesosNiveis,
  indicadorAplicaAoSubpapel,
} from "../config/pesosIaps";

function toPercentScore(score) {
  if (score === null || score === undefined || Number.isNaN(Number(score))) {
    return null;
  }

  const numeric = Number(score);
  if (numeric <= 1 && numeric >= 0) {
    return numeric * 100;
  }

  return numeric;
}

function normalizeMetrica(metrica) {
  const resumo =
    metrica.resumo && typeof metrica.resumo === "object"
      ? metrica.resumo
      : metrica.payload?.resumo || {};

  return {
    ...metrica,
    nome_metrica:
      metrica.nome_metrica ||
      metrica.indicador?.nome_metrica ||
      metrica.payload?.metrica ||
      "Indicador",
    resumo,
    itens_total: metrica.itens_total ?? 0,
    periodo:
      metrica.periodo ||
      metrica.payload?.periodo ||
      (metrica.data_referencia
        ? { inicio: metrica.data_referencia, fim: metrica.data_referencia }
        : null),
    explicacao:
      metrica.explicacao ??
      metrica.indicador?.explicacao ??
      metrica.descricao?.explicacao ??
      null,
    importancia:
      metrica.importancia ??
      metrica.indicador?.importancia ??
      metrica.descricao?.importancia ??
      null,
    nome_colaborador: metrica.nome_colaborador ?? metrica.colaborador?.nome ?? null,
    funcao_colaborador:
      metrica.funcao_colaborador ?? metrica.colaborador?.funcao ?? null,
    codsetor: metrica.codsetor ?? metrica.colaborador?.codsetor ?? null,
    baseline_score: metrica.baseline_score ?? null,
    dimensao: metrica.dimensao ?? metrica.indicador?.dimensao ?? null,
    nivel_avaliacao:
      metrica.nivel_avaliacao ?? metrica.indicador?.nivel_avaliacao ?? null,
    nome_grupo: metrica.nome_grupo ?? metrica.indicador?.nome_grupo ?? null,
    subpapeis_aplicaveis:
      metrica.subpapeis_aplicaveis ??
      metrica.indicador?.subpapeis_aplicaveis ??
      null,
    papel_colaborador:
      metrica.papel_colaborador ??
      metrica.colaborador?.papel ??
      mapNomeGrupoParaPapel(metrica.nome_grupo ?? metrica.indicador?.nome_grupo),
    subpapel_colaborador:
      metrica.subpapel_colaborador ?? metrica.colaborador?.subpapel ?? null,
  };
}

function metricaElegivelIaps(normalized, contexto) {
  const dimensao = normalized.dimensao;
  const pesosDimensoes = resolverPesosDimensoes(contexto.papel, contexto.subpapel);
  if (!dimensao || pesosDimensoes[dimensao] === undefined) {
    return false;
  }

  return indicadorAplicaAoSubpapel(normalized.subpapeis_aplicaveis, contexto.subpapel);
}

export function filtrarMetricasComposicaoIaps(metricas, contexto) {
  if (!contexto?.papel) {
    return metricas;
  }

  return metricas.filter((metrica) => {
    const normalized = normalizeMetrica(metrica);
    const codIndicador =
      metrica.cod_indicador || metrica.indicador?.cod_indicador || normalized.cod_indicador;
    if (!codIndicador) {
      return false;
    }

    return metricaElegivelIaps(normalized, contexto);
  });
}

function resolverContextoIapsColaborador(metricas, iapsCalculado = null, filtros = {}) {
  if (iapsCalculado?.papel) {
    return {
      id_colaborador: iapsCalculado.id_colaborador ?? null,
      papel: iapsCalculado.papel,
      subpapel: iapsCalculado.subpapel ?? null,
    };
  }

  if (filtros.id_colaborador) {
    return resolverContextoIaps(metricas);
  }

  return null;
}

export function extractPainelIndicadores(
  metricas,
  filtros = { nivel: "colaborador", busca: "" },
  iapsCalculado = null
) {
  const porIndicador = new Map();
  const nivel = filtros.nivel || "colaborador";
  const busca = String(filtros.busca || "").trim();

  let metricasFonte = metricas;
  if (nivel === "colaborador") {
    const contexto = resolverContextoIapsColaborador(metricas, iapsCalculado, filtros);
    const escopoColaborador =
      iapsCalculado?.id_colaborador || filtros.id_colaborador || busca;
    if (contexto && escopoColaborador) {
      metricasFonte = filtrarMetricasComposicaoIaps(metricas, contexto);
    }
  }

  metricasFonte.forEach((metrica) => {
    const normalized = normalizeMetrica(metrica);
    const codIndicador =
      metrica.cod_indicador || metrica.indicador?.cod_indicador || normalized.cod_indicador;
    if (!codIndicador) {
      return;
    }

    const resumo = normalized.resumo || {};
    const scoreRaw =
      resumo.score_percentual ??
      resumo.score ??
      resumo.score_medio ??
      resumo.score_medio_geral;
    const score = toPercentScore(scoreRaw);
    if (score === null) {
      return;
    }

    const baselineRaw =
      normalized.baseline_score ?? resumo.baseline_score_percentual ?? null;
    const baseline = baselineRaw !== null ? Number(baselineRaw) : null;
    const dataReferencia =
      normalized.data_referencia ||
      normalized.periodo?.inicio ||
      normalized.periodo?.fim ||
      null;

    if (!porIndicador.has(codIndicador)) {
      porIndicador.set(codIndicador, {
        cod_indicador: codIndicador,
        nome_metrica: normalized.nome_metrica,
        dimensao: normalized.dimensao,
        explicacao: normalized.explicacao,
        importancia: normalized.importancia,
        medicoes: [],
      });
    }

    porIndicador.get(codIndicador).medicoes.push({
      id: metrica.id,
      data_referencia: dataReferencia ? String(dataReferencia) : null,
      score,
      baseline,
      nome_colaborador: normalized.nome_colaborador,
      funcao_colaborador: normalized.funcao_colaborador,
      codsetor: normalized.codsetor,
    });
  });

  return Array.from(porIndicador.values())
    .map((indicador) => {
      const medicoes = indicador.medicoes.sort((a, b) =>
        String(a.data_referencia || "").localeCompare(String(b.data_referencia || ""))
      );
      const ultima = medicoes[medicoes.length - 1] || null;

      const subtituloAlvo = buildSubtituloAlvo(nivel, busca, ultima);
      const subtituloBaseline = buildSubtituloBaseline(nivel, busca, ultima);

      const evolucao = medicoes.map((medicao) => ({
        data_referencia: medicao.data_referencia,
        score: medicao.score,
        baseline: medicao.baseline,
      }));

      return {
        ...indicador,
        score_selecionado: ultima?.score ?? null,
        score_baseline: ultima?.baseline ?? null,
        subtitulo_alvo: subtituloAlvo,
        subtitulo_baseline: subtituloBaseline,
        evolucao,
      };
    })
    .sort((a, b) => a.cod_indicador.localeCompare(b.cod_indicador));
}

function resolverContextoIaps(metricasArray) {
  const contagem = new Map();

  metricasArray.forEach((metrica) => {
    const normalized = normalizeMetrica(metrica);
    const papel = normalized.papel_colaborador || mapNomeGrupoParaPapel(normalized.nome_grupo);
    const subpapel = normalized.subpapel_colaborador;

    if (!papel) {
      return;
    }

    const chave = `${papel}::${subpapel || ""}`;
    contagem.set(chave, (contagem.get(chave) || 0) + 1);
  });

  if (contagem.size === 0) {
    return { papel: "Técnica", subpapel: null };
  }

  const [chaveDominante] = [...contagem.entries()].sort((a, b) => b[1] - a[1])[0];
  const [papel, subpapel] = chaveDominante.split("::");

  return {
    papel,
    subpapel: subpapel || null,
  };
}

function normalizarNivelAvaliacao(nivel) {
  return nivel === "Individual" ? "Individual" : "Equipe";
}

function extrairMedicoesIaps(metricasArray, contextoIaps = null) {
  const contexto = contextoIaps || resolverContextoIaps(metricasArray);
  const registros = [];

  metricasArray.forEach((metrica) => {
    const normalized = normalizeMetrica(metrica);
    const codIndicador =
      metrica.cod_indicador || metrica.indicador?.cod_indicador || normalized.cod_indicador;
    if (!codIndicador) {
      return;
    }

    const dimensao = normalized.dimensao;
    if (!metricaElegivelIaps(normalized, contexto)) {
      return;
    }

    const resumo = normalized.resumo || {};
    const scoreRaw =
      resumo.score_percentual ??
      resumo.score ??
      resumo.score_medio ??
      resumo.score_medio_geral;
    const scoreSelecionado = toPercentScore(scoreRaw);
    if (scoreSelecionado === null) {
      return;
    }

    const baselineRaw =
      normalized.baseline_score ?? resumo.baseline_score_percentual ?? null;
    const scoreBaseline = baselineRaw !== null ? Number(baselineRaw) : null;
    const dataReferencia =
      normalized.data_referencia ||
      normalized.periodo?.inicio ||
      normalized.periodo?.fim ||
      "";

    if (!dataReferencia) {
      return;
    }

    registros.push({
      cod_indicador: codIndicador,
      dimensao,
      nivel_avaliacao: normalizarNivelAvaliacao(normalized.nivel_avaliacao),
      score_selecionado: scoreSelecionado,
      score_baseline: scoreBaseline,
      data_referencia: String(dataReferencia),
      papel: contexto.papel,
      subpapel: contexto.subpapel,
    });
  });

  return registros;
}

function deduplicarMedicoesPorIndicador(registros) {
  const porIndicador = new Map();

  registros.forEach((item) => {
    const existente = porIndicador.get(item.cod_indicador);
    if (
      !existente ||
      String(item.data_referencia).localeCompare(String(existente.data_referencia)) > 0
    ) {
      porIndicador.set(item.cod_indicador, item);
    }
  });

  return Array.from(porIndicador.values());
}

function obterChavePeriodo(dataReferencia) {
  const parsed = new Date(dataReferencia);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  const mes = String(parsed.getMonth() + 1).padStart(2, "0");
  return `${parsed.getFullYear()}-${mes}`;
}

function formatarPeriodoMesAno(chavePeriodo) {
  const [ano, mes] = chavePeriodo.split("-");
  if (!ano || !mes) {
    return chavePeriodo;
  }

  return `${mes}/${ano}`;
}

function extrairMetricasParaIaps(metricasArray, contextoIaps = null) {
  const contexto = contextoIaps || resolverContextoIaps(metricasArray);
  return deduplicarMedicoesPorIndicador(extrairMedicoesIaps(metricasArray, contexto));
}

function calcularScoreDimensoesPorNivel(metricasIaps, campoScore, nivel, contextoIaps) {
  const itensNivel = metricasIaps.filter((item) => item.nivel_avaliacao === nivel);
  if (itensNivel.length === 0) {
    return null;
  }

  const pesosDimensoes = resolverPesosDimensoes(contextoIaps.papel, contextoIaps.subpapel);
  const porDimensao = new Map();

  itensNivel.forEach((item) => {
    const valor = item[campoScore];
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
      return;
    }

    if (!porDimensao.has(item.dimensao)) {
      porDimensao.set(item.dimensao, []);
    }

    porDimensao.get(item.dimensao).push(Number(valor));
  });

  let total = 0;

  porDimensao.forEach((valores, dimensao) => {
    const peso = pesosDimensoes[dimensao];
    if (!peso || valores.length === 0) {
      return;
    }

    const media = valores.reduce((acumulado, valor) => acumulado + valor, 0) / valores.length;
    total += media * peso;
  });

  return total;
}

function calcularIapsPorCampo(metricasIaps, campoScore, contextoIaps) {
  const pesosNiveis = resolverPesosNiveis(contextoIaps.papel, contextoIaps.subpapel);
  const scoreIndividual = calcularScoreDimensoesPorNivel(
    metricasIaps,
    campoScore,
    "Individual",
    contextoIaps
  );
  const scoreEquipe = calcularScoreDimensoesPorNivel(
    metricasIaps,
    campoScore,
    "Equipe",
    contextoIaps
  );

  let total = 0;
  let pesoAplicado = 0;

  if (scoreIndividual !== null && !Number.isNaN(scoreIndividual)) {
    total += scoreIndividual * pesosNiveis.Individual;
    pesoAplicado += pesosNiveis.Individual;
  }

  if (scoreEquipe !== null && !Number.isNaN(scoreEquipe)) {
    total += scoreEquipe * pesosNiveis.Equipe;
    pesoAplicado += pesosNiveis.Equipe;
  }

  if (pesoAplicado === 0) {
    return null;
  }

  return total / pesoAplicado;
}

export function calcularIAPS(metricasArray) {
  const contextoIaps = resolverContextoIaps(metricasArray);
  const metricasIaps = extrairMetricasParaIaps(metricasArray, contextoIaps);

  if (metricasIaps.length === 0) {
    return {
      iapsSelecionado: null,
      iapsReferencial: null,
      contexto: contextoIaps,
    };
  }

  const possuiBaseline = metricasIaps.some(
    (item) => item.score_baseline !== null && item.score_baseline !== undefined
  );

  return {
    iapsSelecionado: calcularIapsPorCampo(metricasIaps, "score_selecionado", contextoIaps),
    iapsReferencial: possuiBaseline
      ? calcularIapsPorCampo(metricasIaps, "score_baseline", contextoIaps)
      : null,
    contexto: contextoIaps,
  };
}

export function calcularHistoricoIAPS(metricasArray) {
  const contextoIaps = resolverContextoIaps(metricasArray);
  const registros = extrairMedicoesIaps(metricasArray, contextoIaps);
  const porPeriodo = new Map();

  registros.forEach((registro) => {
    const chavePeriodo = obterChavePeriodo(registro.data_referencia);
    if (!chavePeriodo) {
      return;
    }

    if (!porPeriodo.has(chavePeriodo)) {
      porPeriodo.set(chavePeriodo, []);
    }

    porPeriodo.get(chavePeriodo).push(registro);
  });

  return Array.from(porPeriodo.entries())
    .sort(([periodoA], [periodoB]) => periodoA.localeCompare(periodoB))
    .map(([chavePeriodo, medicoesPeriodo]) => {
      const metricasPeriodo = deduplicarMedicoesPorIndicador(medicoesPeriodo);
      const possuiBaseline = metricasPeriodo.some(
        (item) => item.score_baseline !== null && item.score_baseline !== undefined
      );

      return {
        periodo: formatarPeriodoMesAno(chavePeriodo),
        iapsSelecionado: calcularIapsPorCampo(metricasPeriodo, "score_selecionado", contextoIaps),
        iapsBaseline: possuiBaseline
          ? calcularIapsPorCampo(metricasPeriodo, "score_baseline", contextoIaps)
          : null,
      };
    })
    .filter(
      (item) => item.iapsSelecionado !== null && !Number.isNaN(item.iapsSelecionado)
    );
}

export function obterTitulosIaps(filtros = { nivel: "colaborador", busca: "" }) {
  const nivel = filtros.nivel || "colaborador";
  const busca = String(filtros.busca || "").trim();

  if (nivel === "colaborador") {
    return {
      tituloSelecionado: busca ? "IAPS do Escopo Selecionado" : "IAPS do Colaborador",
      tituloReferencial: "IAPS Referencial (Média do Subpapel)",
    };
  }

  if (nivel === "papel") {
    return {
      tituloSelecionado: "IAPS do Papel",
      tituloReferencial: "IAPS Referencial (Média do Setor)",
    };
  }

  if (nivel === "subpapel" || nivel === "funcao") {
    return {
      tituloSelecionado: "IAPS do Subpapel",
      tituloReferencial: "IAPS Referencial (Média do Papel)",
    };
  }

  if (nivel === "setor") {
    if (!busca) {
      return {
        tituloSelecionado: "IAPS da Organização",
        tituloReferencial: "Referencial Institucional",
      };
    }
    return {
      tituloSelecionado: "IAPS do Setor",
      tituloReferencial: "IAPS Referencial (Média Total)",
    };
  }

  return {
    tituloSelecionado: "IAPS do Setor",
    tituloReferencial: "IAPS Referencial (Média Total)",
  };
}

function buildSubtituloAlvo(nivel, busca, ultima) {
  if (nivel === "colaborador") {
    if (ultima?.nome_colaborador) {
      return ultima.nome_colaborador;
    }
    if (busca) {
      return `Busca: ${busca}`;
    }
    return "Todos os colaboradores";
  }

  if (nivel === "papel") {
    if (busca) {
      return `Papel: ${busca}`;
    }
    if (ultima?.papel_colaborador) {
      return `Papel: ${ultima.papel_colaborador}`;
    }
    return "Todos os papéis";
  }

  if (nivel === "subpapel" || nivel === "funcao") {
    if (busca) {
      return `Subpapel: ${busca}`;
    }
    if (ultima?.subpapel_colaborador) {
      return `Subpapel: ${ultima.subpapel_colaborador}`;
    }
    return "Todos os subpapéis";
  }

  if (busca) {
    return `Setor: ${busca}`;
  }
  if (ultima?.codsetor) {
    return `Setor: ${ultima.codsetor}`;
  }
  return "Todos os setores";
}

function buildSubtituloBaseline(nivel, busca, ultima) {
  if (nivel === "colaborador") {
    const subpapel = ultima?.subpapel_colaborador || busca || "—";
    return `Média do Subpapel: ${subpapel}`;
  }

  if (nivel === "papel") {
    const setor = ultima?.codsetor || busca || "—";
    return `Média do Setor: ${setor}`;
  }

  if (nivel === "subpapel" || nivel === "funcao") {
    const papel = ultima?.papel_colaborador || busca || "—";
    return `Média do Papel: ${papel}`;
  }

  return "Média da Unidade";
}

export function extractTableRows(metricas) {
  const rows = [];

  metricas.forEach((metrica) => {
    const normalized = normalizeMetrica(metrica);
    const itens = Array.isArray(normalized.itens) ? normalized.itens : [];
    itens.forEach((item, index) => {
      rows.push({
        id: `${normalized.id}-${item.id ?? index}`,
        metrica: normalized.nome_metrica,
        data_importacao: normalized.data_importacao,
        ...item,
      });
    });
  });

  return rows;
}

export function getTableColumns(rows) {
  if (rows.length === 0) return [];

  const preferred = ["metrica", "titulo", "nome", "descricao", "volume", "volumetria", "quantidade", "score", "pontuacao", "nota", "data", "data_importacao", "data_referencia_inicio", "data_referencia_fim"];
  const keys = new Set();

  rows.forEach((row) => {
    Object.keys(row).forEach((key) => {
      if (key !== "id") keys.add(key);
    });
  });

  const ordered = preferred.filter((key) => keys.has(key));
  const remaining = [...keys].filter((key) => !ordered.includes(key));

  return [...ordered, ...remaining];
}
