import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAgendaBoard, useAgendaMutations } from "@/hooks/useAgendaBoard";
import { useAssessments } from "@/hooks/useAssessments";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { GuidedEmptyState, StatusBadge } from "@/components/qm";
import { ScheduleActivityModal } from "@/components/ScheduleActivityModal";
import type { AgendaEvent } from "@/api/agendaApi";
import { labelAssessmentType } from "@/lib/labels";

const TYPE_LABEL: Record<string, string> = {
  interview: "Entrevista",
  meeting: "Reunião",
  visit: "Visita",
  reminder: "Lembrete",
  milestone: "Marco",
  deadline: "Prazo",
  other: "Compromisso",
};

const STATUS_LABEL: Record<string, string> = {
  scheduled: "Agendado",
  completed: "Concluído",
  cancelled: "Cancelado",
};

function todayIsoInTz(tz: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

function formatTime(iso: string, tz: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      timeZone: tz,
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return "—";
  }
}

function formatDayLabel(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  if (!y || !m || !d) return isoDate;
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(y, m - 1, d));
}

function shiftMonth(isoDate: string, delta: number): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  const dt = new Date(y, m - 1 + delta, 1);
  const day = Math.min(d, 28);
  dt.setDate(day);
  const yy = dt.getFullYear();
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  const dd = String(dt.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function monthGrid(isoDate: string): { date: string; inMonth: boolean }[] {
  const [y, m] = isoDate.split("-").map(Number);
  const first = new Date(y, m - 1, 1);
  const startPad = (first.getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(y, m, 0).getDate();
  const cells: { date: string; inMonth: boolean }[] = [];
  for (let i = 0; i < startPad; i++) {
    const dt = new Date(y, m - 1, 1 - (startPad - i));
    cells.push({
      date: `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`,
      inMonth: false,
    });
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({
      date: `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
      inMonth: true,
    });
  }
  while (cells.length % 7 !== 0) {
    const last = cells[cells.length - 1];
    const [ly, lm, ld] = last.date.split("-").map(Number);
    const dt = new Date(ly, lm - 1, ld + 1);
    cells.push({
      date: `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`,
      inMonth: false,
    });
  }
  return cells;
}

function EventRow({
  event,
  tz,
  onOpen,
  onComplete,
  onCancel,
  canMutate,
}: {
  event: AgendaEvent;
  tz: string;
  onOpen: (e: AgendaEvent) => void;
  onComplete: (id: string) => void;
  onCancel: (id: string) => void;
  canMutate: boolean;
}) {
  return (
    <li
      className={`org-agenda__event ${event.is_overdue ? "org-agenda__event--overdue" : ""}`}
      data-testid="agenda-event"
    >
      <button
        type="button"
        className="org-agenda__event-main"
        onClick={() => onOpen(event)}
      >
        <span className="org-agenda__event-time" aria-hidden="true">
          {formatTime(event.starts_at, tz)}
        </span>
        <span className="min-w-0 text-left">
          <span className="block font-semibold text-[var(--qm-ink)]">
            {event.title}
          </span>
          <span className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-[var(--qm-muted)]">
            <span>{TYPE_LABEL[event.event_type] ?? event.event_type}</span>
            {event.assessment_label ? (
              <span>· {event.assessment_label}</span>
            ) : null}
            {event.owner_label ? <span>· {event.owner_label}</span> : null}
            <StatusBadge
              label={
                event.is_overdue
                  ? "Atrasado"
                  : (STATUS_LABEL[event.status] ?? event.status)
              }
              tone={event.is_overdue ? "risk" : "neutral"}
            />
            {event.is_auto ? <span aria-label="Automático">· Auto</span> : null}
          </span>
        </span>
      </button>
      <div className="org-agenda__event-actions">
        {event.primary_action_href ? (
          <Link to={event.primary_action_href} className="qm-btn-primary text-sm">
            {event.primary_action_label}
          </Link>
        ) : (
          <span className="text-sm text-[var(--qm-muted)]">
            {event.primary_action_label}
          </span>
        )}
        {canMutate && event.status === "scheduled" ? (
          <>
            <button
              type="button"
              className="qm-btn-secondary text-sm"
              onClick={() => onComplete(event.id)}
            >
              Concluir
            </button>
            <button
              type="button"
              className="text-sm text-[var(--qm-muted)] underline"
              onClick={() => onCancel(event.id)}
            >
              Cancelar
            </button>
          </>
        ) : null}
      </div>
    </li>
  );
}

export function OrgAgenda() {
  const perms = useAssessmentPermissions();
  const assessments = useAssessments();
  const [selectedDate, setSelectedDate] = useState(() =>
    todayIsoInTz("America/Sao_Paulo"),
  );
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [detail, setDetail] = useState<AgendaEvent | null>(null);

  const boardQuery = useAgendaBoard(selectedDate);
  const { create, setStatus } = useAgendaMutations(selectedDate);

  const board = boardQuery.data;
  const tz = board?.timezone ?? "America/Sao_Paulo";

  const markerMap = useMemo(() => {
    const m = new Map<string, { count: number; has_overdue: boolean }>();
    for (const mk of board?.month_markers ?? []) {
      m.set(mk.date, { count: mk.count, has_overdue: mk.has_overdue });
    }
    return m;
  }, [board?.month_markers]);

  const cells = useMemo(() => monthGrid(selectedDate), [selectedDate]);
  const monthTitle = useMemo(() => {
    const [y, m] = selectedDate.split("-").map(Number);
    return new Intl.DateTimeFormat("pt-BR", {
      month: "long",
      year: "numeric",
    }).format(new Date(y, m - 1, 1));
  }, [selectedDate]);

  if (boardQuery.isLoading) {
    return <LoadingPanel title="Carregando agenda da organização…" />;
  }

  if (boardQuery.isError) {
    return (
      <ApiErrorBanner
        title="Não foi possível carregar a agenda"
        error={boardQuery.error}
        onRetry={() => void boardQuery.refetch()}
      />
    );
  }

  if (!board) {
    return null;
  }

  const today = todayIsoInTz(tz);

  return (
    <section className="org-agenda" data-testid="org-agenda">
      <header className="org-agenda__header">
        <div>
          <h2 className="font-display text-xl font-semibold text-[var(--qm-ink)]">
            Agenda da organização
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-[var(--qm-muted)]">
            Aqui você vê o que acontece nas avaliações: entrevistas, marcos e
            prazos — com data, horário e a ação que precisa executar.
          </p>
        </div>
        {perms.canMutate ? (
          <button
            type="button"
            className="qm-btn-primary shrink-0"
            data-testid="schedule-activity"
            onClick={() => setScheduleOpen(true)}
          >
            Agendar atividade
          </button>
        ) : null}
      </header>

      {board.next_up ? (
        <div className="org-agenda__next" data-testid="agenda-next-up">
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--qm-accent)]">
            Próxima atividade
          </p>
          <p className="mt-1 text-lg font-semibold text-[var(--qm-ink)]">
            {board.next_up.title}
          </p>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            {formatTime(board.next_up.starts_at, tz)}
            {board.next_up.is_overdue ? " · Atrasada" : ""}
            {board.next_up.assessment_label
              ? ` · ${board.next_up.assessment_label}`
              : ""}
          </p>
          {board.next_up.primary_action_href ? (
            <Link
              to={board.next_up.primary_action_href}
              className="qm-btn-primary mt-3 inline-flex text-sm"
            >
              {board.next_up.primary_action_label}
            </Link>
          ) : null}
        </div>
      ) : null}

      <div className="org-agenda__layout">
        <div className="org-agenda__calendar" data-testid="agenda-calendar">
          <div className="org-agenda__cal-nav">
            <button
              type="button"
              className="qm-btn-secondary text-sm"
              onClick={() => setSelectedDate((d) => shiftMonth(d, -1))}
              aria-label="Mês anterior"
            >
              ←
            </button>
            <p className="font-semibold capitalize text-[var(--qm-ink)]">
              {monthTitle}
            </p>
            <button
              type="button"
              className="qm-btn-secondary text-sm"
              onClick={() => setSelectedDate((d) => shiftMonth(d, 1))}
              aria-label="Próximo mês"
            >
              →
            </button>
          </div>
          <div className="org-agenda__weekdays" aria-hidden="true">
            {["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"].map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
          <div className="org-agenda__days" role="grid" aria-label="Calendário mensal">
            {cells.map((cell) => {
              const marker = markerMap.get(cell.date);
              const selected = cell.date === selectedDate;
              const isToday = cell.date === today;
              return (
                <button
                  key={cell.date}
                  type="button"
                  role="gridcell"
                  aria-selected={selected}
                  aria-label={`${cell.date}${marker ? `, ${marker.count} atividades` : ""}${marker?.has_overdue ? ", com atraso" : ""}`}
                  className={[
                    "org-agenda__day",
                    cell.inMonth ? "" : "org-agenda__day--muted",
                    selected ? "org-agenda__day--selected" : "",
                    isToday ? "org-agenda__day--today" : "",
                    marker ? "org-agenda__day--has-events" : "",
                    marker?.has_overdue ? "org-agenda__day--has-overdue" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={() => setSelectedDate(cell.date)}
                >
                  <span>{Number(cell.date.slice(-2))}</span>
                  {marker ? (
                    <span
                      className="org-agenda__dot"
                      title={`${marker.count} atividade(s)${marker.has_overdue ? " · com atraso" : ""}`}
                    >
                      {marker.has_overdue ? "!" : "•"}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-[var(--qm-muted)]">
            Fuso: {tz}. Dias com • têm atividades; ! indica atraso.
          </p>
        </div>

        <div className="org-agenda__day-panel" data-testid="agenda-day-panel">
          <h3 className="font-semibold capitalize text-[var(--qm-ink)]">
            {formatDayLabel(selectedDate)}
          </h3>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Atividades ordenadas por horário. Toque para ver orientação e a ação
            recomendada.
          </p>

          {board.selected_day.length === 0 ? (
            <div className="mt-4">
              <GuidedEmptyState
                title="Nenhuma atividade neste dia"
                why="A agenda organiza entrevistas, marcos e prazos das avaliações — não é um calendário genérico da empresa."
                example="Ex.: “Entrevista com o responsável do processo” às 10h, ou “Marco: início da avaliação”."
                howToStart={
                  perms.canMutate
                    ? "Toque em “Agendar atividade” para criar a primeira. Eventos da jornada também podem aparecer automaticamente quando houver data confiável."
                    : "Quando houver datas nas avaliações, os eventos aparecem aqui automaticamente."
                }
                action={
                  perms.canMutate
                    ? {
                        label: "Agendar atividade",
                        onClick: () => setScheduleOpen(true),
                      }
                    : undefined
                }
              />
            </div>
          ) : (
            <ol className="org-agenda__timeline mt-4">
              {board.selected_day.map((ev) => (
                <EventRow
                  key={ev.id}
                  event={ev}
                  tz={tz}
                  canMutate={perms.canMutate}
                  onOpen={setDetail}
                  onComplete={(id) =>
                    void setStatus.mutateAsync({ eventId: id, status: "completed" })
                  }
                  onCancel={(id) =>
                    void setStatus.mutateAsync({ eventId: id, status: "cancelled" })
                  }
                />
              ))}
            </ol>
          )}
        </div>
      </div>

      {(board.today.length > 0 || board.overdue.length > 0) && (
        <div className="org-agenda__strips">
          {board.today.length > 0 ? (
            <div>
              <h3 className="text-sm font-semibold text-[var(--qm-ink)]">
                Hoje
              </h3>
              <ul className="mt-2 space-y-1 text-sm text-[var(--qm-muted)]">
                {board.today.map((ev) => (
                  <li key={ev.id}>
                    {formatTime(ev.starts_at, tz)} — {ev.title}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {board.overdue.length > 0 ? (
            <div data-testid="agenda-overdue">
              <h3 className="text-sm font-semibold text-[var(--qm-ink)]">
                Pendências atrasadas
              </h3>
              <ul className="mt-2 space-y-1 text-sm">
                {board.overdue.map((ev) => (
                  <li key={ev.id} className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-[var(--qm-ink)]">
                      {ev.title}
                    </span>
                    <span className="text-xs uppercase tracking-wide text-[var(--qm-risk)]">
                      Atrasado
                    </span>
                    {ev.primary_action_href ? (
                      <Link
                        to={ev.primary_action_href}
                        className="text-sm font-semibold text-[var(--qm-accent)] underline"
                      >
                        {ev.primary_action_label}
                      </Link>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}

      {board.in_progress_assessments.length > 0 ? (
        <div className="org-agenda__in-progress">
          <h3 className="text-sm font-semibold text-[var(--qm-ink)]">
            Avaliações em andamento
          </h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {board.in_progress_assessments.map((a) => (
              <li key={a.id}>
                <Link to={a.href} className="org-agenda__chip">
                  {a.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {detail ? (
        <div
          className="org-agenda__modal-backdrop"
          role="presentation"
          onClick={() => setDetail(null)}
        >
          <div
            className="org-agenda__modal"
            role="dialog"
            aria-labelledby="agenda-event-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="agenda-event-title" className="text-lg font-semibold">
              {detail.title}
            </h3>
            <p className="mt-2 text-sm text-[var(--qm-muted)]">
              {detail.guidance || "Esta atividade faz parte do trabalho da avaliação."}
            </p>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="font-semibold text-[var(--qm-ink)]">
                  O que acontecerá
                </dt>
                <dd className="mt-1 text-[var(--qm-muted)]">
                  {TYPE_LABEL[detail.event_type]} em{" "}
                  {formatTime(detail.starts_at, tz)}
                  {detail.location_or_link
                    ? ` · ${detail.location_or_link}`
                    : ""}
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-[var(--qm-ink)]">
                  Por que é importante
                </dt>
                <dd className="mt-1 text-[var(--qm-muted)]">
                  {detail.why_it_matters}
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-[var(--qm-ink)]">
                  Preparação necessária
                </dt>
                <dd className="mt-1 text-[var(--qm-muted)]">
                  {detail.preparation}
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-[var(--qm-ink)]">
                  Ação recomendada
                </dt>
                <dd className="mt-1 text-[var(--qm-muted)]">
                  {detail.primary_action_label}
                </dd>
              </div>
            </dl>
            <div className="mt-5 flex flex-wrap gap-2">
              {detail.primary_action_href ? (
                <Link
                  to={detail.primary_action_href}
                  className="qm-btn-primary text-sm"
                >
                  {detail.primary_action_label}
                </Link>
              ) : null}
              <button
                type="button"
                className="qm-btn-secondary text-sm"
                onClick={() => setDetail(null)}
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {scheduleOpen ? (
        <ScheduleActivityModal
          timezone={tz}
          assessments={(assessments.data ?? []).map((a) => ({
            id: a.id,
            label: labelAssessmentType(a.type),
          }))}
          defaultDate={selectedDate}
          busy={create.isPending}
          error={create.error}
          onClose={() => setScheduleOpen(false)}
          onSubmit={async (payload) => {
            await create.mutateAsync(payload);
            setScheduleOpen(false);
          }}
        />
      ) : null}
    </section>
  );
}
