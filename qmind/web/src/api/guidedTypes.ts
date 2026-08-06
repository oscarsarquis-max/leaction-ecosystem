export type GuidedStep =
  | "organization"
  | "qms_scope"
  | "products_services"
  | "sites"
  | "processes"
  | "stakeholders"
  | "route"
  | "review";

export type AnswerValue =
  | "yes"
  | "partial"
  | "no"
  | "unknown"
  | "not_applicable";

export type EvidenceMode =
  | "none"
  | "attach"
  | "link_existing"
  | "describe"
  | "provide_later";

export type GuidedAnswer = {
  question_id: string;
  question_version: string;
  answer_value: AnswerValue | null;
  description: string;
  na_justification: string;
  evidence_mode: EvidenceMode;
  evidence_ids: string[];
  evidence_note: string;
  provide_later: boolean;
  updated_at?: string | null;
};

export type GuidedContext = {
  organization_profile: {
    trade_name: string;
    summary: string;
    size_band: string;
  };
  qms_scope: {
    description: string;
    exclusions: string;
    exclusion_justification: string;
  };
  products_services: { name: string; notes: string }[];
  sites: { name: string; location: string; notes: string }[];
  processes: { name: string; owner: string; notes: string }[];
  stakeholders: { name: string; interest: string; notes: string }[];
};

export type GuidedSession = {
  id: string;
  assessment_id: string;
  organization_id: string;
  catalog_version: string;
  status: string;
  current_step: GuidedStep;
  current_question_id: string | null;
  context: GuidedContext;
  answers: GuidedAnswer[];
  answered_count: number;
  question_count: number;
  updated_at: string;
};

export type GuidedQuestion = {
  id: string;
  version: string;
  theme: string;
  clause_ref: string;
  question: string;
  explanation: string;
  practice_examples: string[];
  evidence_examples: string[];
  answer_type: string;
  required: boolean;
  show_when: null | Record<string, unknown>;
};

export type GuidedClauseGroup = {
  id: string;
  label: string;
  refs: string[];
};

export type GuidedCatalog = {
  catalog_version: string;
  title: string;
  standard_label: string;
  disclaimer: string;
  steps: GuidedStep[];
  clause_groups?: GuidedClauseGroup[];
  questions: GuidedQuestion[];
};

export type GuidedAnswerUpsert = {
  question_version: string;
  answer_value?: AnswerValue | null;
  description?: string;
  na_justification?: string;
  evidence_mode?: EvidenceMode;
  evidence_ids?: string[];
  evidence_note?: string;
  provide_later?: boolean;
};

export const GUIDED_STEPS: { id: GuidedStep; label: string; hint: string }[] = [
  {
    id: "organization",
    label: "Organização",
    hint: "Quem é a empresa e o que ela faz",
  },
  {
    id: "qms_scope",
    label: "Escopo do SGQ",
    hint: "O que entra e o que fica de fora do sistema de qualidade",
  },
  {
    id: "products_services",
    label: "Produtos e serviços",
    hint: "O que a empresa entrega ao cliente",
  },
  {
    id: "sites",
    label: "Unidades e locais",
    hint: "Onde as atividades acontecem",
  },
  {
    id: "processes",
    label: "Processos principais",
    hint: "Como o trabalho flui até a entrega",
  },
  {
    id: "stakeholders",
    label: "Partes interessadas",
    hint: "Quem influencia ou é influenciado pela qualidade",
  },
  {
    id: "route",
    label: "Roteiro orientado",
    hint: "Perguntas guiadas sobre contexto e liderança",
  },
  {
    id: "review",
    label: "Revisão",
    hint: "Resumo do que foi registrado",
  },
];

export const ANSWER_OPTIONS: { value: AnswerValue; label: string }[] = [
  { value: "yes", label: "Sim" },
  { value: "partial", label: "Parcialmente" },
  { value: "no", label: "Não" },
  { value: "unknown", label: "Não sei" },
  { value: "not_applicable", label: "Não aplicável" },
];

export function emptyGuidedContext(): GuidedContext {
  return {
    organization_profile: { trade_name: "", summary: "", size_band: "" },
    qms_scope: { description: "", exclusions: "", exclusion_justification: "" },
    products_services: [],
    sites: [],
    processes: [],
    stakeholders: [],
  };
}

export function normalizeContext(raw: unknown): GuidedContext {
  const base = emptyGuidedContext();
  if (!raw || typeof raw !== "object") return base;
  const c = raw as Partial<GuidedContext>;
  return {
    organization_profile: {
      ...base.organization_profile,
      ...(c.organization_profile ?? {}),
    },
    qms_scope: { ...base.qms_scope, ...(c.qms_scope ?? {}) },
    products_services: Array.isArray(c.products_services)
      ? c.products_services
      : [],
    sites: Array.isArray(c.sites) ? c.sites : [],
    processes: Array.isArray(c.processes) ? c.processes : [],
    stakeholders: Array.isArray(c.stakeholders) ? c.stakeholders : [],
  };
}
