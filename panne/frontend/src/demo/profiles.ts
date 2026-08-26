export type DemoProfile = {
  subject: string;
  label: string;
  role: string;
};

export const DEMO_PROFILES: DemoProfile[] = [
  { subject: "demo-owner", label: "Proprietário", role: "owner" },
  { subject: "demo-manager", label: "Gestor de produção", role: "production_manager" },
  { subject: "demo-formulator", label: "Técnico / formulador", role: "technical_responsible" },
  { subject: "demo-baker", label: "Padeiro", role: "baker_operator" },
  { subject: "demo-reviewer", label: "Revisor regulatório", role: "regulatory_reviewer" },
  { subject: "demo-buyer", label: "Comercial / compras", role: "commercial" },
  { subject: "demo-reader", label: "Leitor", role: "viewer" },
];
