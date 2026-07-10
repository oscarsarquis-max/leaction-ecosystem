/**
 * Hints exibidos durante a Gênese IA — relatório de maturidade + diretrizes PanelDX.
 */

const EXECUTIVE_DIRETRIZES = [
  'Seletividade estratégica: focar nos gaps com maior impacto operacional.',
  'Cada sprint deve citar gap real, Bússola Presente × Futuro e contexto da organização.',
  'Roadmap estratégico: no máximo 10 blocos críticos nos domínios oficiais PanelDX.',
  'Plano tático: até 3 sprints na Onda 1 ligadas ao problema declarado.',
  'Relatório de inteligência cobrindo domínios com densidade sectorial.',
  'Personalização: correlacionar gaps com mercado, clientes e clima organizacional.',
];

function topGapHints(result, limit = 3) {
  const gapScores = result?.scores_detalhe_gap?.pdom_scores || {};
  const labels = result?.domain_labels || {};
  return Object.entries(gapScores)
    .map(([key, value]) => ({
      key,
      gap: Number(value),
      label: labels[key] || key,
    }))
    .filter((item) => !Number.isNaN(item.gap))
    .sort((a, b) => b.gap - a.gap)
    .slice(0, limit)
    .map(
      (item) =>
        `Gap prioritário em ${item.label}: ${item.gap.toFixed(2)} pontos entre presente e futuro desejado.`,
    );
}

function gapListHints(gaps = [], limit = 3) {
  return gaps
    .filter((item) => item?.domain)
    .slice(0, limit)
    .map((item) => {
      if (item.gap != null && !Number.isNaN(Number(item.gap))) {
        return `Gap prioritário em ${item.domain}: ${Number(item.gap).toFixed(2)} pontos entre presente e futuro desejado.`;
      }
      return `Domínio prioritário: ${item.domain}.`;
    });
}

function contextHints(contextValues = {}) {
  const items = [];
  if (contextValues.dados_mercado?.trim()) {
    items.push('Mercado e concorrência informados — o Consultor usa isso na priorização.');
  }
  if (contextValues.dados_clientes?.trim()) {
    items.push('Perfil de clientes carregado para personalizar o plano tático.');
  }
  if (contextValues.clima_organizacional?.trim()) {
    items.push('Clima organizacional considerado na seleção de sprints e ritmo de mudança.');
  }
  return items;
}

export function buildGenesisHints({ result, contextValues, gaps } = {}) {
  const hints = [];

  if (result?.nivel_maturidade) {
    const score =
      result.score_global != null
        ? Number(result.score_global).toFixed(2)
        : result.score_global;
    hints.push(`Nível de maturidade: ${result.nivel_maturidade}${score ? ` (score global ${score})` : ''}.`);
  }

  if (result?.maturity_level_description) {
    const text = String(result.maturity_level_description).trim();
    hints.push(text.length > 180 ? `${text.slice(0, 177)}…` : text);
  }

  if (result?.score_geral_gap != null && !Number.isNaN(Number(result.score_geral_gap))) {
    hints.push(
      `Bússola geral: gap de ${Number(result.score_geral_gap).toFixed(2)} — base para priorizar domínios.`,
    );
  }

  hints.push(...topGapHints(result));
  hints.push(...gapListHints(gaps));
  hints.push(...contextHints(contextValues));
  hints.push(...EXECUTIVE_DIRETRIZES);

  return hints.filter(Boolean);
}

export const GENESIS_STATUS_LABELS = {
  PENDENTE: 'Na fila — preparando o Consultor LeAction…',
  PROCESSANDO: 'Consultor LeAction Master analisando gaps, Bússola e contexto…',
  CONCLUIDO: 'Plano estratégico gerado com sucesso!',
};
