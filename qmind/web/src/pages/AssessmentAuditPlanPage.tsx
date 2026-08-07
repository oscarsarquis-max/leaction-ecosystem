import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import { JourneyBar } from "@/components/navigation/JourneyBar";
import { AssessmentSectionNav } from "@/components/navigation/AssessmentSectionNav";
import { PageHeader } from "@/components/qm";
import {
  useAssessment,
  useAssessmentTeam,
} from "@/hooks/useAssessmentDetail";
import { useAuditDashboard } from "@/hooks/useAuditDashboard";
import {
  useAuditPlan,
  usePatchAuditPlan,
  useRefreshAuditPlan,
} from "@/hooks/useAuditPlan";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { AuditPlanScheduleSection } from "@/components/AuditPlanScheduleSection";
import { AuditPlanHandoffPanel } from "@/components/AuditPlanHandoffPanel";
import {
  MODALITY_OPTIONS,
  planStatusLabel,
  type AuditPlan,
  type AuditPlanCriteria,
  type AuditPlanModality,
  type AuditPlanProcess,
  type AuditPlanSite,
  type OrgRepresentative,
} from "@/api/auditPlanTypes";
import { QmindApiError } from "@/api/qmindApi";
import { useAuditPlanSchedule } from "@/hooks/useAuditPlanSchedule";

type SaveState = "idle" | "saving" | "saved" | "error";

function SourceBadge({ source }: { source?: string }) {
  if (source === "preparation" || source === "assessment") {
    return (
      <span className="rounded bg-[var(--qm-surface-soft)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--qm-muted)]">
        Da preparação
      </span>
    );
  }
  if (source === "manual") {
    return (
      <span className="rounded bg-[var(--qm-surface-soft)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--qm-muted)]">
        Revisado
      </span>
    );
  }
  return null;
}

function Block({
  title,
  objective,
  expected,
  example,
  pending,
  children,
}: {
  title: string;
  objective: string;
  expected: string;
  example: string;
  pending?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-4">
      <div>
        <h3 className="font-display text-lg text-[var(--qm-ink)]">{title}</h3>
        <p className="mt-1 text-sm text-[var(--qm-muted)]">{objective}</p>
        <ul className="mt-2 space-y-1 text-xs text-[var(--qm-muted)]">
          <li>
            <span className="font-semibold text-[var(--qm-ink)]">Esperado: </span>
            {expected}
          </li>
          <li>
            <span className="font-semibold text-[var(--qm-ink)]">Exemplo: </span>
            {example}
          </li>
          {pending ? (
            <li className="text-[var(--qm-accent)]">
              <span className="font-semibold">Pendência: </span>
              {pending}
            </li>
          ) : null}
        </ul>
      </div>
      {children}
    </section>
  );
}

function listToText(items: { name: string; location?: string; owner?: string }[]) {
  return items
    .map((i) => {
      const extra = i.location || i.owner || "";
      return extra ? `${i.name} — ${extra}` : i.name;
    })
    .join("\n");
}

function textToSites(text: string, prev: AuditPlanSite[]): AuditPlanSite[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, location = ""] = line.split("—").map((s) => s.trim());
      const old = prev.find((p) => p.name === name);
      return {
        name: name || line,
        location: location || old?.location || "",
        notes: old?.notes || "",
        from_preparation: old?.from_preparation ?? false,
      };
    });
}

function textToProcesses(text: string, prev: AuditPlanProcess[]): AuditPlanProcess[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, owner = ""] = line.split("—").map((s) => s.trim());
      const old = prev.find((p) => p.name === name);
      return {
        name: name || line,
        owner: owner || old?.owner || "",
        notes: old?.notes || "",
        from_preparation: old?.from_preparation ?? false,
        interview_justification: old?.interview_justification || "",
      };
    });
}

