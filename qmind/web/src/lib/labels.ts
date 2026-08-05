/**
 * Rótulos pt-BR para valores de domínio exibidos na UI.
 * Chaves = valores da API (não traduzir no backend).
 */

/** Mapa visual genérico — nunca exibir enum cru na tela. */
export const STATUS_MAP: Record<string, string> = {
  draft: "Rascunho",
  planned: "Planejada",
  in_progress: "Em andamento",
  analysis: "Em análise",
  actions: "Plano de ação",
  report: "Relatório",
  closed: "Concluído",
  cancelled: "Cancelada",
  STATUS_DRAFT: "Rascunho",
  STATUS_PLANNED: "Planejada",
  STATUS_IN_PROGRESS: "Em andamento",
  STATUS_ANALYSIS: "Em análise",
  STATUS_ACTIONS: "Plano de ação",
  STATUS_REPORT: "Relatório",
  STATUS_CLOSED: "Concluído",
  STATUS_CANCELLED: "Cancelada",
  in_review: "Em revisão",
  approved: "Aprovada",
  rejected: "Rejeitada",
  withdrawn: "Retirada",
  discarded: "Descartada",
  active: "Ativo",
  completed: "Concluído",
  done: "Concluído",
  submitted: "Enviado para revisão",
  published: "Publicado",
  queued: "Na fila",
  running: "Em andamento",
  succeeded: "Concluído",
  failed: "Falhou",
  quarantined: "Em quarentena",
  pending: "Pendente",
  upload_pending: "Em revisão de envio",
  archived: "Arquivado",
  superseded: "Substituído",
  open: "Aberta",
  implemented: "Implementada",
  validated: "Validada (eficácia pendente)",
  ineffective: "Ineficaz",
  ineffective_closed: "Ineficaz (fechada)",
};

const ASSESSMENT_STATUS: Record<string, string> = {
  draft: "Em preparação",
  planned: "Planejada",
  in_progress: "Em andamento",
  analysis: "Em análise",
  actions: "Plano de ação",
  report: "Relatório",
  closed: "Concluído",
  cancelled: "Cancelada",
};

const ASSESSMENT_TYPE: Record<string, string> = {
  diagnosis: "Diagnóstico inicial",
  internal_audit: "Avaliação interna",
  external_audit: "Avaliação externa",
  certification_prep: "Preparação para certificação",
  other: "Outro",
};

const FINDING_TYPE: Record<string, string> = {
  conformity: "conformidade",
  nonconformity: "não conformidade",
  opportunity: "oportunidade",
  observation: "observação",
};

const INTERVIEW_MODE: Record<string, string> = {
  onsite: "presencial",
  remote: "remota",
  hybrid: "híbrida",
};

const MATURITY_LEVEL: Record<string, string> = {
  "1": "1 — inicial",
  "2": "2 — definido",
  "3": "3 — gerenciado",
  "4": "4 — medido",
  "5": "5 — otimizando",
  initial: "inicial",
  defined: "definido",
  managed: "gerenciado",
  measured: "medido",
  optimizing: "otimizando",
};

const APPLICABILITY: Record<string, string> = {
  applicable: "aplicável",
  not_applicable: "não aplicável",
  insufficient_info: "informação insuficiente",
};

function lookup(map: Record<string, string>, value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  return map[value] ?? STATUS_MAP[value] ?? value.replaceAll("_", " ");
}

export function labelAssessmentStatus(value: string | null | undefined): string {
  return lookup(ASSESSMENT_STATUS, value);
}

export function labelAssessmentType(value: string | null | undefined): string {
  return lookup(ASSESSMENT_TYPE, value);
}

export function labelFindingType(value: string | null | undefined): string {
  return lookup(FINDING_TYPE, value);
}

export function labelWorkflowStatus(value: string | null | undefined): string {
  return lookup(STATUS_MAP, value);
}

export function labelInterviewMode(value: string | null | undefined): string {
  return lookup(INTERVIEW_MODE, value);
}

export function labelMaturityLevel(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  return lookup(MATURITY_LEVEL, String(value));
}

export function labelApplicability(value: string | null | undefined): string {
  return lookup(APPLICABILITY, value);
}

export const ASSESSMENT_TYPE_OPTIONS = [
  {
    value: "internal_audit",
    label: "Avaliação interna",
    description:
      "A própria organização verifica se o sistema de qualidade está funcionando no dia a dia.",
  },
  {
    value: "external_audit",
    label: "Avaliação externa",
    description:
      "Uma parte de fora (cliente ou organismo) avalia a organização — use para se preparar ou registrar esse ciclo.",
  },
  {
    value: "diagnosis",
    label: "Diagnóstico inicial",
    description:
      "Primeiro retrato do sistema de qualidade: onde estamos hoje, sem a formalidade de uma avaliação completa.",
  },
  {
    value: "certification_prep",
    label: "Preparação para certificação",
    description:
      "Organiza o percurso até uma certificação: lacunas, evidências e ações antes da avaliação oficial.",
  },
  {
    value: "other",
    label: "Outro",
    description: "Quando o trabalho não se encaixa nos tipos acima — ainda assim o QMind guia o percurso.",
  },
] as const;

export const FINDING_TYPE_OPTIONS = [
  { value: "conformity", label: "Conformidade" },
  { value: "nonconformity", label: "Não conformidade" },
  { value: "opportunity", label: "Oportunidade" },
  { value: "observation", label: "Observação" },
] as const;

export const INTERVIEW_MODE_OPTIONS = [
  { value: "onsite", label: "Presencial" },
  { value: "remote", label: "Remota" },
  { value: "hybrid", label: "Híbrida" },
] as const;
