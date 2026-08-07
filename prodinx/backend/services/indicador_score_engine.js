const { create, all } = require("mathjs");

const math = create(all, {});

const PAYLOAD_META_KEYS = new Set([
  "metrica",
  "nome_metrica",
  "nome",
  "periodo",
  "itens",
  "bugs_detalhes",
  "timestamp",
  "origem",
  "cod_indicador",
  "nome_indicador",
  "nome_grupo",
  "dimensao",
  "nivel_avaliacao",
  "formula",
  "duvidas_abertas",
  "campos_custom_esperados",
  "sprint_breakdown",
  "tipos_analisados",
  "categorias_entregue",
  "categorias_ativo",
  "_conteudo_bruto",
  "_valor_parseado",
  "colaborador",
  "matricula",
  "colaborador_matricula",
  "resumo",
  "efficiency_score",
  "efficiency_percentage",
]);

const RESUMO_EXCLUDED_KEYS = new Set([
  "score",
  "score_percentual",
  "score_medio",
  "score_medio_geral",
  "baseline_score",
  "baseline_score_percentual",
]);

function isValorNumerico(valor) {
  return (
    valor !== null &&
    valor !== undefined &&
    valor !== "" &&
    !Number.isNaN(Number(valor))
  );
}

function registrarAliasAbreviado(variaveis, chave, valorNumerico) {
  const match = chave.match(/^([A-Za-z][A-Za-z0-9]*?)_/);
  if (match && variaveis[match[1]] === undefined) {
    variaveis[match[1]] = valorNumerico;
  }
}

function extrairVariaveisPayload(payload) {
  const variaveis = {};

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return variaveis;
  }

  const resumo = payload.resumo;
  if (resumo && typeof resumo === "object" && !Array.isArray(resumo)) {
    Object.entries(resumo).forEach(([chave, valor]) => {
      if (RESUMO_EXCLUDED_KEYS.has(chave) || !isValorNumerico(valor)) {
        return;
      }

      const numerico = Number(valor);
      variaveis[chave] = numerico;
      registrarAliasAbreviado(variaveis, chave, numerico);
    });
  }

  Object.entries(payload).forEach(([chave, valor]) => {
    if (PAYLOAD_META_KEYS.has(chave) || !isValorNumerico(valor)) {
      return;
    }

    variaveis[chave] = Number(valor);
    registrarAliasAbreviado(variaveis, chave, Number(valor));
  });

  return variaveis;
}

function mesclarEscopoFormula(variaveisPayload, parametrosConfiguraveis) {
  const parametros =
    parametrosConfiguraveis &&
    typeof parametrosConfiguraveis === "object" &&
    !Array.isArray(parametrosConfiguraveis)
      ? parametrosConfiguraveis
      : {};

  const escopo = { ...variaveisPayload };

  Object.entries(parametros).forEach(([chave, valor]) => {
    if (isValorNumerico(valor)) {
      escopo[chave] = Number(valor);
    }
  });

  return escopo;
}

function normalizarScorePercentual(resultado) {
  if (resultado === null || resultado === undefined || Number.isNaN(Number(resultado))) {
    return null;
  }

  const numerico = Number(resultado);

  if (!Number.isFinite(numerico)) {
    return null;
  }

  if (numerico >= 0 && numerico <= 1) {
    return Number((numerico * 100).toFixed(4));
  }

  return Number(numerico.toFixed(4));
}

function aplicarAliasesIndicador(variaveis, codIndicador) {
  const cod = String(codIndicador || "").toUpperCase();
  const resultado = { ...variaveis };

  if (cod === "A010") {
    if (resultado.btes === undefined && resultado.bugs_detectados_teste !== undefined) {
      resultado.btes = Number(resultado.bugs_detectados_teste);
    }

    if (resultado.bprod === undefined && resultado.bugs_em_producao !== undefined) {
      resultado.bprod = Number(resultado.bugs_em_producao);
    }

    if (resultado.bprod === undefined && resultado.bugs_producao !== undefined) {
      resultado.bprod = Number(resultado.bugs_producao);
    }

    if (
      resultado.bprod === undefined &&
      resultado.total_bugs !== undefined &&
      resultado.btes !== undefined
    ) {
      resultado.bprod = Math.max(0, Number(resultado.total_bugs) - Number(resultado.btes));
    }
  }

  return resultado;
}

function extrairScoreArmazenado(metrica) {
  const resumo = metrica.resumo || {};
  const payload =
    metrica.payload && typeof metrica.payload === "object" && !Array.isArray(metrica.payload)
      ? metrica.payload
      : {};

  const raw =
    resumo.score_percentual ??
    resumo.score ??
    resumo.score_medio ??
    resumo.score_medio_geral ??
    payload.efficiency_score ??
    payload.efficiency_percentage;

  if (raw === null || raw === undefined || Number.isNaN(Number(raw))) {
    return null;
  }

  const numerico = Number(raw);
  if (numerico <= 1 && numerico >= 0) {
    return numerico * 100;
  }

  return numerico;
}

