import { useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useAddScope,
  useAddTeamMember,
  useAssessment,
  useAssessmentScopes,
  useAssessmentTeam,
  useDeleteScope,
  usePlanAssessment,
  useRemoveTeamMember,
} from "@/hooks/useAssessmentDetail";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import {
  AccessDeniedPanel,
  EmptyPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { QmindApiError } from "@/api/qmindApi";
import { isUuid } from "@/lib/validation";

export function AssessmentDetailPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const assessment = useAssessment(assessmentId);
  const scopes = useAssessmentScopes(assessmentId);
  const team = useAssessmentTeam(assessmentId);
  const perms = useAssessmentPermissions(assessment.data?.status);

  if (!assessmentId) {
    return <EmptyPanel title="Avaliação inválida" />;
  }

  if (assessment.isLoading) {
    return <LoadingPanel title="Carregando avaliação…" />;
  }

  if (assessment.isError) {
    const err = assessment.error;
    if (err instanceof QmindApiError && (err.status === 401 || err.status === 403)) {
      return <AccessDeniedPanel message={err.message} />;
    }
    return (
      <ApiErrorBanner
        title="Erro ao carregar avaliação"
        error={err}
        onRetry={() => void assessment.refetch()}
      />
    );
  }

  const a = assessment.data!;
  const canEdit = perms.canEditSetup;

  return (
    <section className="space-y-8">
      <header>
        <p className="text-sm text-teal-950/60">
          <Link to="/assessments" className="hover:underline">
            Avaliações
          </Link>
          {" / "}
          <span className="font-mono text-xs">{a.id}</span>
        </p>
        <div className="mt-2 flex flex-wrap items-baseline justify-between gap-3">
          <h1 className="font-display text-3xl tracking-tight text-teal-950">
            {a.type}
          </h1>
          <span
            className="rounded-md bg-teal-900/10 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-teal-900"
            data-testid="assessment-status"
          >
            {a.status}
          </span>
        </div>
        <p className="mt-2 text-sm text-teal-950/60">
          Papel:{" "}
          <span className="font-semibold text-teal-950">
            {perms.roles.join(", ") || "—"}
          </span>
          {!perms.canMutate ? (
            <span className="ml-2 text-amber-900">(somente leitura)</span>
          ) : null}
        </p>
        <dl className="mt-3 grid gap-1 text-sm text-teal-950/70 sm:grid-cols-2">
          <div>
            <dt className="inline font-semibold text-teal-950">Model: </dt>
            <dd className="inline font-mono text-xs">{a.assessment_model_id}</dd>
          </div>
          <div>
            <dt className="inline font-semibold text-teal-950">Standard: </dt>
            <dd className="inline font-mono text-xs">{a.standard_version_id}</dd>
          </div>
          <div>
            <dt className="inline font-semibold text-teal-950">Lead: </dt>
            <dd className="inline font-mono text-xs">
              {a.lead_membership_id ?? "—"}
            </dd>
          </div>
        </dl>
      </header>

      {!canEdit && a.status === "draft" && !perms.canMutate ? (
        <p
          className="rounded-md border border-amber-300/60 bg-amber-50/80 px-3 py-2 text-sm text-amber-950"
          data-testid="reader-notice"
        >
          Seu papel não permite alterar escopo, equipe ou planejar esta avaliação.
        </p>
      ) : null}

      <ScopeSection
        assessmentId={assessmentId}
        canEdit={canEdit}
        scopesQuery={scopes}
        onConflictReload={() => {
          void assessment.refetch();
          void scopes.refetch();
        }}
      />
      <TeamSection
        assessmentId={assessmentId}
        canEdit={canEdit}
        teamQuery={team}
        leadMembershipId={a.lead_membership_id}
      />
      <PlanSection
        assessmentId={assessmentId}
        canEdit={canEdit}
        isDraft={a.status === "draft"}
        scopeCount={scopes.data?.length ?? 0}
        teamCount={team.data?.length ?? 0}
        hasLead={!!a.lead_membership_id}
      />
    </section>
  );
}

