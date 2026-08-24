import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import { canMutateAgileExecution } from "@/lib/permissions";
import { LoadingPanel, EmptyPanel, ErrorPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useExecutionBoard,
  useMoveBoardCard,
  useSquads,
  useSprints,
} from "@/execution/hooks";
import type { BoardCard, BoardColumnKey, BoardOut } from "@/execution/api";
import {
  ACTION_KIND_LABELS,
  analysisProvenanceLink,
  BOARD_COLUMN_LABELS,
  BOARD_COLUMN_ORDER,
  CHECKIN_HEALTH_LABELS,
  formatRelativeAge,
  formatShortDate,
  isCheckInStale,
  originLinkLabel,
  PRIORITY_LABELS,
  STATUS_LABELS,
} from "@/execution/labels";

type BoardFilters = {
  squadId: string;
  sprintId: string;
  ownerId: string;
  origin: string;
  priority: string;
  showBlocked: boolean;
  showOverdue: boolean;
  showStaleCheckIn: boolean;
  showStaleAnalysis: boolean;
};

function useCompactLayout(): boolean {
  const [compact, setCompact] = useState(() =>
    typeof window !== "undefined"
      ? window.matchMedia("(max-width: 768px)").matches
      : false,
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = () => setCompact(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return compact;
}

function cloneBoard(board: BoardOut): BoardOut {
  return {
    ...board,
    columns: board.columns.map((c) => ({ ...c, cards: [...c.cards] })),
  };
}

function moveCardInBoard(
  board: BoardOut,
  actionItemId: string,
  fromColumn: BoardColumnKey,
  toColumn: BoardColumnKey,
): BoardOut {
  const next = cloneBoard(board);
  const from = next.columns.find((c) => c.key === fromColumn);
  const to = next.columns.find((c) => c.key === toColumn);
  if (!from || !to) return board;
  const idx = from.cards.findIndex((c) => c.action_item_id === actionItemId);
  if (idx < 0) return board;
  const [card] = from.cards.splice(idx, 1);
  to.cards.push(card);
  return next;
}

function filterCard(card: BoardCard, filters: BoardFilters): boolean {
  if (filters.ownerId && card.owner_membership_id !== filters.ownerId) return false;
  if (filters.priority && card.priority !== filters.priority) return false;
  if (filters.origin === "case" && !card.improvement_case_id) return false;
  if (filters.origin === "assessment" && !card.assessment_id) return false;
  if (filters.showBlocked && !card.has_open_impediment && !card.has_blocking_dependency) {
    return false;
  }
  if (filters.showOverdue && !card.is_overdue) return false;
  if (filters.showStaleCheckIn && !isCheckInStale(card.latest_check_in_at)) return false;
  if (filters.showStaleAnalysis && card.source_analysis_is_stale !== true) return false;
  return true;
}

function ExecutionCard({
  card,
  columnKey,
  canMutate,
  compact,
  activeSprintId,
  onMove,
}: {
  card: BoardCard;
  columnKey: BoardColumnKey;
  canMutate: boolean;
  compact: boolean;
  activeSprintId: string | null | undefined;
  onMove: (
    actionItemId: string,
    from: BoardColumnKey,
    to: BoardColumnKey,
    extra?: { sprint_id?: string; impediment_override_justification?: string },
  ) => Promise<void>;
}) {
  const origin = originLinkLabel(card);
  const checkInStale = isCheckInStale(card.latest_check_in_at);
  const analysisStale = card.source_analysis_is_stale === true;
  const provenance = analysisProvenanceLink(card);
  const [moveTarget, setMoveTarget] = useState<BoardColumnKey | "">("");
  const [overrideNote, setOverrideNote] = useState("");
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const dragEnabled = canMutate && !compact && !reducedMotion;

  async function handleDragStart(e: React.DragEvent) {
    if (!dragEnabled) {
      e.preventDefault();
      return;
    }
    e.dataTransfer.setData("text/plain", card.action_item_id);
    e.dataTransfer.setData("application/x-qmind-column", columnKey);
    e.dataTransfer.effectAllowed = "move";
  }

  async function submitMove() {
    if (!moveTarget || moveTarget === columnKey) return;
    const extra: { sprint_id?: string; impediment_override_justification?: string } = {};
    if (moveTarget === "selected" && activeSprintId) {
      extra.sprint_id = activeSprintId;
    }
    if (card.has_open_impediment && overrideNote.trim()) {
      extra.impediment_override_justification = overrideNote.trim();
    }
    await onMove(card.action_item_id, columnKey, moveTarget, extra);
    setMoveTarget("");
    setOverrideNote("");
  }

  return (
    <article
      className="execution-card"
      draggable={dragEnabled}
      onDragStart={handleDragStart}
      data-testid={`execution-card-${card.action_item_id}`}
    >
      <h3 className="execution-card__title">
        <Link
          to={`/execution/cards/${card.action_item_id}`}
          className="text-[var(--qm-ink)] hover:underline"
        >
          {card.description}
        </Link>
      </h3>
      <p className="execution-card__meta">
        {ACTION_KIND_LABELS[card.action_kind] ?? card.action_kind}
        {origin.href ? (
          <>
            {" · "}
            <Link to={origin.href} className="underline">
              {origin.label}
            </Link>
          </>
        ) : (
          <> · {origin.label}</>
        )}
      </p>
      <p className="execution-card__meta">
        {card.squad_name ? `${card.squad_name}` : "Sem squad"}
        {card.sprint_name ? ` · ${card.sprint_name}` : ""}
      </p>
      <p className="execution-card__meta">
        {card.owner_display_name || card.owner_email || "Responsável"}
        {card.priority ? ` · ${PRIORITY_LABELS[card.priority]}` : ""}
        {card.estimate_points != null ? ` · ${card.estimate_points} pts` : ""}
      </p>
      <p className="execution-card__meta">
        Prazo {formatShortDate(card.due_at)} · {STATUS_LABELS[card.status]}
      </p>
      <p className="execution-card__meta">
        Check-in: {formatRelativeAge(card.latest_check_in_at)}
        {card.latest_check_in_health
          ? ` · ${CHECKIN_HEALTH_LABELS[card.latest_check_in_health]}`
          : ""}
      </p>
      <div>
        {card.is_overdue ? (
          <span className="execution-badge execution-badge--danger">Atrasada</span>
        ) : null}
        {card.has_open_impediment ? (
          <span className="execution-badge execution-badge--warn">
            Bloqueada
            {card.open_impediment_count && card.open_impediment_count > 1
              ? ` (${card.open_impediment_count})`
              : ""}
          </span>
        ) : null}
        {card.has_blocking_dependency ? (
          <span className="execution-badge execution-badge--warn">
            Dependência
            {card.blocking_dependency_count && card.blocking_dependency_count > 1
              ? ` (${card.blocking_dependency_count})`
              : ""}
          </span>
        ) : null}
        {checkInStale ? (
          <span className="execution-badge execution-badge--muted">Sem check-in recente</span>
        ) : null}
        {analysisStale ? (
          <span
            className="execution-badge execution-badge--warn"
            data-testid={`execution-stale-analysis-${card.action_item_id}`}
          >
            Análise QMind desatualizada
          </span>
        ) : null}
      </div>
      {analysisStale && provenance ? (
        <p className="execution-card__meta">
          <Link to={provenance.href} className="underline">
            {provenance.label}
          </Link>
        </p>
      ) : null}

      {canMutate && compact ? (
        <div className="mt-2 space-y-2" data-testid="execution-keyboard-move">
          <label className="block text-xs font-semibold text-[var(--qm-muted)]">
            Mover para
            <select
              className="qm-field mt-1 text-sm"
              value={moveTarget}
              onChange={(e) => setMoveTarget(e.target.value as BoardColumnKey | "")}
              aria-label={`Mover card ${card.description}`}
            >
              <option value="">Selecione…</option>
              {BOARD_COLUMN_ORDER.filter((k) => k !== columnKey).map((k) => (
                <option key={k} value={k}>
                  {BOARD_COLUMN_LABELS[k]}
                </option>
              ))}
            </select>
          </label>
          {card.has_open_impediment && moveTarget ? (
            <input
              className="qm-field text-sm"
              placeholder="Justificativa para avançar com impedimento"
              value={overrideNote}
              onChange={(e) => setOverrideNote(e.target.value)}
            />
          ) : null}
          <button
            type="button"
            className="qm-btn-secondary !px-2 !py-1 text-xs"
            disabled={!moveTarget}
            onClick={() => void submitMove()}
          >
            Mover
          </button>
        </div>
      ) : null}
    </article>
  );
}

export function BoardPage() {
  const org = useOrganization();
  const canMutate = canMutateAgileExecution(org.currentOrganization?.roles);
  const compact = useCompactLayout();

  const [filters, setFilters] = useState<BoardFilters>({
    squadId: "",
    sprintId: "",
    ownerId: "",
    origin: "",
    priority: "",
    showBlocked: false,
    showOverdue: false,
    showStaleCheckIn: false,
    showStaleAnalysis: false,
  });

  const boardQuery = useExecutionBoard({
    squadId: filters.squadId || undefined,
    sprintId: filters.sprintId || undefined,
  });
  const squadsQuery = useSquads();
  const sprintsQuery = useSprints(filters.squadId || undefined);
  const moveMutation = useMoveBoardCard();

  const [optimisticBoard, setOptimisticBoard] = useState<BoardOut | null>(null);
  const board = optimisticBoard ?? boardQuery.data;

  const owners = useMemo(() => {
    if (!board) return [];
    const seen = new Map<string, string>();
    for (const col of board.columns) {
      for (const card of col.cards) {
        const label = card.owner_display_name || card.owner_email;
        if (label) seen.set(card.owner_membership_id, label);
      }
    }
    return [...seen.entries()].map(([id, label]) => ({ id, label }));
  }, [board]);

  const handleMove = useCallback(
    async (
      actionItemId: string,
      fromColumn: BoardColumnKey,
      toColumn: BoardColumnKey,
      extra?: { sprint_id?: string; impediment_override_justification?: string },
    ) => {
      if (!board) return;
      const snapshot = cloneBoard(board);
      setOptimisticBoard(moveCardInBoard(board, actionItemId, fromColumn, toColumn));
      try {
        await moveMutation.mutateAsync({
          action_item_id: actionItemId,
          target_column: toColumn,
          sprint_id: extra?.sprint_id ?? board.active_sprint_id ?? undefined,
          impediment_override_justification: extra?.impediment_override_justification,
        });
        setOptimisticBoard(null);
        await boardQuery.refetch();
      } catch {
        setOptimisticBoard(snapshot);
      }
    },
    [board, boardQuery, moveMutation],
  );

  async function onDrop(
    e: React.DragEvent,
    targetColumn: BoardColumnKey,
  ) {
    e.preventDefault();
    if (!canMutate || !board) return;
    const actionItemId = e.dataTransfer.getData("text/plain");
    const fromColumn = e.dataTransfer.getData(
      "application/x-qmind-column",
    ) as BoardColumnKey;
    if (!actionItemId || !fromColumn || fromColumn === targetColumn) return;
    await handleMove(actionItemId, fromColumn, targetColumn, {
      sprint_id: targetColumn === "selected" ? board.active_sprint_id ?? undefined : undefined,
    });
  }

  if (boardQuery.isLoading) {
    return <LoadingPanel title="Carregando board de execução…" />;
  }

  if (boardQuery.isError) {
    return (
      <ErrorPanel
        title="Não foi possível carregar o board"
        message={boardQuery.error instanceof Error ? boardQuery.error.message : undefined}
        action={{ label: "Tentar de novo", onClick: () => void boardQuery.refetch() }}
      />
    );
  }

  if (!board || board.columns.every((c) => c.cards.length === 0)) {
    return (
      <>
        <BoardFiltersBar
          filters={filters}
          setFilters={setFilters}
          squads={squadsQuery.data ?? []}
          sprints={sprintsQuery.data ?? []}
          owners={owners}
        />
        <EmptyPanel
          title="Nenhuma ação no board ainda"
          message="Quando ações forem alocadas a sprints, elas aparecem aqui por coluna de status."
          example="Crie uma squad, abra uma sprint e aloque cards a partir do backlog."
        />
      </>
    );
  }

  return (
    <div>
      {moveMutation.isError ? (
        <ApiErrorBanner error={moveMutation.error} title="Não foi possível mover o card" />
      ) : null}

      <BoardFiltersBar
        filters={filters}
        setFilters={setFilters}
        squads={squadsQuery.data ?? []}
        sprints={sprintsQuery.data ?? []}
        owners={owners}
      />

      {board.wip_signal ? (
        <div className="execution-wip-banner" role="status" data-testid="execution-wip-banner">
          Limite WIP em execução ({board.wip_limit_in_progress}) ultrapassado —{" "}
          {board.in_progress_count} cards em andamento. Priorize conclusão antes de puxar
          novos itens.
        </div>
      ) : null}

      <div
        className={compact ? "execution-list-board" : "execution-board"}
        role="region"
        aria-label="Board de execução ágil"
      >
        {BOARD_COLUMN_ORDER.map((key) => {
          const column = board.columns.find((c) => c.key === key) ?? {
            key,
            label: BOARD_COLUMN_LABELS[key],
            cards: [],
          };
          const visibleCards = column.cards.filter((card) => filterCard(card, filters));

          return (
            <section
              key={key}
              className="execution-board__column"
              aria-label={`Coluna ${BOARD_COLUMN_LABELS[key]}`}
              onDragOver={(e) => {
                if (canMutate && !compact) e.preventDefault();
              }}
              onDrop={(e) => void onDrop(e, key)}
            >
              <header className="execution-board__column-header">
                {BOARD_COLUMN_LABELS[key]} ({visibleCards.length})
              </header>
              <div className="execution-board__column-body">
                {visibleCards.length === 0 ? (
                  <p className="text-xs text-[var(--qm-muted)]">Nenhum card nesta coluna.</p>
                ) : (
                  visibleCards.map((card) => (
                    <ExecutionCard
                      key={card.action_item_id}
                      card={card}
                      columnKey={key}
                      canMutate={canMutate}
                      compact={compact}
                      activeSprintId={board.active_sprint_id}
                      onMove={handleMove}
                    />
                  ))
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function BoardFiltersBar({
  filters,
  setFilters,
  squads,
  sprints,
  owners,
}: {
  filters: BoardFilters;
  setFilters: React.Dispatch<React.SetStateAction<BoardFilters>>;
  squads: { id: string; name: string }[];
  sprints: { id: string; name: string }[];
  owners: { id: string; label: string }[];
}) {
  return (
    <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <label className="text-xs font-semibold text-[var(--qm-muted)]">
        Squad
        <select
          className="qm-field mt-1"
          value={filters.squadId}
          onChange={(e) =>
            setFilters((f) => ({ ...f, squadId: e.target.value, sprintId: "" }))
          }
        >
          <option value="">Todas</option>
          {squads.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs font-semibold text-[var(--qm-muted)]">
        Sprint
        <select
          className="qm-field mt-1"
          value={filters.sprintId}
          onChange={(e) => setFilters((f) => ({ ...f, sprintId: e.target.value }))}
        >
          <option value="">Todas</option>
          {sprints.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs font-semibold text-[var(--qm-muted)]">
        Responsável
        <select
          className="qm-field mt-1"
          value={filters.ownerId}
          onChange={(e) => setFilters((f) => ({ ...f, ownerId: e.target.value }))}
        >
          <option value="">Todos</option>
          {owners.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs font-semibold text-[var(--qm-muted)]">
        Prioridade
        <select
          className="qm-field mt-1"
          value={filters.priority}
          onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value }))}
        >
          <option value="">Todas</option>
          {(["critical", "high", "medium", "low"] as const).map((p) => (
            <option key={p} value={p}>
              {PRIORITY_LABELS[p]}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs font-semibold text-[var(--qm-muted)]">
        Origem
        <select
          className="qm-field mt-1"
          value={filters.origin}
          onChange={(e) => setFilters((f) => ({ ...f, origin: e.target.value }))}
        >
          <option value="">Todas</option>
          <option value="case">Caso de melhoria</option>
          <option value="assessment">Avaliação</option>
        </select>
      </label>
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.showBlocked}
            onChange={(e) => setFilters((f) => ({ ...f, showBlocked: e.target.checked }))}
          />
          Bloqueadas
        </label>
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.showOverdue}
            onChange={(e) => setFilters((f) => ({ ...f, showOverdue: e.target.checked }))}
          />
          Atrasadas
        </label>
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.showStaleCheckIn}
            onChange={(e) =>
              setFilters((f) => ({ ...f, showStaleCheckIn: e.target.checked }))
            }
          />
          Sem check-in recente
        </label>
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.showStaleAnalysis}
            onChange={(e) =>
              setFilters((f) => ({ ...f, showStaleAnalysis: e.target.checked }))
            }
          />
          Inteligência desatualizada
        </label>
      </div>
    </div>
  );
}
