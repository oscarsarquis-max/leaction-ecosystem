import { useMemo, useState } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { canMutateAgileExecution } from "@/lib/permissions";
import { LoadingPanel, EmptyPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useActivateSprint,
  useCompleteSprint,
  useCreateSprint,
  useExecutionBoard,
  useSprintMetrics,
  useSprints,
  useSquads,
} from "@/execution/hooks";
import { formatHours, formatShortDate, SPRINT_STATUS_LABELS } from "@/execution/labels";
import type { BoardCard, Sprint } from "@/execution/api";

export function SprintsPage() {
  const org = useOrganization();
  const canMutate = canMutateAgileExecution(org.currentOrganization?.roles);
  const [squadFilter, setSquadFilter] = useState("");
  const squadsQuery = useSquads();
  const sprintsQuery = useSprints(squadFilter || undefined);
  const createSprint = useCreateSprint();

  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [squadId, setSquadId] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");

  if (squadsQuery.isLoading || sprintsQuery.isLoading) {
    return <LoadingPanel title="Carregando sprints…" />;
  }

  const squads = squadsQuery.data ?? [];
  const sprints = sprintsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3">
        <label className="text-sm font-semibold text-[var(--qm-muted)]">
          Filtrar por squad
          <select
            className="qm-field mt-1"
            value={squadFilter}
            onChange={(e) => setSquadFilter(e.target.value)}
          >
            <option value="">Todas</option>
            {squads.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {canMutate ? (
        <form
          className="qm-panel grid gap-3 px-6 py-5 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!squadId || !name.trim() || !startsAt || !endsAt) return;
            void createSprint
              .mutateAsync({
                squad_id: squadId,
                name: name.trim(),
                goal: goal.trim(),
                starts_at: new Date(startsAt).toISOString(),
                ends_at: new Date(endsAt).toISOString(),
              })
              .then(() => {
                setName("");
                setGoal("");
                setStartsAt("");
                setEndsAt("");
              });
          }}
        >
          <h2 className="font-semibold text-[var(--qm-ink)] sm:col-span-2">Nova sprint</h2>
          <label className="block text-sm font-semibold">
            Squad responsável
            <select
              className="qm-field mt-1"
              value={squadId}
              onChange={(e) => setSquadId(e.target.value)}
              required
            >
              <option value="">Squad…</option>
              {squads.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold">
            Nome da sprint
            <input
              className="qm-field mt-1"
              placeholder="Ex.: Sprint 1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm font-semibold">
            Início
            <input
              className="qm-field mt-1"
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm font-semibold">
            Término
            <input
              className="qm-field mt-1"
              type="datetime-local"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
              required
            />
          </label>
          <textarea
            className="qm-field min-h-[4rem] sm:col-span-2"
            placeholder="Objetivo da sprint"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
          <button type="submit" className="qm-btn-primary sm:col-span-2" disabled={createSprint.isPending}>
            Criar sprint
          </button>
        </form>
      ) : null}

      {sprints.length === 0 ? (
        <EmptyPanel
          title="Nenhuma sprint ainda"
          message="Sprints cadenciam o trabalho da squad em ciclos curtos."
          example="Ex.: Sprint 1 — fechar achados críticos do mês."
        />
      ) : (
        <ul className="space-y-4">
          {sprints.map((sprint) => (
            <SprintRow key={sprint.id} sprint={sprint} canMutate={canMutate} squads={squads} />
          ))}
        </ul>
      )}
    </div>
  );
}

