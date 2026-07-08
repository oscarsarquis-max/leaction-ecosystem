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

function avaliarFormulaNormalizada(formulaNormalizada, escopo, contextoLog = {}) {
  const formula = String(formulaNormalizada || "").trim();

  if (!formula) {
    return { score: null, escopo: null, erro: null };
  }

  try {
    const resultado = math.evaluate(formula, escopo);
    const score = normalizarScorePercentual(resultado);

    if (score === null) {
      console.warn(
        "[indicador_score_engine] Resultado inválido para fórmula:",
        JSON.stringify({
          cod_indicador: contextoLog.cod_indicador ?? null,
          formula,
          resultado,
        })
      );
    }

    return { score, escopo, erro: null };
  } catch (error) {
    console.warn(
      "[indicador_score_engine] Falha ao avaliar fórmula:",
      JSON.stringify({
        cod_indicador: contextoLog.cod_indicador ?? null,
        formula,
        mensagem: error.message,
        variaveis: Object.keys(escopo),
      })
    );

    return { score: null, escopo, erro: error.message };
  }
}

function calcularScoreIndicador(metrica, campoScore = "selecionado") {
  if (campoScore === "baseline") {
    const baseline =
      metrica.baseline_score !== null && metrica.baseline_score !== undefined
        ? Number(metrica.baseline_score)
        : null;

    return baseline !== null && !Number.isNaN(baseline) ? baseline : null;
  }

  const formulaNormalizada =
    metrica.formula_normalizada ??
    metrica.indicador?.formula_normalizada ??
    null;

  if (!formulaNormalizada) {
    return extrairScoreArmazenado(metrica);
  }

  const payload = metrica.payload ?? null;
  const parametrosConfiguraveis =
    metrica.parametros_configuraveis ??
    metrica.indicador?.parametros_configuraveis ??
    null;

  const variaveisPayload = extrairVariaveisPayload(payload);
  const codIndicador = metrica.cod_indicador ?? metrica.indicador?.cod_indicador ?? null;
  const variaveisComAliases = aplicarAliasesIndicador(variaveisPayload, codIndicador);
  const escopo = mesclarEscopoFormula(variaveisComAliases, parametrosConfiguraveis);
  const { score } = avaliarFormulaNormalizada(formulaNormalizada, escopo, {
    cod_indicador: codIndicador,
  });

  if (score !== null) {
    return score;
  }

  return extrairScoreArmazenado(metrica);
}

module.exports = {
  PAYLOAD_META_KEYS,
  RESUMO_EXCLUDED_KEYS,
  aplicarAliasesIndicador,
  extrairVariaveisPayload,
  mesclarEscopoFormula,
  normalizarScorePercentual,
  avaliarFormulaNormalizada,
  calcularScoreIndicador,
};
