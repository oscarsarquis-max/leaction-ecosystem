/** Rótulos humanos do Mapa de Evolução — nunca exibir enums crus. */

export const EVOLUTION_CATEGORY_LABEL: Record<string, string> = {
  direction_governance: "Direção e governança",
  planning_risks: "Planejamento e riscos",
  people_resources: "Pessoas e recursos",
  operations_customers: "Operação e clientes",
  measurement_decisions: "Indicadores e decisões",
  correction_improvement: "Correção e melhoria",
};

export const EVOLUTION_PRIORITY_LABEL: Record<string, string> = {
  now: "Agora",
  next_cycle: "Próximo ciclo",
  future: "Evolução futura",
  investigate: "Aprofundar",
};

export const EVOLUTION_CONFIDENCE_LABEL: Record<string, string> = {
  high: "Fundamentação forte",
  medium: "Fundamentação moderada",
  low: "Precisa de mais informações",
};

export const EVOLUTION_STATUS_LABEL: Record<string, string> = {
  proposed: "Sugerida",
  accepted: "Aceita",
  dismissed: "Descartada",
  converted_to_action: "Convertida em ação",
  superseded: "Substituída por nova análise",
};

export const EVOLUTION_IMPACT_LABEL: Record<string, string> = {
  high: "Alto",
  medium: "Médio",
  low: "Baixo",
};

export const EVOLUTION_EFFORT_LABEL: Record<string, string> = {
  high: "Alto",
  medium: "Médio",
  low: "Baixo",
};

export const EVOLUTION_MODE_LABEL: Record<string, string> = {
  preliminary: "Leitura preliminar (após preparação)",
  analysis_ready: "Leitura com análise (evidências e resultados)",
};

export const EVOLUTION_CATEGORY_ORDER = [
  "direction_governance",
  "planning_risks",
  "people_resources",
  "operations_customers",
  "measurement_decisions",
  "correction_improvement",
] as const;

export function labelEvolutionCategory(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_CATEGORY_LABEL[v] ?? v;
}

export function labelEvolutionPriority(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_PRIORITY_LABEL[v] ?? v;
}

export function labelEvolutionConfidence(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_CONFIDENCE_LABEL[v] ?? v;
}

export function labelEvolutionStatus(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_STATUS_LABEL[v] ?? v;
}

export function labelEvolutionImpact(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_IMPACT_LABEL[v] ?? v;
}

export function labelEvolutionEffort(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_EFFORT_LABEL[v] ?? v;
}

export function labelEvolutionMode(v: string | null | undefined): string {
  if (!v) return "—";
  return EVOLUTION_MODE_LABEL[v] ?? v;
}