function SprintRow({
  sprint,
  canMutate,
  squads,
}: {
  sprint: Sprint;
  canMutate: boolean;
  squads: { id: string; name: string }[];
}) {
  const activate = useActivateSprint();
  const complete = useCompleteSprint();
  const metricsQuery = useSprintMetrics(sprint.id);
  const boardQuery = useExecutionBoard({ sprintId: sprint.id });
  const [showComplete, setShowComplete] = useState(false);
  const [carry, setCarry] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const squadName = squads.find((s) => s.id === sprint.squad_id)?.name ?? "Squad";
  const incompleteCards = useMemo(() => {
    if (!boardQuery.data) return [] as BoardCard[];
    const terminal = new Set(["done"]);
    return boardQuery.data.columns.flatMap((c) =>
      c.cards.filter((card) => !terminal.has(card.status)),
    );
  }, [boardQuery.data]);

  async function handleComplete() {
    setError(null);
    const decisions = incompleteCards.map((c) => ({
      action_item_id: c.action_item_id,
      decision: carry[c.action_item_id] || "backlog",
    }));
    try {
      await complete.mutateAsync({ sprintId: sprint.id, carry_decisions: decisions });
      setShowComplete(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao concluir sprint");
    }
  }

  const metrics = metricsQuery.data;

  return (
    <li className="qm-panel px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-[var(--qm-ink)]">
            {sprint.name}{" "}
            <span className="text-sm font-normal text-[var(--qm-muted)]">
              ({SPRINT_STATUS_LABELS[sprint.status]})
            </span>
          </h3>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            {squadName} · {formatShortDate(sprint.starts_at)} — {formatShortDate(sprint.ends_at)}
          </p>
          {sprint.goal ? (
            <p className="mt-2 text-sm text-[var(--qm-ink)]">{sprint.goal}</p>
          ) : null}
        </div>
        {canMutate ? (
          <div className="flex flex-wrap gap-2">
            {sprint.status === "planned" ? (
              <button
                type="button"
                className="qm-btn-primary"
                disabled={activate.isPending}
                onClick={() => void activate.mutateAsync({ sprintId: sprint.id })}
              >
                Ativar
              </button>
            ) : null}
            {sprint.status === "active" ? (
              <button
                type="button"
                className="qm-btn-secondary"
                onClick={() => setShowComplete((v) => !v)}
              >
                Concluir sprint
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      {boardQuery.data?.wip_signal ? (
        <div
          className="execution-wip-banner mt-4"
          role="status"
          data-testid={`sprint-wip-banner-${sprint.id}`}
        >
          Limite WIP em execução ({boardQuery.data.wip_limit_in_progress}) ultrapassado —{" "}
          {boardQuery.data.in_progress_count} cards em andamento.
        </div>
      ) : null}

      {metrics ? (
        <dl
          className="mt-4 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4"
          data-testid={`sprint-metrics-${sprint.id}`}
        >
          <div>
            <dt className="text-[var(--qm-muted)]">Planejados</dt>
            <dd>{metrics.planned_cards}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Concluídos</dt>
            <dd>{metrics.completed_cards}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Em execução</dt>
            <dd>{metrics.in_progress_count}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Atrasadas</dt>
            <dd>{metrics.overdue_actions}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Carry-over</dt>
            <dd>{metrics.carry_over_cards}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Tempo de ciclo (média)</dt>
            <dd>{formatHours(metrics.average_cycle_time_hours)}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Tempo de ciclo (mediana)</dt>
            <dd>{formatHours(metrics.median_cycle_time_hours)}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Card mais antigo em execução</dt>
            <dd>{formatHours(metrics.oldest_in_progress_age_hours)}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Tempo bloqueado</dt>
            <dd>{formatHours(metrics.blocked_time_hours)}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">
              Sem check-in há mais de {metrics.check_in_stale_window_hours ?? 72}h
            </dt>
            <dd>{metrics.cards_without_recent_check_in ?? 0}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Impedimentos abertos</dt>
            <dd>{metrics.open_impediments}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Resultado da revisão</dt>
            <dd>{metrics.review_outcome ?? "—"}</dd>
          </div>
        </dl>
      ) : null}

      {showComplete ? (
        <div className="mt-4 rounded border border-[var(--qm-line)] p-4">
          <h4 className="font-semibold text-[var(--qm-ink)]">Carry-over</h4>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Defina o destino de cada card incompleto antes de fechar a sprint.
          </p>
          {error ? <ApiErrorBanner error={error} title="Erro ao concluir sprint" /> : null}
          <ul className="mt-3 space-y-2 text-sm">
            {incompleteCards.map((c) => (
              <li key={c.action_item_id} className="flex flex-wrap items-center gap-2">
                <span className="flex-1">{c.description}</span>
                <select
                  className="qm-field"
                  value={carry[c.action_item_id] ?? "backlog"}
                  onChange={(e) =>
                    setCarry((prev) => ({
                      ...prev,
                      [c.action_item_id]: e.target.value,
                    }))
                  }
                >
                  <option value="backlog">Voltar ao backlog</option>
                </select>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="qm-btn-primary mt-3"
            disabled={complete.isPending || incompleteCards.length === 0}
            onClick={() => void handleComplete()}
          >
            Confirmar conclusão
          </button>
        </div>
      ) : null}
    </li>
  );
}