export function AssessmentAuditPlanPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const assessment = useAssessment(assessmentId);
  const dash = useAuditDashboard(assessmentId);
  const planQ = useAuditPlan(assessmentId);
  const team = useAssessmentTeam(assessmentId);
  const perms = useAssessmentPermissions(assessment.data?.status);
  const patch = usePatchAuditPlan(assessmentId ?? "");
  const refresh = useRefreshAuditPlan(assessmentId ?? "");
  const scheduleQ = useAuditPlanSchedule(assessmentId);

  const [local, setLocal] = useState<AuditPlan | null>(null);
  const [readyInfo, setReadyInfo] = useState<string | null>(null);
  const [amendmentReason, setAmendmentReason] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState<unknown>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (!planQ.data || hydrated.current) return;
    hydrated.current = true;
    setLocal(planQ.data);
  }, [planQ.data]);

  useEffect(() => {
    if (planQ.data) setLocal(planQ.data);
  }, [planQ.data?.updated_at]);

  const readOnly =
    !perms.canMutate || !local?.editable || assessment.data?.status === "cancelled";
  const needsReason = !!local?.requires_amendment_reason;

  function scheduleSave(next: AuditPlan, extra?: { amendment_reason?: string }) {
    if (readOnly || !assessmentId) return;
    setLocal(next);
    setSaveState("saving");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void (async () => {
        try {
          if (needsReason && !(extra?.amendment_reason || amendmentReason).trim()) {
            setSaveState("error");
            setError(
              new QmindApiError(422, {
                code: "validation_error",
                message: "Informe o motivo do ajuste antes de salvar.",
                correlation_id: "",
              }),
            );
            return;
          }
          const saved = await patch.mutateAsync({
            objective: next.objective,
            modality: next.modality,
            scope_text: next.scope_text,
            criteria: next.criteria,
            sites: next.sites,
            processes: next.processes,
            lead_membership_id: next.lead_membership_id,
            team_membership_ids: next.team_membership_ids,
            org_representatives: next.org_representatives,
            planned_start: next.planned_start,
            planned_end: next.planned_end,
            preparation_notes: next.preparation_notes,
            risks_notes: next.risks_notes,
            expected_updated_at: next.updated_at,
            amendment_reason: needsReason
              ? extra?.amendment_reason || amendmentReason
              : undefined,
          });
          setLocal(saved);
          setSaveState("saved");
          setError(null);
        } catch (err) {
          setSaveState("error");
          setError(err);
        }
      })();
    }, 700);
  }

  if (!assessmentId || planQ.isLoading || assessment.isLoading) {
    return <LoadingPanel title="Abrindo o Plano da Auditoria…" />;
  }
  if (planQ.isError && isForbidden(planQ.error)) {
    return <AccessDeniedPanel />;
  }
  if (!local) {
    return <LoadingPanel title="Preparando o plano…" />;
  }

  const readiness = local.readiness;
  const pendingByKey = Object.fromEntries(
    readiness.items.filter((i) => !i.done).map((i) => [i.key, i.label]),
  );
  const openingSatisfied = (scheduleQ.data?.items ?? []).some(
    (i) =>
      i.plan_activity_kind === "opening_meeting" &&
      (i.status === "completed" || i.status === "waived"),
  );

  return (
    <div className="space-y-6" data-testid="audit-plan-page">
      <JourneyBar
        status={dash.status}
        percent={dash.percent}
        pendingCount={dash.pending.length}
        pending={dash.pending}
        assessmentId={assessmentId}
        preparationReady={dash.preparationReady}
      />

      <AssessmentSectionNav assessmentId={assessmentId} />

      <p className="text-sm text-[var(--qm-muted)]">
        <Link to="/assessments" className="hover:underline">
          Minhas avaliações
        </Link>
        {" / "}
        <Link to={`/assessments/${assessmentId}`} className="hover:underline">
          Visão geral
        </Link>
        {" / "}
        Plano da Auditoria
      </p>

      <PageHeader
        title="Plano da Auditoria"
        explanation="O plano organiza o propósito, o percurso e as pessoas envolvidas. Ele evita entrevistas improvisadas e ajuda todos a saber o que acontecerá."
        expectedResult="Documento operacional claro antes do início em campo."
        progress={`${readiness.percent}% do checklist · ${planStatusLabel(local.plan_status)}`}
        nextStep={readiness.next_action}
      />

      {error ? <ApiErrorBanner error={error} /> : null}

      <div
        className="grid gap-3 sm:grid-cols-4"
        data-testid="audit-plan-readiness"
      >
        <Stat label="Concluídos" value={String(readiness.completed_count)} />
        <Stat label="Pendentes" value={String(readiness.pending_count)} />
        <Stat label="Checklist" value={`${readiness.percent}%`} />
        <Stat label="Situação" value={planStatusLabel(local.plan_status)} />
      </div>

      {readiness.blockers.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {readiness.blockers.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      ) : null}

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <SaveHint state={saveState} />
        {!readOnly ? (
          <button
            type="button"
            className="qm-btn-secondary"
            disabled={refresh.isPending}
            onClick={() => void refresh.mutateAsync(false)}
          >
            Completar vazios com a preparação
          </button>
        ) : (
          <p className="text-[var(--qm-muted)]">Visualização — sem edição nesta fase.</p>
        )}
      </div>

      {readyInfo ? (
        <p
          className="rounded-md border border-qmind-semantic-success/30 bg-qmind-semantic-success/10 px-3 py-2 text-sm"
          data-testid="audit-plan-ready-info"
        >
          {readyInfo}
        </p>
      ) : null}

      <AuditPlanHandoffPanel
        assessmentId={assessmentId}
        plan={local}
        assessmentStatus={assessment.data?.status}
        canMutate={!!perms.canMutate && assessment.data?.status !== "cancelled"}
        openingSatisfied={openingSatisfied}
        onError={setError}
        onPlanUpdated={(p) => {
          setLocal(p);
          if (p.plan_status === "ready") {
            setReadyInfo(
              "O plano está completo e pronto para ser formalizado. A próxima etapa confirmará o planejamento da avaliação.",
            );
          }
        }}
      />

      {needsReason && !readOnly ? (
        <label className="block space-y-1.5">
          <span className="text-sm font-semibold text-[var(--qm-ink)]">
            Motivo do ajuste / emenda (obrigatório)
          </span>
          <input
            className="qm-field"
            value={amendmentReason}
            data-testid="audit-plan-amendment-reason"
            onChange={(e) => setAmendmentReason(e.target.value)}
            placeholder="Ex.: mudança de turno da planta visitada"
          />
        </label>
      ) : null}

      <Block
        title="1. Propósito"
        objective="Deixar claro por que a avaliação acontece e em qual modalidade."
        expected="Objetivo em linguagem de negócio e modalidade."
        example="Realizar auditoria interna do SGQ da planta de São Paulo."
        pending={pendingByKey.objective}
      >
        <label className="block space-y-1.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold">
            Objetivo <SourceBadge source={local.field_sources.objective} />
          </span>
          <textarea
            className="qm-field min-h-24"
            disabled={readOnly}
            value={local.objective}
            data-testid="audit-plan-objective"
            onChange={(e) =>
              scheduleSave({ ...local, objective: e.target.value })
            }
          />
        </label>
        <label className="block space-y-1.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold">
            Modalidade <SourceBadge source={local.field_sources.modality} />
          </span>
          <select
            className="qm-field"
            disabled={readOnly}
            value={local.modality}
            onChange={(e) =>
              scheduleSave({
                ...local,
                modality: e.target.value as AuditPlanModality,
              })
            }
          >
            {MODALITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-[var(--qm-muted)]">
            O QMind organiza a avaliação; não é certificadora.
          </p>
        </label>
      </Block>

      <Block
        title="2. Escopo e critérios"
        objective="Delimitar o que entra na avaliação e com base em quais critérios."
        expected="Escopo textual e ao menos um critério marcado."
        example="ISO 9001:2015 + processos internos da produção."
        pending={pendingByKey.scope || pendingByKey.criteria}
      >
        <label className="block space-y-1.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold">
            Escopo <SourceBadge source={local.field_sources.scope_text} />
          </span>
          <textarea
            className="qm-field min-h-28"
            disabled={readOnly}
            value={local.scope_text}
            onChange={(e) =>
              scheduleSave({ ...local, scope_text: e.target.value })
            }
          />
        </label>
        <CriteriaEditor
          value={local.criteria}
          disabled={readOnly}
          onChange={(criteria) => scheduleSave({ ...local, criteria })}
        />
      </Block>

      <Block
        title="3. Processos e locais"
        objective="Indicar onde a avaliação ocorrerá e quais processos serão visitados."
        expected="Ao menos um processo; unidades quando aplicável."
        example="Produção — Planta 1; Compras — escritório central."
        pending={pendingByKey.processes}
      >
        <label className="block space-y-1.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold">
            Processos (um por linha: Nome — responsável)
            <SourceBadge source={local.field_sources.processes} />
          </span>
          <textarea
            className="qm-field min-h-24"
            disabled={readOnly}
            value={listToText(local.processes)}
            onChange={(e) =>
              scheduleSave({
                ...local,
                processes: textToProcesses(e.target.value, local.processes),
              })
            }
          />
        </label>
        <label className="block space-y-1.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold">
            Unidades e locais (um por linha: Nome — localização)
            <SourceBadge source={local.field_sources.sites} />
          </span>
          <textarea
            className="qm-field min-h-20"
            disabled={readOnly}
            value={listToText(local.sites)}
            onChange={(e) =>
              scheduleSave({
                ...local,
                sites: textToSites(e.target.value, local.sites),
              })
            }
          />
        </label>
      </Block>

      <Block
        title="4. Pessoas envolvidas"
        objective="Definir quem conduz e quem representa a organização."
        expected="Auditor líder obrigatório; equipe e representantes quando possível."
        example="Líder: consultor interno; representante: gerente da qualidade."
        pending={pendingByKey.lead}
      >
        <label className="block space-y-1.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold">
            Auditor líder <SourceBadge source={local.field_sources.lead_membership_id} />
          </span>
          <select
            className="qm-field"
            disabled={readOnly}
            value={local.lead_membership_id ?? ""}
            data-testid="audit-plan-lead"
            onChange={(e) =>
              scheduleSave({
                ...local,
                lead_membership_id: e.target.value || null,
              })
            }
          >
            <option value="">Selecione…</option>
            {(team.data ?? []).map((m) => (
              <option key={m.membership_id} value={m.membership_id}>
                {m.label || m.membership_id.slice(0, 8)} ({m.team_role})
              </option>
            ))}
          </select>
        </label>
        <RepresentativesEditor
          value={local.org_representatives}
          disabled={readOnly}
          onChange={(org_representatives) =>
            scheduleSave({ ...local, org_representatives })
          }
        />
      </Block>

      <Block
        title="5. Período"
        objective="Combinar quando a avaliação deve começar e terminar."
        expected="Datas de início e término válidas."
        example="01/09/2026 a 05/09/2026."
        pending={pendingByKey.period || pendingByKey.period_order}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block space-y-1.5">
            <span className="text-sm font-semibold">Início previsto</span>
            <input
              type="date"
              className="qm-field"
              disabled={readOnly}
              value={local.planned_start ?? ""}
              data-testid="audit-plan-start"
              onChange={(e) =>
                scheduleSave({
                  ...local,
                  planned_start: e.target.value || null,
                })
              }
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-semibold">Término previsto</span>
            <input
              type="date"
              className="qm-field"
              disabled={readOnly}
              value={local.planned_end ?? ""}
              data-testid="audit-plan-end"
              onChange={(e) =>
                scheduleSave({
                  ...local,
                  planned_end: e.target.value || null,
                })
              }
            />
          </label>
        </div>
      </Block>

      <AuditPlanScheduleSection
        assessmentId={assessmentId}
        readOnly={readOnly}
        processNames={local.processes.map((p) => p.name).filter(Boolean)}
        leadMembershipId={local.lead_membership_id}
        teamMembers={(team.data ?? []).map((m) => ({
          membership_id: m.membership_id,
          label: m.label,
          team_role: m.team_role,
        }))}
      />

      <Block
        title="6. Preparação e cuidados"
        objective="Registrar o que precisa estar pronto e riscos operacionais."
        expected="Notas úteis para a equipe — opcional, mas recomendado."
        example="Reservar sala de reunião; acesso a registros de produção."
      >
        <label className="block space-y-1.5">
          <span className="text-sm font-semibold">Observações de preparação</span>
          <textarea
            className="qm-field min-h-20"
            disabled={readOnly}
            value={local.preparation_notes}
            onChange={(e) =>
              scheduleSave({ ...local, preparation_notes: e.target.value })
            }
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-semibold">Riscos ou cuidados</span>
          <textarea
            className="qm-field min-h-20"
            disabled={readOnly}
            value={local.risks_notes}
            onChange={(e) =>
              scheduleSave({ ...local, risks_notes: e.target.value })
            }
          />
        </label>
      </Block>

      <Block
        title="7. Revisão do plano"
        objective="Conferir se o plano está pronto para orientar a execução."
        expected="Checklist completo; situação ready quando aplicável."
        example="Próxima ação: confirmar planejamento da avaliação no mapa."
      >
        <ul className="space-y-2 text-sm">
          {readiness.items.map((item) => (
            <li
              key={item.key}
              className="flex items-center justify-between gap-2 rounded border border-[var(--qm-line)] px-3 py-2"
            >
              <span>{item.label}</span>
              <span
                className={
                  item.done
                    ? "font-semibold text-qmind-semantic-success"
                    : "font-semibold text-[var(--qm-accent)]"
                }
              >
                {item.done ? "Ok" : "Pendente"}
              </span>
            </li>
          ))}
        </ul>
        <p className="text-sm text-[var(--qm-muted)]">
          Próxima ação recomendada: <strong>{readiness.next_action}</strong>
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to={`/assessments/${assessmentId}`} className="qm-btn-primary">
            Ir ao Mapa do Percurso
          </Link>
          {assessment.data?.status === "in_progress" ? (
            <Link
              to={`/assessments/${assessmentId}/work`}
              className="qm-btn-secondary"
            >
              Ir à Execução em campo
            </Link>
          ) : null}
        </div>
      </Block>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--qm-line)] px-3 py-2">
      <p className="text-lg font-semibold text-[var(--qm-ink)]">{value}</p>
      <p className="text-[11px] text-[var(--qm-muted)]">{label}</p>
    </div>
  );
}

