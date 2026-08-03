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
      <span className="text-sm text-teal-950/60" aria-live="polite">
        Organizações…
      </span>
    );
  }

  if (memberships.length === 0) {
    return (
      <span className="text-sm text-teal-950/60">Nenhuma organização ativa</span>
    );
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="sr-only">Organização</span>
      <select
        className="max-w-[16rem] rounded-md border border-teal-900/20 bg-white/90 px-2 py-1.5 text-sm font-semibold text-teal-950 shadow-sm"
        value={currentOrganizationId ?? ""}
        onChange={(e) => {
          const next = e.target.value;
          if (next) void switchOrganization(next);
        }}
        aria-label="Selecionar organização"
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
