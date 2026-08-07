/**
 * Contexto seguro do Assistente QMind — só o necessário para orientar.
 * Sem tokens, credenciais, URLs assinadas ou conteúdo de documentos.
 */

export type AssistantPageId =
  | "org_home"
  | "assessment_map"
  | "wizard"
  | "audit_plan"
  | "field_central"
  | "evolution_map"
  | "generic";

export type AssistantQuickActionId =
  | "explain_stage"
  | "what_now"
  | "what_pending"
  | "why_important"
  | "go_next";

export type AssistantNextAction = {
  label: string;
  hint: string;
  href?: string;
  /** Se true, só oferecer CTA de mutação quando can_mutate. */
  mutates?: boolean;
};

export type AssistantPendency = {
  key: string;
  problem: string;
  impact: string;
  actionLabel: string;
  href?: string;
};

export type AssistantWizardSnippet = {
  questionTheme: string;
  questionText: string;
  explanation: string;
  practiceExamples: string[];
  evidenceExamples: string[];
  whyNeeded: string;
};

export type AssistantPlanSnippet = {
  planStatus: string | null;
  planReady: boolean;
  assessmentPlanned: boolean;
  needsAmendment: boolean;
  readinessNext: string | null;
  freezeNote: string;
};

export type AssistantFieldSnippet = {
  currentActivityTitle: string | null;
  earlyEvidenceCount: number;
  pendingEvidenceCount: number;
  closingPrepShow: boolean;
};

export type AssistantEvolutionSnippet = {
  hasPackage: boolean;
  priorityCount: number;
  secondaryCount: number;
  needsReviewCount: number;
  topPriorityTitle: string | null;
  generationMode: string | null;
};

/** Snapshot registrado pela página ativa. */
export type AssistantContext = {
  organization_id: string | null;
  organization_name: string;
  assessment_id: string | null;
  assessment_label: string | null;
  route: string;
  page: AssistantPageId;
  phase_label: string | null;
  assessment_status: string | null;
  user_roles: string[];
  can_mutate: boolean;
  next_action: AssistantNextAction | null;
  pendencies: AssistantPendency[];
  blockers: string[];
  progress_summary: string | null;
  allowed_links: string[];
  stage_title: string;
  stage_explanation: string;
  wizard?: AssistantWizardSnippet | null;
  plan?: AssistantPlanSnippet | null;
  field?: AssistantFieldSnippet | null;
  evolution?: AssistantEvolutionSnippet | null;
};

export type AssistantReplyBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "link"; label: string; href: string }
  | { type: "note"; text: string };

export type AssistantReply = {
  title: string;
  blocks: AssistantReplyBlock[];
  /** Link permitido para “Leve-me ao próximo passo”. */
  navigateHref?: string;
};

export type AssistantEngine = {
  answer: (
    action: AssistantQuickActionId,
    ctx: AssistantContext,
  ) => AssistantReply;
};

export type AssistantSessionUi = {
  open: boolean;
  lastQuickAction: AssistantQuickActionId | null;
};