function montarExpressaoSubstituida(formula, escopo) {
  if (!formula) {
    return null;
  }

  let expressao = String(formula);
  const chaves = Object.keys(escopo || {}).sort((a, b) => b.length - a.length);

  for (const chave of chaves) {
    const valor = escopo[chave];
    if (!isValorNumerico(valor)) {
      continue;
    }
    const re = new RegExp(`\\b${chave.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g");
    expressao = expressao.replace(re, String(valor));
  }

  return expressao;
}

function avaliarFormulaNormalizada(formulaNormalizada, escopo, contextoLog = {}) {
  const formula = String(formulaNormalizada || "").trim();

  if (!formula) {
    return { score: null, resultado_bruto: null, escopo: escopo || {}, erro: null };
  }

  try {
    const resultadoBruto = math.evaluate(formula, escopo);
    const score = normalizarScorePercentual(resultadoBruto);

    if (score === null) {
      return {
        score: null,
        resultado_bruto: resultadoBruto ?? null,
        escopo,
        erro: "resultado_invalido",
      };
    }

    return { score, resultado_bruto: Number(resultadoBruto), escopo, erro: null };
  } catch (error) {
    console.warn(
      "[indicador_score_engine] Falha ao avaliar fórmula:",
      JSON.stringify({
        cod_indicador: contextoLog.cod_indicador ?? null,
        formula,
        mensagem: error.message,
        variaveis: Object.keys(escopo || {}),
      })
    );

    // Divisão por zero / variável ausente → score nulo (não quebra o IAPS)
    return {
      score: null,
      resultado_bruto: null,
      escopo,
      erro: error.message,
    };
  }
}

function montarEscopoAvaliacao(metrica) {
  const payload = metrica.payload ?? null;
  const parametrosConfiguraveis =
    metrica.parametros_configuraveis ??
    metrica.indicador?.parametros_configuraveis ??
    null;
  const codIndicador = metrica.cod_indicador ?? metrica.indicador?.cod_indicador ?? null;

  const variaveisPayload = extrairVariaveisPayload(payload);
  const variaveisComAliases = aplicarAliasesIndicador(variaveisPayload, codIndicador);
  const escopo = mesclarEscopoFormula(variaveisComAliases, parametrosConfiguraveis);

  return { codIndicador, escopo, payload };
}

/**
 * Avalia fórmula mathjs sobre o payload limpo.
 * Retorna detalhe completo para memória de cálculo / auditoria.
 */
function calcularScoreIndicadorDetalhado(metrica, campoScore = "selecionado") {
  if (campoScore === "baseline") {
    const baseline =
      metrica.baseline_score !== null && metrica.baseline_score !== undefined
        ? Number(metrica.baseline_score)
        : null;
    const score =
      baseline !== null && !Number.isNaN(baseline) ? baseline : null;

    return {
      score,
      score_percentual: score,
      formula_normalizada: null,
      variaveis: {},
      expressao_substituida: null,
      resultado_bruto: score,
      origem: "baseline",
      erro: score === null ? "baseline_ausente" : null,
    };
  }

  const formulaNormalizada =
    metrica.formula_normalizada ??
    metrica.indicador?.formula_normalizada ??
    null;

  if (!formulaNormalizada || !String(formulaNormalizada).trim()) {
    const armazenado = extrairScoreArmazenado(metrica);
    return {
      score: armazenado,
      score_percentual: armazenado,
      formula_normalizada: null,
      variaveis: extrairVariaveisPayload(metrica.payload),
      expressao_substituida: null,
      resultado_bruto: armazenado,
      origem: "armazenado",
      erro: armazenado === null ? "sem_formula_nem_score" : null,
    };
  }

  const { codIndicador, escopo } = montarEscopoAvaliacao(metrica);
  const avaliacao = avaliarFormulaNormalizada(formulaNormalizada, escopo, {
    cod_indicador: codIndicador,
  });

  return {
    score: avaliacao.score,
    score_percentual: avaliacao.score,
    formula_normalizada: String(formulaNormalizada).trim(),
    variaveis: escopo,
    expressao_substituida: montarExpressaoSubstituida(formulaNormalizada, escopo),
    resultado_bruto: avaliacao.resultado_bruto,
    origem: "formula_normalizada",
    erro: avaliacao.erro,
  };
}

function calcularScoreIndicador(metrica, campoScore = "selecionado") {
  return calcularScoreIndicadorDetalhado(metrica, campoScore).score;
}

module.exports = {
  PAYLOAD_META_KEYS,
  RESUMO_EXCLUDED_KEYS,
  aplicarAliasesIndicador,
  extrairVariaveisPayload,
  mesclarEscopoFormula,
  normalizarScorePercentual,
  avaliarFormulaNormalizada,
  calcularScoreIndicadorDetalhado,
  calcularScoreIndicador,
  montarExpressaoSubstituida,
};
