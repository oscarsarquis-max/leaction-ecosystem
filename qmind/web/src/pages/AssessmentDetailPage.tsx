import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  useAddScope,
  useAddTeamMember,
  useAssessment,
  useAssessmentScopes,
  useAssessmentTeam,
  useDeleteScope,
  useEnsureScopes,
  useOrgMembers,
  useRemoveTeamMember,
  useScopeOptions,
} from "@/hooks/useAssessmentDetail";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import {
  AccessDeniedPanel,
  EmptyPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { FindingsAnalysisPanel } from "@/components/FindingsAnalysisPanel";
import { MaturityAnalysisPanel } from "@/components/MaturityAnalysisPanel";
import { ActionPlanPanel } from "@/components/ActionPlanPanel";
import { ReportPanel } from "@/components/ReportPanel";
import { BlockingNotice } from "@/components/shared/BlockingNotice";
import { AssessmentSectionNav } from "@/components/navigation/AssessmentSectionNav";
import { QmindApiError } from "@/api/qmindApi";
import { labelAssessmentStatus, labelAssessmentType } from "@/lib/labels";
import type { ScopeKind } from "@/lib/validation";
import { useBeginAssessmentAnalysis } from "@/hooks/useFieldExecution";

export function AssessmentDetailPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();
  const assessment = useAssessment(assessmentId);
  const scopes = useAssessmentScopes(assessmentId);
  const team = useAssessmentTeam(assessmentId);
  const perms = useAssessmentPermissions(assessment.data?.status);
  const beginAnalysis = useBeginAssessmentAnalysis(assessmentId ?? "");
  const [phaseError, setPhaseError] = useState<unknown>(null);

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

  if (!assessment.data) {
    return <LoadingPanel title="Carregando avaliação…" />;
  }

  const a = assessment.data;
  const canEdit = perms.canEditSetup;

  return (
    <section className="space-y-8">
      <AssessmentSectionNav assessmentId={assessmentId} />
      <header>
        <p className="text-sm text-teal-950/60">
          <Link to={`/assessments/${assessmentId}`} className="hover:underline">
            Visão geral
          </Link>
          {" / "}
          Análise, ações e relatório
        </p>
        <div className="mt-2 flex flex-wrap items-baseline justify-between gap-3">
          <h1 className="font-display text-3xl tracking-tight text-teal-950">
            {labelAssessmentType(a.type)}
          </h1>
          <span
            className="rounded-md bg-teal-900/10 px-2 py-0.5 text-xs font-semibold tracking-wide text-teal-900"
            data-testid="assessment-status"
          >
            {labelAssessmentStatus(a.status)}
          </span>
        </div>
        <p className="mt-2 text-sm text-teal-950/60">
          {!perms.canMutate ? (
            <span className="text-amber-900">Visualização — sem permissão de edição.</span>
          ) : (
            <span>Você pode editar o que a fase atual permitir.</span>
          )}
        </p>
        <p className="mt-3 text-sm text-teal-950/70">
          Aqui você registra constatações, maturidade, plano de ação e relatório —
          na ordem do percurso. O Assistente QMind explica cada bloco.
        </p>
      </header>

      {phaseError ? <ApiErrorBanner error={phaseError} /> : null}

      {a.status === "in_progress" && perms.canMutate ? (
        <section
          className="rounded-lg border border-teal-900/15 bg-teal-50/50 p-4"
          data-testid="begin-analysis-cta"
        >
          <h2 className="font-display text-lg text-teal-950">
            Pronto para a análise?
          </h2>
          <p className="mt-1 text-sm text-teal-950/70">
            Você pode registrar constatações ainda durante o campo. Quando a
            coleta estiver suficiente, encerre o campo e formalize a fase de
            análise.
          </p>
          <button
            type="button"
            className="qm-btn-primary mt-3"
            disabled={beginAnalysis.isPending}
            data-testid="begin-analysis-button"
            onClick={() =>
              void beginAnalysis.mutateAsync().then(() => setPhaseError(null)).catch(setPhaseError)
            }
          >
            Encerrar campo e iniciar análise
          </button>
        </section>
      ) : null}

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
      <section
        className="rounded-lg border border-teal-900/10 bg-white/70 p-4"
        data-testid="audit-plan-entry"
      >
        <h2 className="font-display text-xl text-teal-950">Plano da Auditoria</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          O planejamento e o início do campo acontecem no Plano da Auditoria —
          único caminho principal (concluir plano, concluir planejamento, abertura
          e iniciar execução).
        </p>
        <Link
          to={`/assessments/${assessmentId}/audit-plan`}
          className="qm-btn-primary mt-3 inline-flex"
          data-testid="open-audit-plan"
        >
          {a.status === "draft"
            ? "Abrir Plano da Auditoria"
            : a.status === "planned"
              ? "Continuar handoff no Plano da Auditoria"
              : "Revisar Plano da Auditoria"}
        </Link>
        {(a.status === "draft" || a.status === "planned") && canEdit ? (
          <p className="mt-2 text-xs text-teal-950/60" data-testid="legacy-plan-compat-note">
            Escopo e equipe abaixo ficam para compatibilidade; a confirmação oficial
            do planejamento e o início do campo são feitos no Plano da Auditoria.
          </p>
        ) : null}
      </section>
      {a.status === "in_progress" ||
      a.status === "analysis" ||
      a.status === "actions" ||
      a.status === "report" ||
      a.status === "closed" ? (
        <section
          className="rounded-lg border border-teal-900/10 bg-white/70 p-4"
          data-testid="field-central-entry"
        >
          <h2 className="font-display text-xl text-teal-950">Central de Campo</h2>
          <p className="mt-1 text-sm text-teal-950/70">
            Entrevistas, evidências e pendências do dia ficam na Central de Campo —
            use esta tela para constatações, maturidade, ações e relatório.
          </p>
          <Link
            to={`/assessments/${assessmentId}/work`}
            className="qm-btn-primary mt-3 inline-flex"
            data-testid="open-field-central"
          >
            {a.status === "in_progress"
              ? "Abrir Central de Campo"
              : "Ver resumo do campo"}
          </Link>
        </section>
      ) : a.status === "draft" || a.status === "planned" ? (
        <BlockingNotice
          title="Execução em campo bloqueada"
          reason="A execução em campo só é liberada depois do handoff no Plano da Auditoria."
          missingItem={
            a.status === "draft"
              ? "Conclua o Plano, conclua o planejamento e formalize a avaliação como planejada."
              : "Registre a reunião de abertura (ou dispense) e use «Iniciar execução em campo» no Plano."
          }
          actionText="Abrir Plano da Auditoria"
          onResolve={() => {
            void navigate(`/assessments/${assessmentId}/audit-plan`);
          }}
        />
      ) : null}

      {perms.canWorkFindings ? (
        <FindingsAnalysisPanel
          assessmentId={assessmentId}
          canCreate={perms.canCreateFindings}
          canReview={perms.canReviewFindings}
          membershipId={perms.membershipId}
          roles={perms.roles}
        />
      ) : a.status === "draft" || a.status === "planned" ? (
        <BlockingNotice
          title="Análise bloqueada"
          reason="A fase de análise só é liberada após a conclusão da execução em campo."
          missingItem="Ainda não há execução em campo concluída para gerar constatações e nível de maturidade."
          actionText="Voltar para a Execução em campo"
          onResolve={() => {
            void navigate(`/assessments/${assessmentId}/work`);
          }}
        />
      ) : null}

      {perms.canWorkMaturity ? (
        <MaturityAnalysisPanel
          assessmentId={assessmentId}
          canElaborate={perms.canElaborateMaturity}
          canReview={perms.canReviewMaturity}
          membershipId={perms.membershipId}
          roles={perms.roles}
          assessmentStatus={a.status}
        />
      ) : null}

      {perms.canWorkActionPlans ? (
        <ActionPlanPanel
          assessmentId={assessmentId}
          assessmentStatus={a.status}
          canManage={perms.canManageActionPlans}
          membershipId={perms.membershipId}
          roles={perms.roles}
        />
      ) : a.status === "draft" ||
        a.status === "planned" ||
        a.status === "in_progress" ? (
        <BlockingNotice
          title="Plano de ação bloqueado"
          reason="O plano de ação só é liberado após a fase de análise."
          missingItem="Registre e revise as constatações da análise antes de abrir o plano de ação."
          actionText="Voltar para a Análise"
          onResolve={() => {
            void navigate(`/assessments/${assessmentId}/advanced`);
          }}
        />
      ) : null}

      {perms.canWorkReports ? (
        <ReportPanel
          assessmentId={assessmentId}
          assessmentStatus={a.status}
          canElaborate={perms.canElaborateReports}
          canReview={perms.canReviewReports}
          canBeginReport={perms.canBeginReport}
          canClose={perms.canCloseAssessment}
          canReopen={perms.canReopenAssessment}
          membershipId={perms.membershipId}
          roles={perms.roles}
        />
      ) : a.status === "draft" ||
        a.status === "planned" ||
        a.status === "in_progress" ||
        a.status === "analysis" ? (
        <BlockingNotice
          title="Relatório bloqueado"
          reason="O relatório só é liberado após o plano de ação."
          missingItem="Conclua análise e plano de ação antes de consolidar o relatório."
          actionText="Continuar nesta tela"
          onResolve={() => {
            void navigate(`/assessments/${assessmentId}/advanced`);
          }}
        />
      ) : null}
    </section>
  );
}

