/**
 * Apresentação guiada autenticada — contexto em sessionStorage.
 * Sem mutações; limpar ao trocar organização ou sair.
 */

const TOUR_STEP_KEY = "qmind.guidedTour.step";
const TOUR_ACTIVE_KEY = "qmind.guidedTour.active";
const TOUR_ORG_KEY = "qmind.guidedTour.orgId";

export type GuidedTourStepId =
  | "home"
  | "agenda"
  | "wizard"
  | "audit_plan"
  | "field"
  | "evidence"
  | "analysis"
  | "evolution"
  | "actions"
  | "report"
  | "quality_control";

export type GuidedTourStep = {
  id: GuidedTourStepId;
  title: string;
  demonstrate: string;
  message: string;
  benefit: string;
  /** Constrói href a partir da avaliação em foco; null se precisa de avaliação. */
  resolveHref: (assessmentId: string | null) => string | null;
  needsAssessment: boolean;
};

export const GUIDED_TOUR_STEPS: GuidedTourStep[] = [
  {
    id: "home",
    title: "Home e Mapa do Percurso",
    demonstrate:
      "Visão da organização, avaliação em foco e o mapa do que já foi concluído.",
    message: "Comece pelo mapa: ele mostra a fase atual e a próxima ação.",
    benefit: "Gestores e consultores permanecem orientados sem telas concorrentes.",
    resolveHref: () => "/assessments",
    needsAssessment: false,
  },
  {
    id: "agenda",
    title: "Agenda da Organização",
    demonstrate:
      "Entrevistas, reuniões, prazos e marcos conectados às avaliações.",
    message: "O planejamento vira compromissos visíveis na home da organização.",
    benefit: "Ajuda a reduzir esquecimentos e improvisos de agenda.",
    resolveHref: () => "/assessments",
    needsAssessment: false,
  },
  {
    id: "wizard",
    title: "Wizard ISO 9001",
    demonstrate:
      "Autoavaliação guiada por perguntas, exemplos e evidências acessíveis.",
    message: "A organização compreende a própria realidade antes da auditoria formal.",
    benefit: "Reduz dependência de jargão e acelera a preparação.",
    resolveHref: (id) => (id ? `/assessments/${id}/guided` : null),
    needsAssessment: true,
  },
  {
    id: "audit_plan",
    title: "Plano da Auditoria",
    demonstrate:
      "Objetivo, escopo, processos, equipe e programação em um único caminho.",
    message: "Um plano executável elimina fluxos concorrentes.",
    benefit: "Pode contribuir para menos improviso no campo.",
    resolveHref: (id) => (id ? `/assessments/${id}/audit-plan` : null),
    needsAssessment: true,
  },
  {
    id: "field",
    title: "Central de Campo",
    demonstrate:
      "Execução das entrevistas e registro estruturado no percurso da avaliação.",
    message: "Conversas orientadas por processos geram informação rastreável.",
    benefit: "Melhora a preparação do material para análise.",
    resolveHref: (id) => (id ? `/assessments/${id}/work` : null),
    needsAssessment: true,
  },
  {
    id: "evidence",
    title: "Evidências",
    demonstrate:
      "Anexar, classificar, verificar e relacionar documentos às perguntas.",
    message: "A evidência certa fica ligada à pergunta certa.",
    benefit: "Facilita o consumo racional das evidências na auditoria formal.",
    resolveHref: (id) => (id ? `/assessments/${id}/guided` : null),
    needsAssessment: true,
  },
  {
    id: "analysis",
    title: "Análise e constatações",
    demonstrate:
      "Confrontar respostas, evidências, constatações e maturidade.",
    message: "Pontos fortes, lacunas e assuntos para aprofundamento ficam claros.",
    benefit: "Permite identificar lacunas antes da auditoria formal.",
    resolveHref: (id) => (id ? `/assessments/${id}/advanced` : null),
    needsAssessment: true,
  },
  {
    id: "evolution",
    title: "Mapa de Evolução Empresarial",
    demonstrate:
      "Sugestões práticas e rastreáveis, sempre revisadas por uma pessoa.",
    message: "A avaliação termina com próximos passos, não só com um diagnóstico.",
    benefit: "Permite iniciar melhorias antes da auditoria formal.",
    resolveHref: (id) => (id ? `/assessments/${id}/evolution` : null),
    needsAssessment: true,
  },
  {
    id: "actions",
    title: "Plano de ação",
    demonstrate: "Transformar sugestões aceitas em ações priorizadas.",
    message: "Responsabilidades e prazos ficam visíveis.",
    benefit: "Tende a reduzir retrabalho na fase de acompanhamento.",
    resolveHref: (id) => (id ? `/assessments/${id}/advanced` : null),
    needsAssessment: true,
  },
  {
    id: "report",
    title: "Relatório e PDF",
    demonstrate:
      "Consolidar relatório, histórico, ações e evidências em um pacote apresentável.",
    message: "Uma preparação clara, verificável e apresentável.",
    benefit: "Melhora a preparação para a auditoria formal.",
    resolveHref: (id) => (id ? `/assessments/${id}/advanced` : null),
    needsAssessment: true,
  },
  {
    id: "quality_control",
    title: "Quality control e auditoria",
    demonstrate:
      "Quem fez, quando, em qual versão, quem revisou e o que entrou no relatório.",
    message: "Cada informação tem origem. Cada decisão deixa um rastro.",
    benefit: "Preserva confiança, responsabilidade e histórico das decisões.",
    resolveHref: (id) => (id ? `/assessments/${id}/advanced` : null),
    needsAssessment: true,
  },
];

export function writeGuidedTourActive(orgId: string, stepIndex: number): void {
  try {
    sessionStorage.setItem(TOUR_ACTIVE_KEY, "1");
    sessionStorage.setItem(TOUR_ORG_KEY, orgId);
    sessionStorage.setItem(TOUR_STEP_KEY, String(Math.max(0, stepIndex)));
  } catch {
    /* ignore */
  }
}

export function readGuidedTourStepIndex(): number {
  try {
    const raw = sessionStorage.getItem(TOUR_STEP_KEY);
    const n = raw == null ? 0 : Number.parseInt(raw, 10);
    if (!Number.isFinite(n) || n < 0) return 0;
    return Math.min(n, GUIDED_TOUR_STEPS.length - 1);
  } catch {
    return 0;
  }
}

export function isGuidedTourActive(orgId: string | null): boolean {
  try {
    if (sessionStorage.getItem(TOUR_ACTIVE_KEY) !== "1") return false;
    const storedOrg = sessionStorage.getItem(TOUR_ORG_KEY);
    if (!orgId || !storedOrg || storedOrg !== orgId) return false;
    return true;
  } catch {
    return false;
  }
}

export function setGuidedTourStepIndex(stepIndex: number): void {
  try {
    sessionStorage.setItem(
      TOUR_STEP_KEY,
      String(Math.max(0, Math.min(stepIndex, GUIDED_TOUR_STEPS.length - 1))),
    );
  } catch {
    /* ignore */
  }
}

export function clearGuidedTour(): void {
  try {
    sessionStorage.removeItem(TOUR_ACTIVE_KEY);
    sessionStorage.removeItem(TOUR_ORG_KEY);
    sessionStorage.removeItem(TOUR_STEP_KEY);
  } catch {
    /* ignore */
  }
}
