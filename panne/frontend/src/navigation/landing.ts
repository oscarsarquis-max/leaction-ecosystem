const MANAGERIAL = new Set([
  "owner",
  "organization_owner",
  "administrator",
  "organization_admin",
  "production_manager",
]);

export function primaryRole(roles: string[] | undefined | null): string {
  return roles?.[0] ?? "";
}

export function isManagerialRole(roles: string[] | undefined | null): boolean {
  return Boolean(roles?.some((role) => MANAGERIAL.has(role)));
}

/** Destino pós-login: gerencial no painel; operacional no destino funcional do papel. */
export function landingPathForRoles(roles: string[] | undefined | null): string {
  if (isManagerialRole(roles)) return "/inicio";
  switch (primaryRole(roles)) {
    case "baker_operator":
    case "production":
      return "/producao";
    case "technical_responsible":
      return "/receitas";
    case "regulatory_reviewer":
      return "/conformidade";
    case "commercial":
      return "/gestao/compras/necessidades";
    case "viewer":
      return "/gestao/custos";
    default:
      return "/fluxo";
  }
}

/** Marca: proprietário e gestores → painel; demais → mapa do processo. */
export function brandHomeForRoles(roles: string[] | undefined | null): string {
  return isManagerialRole(roles) ? "/inicio" : "/fluxo";
}
