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

/** Domínios oficiais do plano TD (taxonomia organizacional Chamelleon). */
export const TD_OFFICIAL_DOMAINS = [
  'Estratégia',
  'Cultura',
  'Processos',
  'Tecnologia',
  'Dados',
  'Clientes',
];

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
export function backlogFromSnapshot(snapshot) {
  const items = snapshot?.backlog_geral_relatorio;
  if (!Array.isArray(items) || items.length === 0) return [];
  return items.map((item, idx) => ({
    id: item.id || `snapshot-backlog-${idx}`,
    title: item.title || item.name_bloc || 'Sprint',
    kanban_stage: TD_STAGE.BACKLOG,
    paneldx_domain: item.domain_name,
    goals_payload: {
      dimension_name: item.dimension_name,
      domain_name: item.domain_name,
      name_bloc: item.name_bloc,
      name_derv: item.name_derv,
      gap_fp: item.gap_fp,
    },
    gap_fp: item.gap_fp,
    origin_type: 'baseline',
    _snapshotOnly: true,
  }));
}

export function resolvePlanBacklog(planSprints, backlogRes, snapshot) {
  const fromPlan = (planSprints || []).filter((s) => s.kanban_stage === TD_STAGE.BACKLOG);
  if (fromPlan.length > 0) return fromPlan;
  if (backlogRes?.sprints?.length) return backlogRes.sprints;
  return backlogFromSnapshot(snapshot);
}

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

export function getSprintBlockMeta(sprint) {
  const goals = sprint?.goals_payload || {};
  const linkage = sprint?.block_linkage || {};
  return {
    dimensionName: goals.dimension_name || linkage.dimension_name,
    domainName: goals.domain_name || linkage.domain_name,
    dimensionNum: goals.dimension_num ?? linkage.dimension_num,
    blockName: goals.name_bloc || linkage.name_bloc,
    deliverableName: goals.name_derv || linkage.name_derv,
    gapFp: sprint?.gap_fp ?? goals.gap_fp ?? null,
    legacyIdBloc: goals.legacy_id_bloc ?? linkage.legacy_id_bloc,
  };
}

export function formatSprintBlockLabel(sprint) {
  const meta = getSprintBlockMeta(sprint);
  if (!meta.blockName && !meta.dimensionName) return null;
  const dim = meta.dimensionNum != null ? `[DIM ${meta.dimensionNum}] ` : '';
  const pair =
    meta.dimensionName && meta.domainName
      ? `${meta.dimensionName} × ${meta.domainName}`
      : meta.domainName || meta.dimensionName || '';
  return { dimBlock: `${dim}${meta.blockName || 'Bloco'}`.trim(), pair, meta };
}

export function groupSprintsByDimensionDomain(sprints) {
  const groups = new Map();
  for (const sprint of sprints || []) {
    const meta = getSprintBlockMeta(sprint);
    const key = `${meta.dimensionName || '—'}|${meta.domainName || sprint.paneldx_domain || 'Outros'}`;
    if (!groups.has(key)) {
      groups.set(key, {
        dimensionName: meta.dimensionName,
        domainName: meta.domainName || sprint.paneldx_domain,
        sprints: [],
      });
    }
    groups.get(key).sprints.push(sprint);
  }
  return Array.from(groups.values());
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