function scopeLabel(s: {
  label?: string | null;
  requirement_id?: string | null;
  org_process_id?: string | null;
}): string {
  const label = s.label?.trim();
  if (label && !/^[0-9a-f-]{36}$/i.test(label)) return label;
  if (s.requirement_id) return "Requisito da norma";
  if (s.org_process_id) return "Processo da organização";
  return "Item de escopo";
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
  const ensureScopes = useEnsureScopes(assessmentId);
  const options = useScopeOptions(canEdit ? assessmentId : undefined);
  const delScope = useDeleteScope(assessmentId);
  const [selectedOption, setSelectedOption] = useState("");
  const busyRef = useRef(false);
  const autoTried = useRef(false);

  useEffect(() => {
    if (!canEdit || autoTried.current) return;
    if (scopesQuery.isLoading || scopesQuery.isError) return;
    if ((scopesQuery.data?.length ?? 0) > 0) return;
    autoTried.current = true;
    void ensureScopes.mutateAsync().catch(() => {
      /* banner via ensureScopes.error */
    });
  }, [
    canEdit,
    scopesQuery.isLoading,
    scopesQuery.isError,
    scopesQuery.data?.length,
    ensureScopes,
  ]);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!canEdit || busyRef.current || addScope.isPending || !selectedOption) return;
    const opt = options.data?.find(
      (o) => `${o.kind}:${o.target_id}` === selectedOption,
    );
    if (!opt) return;
    busyRef.current = true;
    try {
      await addScope.mutateAsync({
        kind: opt.kind as ScopeKind,
        value: opt.target_id,
      });
      setSelectedOption("");
    } catch {
      // surfaced via addScope.error
    } finally {
      busyRef.current = false;
    }
  }

  const available =
    options.data?.filter((o) => !o.already_in_scope) ?? [];

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Escopo</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        O planejamento exige pelo menos um item. O QMind preenche com base no modelo
        e na preparação — você só confirma ou ajusta.
        {!canEdit ? " Edição bloqueada neste estado/papel." : null}
      </p>

      {scopesQuery.isLoading || ensureScopes.isPending ? (
        <p className="mt-3 text-sm text-teal-950/60">Montando escopo…</p>
      ) : scopesQuery.isError ? (
        <div className="mt-3">
          <ApiErrorBanner
            title="Erro ao listar escopo"
            error={scopesQuery.error}
            onRetry={() => void scopesQuery.refetch()}
          />
        </div>
      ) : (scopesQuery.data?.length ?? 0) === 0 ? (
        <div className="mt-3 space-y-3" data-testid="scope-empty">
          <p className="text-sm text-teal-950/60">Nenhum item de escopo ainda.</p>
          {canEdit ? (
            <button
              type="button"
              className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
              disabled={ensureScopes.isPending}
              data-testid="scope-ensure"
              onClick={() => void ensureScopes.mutateAsync()}
            >
              Preencher escopo automaticamente
            </button>
          ) : null}
        </div>
      ) : (
        <ul className="mt-3 divide-y divide-teal-900/10" data-testid="scope-list">
          {scopesQuery.data!.map((s) => (
            <li
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
            >
              <span className="text-[var(--qm-ink)]">
                {scopeLabel(s as { label?: string | null; requirement_id?: string | null; org_process_id?: string | null })}
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

      {canEdit && available.length > 0 ? (
        <form onSubmit={(e) => void onAdd(e)} className="mt-4 flex flex-wrap gap-2">
          <select
            className="field min-w-[16rem] flex-1"
            value={selectedOption}
            onChange={(e) => setSelectedOption(e.target.value)}
            aria-label="Item de escopo"
            data-testid="scope-option"
          >
            <option value="">Escolher item…</option>
            {available.map((o) => (
              <option key={`${o.kind}:${o.target_id}`} value={`${o.kind}:${o.target_id}`}>
                {o.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={addScope.isPending || !selectedOption}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="scope-add"
          >
            Adicionar ao escopo
          </button>
        </form>
      ) : null}
      {ensureScopes.isError ? (
        <div className="mt-2">
          <ApiErrorBanner
            title="Não foi possível montar o escopo"
            error={ensureScopes.error}
          />
        </div>
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
  const orgMembers = useOrgMembers();
  const [membershipId, setMembershipId] = useState("");
  const [teamRole, setTeamRole] = useState("assessor");
  const busyRef = useRef(false);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!canEdit || busyRef.current || addMember.isPending || !membershipId) return;
    busyRef.current = true;
    try {
      await addMember.mutateAsync({
        membership_id: membershipId,
        team_role: teamRole.trim() || undefined,
      });
      setMembershipId("");
    } catch {
      // surfaced via addMember.error
    } finally {
      busyRef.current = false;
    }
  }

  const onTeam = new Set((teamQuery.data ?? []).map((m) => m.membership_id));
  const candidates =
    orgMembers.data?.filter((m) => !onTeam.has(m.membership_id)) ?? [];

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Equipe</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        O planejamento exige um líder e ao menos um membro (o criador já entra como líder).
      </p>

      {teamQuery.isLoading ? (
        <p className="mt-3 text-sm text-teal-950/60">Carregando…</p>
      ) : (teamQuery.data?.length ?? 0) === 0 ? (
        <p className="mt-3 text-sm text-teal-950/60">Nenhum membro.</p>
      ) : (
        <ul className="mt-3 divide-y divide-teal-900/10" data-testid="team-list">
          {teamQuery.data!.map((m) => {
            const labeled = m as { label?: string | null };
            const person =
              labeled.label?.trim() ||
              orgMembers.data?.find((x) => x.membership_id === m.membership_id)
                ?.display_name ||
              orgMembers.data?.find((x) => x.membership_id === m.membership_id)
                ?.email ||
              "Membro da equipe";
            return (
              <li
                key={m.id}
                className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
              >
                <span>
                  <span className="text-[var(--qm-ink)]">{person}</span>
                  {m.team_role ? (
                    <span className="ml-2 text-teal-950/60">({m.team_role})</span>
                  ) : null}
                  {m.membership_id === leadMembershipId ? (
                    <span className="ml-2 text-xs font-semibold text-teal-900">
                      líder
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
            );
          })}
        </ul>
      )}

      {canEdit && candidates.length > 0 ? (
        <form onSubmit={(e) => void onAdd(e)} className="mt-4 flex flex-wrap gap-2">
          <select
            className="field min-w-[16rem] flex-1"
            value={membershipId}
            onChange={(e) => setMembershipId(e.target.value)}
            required
            aria-label="Pessoa da organização"
            data-testid="team-member-select"
          >
            <option value="">Escolher pessoa…</option>
            {candidates.map((m) => (
              <option key={m.membership_id} value={m.membership_id}>
                {m.display_name?.trim() || m.email}
              </option>
            ))}
          </select>
          <input
            className="field w-36"
            value={teamRole}
            onChange={(e) => setTeamRole(e.target.value)}
            placeholder="papel"
            aria-label="Papel na equipe"
          />
          <button
            type="submit"
            disabled={addMember.isPending || !membershipId}
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

