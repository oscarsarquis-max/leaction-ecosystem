/** Estágios e rótulos do módulo Transformação Digital (PanelDX). */

export const TD_STAGE = {
  BACKLOG: 'Backlog',
  KAIZEN_ENTRADA: 'Kaizen_Entrada',
  PLANEJADA: 'Planejada',
  EXECUCAO: 'Execucao',
  CONCLUIDA: 'Concluida',
};

export const TD_ORIGIN = {
  BASELINE: 'baseline',
  KAIZEN_EMERGENT: 'kaizen_emergent',
};

/** Colunas do Kanban de Implementação (ordem de fluxo). */
export const TD_KANBAN_COLUMNS = [
  {
    id: TD_STAGE.KAIZEN_ENTRADA,
    label: 'Entradas Kaizen',
    hint: 'Emergentes do Gemba',
  },
  {
    id: TD_STAGE.PLANEJADA,
    label: 'Planejadas',
    hint: 'Baseline do Plano Diretor',
  },
  {
    id: TD_STAGE.EXECUCAO,
    label: 'Em Execução',
    hint: 'Em andamento',
  },
  {
    id: TD_STAGE.CONCLUIDA,
    label: 'Concluídas',
    hint: 'Encerradas',
  },
];

export function emptyTdKanbanBoard() {
  return Object.fromEntries(TD_KANBAN_COLUMNS.map((col) => [col.id, []]));
}

/**
 * Extrai gaps priorizados do survey_snapshot do plano.
 * Aceita formatos flexíveis para integração futura com IA/PanelDX.
 */
export function extractTopGaps(snapshot, limit = 5) {
  if (!snapshot || typeof snapshot !== 'object') return [];

  const fromArray = (arr) =>
    (arr || [])
      .map((item) => {
        if (typeof item === 'string') return { domain: item, gap: null, score: null };
        const domain =
          item.domain || item.paneldx_domain || item.name || item.label || 'Domínio';
        const gap =
          item.gap ??
          item.gap_score ??
          item.pdom_gap ??
          (typeof item.score === 'number' && typeof item.target === 'number'
            ? item.target - item.score
            : null);
        const score = item.score ?? item.present ?? item.pdom_pres ?? null;
        return {
          domain: String(domain),
          gap: gap == null ? null : Number(gap),
          score: score == null ? null : Number(score),
        };
      })
      .filter((g) => g.domain);

  if (Array.isArray(snapshot.top_gaps)) return fromArray(snapshot.top_gaps).slice(0, limit);
  if (Array.isArray(snapshot.gaps)) return fromArray(snapshot.gaps).slice(0, limit);
  if (Array.isArray(snapshot.domains)) {
    return fromArray(snapshot.domains)
      .sort((a, b) => (b.gap ?? 0) - (a.gap ?? 0))
      .slice(0, limit);
  }

  // Objeto { Processo: 2.1, Tecnologia: 1.4, ... }
  if (snapshot.pdom_gap && typeof snapshot.pdom_gap === 'object') {
    return Object.entries(snapshot.pdom_gap)
      .map(([domain, gap]) => ({
        domain,
        gap: Number(gap),
        score: snapshot.pdom_pres?.[domain] ?? null,
      }))
      .sort((a, b) => (b.gap ?? 0) - (a.gap ?? 0))
      .slice(0, limit);
  }

  return [];
}

export function groupSprintsByDomain(sprints) {
  const groups = new Map();
  for (const sprint of sprints || []) {
    const key = sprint.paneldx_domain || 'Outros';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(sprint);
  }
  return Array.from(groups.entries()).map(([domain, items]) => ({ domain, sprints: items }));
}

export function isEmergentSprint(sprint) {
  return (
    sprint?.origin_type === TD_ORIGIN.KAIZEN_EMERGENT ||
    sprint?.kanban_stage === TD_STAGE.KAIZEN_ENTRADA ||
    Boolean(sprint?.is_emergent)
  );
}
