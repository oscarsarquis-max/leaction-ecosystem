/** Papéis de associação em linguagem humana — nunca mostrar o código cru. */
export const ROLE_LABEL: Record<string, string> = {
  owner: "Proprietário",
  organization_owner: "Proprietário",
  administrator: "Administrador",
  viewer: "Leitor",
  production_manager: "Gestor de produção",
  production: "Gestor de produção",
  technical_responsible: "Formulador",
  baker_operator: "Padeiro",
  regulatory_reviewer: "Revisor",
  commercial: "Comercial / compras",
};

export function roleLabel(code: string | null | undefined): string {
  const cleaned = code?.trim();
  if (!cleaned) return "";
  return ROLE_LABEL[cleaned] ?? "Perfil operacional";
}
