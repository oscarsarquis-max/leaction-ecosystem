import { useMemo, useState } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { canMutateAgileExecution } from "@/lib/permissions";
import { LoadingPanel, EmptyPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useCeremonyRecords,
  useCreateCeremonyAgendaEvent,
  useCreateCeremonyRecord,
  useSprintCeremonyEvents,
  useSprints,
  useSquads,
} from "@/execution/hooks";
import { CEREMONY_TYPE_LABELS, formatShortDate } from "@/execution/labels";
import type { AgendaEventOut, CeremonyType } from "@/execution/api";

function eventLabel(event: AgendaEventOut): string {
  const type = CEREMONY_TYPE_LABELS[event.event_type as CeremonyType] ?? event.event_type;
  return `${event.title} · ${formatShortDate(event.starts_at)} · ${type}`;
}

export function CeremoniesPage() {
  const canMutate = canMutateAgileExecution(useOrganization().currentOrganization?.roles);
  const squadsQuery = useSquads();
  const [squadId, setSquadId] = useState("");
  const sprintsQuery = useSprints(squadId || undefined);
  const [sprintId, setSprintId] = useState("");

  const sprints = useMemo(() => sprintsQuery.data ?? [], [sprintsQuery.data]);
  const sprint = useMemo(
    () => sprints.find((s) => s.id === sprintId),
    [sprints, sprintId],
  );

  const eventsQuery = useSprintCeremonyEvents(sprint);
  const ceremoniesQuery = useCeremonyRecords(sprintId || undefined);
  const createCeremony = useCreateCeremonyRecord(sprintId || "");
  const createEvent = useCreateCeremonyAgendaEvent(sprintId || "");

  const [ceremonyType, setCeremonyType] = useState<CeremonyType>("daily_check_in");
  const [eventMode, setEventMode] = useState<"select" | "create">("select");
  const [selectedEventId, setSelectedEventId] = useState("");
  const [eventTitle, setEventTitle] = useState("");
  const [eventStarts, setEventStarts] = useState("");
  const [summary, setSummary] = useState("");
  const [decisions, setDecisions] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const events = useMemo(() => eventsQuery.data ?? [], [eventsQuery.data]);
  const eventsById = useMemo(() => {
    const map = new Map<string, AgendaEventOut>();
    for (const e of events) map.set(e.id, e);
    return map;
  }, [events]);

  if (squadsQuery.isLoading) {
    return <LoadingPanel title="Carregando cerimônias…" />;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!sprintId || !canMutate) return;
    setError(null);
    setPending(true);
    try {
      let eventId = selectedEventId;
      let recordType = ceremonyType;

      if (eventMode === "create") {
        if (!eventTitle.trim() || !eventStarts) return;
        const created = await createEvent.mutateAsync({
          title: eventTitle.trim(),
          ceremony_type: ceremonyType,
          starts_at: new Date(eventStarts).toISOString(),
          description: `Cerimônia: ${CEREMONY_TYPE_LABELS[ceremonyType]}`,
        });
        eventId = created.id;
      } else {
        const chosen = eventsById.get(selectedEventId);
        if (!chosen) return;
        recordType = chosen.event_type as CeremonyType;
      }

      if (!eventId) return;
      await createCeremony.mutateAsync({
        agenda_event_id: eventId,
        ceremony_type: recordType,
        summary: summary.trim(),
        decisions: decisions.trim(),
        follow_up: followUp.trim(),
      });
      setSummary("");
      setDecisions("");
      setFollowUp("");
      setEventTitle("");
      setEventStarts("");
      setSelectedEventId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível salvar a cerimônia.");
    } finally {
      setPending(false);
    }
  }

  const canSubmit =
    eventMode === "create"
      ? !!eventTitle.trim() && !!eventStarts
      : !!selectedEventId;

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-semibold text-[var(--qm-muted)]">
          Squad
          <select
            className="qm-field mt-1"
            value={squadId}
            onChange={(e) => {
              setSquadId(e.target.value);
              setSprintId("");
              setSelectedEventId("");
            }}
          >
            <option value="">Selecione…</option>
            {(squadsQuery.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold text-[var(--qm-muted)]">
          Sprint
          <select
            className="qm-field mt-1"
            value={sprintId}
            onChange={(e) => {
              setSprintId(e.target.value);
              setSelectedEventId("");
            }}
            disabled={!squadId}
          >
            <option value="">Selecione…</option>
            {sprints.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!sprintId ? (
        <EmptyPanel
          title="Escolha uma sprint"
          message="Cerimônias são registradas no contexto de uma sprint."
          example="Selecione squad e sprint para ver ou registrar planning, daily, review ou retro."
        />
      ) : (
        <>
          {canMutate ? (
            <form
              className="qm-panel space-y-3 px-6 py-5"
              data-testid="ceremony-form"
              onSubmit={(e) => void submit(e)}
            >
              <h2 className="font-semibold text-[var(--qm-ink)]">Registrar cerimônia</h2>
              {error ? <ApiErrorBanner error={error} title="Erro ao registrar cerimônia" /> : null}

              <fieldset className="space-y-2 text-sm">
                <legend className="font-semibold">Compromisso da cerimônia</legend>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="ceremony-event-mode"
                    checked={eventMode === "select"}
                    onChange={() => setEventMode("select")}
                  />
                  Escolher um compromisso já agendado nesta sprint
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="ceremony-event-mode"
                    checked={eventMode === "create"}
                    onChange={() => setEventMode("create")}
                  />
                  Agendar um novo compromisso para esta sprint
                </label>
              </fieldset>

              {eventMode === "select" ? (
                <label className="block text-sm font-semibold">
                  Compromisso da sprint
                  <select
                    className="qm-field mt-1"
                    value={selectedEventId}
                    onChange={(e) => setSelectedEventId(e.target.value)}
                  >
                    <option value="">Selecione o compromisso…</option>
                    {events.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {eventLabel(ev)}
                      </option>
                    ))}
                  </select>
                  {eventsQuery.isLoading ? (
                    <span className="mt-1 block text-xs font-normal text-[var(--qm-muted)]">
                      Carregando compromissos da sprint…
                    </span>
                  ) : events.length === 0 ? (
                    <span className="mt-1 block text-xs font-normal text-[var(--qm-muted)]">
                      Nenhuma cerimônia agendada nesta sprint — agende um novo compromisso.
                    </span>
                  ) : null}
                </label>
              ) : (
                <>
                  <label className="block text-sm font-semibold">
                    Tipo de cerimônia
                    <select
                      className="qm-field mt-1"
                      value={ceremonyType}
                      onChange={(e) => setCeremonyType(e.target.value as CeremonyType)}
                    >
                      {(Object.keys(CEREMONY_TYPE_LABELS) as CeremonyType[]).map((t) => (
                        <option key={t} value={t}>
                          {CEREMONY_TYPE_LABELS[t]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-semibold">
                    Título do compromisso
                    <input
                      className="qm-field mt-1"
                      placeholder="Ex.: Daily da Sprint 1"
                      value={eventTitle}
                      onChange={(e) => setEventTitle(e.target.value)}
                    />
                  </label>
                  <label className="block text-sm font-semibold">
                    Data e hora
                    <input
                      className="qm-field mt-1"
                      type="datetime-local"
                      value={eventStarts}
                      onChange={(e) => setEventStarts(e.target.value)}
                    />
                  </label>
                </>
              )}

              <textarea
                className="qm-field min-h-[4rem]"
                placeholder="Resumo"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
              />
              <textarea
                className="qm-field min-h-[3rem]"
                placeholder="Decisões"
                value={decisions}
                onChange={(e) => setDecisions(e.target.value)}
              />
              <textarea
                className="qm-field min-h-[3rem]"
                placeholder="Follow-up"
                value={followUp}
                onChange={(e) => setFollowUp(e.target.value)}
              />
              <button
                type="submit"
                className="qm-btn-primary"
                disabled={pending || createCeremony.isPending || !canSubmit}
              >
                Salvar registro
              </button>
            </form>
          ) : null}

          <section className="qm-panel px-6 py-5">
            <h3 className="font-semibold text-[var(--qm-ink)]">Histórico</h3>
            {ceremoniesQuery.isLoading ? (
              <p className="mt-2 text-sm text-[var(--qm-muted)]">Carregando…</p>
            ) : (ceremoniesQuery.data ?? []).length === 0 ? (
              <p className="mt-2 text-sm text-[var(--qm-muted)]">
                Nenhuma cerimônia registrada nesta sprint.
              </p>
            ) : (
              <ul className="mt-4 space-y-3 text-sm">
                {(ceremoniesQuery.data ?? []).map((c) => {
                  const event = eventsById.get(c.agenda_event_id);
                  return (
                    <li key={c.id} className="border-b border-[var(--qm-line)] pb-3">
                      <p className="font-semibold">
                        {CEREMONY_TYPE_LABELS[c.ceremony_type]} ·{" "}
                        {formatShortDate(c.recorded_at)}
                      </p>
                      {event ? (
                        <p className="mt-1 text-[var(--qm-muted)]">
                          Compromisso: {event.title} · {formatShortDate(event.starts_at)}
                        </p>
                      ) : null}
                      {c.summary ? <p className="mt-1">{c.summary}</p> : null}
                      {c.decisions ? (
                        <p className="mt-1 text-[var(--qm-muted)]">Decisões: {c.decisions}</p>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
