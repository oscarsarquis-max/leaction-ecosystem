import { useState } from "react";
import type { AgendaEventCreate, AgendaEventType } from "@/api/agendaApi";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";

type AssessmentOption = { id: string; label: string };

type Props = {
  timezone: string;
  assessments: AssessmentOption[];
  defaultDate: string;
  busy: boolean;
  error: unknown;
  onClose: () => void;
  onSubmit: (payload: AgendaEventCreate) => Promise<void>;
};

const TYPES: { value: AgendaEventType; label: string }[] = [
  { value: "interview", label: "Entrevista" },
  { value: "milestone", label: "Marco" },
  { value: "meeting", label: "Reunião" },
  { value: "visit", label: "Visita" },
  { value: "reminder", label: "Lembrete" },
  { value: "deadline", label: "Prazo" },
  { value: "other", label: "Outro compromisso" },
];

/** Convert wall clock in organization timezone to UTC ISO. */
function toIsoLocal(date: string, time: string, tz: string): string {
  const desired = `${date}T${time}:00`;
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  let guess = Date.parse(`${desired}Z`);
  for (let i = 0; i < 4; i++) {
    const parts = Object.fromEntries(
      fmt.formatToParts(new Date(guess)).map((p) => [p.type, p.value]),
    );
    const hour = parts.hour === "24" ? "00" : parts.hour;
    const asInTz = `${parts.year}-${parts.month}-${parts.day}T${hour}:${parts.minute}:${parts.second}`;
    const delta = Date.parse(`${desired}Z`) - Date.parse(`${asInTz}Z`);
    guess += delta;
    if (delta === 0) break;
  }
  return new Date(guess).toISOString();
}

export function ScheduleActivityModal({
  timezone,
  assessments,
  defaultDate,
  busy,
  error,
  onClose,
  onSubmit,
}: Props) {
  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState<AgendaEventType>("interview");
  const [date, setDate] = useState(defaultDate);
  const [time, setTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [assessmentId, setAssessmentId] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  return (
    <div
      className="org-agenda__modal-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="org-agenda__modal org-agenda__modal--wide"
        role="dialog"
        aria-labelledby="schedule-title"
        data-testid="schedule-activity-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="schedule-title" className="text-lg font-semibold text-[var(--qm-ink)]">
          Agendar atividade
        </h3>
        <p className="mt-1 text-sm text-[var(--qm-muted)]">
          Crie uma entrevista, marco ou outro compromisso ligado à avaliação.
          Horários usam o fuso {timezone}.
        </p>

        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setLocalError(null);
            if (!title.trim()) {
              setLocalError("Informe um título curto do que vai acontecer.");
              return;
            }
            const starts_at = toIsoLocal(date, time, timezone);
            const ends_at = endTime ? toIsoLocal(date, endTime, timezone) : null;
            void onSubmit({
              title: title.trim(),
              description: description.trim(),
              event_type: eventType,
              starts_at,
              ends_at,
              timezone,
              assessment_id: assessmentId || null,
              location_or_link: location.trim(),
              guidance:
                eventType === "interview"
                  ? "Combine horário e confirme quem será entrevistado."
                  : eventType === "milestone"
                    ? "Revise o que falta para considerar este marco concluído."
                    : "",
            });
          }}
        >
          <label className="sm:col-span-2">
            <span className="text-sm font-semibold text-[var(--qm-ink)]">Título</span>
            <input
              className="qm-field mt-1 w-full"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex.: Entrevista com responsável do processo"
              required
            />
          </label>

          <label>
            <span className="text-sm font-semibold text-[var(--qm-ink)]">Tipo</span>
            <select
              className="qm-field mt-1 w-full"
              value={eventType}
              onChange={(e) => setEventType(e.target.value as AgendaEventType)}
            >
              {TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="text-sm font-semibold text-[var(--qm-ink)]">
              Avaliação relacionada
            </span>
            <select
              className="qm-field mt-1 w-full"
              value={assessmentId}
              onChange={(e) => setAssessmentId(e.target.value)}
            >
              <option value="">Sem vínculo direto</option>
              {assessments.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="text-sm font-semibold text-[var(--qm-ink)]">Data</span>
            <input
              type="date"
              className="qm-field mt-1 w-full"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </label>

          <div className="grid grid-cols-2 gap-2">
            <label>
              <span className="text-sm font-semibold text-[var(--qm-ink)]">Início</span>
              <input
                type="time"
                className="qm-field mt-1 w-full"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                required
              />
            </label>
            <label>
              <span className="text-sm font-semibold text-[var(--qm-ink)]">Término</span>
              <input
                type="time"
                className="qm-field mt-1 w-full"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
              />
            </label>
          </div>

          <label className="sm:col-span-2">
            <span className="text-sm font-semibold text-[var(--qm-ink)]">
              Descrição breve
            </span>
            <textarea
              className="qm-field mt-1 w-full"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="O que precisa ficar claro para quem for executar"
            />
          </label>

          <label className="sm:col-span-2">
            <span className="text-sm font-semibold text-[var(--qm-ink)]">
              Local ou link
            </span>
            <input
              className="qm-field mt-1 w-full"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Sala, planta ou link da reunião"
            />
          </label>

          {localError ? (
            <p className="sm:col-span-2 text-sm text-[var(--qm-risk)]">{localError}</p>
          ) : null}
          {error ? (
            <div className="sm:col-span-2">
              <ApiErrorBanner title="Não foi possível agendar" error={error} />
            </div>
          ) : null}

          <div className="sm:col-span-2 mt-2 flex flex-wrap gap-2">
            <button
              type="submit"
              className="qm-btn-primary"
              disabled={busy}
              data-testid="schedule-submit"
            >
              {busy ? "Salvando…" : "Salvar atividade"}
            </button>
            <button
              type="button"
              className="qm-btn-secondary"
              onClick={onClose}
              disabled={busy}
            >
              Voltar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
