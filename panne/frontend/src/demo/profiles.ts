export type DemoProfile = {
  subject: string;
  label: string;
  role: string;
};

/** Perfis canônicos da demonstração (7). Leitor econômico = demo-viewer. */
export const DEMO_PROFILES: DemoProfile[] = [
  { subject: "demo-owner", label: "Proprietário", role: "owner" },
  { subject: "demo-manager", label: "Gestor de produção", role: "production_manager" },
  { subject: "demo-formulator", label: "Técnico / formulador", role: "technical_responsible" },
  { subject: "demo-baker", label: "Padeiro", role: "baker_operator" },
  { subject: "demo-reviewer", label: "Revisor regulatório", role: "regulatory_reviewer" },
  { subject: "demo-buyer", label: "Comercial / compras", role: "commercial" },
  { subject: "demo-viewer", label: "Leitor econômico", role: "viewer" },
];

/** Sujeitos do mundo descartável GATE4-H1 (:5544) — não entram no seletor demo compartilhado. */
export const GATE4_H1_PROFILES: DemoProfile[] = [
  { subject: "h1-owner", label: "H1 Proprietário (teste)", role: "owner" },
  { subject: "h1-viewer", label: "H1 Leitor econômico (teste)", role: "viewer" },
  { subject: "h1-baker", label: "H1 Padeiro (teste)", role: "baker_operator" },
];
