const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuid(value: string): boolean {
  return UUID_RE.test(value.trim());
}

export type ScopeKind = "requirement" | "process";

/** OpenAPI ScopeItemIn: exactly one of requirement_id | org_process_id. */
export function buildScopeItem(
  kind: ScopeKind,
  value: string,
): { requirement_id: string } | { org_process_id: string } | null {
  const id = value.trim();
  if (!isUuid(id)) return null;
  return kind === "requirement" ? { requirement_id: id } : { org_process_id: id };
}
