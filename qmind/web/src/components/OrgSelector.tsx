import { useOrganization } from "@/org/OrganizationProvider";

export function OrgSelector() {
  const {
    memberships,
    currentOrganizationId,
    switchOrganization,
    loading,
  } = useOrganization();

  if (loading && memberships.length === 0) {
    return (
      <span className="text-sm text-[var(--qm-muted)]" aria-live="polite">
        Organizações…
      </span>
    );
  }

  if (memberships.length === 0) {
    return (
      <span className="text-sm text-[var(--qm-muted)]">Nenhuma organização ativa</span>
    );
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="hidden text-[var(--qm-muted)] sm:inline">Organização</span>
      <select
        className="qm-field max-w-[16rem] !py-1.5 text-sm font-semibold"
        value={currentOrganizationId ?? ""}
        onChange={(e) => {
          const next = e.target.value;
          if (next) void switchOrganization(next);
        }}
        aria-label="Selecionar organização"
        title="Trocar de organização não mistura o progresso entre elas"
      >
        {memberships.map((m) => (
          <option key={m.organizationId} value={m.organizationId}>
            {m.organizationName}
          </option>
        ))}
      </select>
    </label>
  );
}