function ScopeSection({
  assessmentId,
  canEdit,
  scopesQuery,
  onConflictReload,
}: {
  assessmentId: string;
  canEdit: boolean;
  scopesQuery: ReturnType<typeof useAssessmentScopes>;
  onConflictReload: () => void;
}) {
  const addScope = useAddScope(assessmentId);
  const delScope = useDeleteScope(assessmentId);
  const [kind, setKind] = useState<"requirement" | "process">("requirement");
  const [value, setValue] = useState("");
  const busyRef = useRef(false);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!canEdit || busyRef.current || addScope.isPending) return;
    busyRef.current = true;
    try {
      await addScope.mutateAsync({ kind, value });
      setValue("");
    } catch {
      // surfaced via addScope.error
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Escopo</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        Plan exige pelo menos um item (requirement ou processo).
        {!canEdit ? " Edição bloqueada neste estado/papel." : null}
      </p>

      {scopesQuery.isLoading ? (
        <p className="mt-3 text-sm text-teal-950/60">Carregando…</p>
      ) : scopesQuery.isError ? (
        <div className="mt-3">
          <ApiErrorBanner
            title="Erro ao listar escopo"
            error={scopesQuery.error}
            onRetry={() => void scopesQuery.refetch()}
          />
        </div>
      ) : (scopesQuery.data?.length ?? 0) === 0 ? (
        <p className="mt-3 text-sm text-teal-950/60" data-testid="scope-empty">
          Nenhum item de escopo.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-teal-900/10" data-testid="scope-list">
          {scopesQuery.data!.map((s) => (
            <li
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
            >
              <span className="font-mono text-xs">
                {s.requirement_id
                  ? `requirement:${s.requirement_id}`
                  : `process:${s.org_process_id}`}
              </span>
              {canEdit ? (
                <button
                  type="button"
                  className="text-xs font-semibold text-rose-800"
                  disabled={delScope.isPending}
                  onClick={() => void delScope.mutateAsync(s.id)}
                >
                  Remover
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {canEdit ? (
        <form onSubmit={(e) => void onAdd(e)} className="mt-4 flex flex-wrap gap-2">
          <select
            className="field w-auto"
            value={kind}
            onChange={(e) => setKind(e.target.value as "requirement" | "process")}
            aria-label="Tipo de escopo"
          >
            <option value="requirement">requirement_id</option>
            <option value="process">org_process_id</option>
          </select>
          <input
            className="field min-w-[16rem] flex-1"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="UUID"
            required
            aria-label="Valor do escopo"
          />
          <button
            type="submit"
            disabled={addScope.isPending || !isUuid(value)}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="scope-add"
          >
            Adicionar escopo
          </button>
        </form>
      ) : null}
      {addScope.isError ? (
        <div className="mt-2">
          <ApiErrorBanner
            title="Erro ao adicionar escopo"
            error={addScope.error}
            onRetry={
              addScope.error instanceof QmindApiError &&
              (addScope.error.status === 409 || addScope.error.status === 422)
                ? onConflictReload
                : undefined
            }
          />
        </div>
      ) : null}
    </section>
  );
}

function TeamSection({
  assessmentId,
  canEdit,
  teamQuery,
  leadMembershipId,
}: {
  assessmentId: string;
  canEdit: boolean;
  teamQuery: ReturnType<typeof useAssessmentTeam>;
  leadMembershipId: string | null;
}) {
  const addMember = useAddTeamMember(assessmentId);
  const removeMember = useRemoveTeamMember(assessmentId);
  const [membershipId, setMembershipId] = useState("");
  const [teamRole, setTeamRole] = useState("assessor");
  const busyRef = useRef(false);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!canEdit || busyRef.current || addMember.isPending) return;
    busyRef.current = true;
    try {
      await addMember.mutateAsync({
        membership_id: membershipId.trim(),
        team_role: teamRole.trim() || undefined,
      });
      setMembershipId("");
    } catch {
      // surfaced via addMember.error
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Equipe</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        Plan exige lead e ao menos um membro (o criador já entra como lead).
      </p>

      {teamQuery.isLoading ? (
        <p className="mt-3 text-sm text-teal-950/60">Carregando…</p>
      ) : (teamQuery.data?.length ?? 0) === 0 ? (
        <p className="mt-3 text-sm text-teal-950/60">Nenhum membro.</p>
      ) : (
        <ul className="mt-3 divide-y divide-teal-900/10" data-testid="team-list">
          {teamQuery.data!.map((m) => (
            <li
              key={m.id}
              className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
            >
              <span>
                <span className="font-mono text-xs">{m.membership_id}</span>
                {m.team_role ? (
                  <span className="ml-2 text-teal-950/60">({m.team_role})</span>
                ) : null}
                {m.membership_id === leadMembershipId ? (
                  <span className="ml-2 text-xs font-semibold uppercase text-teal-900">
                    lead
                  </span>
                ) : null}
              </span>
              {canEdit && m.membership_id !== leadMembershipId ? (
                <button
                  type="button"
                  className="text-xs font-semibold text-rose-800"
                  disabled={removeMember.isPending}
                  onClick={() => void removeMember.mutateAsync(m.id)}
                >
                  Remover
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {canEdit ? (
        <form onSubmit={(e) => void onAdd(e)} className="mt-4 flex flex-wrap gap-2">
          <input
            className="field min-w-[16rem] flex-1"
            value={membershipId}
            onChange={(e) => setMembershipId(e.target.value)}
            placeholder="membership_id (UUID)"
            required
            aria-label="membership_id"
          />
          <input
            className="field w-36"
            value={teamRole}
            onChange={(e) => setTeamRole(e.target.value)}
            placeholder="papel"
            aria-label="team_role"
          />
          <button
            type="submit"
            disabled={addMember.isPending || !isUuid(membershipId)}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="team-add"
          >
            Adicionar membro
          </button>
        </form>
      ) : null}
      {addMember.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Erro na equipe" error={addMember.error} />
        </div>
      ) : null}
    </section>
  );
}

function PlanSection({
  assessmentId,
  canEdit,
  isDraft,
  scopeCount,
  teamCount,
  hasLead,
}: {
  assessmentId: string;
  canEdit: boolean;
  isDraft: boolean;
  scopeCount: number;
  teamCount: number;
  hasLead: boolean;
}) {
  const plan = usePlanAssessment(assessmentId);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const busyRef = useRef(false);
  const ready = scopeCount >= 1 && teamCount >= 1 && hasLead;

  if (!isDraft) {
    return (
      <section
        className="rounded-lg border border-teal-900/10 bg-teal-50/50 px-4 py-3 text-sm text-teal-950/80"
        data-testid="plan-locked"
      >
        Avaliação já saiu de `draft` — escopo e equipe estão bloqueados para mutação.
      </section>
    );
  }

  if (!canEdit) {
    return (
      <section className="rounded-lg border border-teal-900/10 bg-white/40 px-4 py-3 text-sm text-teal-950/70">
        Planejamento disponível apenas para papéis com permissão de mutação.
      </section>
    );
  }

  async function confirmPlan() {
    if (busyRef.current || plan.isPending) return;
    busyRef.current = true;
    try {
      await plan.mutateAsync();
      setConfirmOpen(false);
    } catch {
      // error banner below; 409/422 already invalidate + reload via hook
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Planejar</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        Transição `draft` → `planned`. Congela o modelo de maturidade ativo.
      </p>
      <ul className="mt-3 list-inside list-disc text-sm text-teal-950/70">
        <li data-testid="plan-guard-scope">
          Escopo: {scopeCount >= 1 ? "ok" : "faltando (≥ 1 item)"}
        </li>
        <li data-testid="plan-guard-team">
          Equipe/lead:{" "}
          {teamCount >= 1 && hasLead ? "ok" : "faltando (lead + membro)"}
        </li>
      </ul>

      {!confirmOpen ? (
        <button
          type="button"
          disabled={!ready || plan.isPending}
          onClick={() => setConfirmOpen(true)}
          className="mt-4 rounded-md bg-teal-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          data-testid="plan-open-confirm"
        >
          Marcar como planned…
        </button>
      ) : (
        <div
          className="mt-4 rounded-md border border-amber-300/70 bg-amber-50/90 p-4"
          data-testid="plan-confirm"
          role="dialog"
          aria-labelledby="plan-confirm-title"
        >
          <h3 id="plan-confirm-title" className="font-semibold text-amber-950">
            Confirmar planejamento?
          </h3>
          <p className="mt-2 text-sm text-amber-950/90">
            Após `plan`, escopo e equipe ficam bloqueados para alteração. Esta ação
            não usa atualização otimista — a tela recarrega o recurso do servidor.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={plan.isPending}
              onClick={() => void confirmPlan()}
              className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
              data-testid="plan-confirm-submit"
            >
              {plan.isPending ? "Planejando…" : "Confirmar plan"}
            </button>
            <button
              type="button"
              disabled={plan.isPending}
              onClick={() => setConfirmOpen(false)}
              className="rounded-md border border-teal-900/20 bg-white px-3 py-1.5 text-sm font-semibold text-teal-950"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {plan.isError ? (
        <div className="mt-3">
          <ApiErrorBanner title="Falha na transição plan" error={plan.error} />
        </div>
      ) : null}
    </section>
  );
}
