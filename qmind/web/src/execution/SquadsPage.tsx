import { useState } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { useOrgMembers } from "@/hooks/useAssessmentDetail";
import { canMutateAgileExecution } from "@/lib/permissions";
import { formatMemberOptionLabel } from "@/lib/memberLabels";
import type { OrgMemberOption } from "@/api/scopeTeamApi";
import { LoadingPanel, EmptyPanel } from "@/components/StatePanels";
import {
  useAddSquadMembership,
  useCreateSquad,
  usePatchSquadMembership,
  useSquadMemberships,
  useSquads,
} from "@/execution/hooks";
import { AGILE_ROLE_LABELS } from "@/execution/labels";
import type { AgileRole } from "@/execution/api";

export function SquadsPage() {
  const org = useOrganization();
  const canMutate = canMutateAgileExecution(org.currentOrganization?.roles);
  const squadsQuery = useSquads();
  const membersQuery = useOrgMembers();
  const createSquad = useCreateSquad();

  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [valueOwnerId, setValueOwnerId] = useState("");
  const [expandedSquad, setExpandedSquad] = useState<string | null>(null);

  if (squadsQuery.isLoading) {
    return <LoadingPanel title="Carregando squads…" />;
  }

  const squads = squadsQuery.data ?? [];
  const members = membersQuery.data ?? [];

  return (
    <div className="space-y-6">
      {canMutate ? (
        <form
          className="qm-panel space-y-3 px-6 py-5"
          data-testid="squad-create-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim() || !valueOwnerId) return;
            void createSquad
              .mutateAsync({
                name: name.trim(),
                purpose: purpose.trim(),
                value_owner_membership_id: valueOwnerId,
              })
              .then(() => {
                setName("");
                setPurpose("");
                setValueOwnerId("");
              });
          }}
        >
          <h2 className="font-semibold text-[var(--qm-ink)]">Nova squad</h2>
          <label className="block text-sm font-semibold">
            Nome da squad
            <input
              className="qm-field mt-1"
              placeholder="Ex.: Squad Qualidade"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm font-semibold">
            Dono de valor
            <select
              className="qm-field mt-1"
              value={valueOwnerId}
              onChange={(e) => setValueOwnerId(e.target.value)}
              required
            >
              <option value="">Selecione quem responde pela squad…</option>
              {members.map((m) => (
                <option key={m.membership_id} value={m.membership_id}>
                  {formatMemberOptionLabel({
                    display_name: m.display_name,
                    email: m.email,
                    roles: m.roles,
                  })}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs font-normal text-[var(--qm-muted)]">
              A squad e o papel de dono de valor são criados na mesma operação.
            </span>
          </label>
          <textarea
            className="qm-field min-h-[4rem]"
            placeholder="Propósito (opcional)"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />
          <button
            type="submit"
            className="qm-btn-primary"
            disabled={createSquad.isPending || !valueOwnerId}
          >
            Criar squad
          </button>
        </form>
      ) : null}

      {squads.length === 0 ? (
        <EmptyPanel
          title="Nenhuma squad cadastrada"
          message="Squads organizam quem executa as ações de melhoria."
          example="Ex.: Squad Qualidade — melhorias do SGQ."
        />
      ) : (
        <ul className="space-y-4">
          {squads.map((squad) => (
            <li key={squad.id} className="qm-panel px-6 py-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--qm-ink)]">{squad.name}</h3>
                  {squad.purpose ? (
                    <p className="mt-1 text-sm text-[var(--qm-muted)]">{squad.purpose}</p>
                  ) : null}
                  <p className="mt-1 text-xs text-[var(--qm-muted)]">
                    Sprint padrão: {squad.default_sprint_length_days} dias · {squad.status}
                  </p>
                </div>
                <button
                  type="button"
                  className="qm-btn-secondary !px-3 !py-1.5 text-sm"
                  onClick={() =>
                    setExpandedSquad((cur) => (cur === squad.id ? null : squad.id))
                  }
                >
                  {expandedSquad === squad.id ? "Ocultar membros" : "Membros"}
                </button>
              </div>
              {expandedSquad === squad.id ? (
                <SquadMembershipPanel squadId={squad.id} canMutate={canMutate} members={members} />
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SquadMembershipPanel({
  squadId,
  canMutate,
  members,
}: {
  squadId: string;
  canMutate: boolean;
  members: OrgMemberOption[];
}) {
  const membershipsQuery = useSquadMemberships(squadId);
  const addMembership = useAddSquadMembership(squadId);
  const patchMembership = usePatchSquadMembership(squadId);
  const [memberId, setMemberId] = useState("");
  const [role, setRole] = useState<AgileRole>("execution_member");

  if (membershipsQuery.isLoading) {
    return <p className="mt-4 text-sm text-[var(--qm-muted)]">Carregando membros…</p>;
  }

  return (
    <div className="mt-4 border-t border-[var(--qm-line)] pt-4">
      <ul className="space-y-2 text-sm">
        {(membershipsQuery.data ?? []).map((m) => (
          <li key={m.id} className="flex flex-wrap items-center justify-between gap-2">
            <span>
              {m.member_display_name || m.member_email || "Membro"} —{" "}
              {AGILE_ROLE_LABELS[m.agile_role]} ({m.status})
            </span>
            {canMutate && m.status === "active" ? (
              <button
                type="button"
                className="qm-btn-secondary !px-2 !py-1 text-xs"
                onClick={() =>
                  void patchMembership.mutateAsync({
                    membershipId: m.membership_id,
                    body: { status: "inactive" },
                  })
                }
              >
                Remover
              </button>
            ) : null}
          </li>
        ))}
      </ul>

      {canMutate ? (
        <form
          className="mt-4 flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!memberId) return;
            void addMembership.mutateAsync({ membership_id: memberId, agile_role: role }).then(() => {
              setMemberId("");
            });
          }}
        >
          <select
            className="qm-field min-w-[14rem]"
            value={memberId}
            onChange={(e) => setMemberId(e.target.value)}
            required
          >
            <option value="">Membro da organização…</option>
            {members.map((m) => (
              <option key={m.membership_id} value={m.membership_id}>
                {formatMemberOptionLabel({
                  display_name: m.display_name,
                  email: m.email,
                  roles: m.roles,
                })}
              </option>
            ))}
          </select>
          <select
            className="qm-field"
            value={role}
            onChange={(e) => setRole(e.target.value as AgileRole)}
          >
            {(Object.keys(AGILE_ROLE_LABELS) as AgileRole[]).map((r) => (
              <option key={r} value={r}>
                {AGILE_ROLE_LABELS[r]}
              </option>
            ))}
          </select>
          <button type="submit" className="qm-btn-secondary" disabled={addMembership.isPending}>
            Adicionar
          </button>
        </form>
      ) : null}
    </div>
  );
}
