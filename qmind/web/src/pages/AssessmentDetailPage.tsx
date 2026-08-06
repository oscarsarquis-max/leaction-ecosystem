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
  usePlanAssessment,
  useRemoveTeamMember,
  useScopeOptions,
} from "@/hooks/useAssessmentDetail";
import { useStartAssessment } from "@/hooks/useFieldExecution";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import {
  AccessDeniedPanel,
  EmptyPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { FieldExecutionPanel } from "@/components/FieldExecutionPanel";
import { FindingsAnalysisPanel } from "@/components/FindingsAnalysisPanel";
import { MaturityAnalysisPanel } from "@/components/MaturityAnalysisPanel";
import { ActionPlanPanel } from "@/components/ActionPlanPanel";
import { ReportPanel } from "@/components/ReportPanel";
import { BlockingNotice } from "@/components/shared/BlockingNotice";
import { QmindApiError } from "@/api/qmindApi";
import { labelAssessmentStatus, labelAssessmentType } from "@/lib/labels";
import type { ScopeKind } from "@/lib/validation";

export function AssessmentDetailPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();
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

  if (!assessment.data) {
    return <LoadingPanel title="Carregando avaliação…" />;
  }

  const a = assessment.data;
  const canEdit = perms.canEditSetup;

  return (
    <section className="space-y-8">
      <header>
        <p className="text-sm text-teal-950/60">
          <Link to={`/assessments/${assessmentId}`} className="hover:underline">
            Visão geral
          </Link>
          {" / "}
          Trabalho da fase
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
          Papel:{" "}
          <span className="font-semibold text-teal-950">
            {perms.roles.join(", ") || "—"}
          </span>
          {!perms.canMutate ? (
            <span className="ml-2 text-amber-900">(somente leitura)</span>
          ) : null}
        </p>
        <p className="mt-3 text-sm text-teal-950/70">
          Modelo e norma já vinculados automaticamente nesta organização.
          {a.lead_membership_id ? " Líder da avaliação definido." : ""}
        </p>
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
      <section
        className="rounded-lg border border-teal-900/10 bg-white/70 p-4"
        data-testid="audit-plan-entry"
      >
        <h2 className="font-display text-xl text-teal-950">Plano da Auditoria</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          Organize propósito, processos, pessoas e período em linguagem clara —
          com preenchimento a partir da preparação.
        </p>
        <Link
          to={`/assessments/${assessmentId}/audit-plan`}
          className="qm-btn-primary mt-3 inline-flex"
          data-testid="open-audit-plan"
        >
          Abrir Plano da Auditoria
        </Link>
      </section>
      <PlanSection
        assessmentId={assessmentId}
        canEdit={canEdit}
        isDraft={a.status === "draft"}
        scopeCount={scopes.data?.length ?? 0}
        teamCount={team.data?.length ?? 0}
        hasLead={!!a.lead_membership_id}
      />
      <StartSection
        assessmentId={assessmentId}
        canStart={perms.canStart}
        isPlanned={a.status === "planned"}
      />
      {a.status === "in_progress" || a.status === "analysis" ? (
        <FieldExecutionPanel
          assessmentId={assessmentId}
          canEditField={perms.canEditField}
          canCollectEvidence={perms.canCollectEvidence}
        />
      ) : a.status === "draft" || a.status === "planned" ? (
        <BlockingNotice
          title="Execução em campo bloqueada"
          reason="A execução em campo só é liberada depois do planejamento da avaliação."
          missingItem={
            a.status === "draft"
              ? "Falta concluir o planejamento (escopo, equipe e marcar como planejada)."
              : "A avaliação está planejada — inicie a execução quando a equipe estiver pronta."
          }
          actionText={
            a.status === "draft"
              ? "Voltar para o planejamento"
              : "Ir para o início da execução"
          }
          onResolve={() => {
            const el = document.querySelector(
              a.status === "draft"
                ? "[data-testid='plan-open-confirm'], [data-testid='plan-locked']"
                : "[data-testid='start-open-confirm'], [data-testid='start-locked']",
            );
            el?.scrollIntoView({ behavior: "smooth", block: "center" });
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
            void navigate(`/assessments/${assessmentId}/work`);
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
          actionText="Voltar para o Plano de ação"
          onResolve={() => {
            void navigate(`/assessments/${assessmentId}/work`);
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
      <div data-testid="plan-locked">
        <BlockingNotice
          title="Planejamento concluído"
          reason="Escopo e equipe ficam imutáveis depois que a avaliação sai da preparação."
          missingItem="Nenhuma alteração de planejamento é necessária nesta etapa."
          actionText="Ir para a próxima etapa"
          onResolve={() => {
            document
              .querySelector(
                "[data-testid='start-open-confirm'], [data-testid='start-locked']",
              )
              ?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
        />
      </div>
    );
  }

  if (!canEdit) {
    return (
      <BlockingNotice
        title="Planejamento bloqueado"
        reason="Seu papel nesta organização não permite alterar o planejamento."
        missingItem="É necessário um papel com permissão de edição (ex.: administrador ou gestor da qualidade)."
        actionText="Voltar ao mapa da avaliação"
        onResolve={() => {
          window.history.back();
        }}
      />
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

  const missing: string[] = [];
  if (scopeCount < 1) {
    missing.push("Inclua pelo menos um item de escopo (requisito ou processo) acima.");
  }
  if (teamCount < 1 || !hasLead) {
    missing.push("Confirme a equipe com um líder definido.");
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Confirmar planejamento</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        Quando escopo e equipe estiverem ok, confirme para liberar a execução em campo.
        Depois disso, escopo e equipe ficam bloqueados para alteração.
      </p>
      <ul className="mt-3 list-inside list-disc text-sm text-teal-950/70">
        <li data-testid="plan-guard-scope">
          Escopo: {scopeCount >= 1 ? "ok" : "faltando (≥ 1 item)"}
        </li>
        <li data-testid="plan-guard-team">
          Equipe/líder:{" "}
          {teamCount >= 1 && hasLead ? "ok" : "faltando (líder + membro)"}
        </li>
      </ul>

      {!ready ? (
        <div className="mt-4">
          <BlockingNotice
            title="Planejamento ainda incompleto"
            reason="Não é possível confirmar o planejamento enquanto faltar o essencial abaixo."
            missingItem={missing.join(" ")}
            actionText="Ir para o escopo"
            onResolve={() => {
              document
                .querySelector(
                  "[data-testid='scope-add'], [data-testid='scope-empty'], [data-testid='scope-list']",
                )
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
          />
        </div>
      ) : null}

      {!confirmOpen ? (
        <button
          type="button"
          disabled={!ready || plan.isPending}
          onClick={() => setConfirmOpen(true)}
          className="mt-4 rounded-md bg-teal-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          data-testid="plan-open-confirm"
        >
          Marcar como planejada…
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
            Após o planejamento, escopo e equipe ficam bloqueados para alteração. Esta ação
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
              {plan.isPending ? "Planejando…" : "Confirmar planejamento"}
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
          <ApiErrorBanner title="Falha na transição de planejamento" error={plan.error} />
        </div>
      ) : null}
    </section>
  );
}

function StartSection({
  assessmentId,
  canStart,
  isPlanned,
}: {
  assessmentId: string;
  canStart: boolean;
  isPlanned: boolean;
}) {
  const start = useStartAssessment(assessmentId);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const busyRef = useRef(false);

  if (!isPlanned) {
    return null;
  }

  if (!canStart) {
    return (
      <div data-testid="start-locked">
        <BlockingNotice
          title="Início da execução bloqueado"
          reason="A avaliação já está planejada, mas seu papel não permite iniciar a execução em campo."
          missingItem="Peça a um responsável com permissão de mutação para iniciar a execução."
          actionText="Voltar ao mapa da avaliação"
          onResolve={() => {
            window.history.back();
          }}
        />
      </div>
    );
  }

  async function confirmStart() {
    if (busyRef.current || start.isPending) return;
    busyRef.current = true;
    try {
      await start.mutateAsync();
      setConfirmOpen(false);
    } catch {
      // banner
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h2 className="font-display text-xl text-teal-950">Iniciar execução</h2>
      <p className="mt-1 text-sm text-teal-950/70">
        Transição planejada → em execução. Abre coleta de entrevistas e evidências.
      </p>

      {!confirmOpen ? (
        <button
          type="button"
          disabled={start.isPending}
          onClick={() => setConfirmOpen(true)}
          className="mt-4 rounded-md bg-teal-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          data-testid="start-open-confirm"
        >
          Iniciar avaliação…
        </button>
      ) : (
        <div
          className="mt-4 rounded-md border border-amber-300/70 bg-amber-50/90 p-4"
          data-testid="start-confirm"
          role="dialog"
          aria-labelledby="start-confirm-title"
        >
          <h3 id="start-confirm-title" className="font-semibold text-amber-950">
            Confirmar início?
          </h3>
          <p className="mt-2 text-sm text-amber-950/90">
            Após o início, a avaliação entra em execução de campo. Sem atualização otimista —
            a tela recarrega o estado do servidor.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={start.isPending}
              onClick={() => void confirmStart()}
              className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
              data-testid="start-confirm-submit"
            >
              {start.isPending ? "Iniciando…" : "Confirmar início"}
            </button>
            <button
              type="button"
              disabled={start.isPending}
              onClick={() => setConfirmOpen(false)}
              className="rounded-md border border-teal-900/20 bg-white px-3 py-1.5 text-sm font-semibold text-teal-950"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {start.isError ? (
        <div className="mt-3">
          <ApiErrorBanner title="Falha na transição de início" error={start.error} />
        </div>
      ) : null}
    </section>
  );
}
