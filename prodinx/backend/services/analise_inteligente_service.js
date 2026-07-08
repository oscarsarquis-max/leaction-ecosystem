const { invocarClaude, extrairJsonResposta, BEDROCK_MODEL_ID } = require("./bedrock_client");
const { getOrganizacaoNome } = require("../config/organizacao");

const SYSTEM_PROMPT = `Você é um consultor de gestão técnica da organização ${getOrganizacaoNome()}, especialista em métricas SPACE/IAPS.
Analise discrepâncias entre desempenho individual do colaborador e baseline de equipe.
Responda APENAS com JSON válido no formato:
{
  "recomendacoes": [
    {
      "titulo": "string curta",
      "tipo": "alerta" ou "oportunidade",
      "analise_cruzada": "parágrafo explicativo",
      "acao_sugerida": "ação concreta para 1-on-1"
    }
  ]
}
Gere de 2 a 5 recomendações priorizadas, em português do Brasil, tom executivo e acionável.`;

function normalizarPercentual(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return null;
  }

  const numero = Number(valor);
  return numero <= 1 ? Number((numero * 100).toFixed(1)) : Number(numero.toFixed(1));
}

function montarDiscrepancias(memoriaCalculo = []) {
  const itens = [];

  memoriaCalculo.forEach((linha) => {
    const ind = linha.indicador_individual;
    const eq = linha.indicador_equipe;

    if (ind?.score != null && eq?.score != null) {
      const gap = Number((ind.score - eq.score).toFixed(1));
      if (Math.abs(gap) >= 8) {
        itens.push({
          dimensao: linha.dimensao,
          cod_indicador: ind.cod_indicador,
          nome_indicador: ind.nome_indicador,
          score_individual: ind.score,
          score_equipe: eq.score,
          gap_percentual: gap,
        });
      }
      return;
    }

    if (ind?.score != null || eq?.score != null) {
      itens.push({
        dimensao: linha.dimensao,
        cod_indicador: ind?.cod_indicador || eq?.cod_indicador,
        nome_indicador: ind?.nome_indicador || eq?.nome_indicador,
        score_individual: ind?.score ?? null,
        score_equipe: eq?.score ?? null,
        gap_percentual:
          ind?.score != null && eq?.score != null
            ? Number((ind.score - eq.score).toFixed(1))
            : null,
      });
    }
  });

  return itens.sort(
    (a, b) => Math.abs(b.gap_percentual || 0) - Math.abs(a.gap_percentual || 0)
  );
}

function montarContextoAnalise({ colaborador, iapsCalculado, scoresDimensoes, memoriaCalculo }) {
  return {
    colaborador: {
      id_colaborador: colaborador.id_colaborador,
      nome: colaborador.nome,
      matricula: colaborador.matricula,
      papel: colaborador.papel,
      subpapel: colaborador.subpapel,
      codsetor: colaborador.codsetor,
    },
    iaps: {
      valor: normalizarPercentual(iapsCalculado?.valor),
      baseline: normalizarPercentual(iapsCalculado?.iaps_baseline),
    },
    dimensoes: (scoresDimensoes || []).map((item) => ({
      dimensao: item.dimensao,
      nota_individual: normalizarPercentual(item.nota_individual),
      nota_equipe: normalizarPercentual(item.nota_equipe),
      score_dimensao: normalizarPercentual(item.score_dimensao),
      baseline_dimensao: normalizarPercentual(item.baseline?.score_dimensao),
    })),
    discrepancias_indicadores: montarDiscrepancias(memoriaCalculo),
  };
}

function normalizarRecomendacoes(payload) {
  const lista = Array.isArray(payload?.recomendacoes) ? payload.recomendacoes : [];

  return lista
    .map((item, index) => ({
      id: index + 1,
      titulo: String(item.titulo || `Recomendação ${index + 1}`).trim(),
      tipo: item.tipo === "oportunidade" ? "oportunidade" : "alerta",
      analise_cruzada: String(item.analise_cruzada || "").trim(),
      acao_sugerida: String(item.acao_sugerida || "").trim(),
    }))
    .filter((item) => item.titulo && item.analise_cruzada);
}

function calcularHashContexto(contexto) {
  const crypto = require("crypto");
  return crypto.createHash("sha256").update(JSON.stringify(contexto)).digest("hex");
}

async function gerarAnaliseInteligente({
  colaborador,
  iapsCalculado,
  scoresDimensoes,
  memoriaCalculo,
}) {
  const contexto = montarContextoAnalise({
    colaborador,
    iapsCalculado,
    scoresDimensoes,
    memoriaCalculo,
  });

  const texto = await invocarClaude({
    system: SYSTEM_PROMPT,
    userContent: JSON.stringify(contexto, null, 2),
    maxTokens: 2500,
    temperature: 0.3,
  });

  const parsed = extrairJsonResposta(texto);
  const recomendacoes = normalizarRecomendacoes(parsed);

  if (recomendacoes.length === 0) {
    throw new Error("O modelo não retornou recomendações utilizáveis.");
  }

  return {
    colaborador: contexto.colaborador,
    iaps: contexto.iaps,
    recomendacoes,
    gerado_em: new Date().toISOString(),
    modelo: BEDROCK_MODEL_ID,
    provider: "aws-bedrock",
  };
}

module.exports = {
  gerarAnaliseInteligente,
  montarContextoAnalise,
  calcularHashContexto,
};
