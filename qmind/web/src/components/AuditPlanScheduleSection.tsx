import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useAuditPlanSchedule,
  useCreatePlannedInterview,
  useCreateScheduleMeeting,
  useCreateScheduleMilestone,
  useStartInterview,
} from "@/hooks/useAuditPlanSchedule";
import type { ScheduleItem } from "@/api/auditPlanScheduleTypes";

type TeamMember = {
  membership_id: string;
  label?: string | null;
  team_role?: string | null;
};

function kindLabel(item: ScheduleItem): string {
  if (item.kind === "interview") return "Entrevista";
  if (item.plan_activity_kind === "opening_meeting") return "Abertura";
  if (item.plan_activity_kind === "closing_meeting") return "Encerramento";
  if (item.kind === "meeting") return "Reunião";
  return "Marco";
}

function formatWhen(iso: string | null | undefined, tz: string): string {
  if (!iso) return "Horário a definir";
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      timeZone: tz || "America/Sao_Paulo",
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function toLocalInputValue(d = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function localInputToIso(value: string): string {
  return new Date(value).toISOString();
}

export function AuditPlanScheduleSection({
  assessmentId,
  readOnly,
  processNames,
  leadMembershipId,
  teamMembers,
}: {
  assessmentId: string;
  readOnly?: boolean;
  processNames: string[];
  leadMembershipId?: string | null;
  teamMembers: TeamMember[];
}) {
  const scheduleQ = useAuditPlanSchedule(assessmentId);
  const createMeeting = useCreateScheduleMeeting(assessmentId);
  const createMilestone = useCreateScheduleMilestone(assessmentId);
  const createInterview = useCreatePlannedInterview(assessmentId);
  const startIv = useStartInterview(assessmentId);
  const [searchParams, setSearchParams] = useSearchParams();
  const [error, setError] = useState<unknown>(null);
  const [form, setForm] = useState<"closed" | "interview" | "meeting" | "milestone">(
    "closed",
  );
  const [meetingKind, setMeetingKind] = useState<
    "opening_meeting" | "closing_meeting" | "additional_meeting"
  >("opening_meeting");
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [processName, setProcessName] = useState("");
  const [orgContact, setOrgContact] = useState("");
  const [whenLocal, setWhenLocal] = useState(toLocalInputValue());
  const [duration, setDuration] = useState(60);
  const [location, setLocation] = useState("");
  const [remote, setRemote] = useState("");
  const [preparation, setPreparation] = useState("");
  const [outsideJust, setOutsideJust] = useState("");

  const schedule = scheduleQ.data;
  const tz = schedule?.timezone || "America/Sao_Paulo";

  const startInterviewId = searchParams.get("startInterview");
  useEffect(() => {
    if (!startInterviewId || readOnly) return;
    void startIv
      .mutateAsync(startInterviewId)
      .then(() => {
        const next = new URLSearchParams(searchParams);
        next.delete("startInterview");
        setSearchParams(next, { replace: true });
      })
      .catch((err) => setError(err));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-shot from agenda deep link
  }, [startInterviewId]);

  const interviews = useMemo(
    () => (schedule?.items ?? []).filter((i) => i.kind === "interview"),
    [schedule?.items],
  );
  const meetings = useMemo(
    () => (schedule?.items ?? []).filter((i) => i.kind === "meeting"),
    [schedule?.items],
  );
  const milestones = useMemo(
    () => (schedule?.items ?? []).filter((i) => i.kind === "milestone"),
    [schedule?.items],
  );

  async function submitInterview() {
    try {
      setError(null);
      await createInterview.mutateAsync({
        title: title.trim() || "Entrevista",
        objective,
        process_name: processName,
        org_contact_name: orgContact,
        interviewer_membership_id: leadMembershipId ?? undefined,
        scheduled_at: localInputToIso(whenLocal),
        duration_minutes: duration,
        location,
        remote_link: remote,
        preparation,
        outside_period_justification: outsideJust,
        mode: remote ? "remote" : "onsite",
      });
      setForm("closed");
      setTitle("");
      setObjective("");
    } catch (err) {
      setError(err);
    }
  }

  async function submitMeeting() {
    try {
      setError(null);
      await createMeeting.mutateAsync({
        kind: meetingKind,
        title: title.trim() || undefined,
        objective,
        starts_at: localInputToIso(whenLocal),
        duration_minutes: duration,
        location_or_link: [location, remote].filter(Boolean).join(" | "),
        preparation,
        owner_membership_id: leadMembershipId ?? undefined,
        outside_period_justification: outsideJust,
        timezone: tz,
      });
      setForm("closed");
    } catch (err) {
      setError(err);
    }
  }

  async function submitMilestone() {
    try {
      setError(null);
      await createMilestone.mutateAsync({
        kind: "milestone_custom",
        title: title.trim() || "Marco personalizado",
        notes: objective,
        occurs_at: localInputToIso(whenLocal),
        owner_membership_id: leadMembershipId ?? undefined,
        outside_period_justification: outsideJust,
        timezone: tz,
      });
      setForm("closed");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <section
      className="space-y-4 rounded-lg border border-[var(--qm-line)] bg-[var(--qm-surface)] p-4"
      data-testid="audit-plan-schedule"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--qm-ink)]">
            Programação da auditoria
          </h2>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Quem fará o quê, quando e com qual finalidade — no fuso {tz}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/assessments" className="qm-btn-secondary text-sm">
            Ver na agenda
          </Link>
          {!readOnly ? (
            <button
              type="button"
              className="qm-btn-primary text-sm"
              data-testid="audit-plan-add-activity"
              onClick={() => setForm(form === "closed" ? "interview" : "closed")}
            >
              {form === "closed" ? "Adicionar atividade" : "Fechar formulário"}
            </button>
          ) : null}
        </div>
      </div>

      {error ? <ApiErrorBanner error={error} /> : null}

      {scheduleQ.isLoading ? (
        <p className="text-sm text-[var(--qm-muted)]">Carregando programação…</p>
      ) : null}

      {schedule?.next_action ? (
        <p className="text-sm font-medium text-[var(--qm-ink)]">
          Próxima ação: {schedule.next_action}
        </p>
      ) : null}

      {(schedule?.pendings?.length ?? 0) > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {schedule!.pendings.map((p) => (
            <li key={p.key}>
              {p.label}
              {!p.blocking ? " (aviso)" : ""}
            </li>
          ))}
        </ul>
      ) : null}

      {(schedule?.overlaps?.length ?? 0) > 0 ? (
        <div
          className="rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm"
          data-testid="audit-plan-overlaps"
        >
          <p className="font-semibold">Conflitos de horário (aviso)</p>
          <ul className="mt-1 list-disc pl-5">
            {schedule!.overlaps.map((o, idx) => (
              <li key={`${o.message}-${idx}`}>{o.message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {form !== "closed" && !readOnly ? (
        <div className="space-y-3 rounded-md border border-[var(--qm-line)] p-3">
          <div className="flex flex-wrap gap-2 text-sm">
            {(
              [
                ["interview", "Entrevista"],
                ["meeting", "Reunião"],
                ["milestone", "Marco"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                type="button"
                className={
                  form === k ? "qm-btn-primary text-sm" : "qm-btn-secondary text-sm"
                }
                onClick={() => setForm(k)}
              >
                {label}
              </button>
            ))}
          </div>
          {form === "meeting" ? (
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Tipo de reunião</span>
              <select
                className="qm-field"
                value={meetingKind}
                onChange={(e) =>
                  setMeetingKind(e.target.value as typeof meetingKind)
                }
              >
                <option value="opening_meeting">Abertura</option>
                <option value="closing_meeting">Encerramento</option>
                <option value="additional_meeting">Adicional</option>
              </select>
            </label>
          ) : null}
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Título</span>
            <input
              className="qm-field"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={
                form === "interview"
                  ? "Ex.: Entrevista com Produção"
                  : "Opcional"
              }
            />
          </label>
          {form === "interview" ? (
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Processo</span>
              <select
                className="qm-field"
                value={processName}
                onChange={(e) => setProcessName(e.target.value)}
              >
                <option value="">Selecione…</option>
                {processNames.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">
              {form === "milestone" ? "Notas" : "Objetivo"}
            </span>
            <textarea
              className="qm-field min-h-16"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
            />
          </label>
          {form === "interview" ? (
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Responsável da organização</span>
              <input
                className="qm-field"
                value={orgContact}
                onChange={(e) => setOrgContact(e.target.value)}
              />
            </label>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Data e horário (local)</span>
              <input
                type="datetime-local"
                className="qm-field"
                value={whenLocal}
                onChange={(e) => setWhenLocal(e.target.value)}
              />
            </label>
            {form !== "milestone" ? (
              <label className="block space-y-1 text-sm">
                <span className="font-semibold">Duração (min)</span>
                <input
                  type="number"
                  min={15}
                  className="qm-field"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value) || 60)}
                />
              </label>
            ) : null}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Local</span>
              <input
                className="qm-field"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Link remoto</span>
              <input
                className="qm-field"
                value={remote}
                onChange={(e) => setRemote(e.target.value)}
              />
            </label>
          </div>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Preparação necessária</span>
            <textarea
              className="qm-field min-h-14"
              value={preparation}
              onChange={(e) => setPreparation(e.target.value)}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">
              Justificativa se fora do período do plano
            </span>
            <input
              className="qm-field"
              value={outsideJust}
              onChange={(e) => setOutsideJust(e.target.value)}
            />
          </label>
          {teamMembers.length > 0 ? (
            <p className="text-xs text-[var(--qm-muted)]">
              Entrevistador padrão: líder do plano
              {leadMembershipId
                ? ` (${teamMembers.find((m) => m.membership_id === leadMembershipId)?.label ?? "definido"})`
                : " (defina o auditor responsável acima)"}
              .
            </p>
          ) : null}
          <button
            type="button"
            className="qm-btn-primary"
            disabled={
              createInterview.isPending ||
              createMeeting.isPending ||
              createMilestone.isPending
            }
            onClick={() => {
              if (form === "interview") void submitInterview();
              else if (form === "meeting") void submitMeeting();
              else void submitMilestone();
            }}
          >
            Salvar atividade
          </button>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <ScheduleColumn title="Cronologia" items={schedule?.items ?? []} tz={tz} />
        <ScheduleColumn title="Entrevistas" items={interviews} tz={tz} />
        <div className="space-y-4">
          <ScheduleColumn title="Reuniões" items={meetings} tz={tz} />
          <ScheduleColumn title="Marcos" items={milestones} tz={tz} />
        </div>
      </div>
    </section>
  );
}

function ScheduleColumn({
  title,
  items,
  tz,
}: {
  title: string;
  items: ScheduleItem[];
  tz: string;
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-[var(--qm-ink)]">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--qm-muted)]">Nenhum item.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={`${item.kind}-${item.id}`}
              className="rounded-md border border-[var(--qm-line)] px-3 py-2 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--qm-muted)]">
                  {kindLabel(item)}
                </span>
                <span className="text-[11px] text-[var(--qm-muted)]">{item.status}</span>
              </div>
              <p className="font-medium text-[var(--qm-ink)]">{item.title}</p>
              <p className="text-[var(--qm-muted)]">{formatWhen(item.starts_at, tz)}</p>
              {item.process_name ? (
                <p className="text-[var(--qm-muted)]">Processo: {item.process_name}</p>
              ) : null}
              {item.location_or_link ? (
                <p className="text-[var(--qm-muted)]">Onde: {item.location_or_link}</p>
              ) : null}
              {item.preparation ? (
                <p className="text-[var(--qm-muted)]">Preparação: {item.preparation}</p>
              ) : null}
              {item.objective ? (
                <p className="text-[var(--qm-muted)]">Finalidade: {item.objective}</p>
              ) : null}
              {item.next_action || item.primary_action_label ? (
                <p className="mt-1 font-medium text-[var(--qm-ink)]">
                  {item.next_action || item.primary_action_label}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
