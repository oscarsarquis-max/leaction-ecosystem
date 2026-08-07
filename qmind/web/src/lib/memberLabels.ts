/** Rótulos humanos para membros — nunca exibir UUID na UI. */

const ROLE_LABEL: Record<string, string> = {
  org_admin: "Administrador",
  consultant_auditor: "Consultor / auditor",
  quality_manager: "Gestor da qualidade",
  process_owner: "Dono de processo",
  action_owner: "Responsável por ação",
  reader: "Leitor",
};

export function labelMembershipRole(role: string | null | undefined): string {
  if (!role) return "";
  return ROLE_LABEL[role] ?? role.replaceAll("_", " ");
}

export function formatMemberOptionLabel(input: {
  display_name?: string | null;
  email?: string | null;
  roles?: string[] | null;
  team_role?: string | null;
}): string {
  const name = input.display_name?.trim() || "";
  const email = input.email?.trim() || "";
  const primary =
    name ||
    email ||
    "Membro sem identificação";
  const roleParts: string[] = [];
  if (input.team_role?.trim()) {
    roleParts.push(input.team_role.trim());
  }
  for (const r of input.roles ?? []) {
    const labeled = labelMembershipRole(r);
    if (labeled && !roleParts.includes(labeled)) roleParts.push(labeled);
  }
  const roleBit = roleParts.length ? roleParts.slice(0, 2).join(" · ") : "";
  if (name && email && name !== email) {
    return roleBit ? `${name} (${email}) — ${roleBit}` : `${name} (${email})`;
  }
  if (roleBit) return `${primary} — ${roleBit}`;
  return primary;
}