function SaveHint({ state }: { state: SaveState }) {
  if (state === "saving") return <span className="text-[var(--qm-muted)]">Salvando…</span>;
  if (state === "saved")
    return <span className="text-qmind-semantic-success">✓ Salvo</span>;
  if (state === "error")
    return <span className="text-qmind-semantic-danger">Erro ao salvar</span>;
  return <span className="text-[var(--qm-muted)]">Autosave ativo</span>;
}

function CriteriaEditor({
  value,
  disabled,
  onChange,
}: {
  value: AuditPlanCriteria;
  disabled?: boolean;
  onChange: (c: AuditPlanCriteria) => void;
}) {
  return (
    <div className="space-y-2 text-sm">
      <p className="font-semibold text-[var(--qm-ink)]">Critérios</p>
      {(
        [
          ["iso9001_2015", "ISO 9001:2015"],
          ["internal_processes", "Processos internos"],
          ["legal_contractual", "Requisitos legais ou contratuais informados"],
        ] as const
      ).map(([key, label]) => (
        <label key={key} className="flex items-center gap-2">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value[key]}
            onChange={(e) => onChange({ ...value, [key]: e.target.checked })}
          />
          {label}
        </label>
      ))}
      {value.legal_contractual ? (
        <textarea
          className="qm-field min-h-16"
          disabled={disabled}
          placeholder="Descreva os requisitos legais/contratuais"
          value={value.legal_contractual_text}
          onChange={(e) =>
            onChange({ ...value, legal_contractual_text: e.target.value })
          }
        />
      ) : null}
      <textarea
        className="qm-field min-h-16"
        disabled={disabled}
        placeholder="Critérios adicionais (texto livre)"
        value={value.additional_text}
        onChange={(e) => onChange({ ...value, additional_text: e.target.value })}
      />
    </div>
  );
}

function RepresentativesEditor({
  value,
  disabled,
  onChange,
}: {
  value: OrgRepresentative[];
  disabled?: boolean;
  onChange: (v: OrgRepresentative[]) => void;
}) {
  const text = value
    .map((r) => [r.name, r.role].filter(Boolean).join(" — "))
    .join("\n");
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold">
        Representantes da organização (um por linha: Nome — papel)
      </span>
      <textarea
        className="qm-field min-h-20"
        disabled={disabled}
        value={text}
        onChange={(e) => {
          const next = e.target.value
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => {
              const [name, role = ""] = line.split("—").map((s) => s.trim());
              return { name: name || line, role, notes: "" };
            });
          onChange(next);
        }}
      />
    </label>
  );
}

function isForbidden(err: unknown): boolean {
  return err instanceof QmindApiError && (err.status === 403 || err.status === 401);
}
