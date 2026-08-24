import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import { canMutateAgileExecution } from "@/lib/permissions";
import { LoadingPanel, ErrorPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useActionItemDetail,
  useCheckIns,
  useCreateCheckIn,
  useCreateDependency,
  useCreateImpediment,
  useDeleteDependency,
  useDependencies,
  useExecutionBoard,
  useImpediments,
  useMoveBoardCard,
  usePatchImpediment,
} from "@/execution/hooks";
import {
  ACTION_KIND_LABELS,
  analysisProvenanceLink,
  BOARD_COLUMN_LABELS,
  CHECKIN_HEALTH_LABELS,
  formatRelativeAge,
  formatShortDate,
  originLinkLabel,
  STATUS_LABELS,
} from "@/execution/labels";
import type { BoardCard, BoardColumnKey, CheckInHealth } from "@/execution/api";
import { QmindApiError } from "@/api/qmindApi";

function columnForStatus(
  status: string,
  inSprint: boolean,
): BoardColumnKey | null {
  if (status === "open") return inSprint ? "selected" : "backlog";
  const map: Record<string, BoardColumnKey> = {
    in_progress: "in_progress",
    implemented: "implemented",
    validated: "validated",
    ineffective: "ineffective",
    done: "done",
  };
  return map[status] ?? null;
}

/** Human label for an action item candidate — description first, never an id. */
function describeCandidate(card: BoardCard): string {
  const parts = [
    card.owner_display_name || card.owner_email,
    originLinkLabel(card).label,
    card.sprint_name ?? "Sem sprint",
    STATUS_LABELS[card.status],
  ].filter(Boolean);
  return `${card.description} — ${parts.join(" · ")}`;
}

function matchesSearch(card: BoardCard, term: string): boolean {
  if (!term.trim()) return true;
  return describeCandidate(card).toLowerCase().includes(term.trim().toLowerCase());
}

export function CardDetailPage() {
  const { actionItemId } = useParams<{ actionItemId: string }>();
  const org = useOrganization();
  const canMutate = canMutateAgileExecution(org.currentOrganization?.roles);

  const itemQuery = useActionItemDetail(actionItemId);
  const boardQuery = useExecutionBoard({});
  const checkInsQuery = useCheckIns(actionItemId);
  const impedimentsQuery = useImpediments(actionItemId);
  const depsQuery = useDependencies(actionItemId);
  const createCheckIn = useCreateCheckIn(actionItemId ?? "");
  const createImpediment = useCreateImpediment(actionItemId ?? "");
  const patchImpediment = usePatchImpediment(actionItemId ?? "");
  const createDependency = useCreateDependency(actionItemId ?? "");
  const deleteDependency = useDeleteDependency(actionItemId ?? "");
  const moveCard = useMoveBoardCard();

  const [health, setHealth] = useState<CheckInHealth>("on_track");
  const [progressNote, setProgressNote] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [impTitle, setImpTitle] = useState("");
  const [predSearch, setPredSearch] = useState("");
  const [predId, setPredId] = useState("");
  const [moveError, setMoveError] = useState<string | null>(null);

  const allCards = useMemo(
    () => (boardQuery.data?.columns ?? []).flatMap((c) => c.cards),
    [boardQuery.data],
  );

  const cardsById = useMemo(() => {
    const map = new Map<string, BoardCard>();
    for (const card of allCards) map.set(card.action_item_id, card);
    return map;
  }, [allCards]);

  const boardCard = useMemo(() => {
    if (!boardQuery.data || !actionItemId) return null;
    for (const col of boardQuery.data.columns) {
      const card = col.cards.find((c) => c.action_item_id === actionItemId);
      if (card) return { card, column: col.key as BoardColumnKey };
    }
    return null;
  }, [boardQuery.data, actionItemId]);

  const dependencies = useMemo(() => depsQuery.data ?? [], [depsQuery.data]);

  const predecessorCandidates = useMemo(() => {
    const linked = new Set(dependencies.map((d) => d.predecessor_action_item_id));
    return allCards
      .filter((c) => c.action_item_id !== actionItemId && !linked.has(c.action_item_id))
      .filter((c) => matchesSearch(c, predSearch));
  }, [allCards, actionItemId, dependencies, predSearch]);

  const origin = boardCard
    ? originLinkLabel(boardCard.card)
    : { label: "Plano de ação", href: null };

  const provenance = boardCard ? analysisProvenanceLink(boardCard.card) : null;

  const allowedMoves = useMemo((): { key: BoardColumnKey; label: string }[] => {
    const item = itemQuery.data;
    if (!item) return [];
    const col = columnForStatus(item.status, boardCard?.column === "selected");
    const moves: BoardColumnKey[] = [];
    if (item.status === "open") {
      moves.push("selected", "in_progress");
    } else if (item.status === "in_progress") {
      moves.push("implemented");
    } else if (item.status === "implemented") {
      moves.push("validated", "done");
    } else if (item.status === "validated") {
      moves.push("done", "ineffective");
    } else if (item.status === "ineffective") {
      moves.push("in_progress");
    }
    if (col === "selected") moves.push("backlog");
    return moves
      .filter((k) => k !== col)
      .map((k) => ({ key: k, label: BOARD_COLUMN_LABELS[k] }));
  }, [itemQuery.data, boardCard?.column]);

  if (itemQuery.isLoading || boardQuery.isLoading) {
    return <LoadingPanel title="Carregando card…" />;
  }

  if (itemQuery.isError || !itemQuery.data) {
    return (
      <ErrorPanel
        title="Card não encontrado"
        message={
          itemQuery.error instanceof Error ? itemQuery.error.message : undefined
        }
        action={{ label: "Voltar ao board", to: "/execution" }}
      />
    );
  }

  const item = itemQuery.data;
  const latestCheckIn = checkInsQuery.data?.[0];
  /** Only report against a sprint the card is actually allocated to. */
  const allocatedSprintId = boardCard?.card.sprint_id ?? null;

  async function submitCheckIn(e: React.FormEvent) {
    e.preventDefault();
    if (!progressNote.trim()) return;
    await createCheckIn.mutateAsync({
      health,
      progress_note: progressNote.trim(),
      next_step: nextStep.trim(),
      sprint_id: allocatedSprintId,
    });
    setProgressNote("");
    setNextStep("");
  }

  async function submitImpediment(e: React.FormEvent) {
    e.preventDefault();
    if (!impTitle.trim()) return;
    await createImpediment.mutateAsync({
      title: impTitle.trim(),
      sprint_id: allocatedSprintId,
    });
    setImpTitle("");
  }

  async function submitDependency(e: React.FormEvent) {
    e.preventDefault();
    if (!predId || !actionItemId) return;
    await createDependency.mutateAsync({
      predecessor_action_item_id: predId,
      dependent_action_item_id: actionItemId,
      dependency_type: "blocks",
    });
    setPredId("");
    setPredSearch("");
  }

  async function runTransition(target: BoardColumnKey) {
    if (!actionItemId) return;
    setMoveError(null);
    try {
      await moveCard.mutateAsync({
        action_item_id: actionItemId,
        target_column: target,
        sprint_id:
          target === "selected"
            ? boardQuery.data?.active_sprint_id ?? undefined
            : undefined,
        efficacy_fail_reason:
          target === "ineffective" ? "Revisão solicitada na execução" : undefined,
      });
      await itemQuery.refetch();
      await boardQuery.refetch();
    } catch (err) {
      setMoveError(
        err instanceof QmindApiError ? err.message : "Transição não permitida.",
      );
    }
  }

  return (
    <div className="space-y-8">
      <p>
        <Link to="/execution" className="text-sm font-semibold text-[var(--qm-muted)] hover:text-[var(--qm-ink)]">
          ← Voltar ao board
        </Link>
      </p>

      <section className="qm-panel px-6 py-5">
        <h2 className="font-display text-xl text-[var(--qm-ink)]">{item.description}</h2>
        <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-[var(--qm-muted)]">Tipo</dt>
            <dd>{ACTION_KIND_LABELS[item.action_kind]}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Status</dt>
            <dd>{STATUS_LABELS[item.status]}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Prazo</dt>
            <dd>{formatShortDate(item.due_at)}</dd>
          </div>
          <div>
            <dt className="text-[var(--qm-muted)]">Origem</dt>
            <dd>
              {origin.href ? (
                <Link to={origin.href} className="underline">
                  {origin.label}
                </Link>
              ) : (
                origin.label
              )}
            </dd>
          </div>
          {boardCard?.card ? (
            <>
              <div>
                <dt className="text-[var(--qm-muted)]">Responsável</dt>
                <dd>
                  {boardCard.card.owner_display_name ||
                    boardCard.card.owner_email ||
                    "Responsável"}
                </dd>
              </div>
              <div>
                <dt className="text-[var(--qm-muted)]">Squad / Sprint</dt>
                <dd>
                  {boardCard.card.squad_name ?? "—"}
                  {boardCard.card.sprint_name ? ` · ${boardCard.card.sprint_name}` : ""}
                </dd>
              </div>
            </>
          ) : null}
        </dl>
        {latestCheckIn ? (
          <p className="mt-3 text-sm text-[var(--qm-muted)]">
            Último check-in: {formatRelativeAge(latestCheckIn.reported_at)} (
            {CHECKIN_HEALTH_LABELS[latestCheckIn.health]})
          </p>
        ) : null}
        {boardCard?.card.source_analysis_is_stale ? (
          <p className="mt-3 text-sm" data-testid="execution-detail-stale-analysis">
            <span className="execution-badge execution-badge--warn">
              Análise QMind desatualizada
            </span>
            {provenance ? (
              <>
                {" "}
                <Link to={provenance.href} className="underline">
                  {provenance.label}
                </Link>
              </>
            ) : null}
          </p>
        ) : null}
      </section>

      {moveError ? <ApiErrorBanner error={moveError} title="Transição não permitida" /> : null}

      {allowedMoves.length > 0 ? (
        <section className="qm-panel px-6 py-5">
          <h3 className="font-semibold text-[var(--qm-ink)]">Próximo passo no fluxo</h3>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Avance o card conforme o ciclo de vida da ação.
          </p>
          {canMutate ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {allowedMoves.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  className="qm-btn-primary"
                  disabled={moveCard.isPending}
                  onClick={() => void runTransition(m.key)}
                >
                  {m.label}
                </button>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-[var(--qm-muted)]">
              Seu perfil é somente leitura — peça a alguém com permissão de execução para avançar o card.
            </p>
          )}
        </section>
      ) : null}

      <section className="qm-panel px-6 py-5">
        <h3 className="font-semibold text-[var(--qm-ink)]">Check-in de progresso</h3>
        <p className="mt-1 text-sm text-[var(--qm-muted)]">
          Registre o que foi feito e qual é o próximo passo — isso mantém o time alinhado.
        </p>

        {canMutate ? (
          <form
            className="mt-4 space-y-3"
            onSubmit={(e) => void submitCheckIn(e)}
            data-testid="execution-check-in-form"
          >
            <label className="block text-sm font-semibold">
              Saúde
              <select
                className="qm-field mt-1"
                value={health}
                onChange={(e) => setHealth(e.target.value as CheckInHealth)}
              >
                {(Object.keys(CHECKIN_HEALTH_LABELS) as CheckInHealth[]).map((k) => (
                  <option key={k} value={k}>
                    {CHECKIN_HEALTH_LABELS[k]}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-semibold">
              O que avançou?
              <textarea
                className="qm-field mt-1 min-h-[5rem]"
                required
                value={progressNote}
                onChange={(e) => setProgressNote(e.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold">
              Próximo passo
              <input
                className="qm-field mt-1"
                value={nextStep}
                onChange={(e) => setNextStep(e.target.value)}
              />
            </label>
            <button type="submit" className="qm-btn-primary" disabled={createCheckIn.isPending}>
              Registrar check-in
            </button>
          </form>
        ) : null}

        <ul className="mt-6 space-y-3">
          {(checkInsQuery.data ?? []).map((c) => (
            <li key={c.id} className="rounded border border-[var(--qm-line)] p-3 text-sm">
              <p className="font-semibold">
                {formatShortDate(c.reported_at)} · {CHECKIN_HEALTH_LABELS[c.health]}
              </p>
              <p className="mt-1">{c.progress_note}</p>
              {c.next_step ? (
                <p className="mt-1 text-[var(--qm-muted)]">Próximo: {c.next_step}</p>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="qm-panel px-6 py-5">
        <h3 className="font-semibold text-[var(--qm-ink)]">Impedimentos</h3>
        {canMutate ? (
          <form className="mt-3 flex flex-wrap gap-2" onSubmit={(e) => void submitImpediment(e)}>
            <input
              className="qm-field min-w-[12rem] flex-1"
              placeholder="Título do impedimento"
              value={impTitle}
              onChange={(e) => setImpTitle(e.target.value)}
            />
            <button type="submit" className="qm-btn-secondary" disabled={createImpediment.isPending}>
              Registrar
            </button>
          </form>
        ) : null}
        <ul className="mt-4 space-y-2 text-sm">
          {(impedimentsQuery.data ?? []).map((imp) => (
            <li key={imp.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--qm-line)] pb-2">
              <span>
                {imp.title} ({imp.status})
              </span>
              {canMutate && imp.status === "open" ? (
                <button
                  type="button"
                  className="qm-btn-secondary !px-2 !py-1 text-xs"
                  onClick={() =>
                    void patchImpediment.mutateAsync({
                      impedimentId: imp.id,
                      body: { status: "resolved", resolution_note: "Resolvido na execução" },
                    })
                  }
                >
                  Resolver
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="qm-panel px-6 py-5">
        <h3 className="font-semibold text-[var(--qm-ink)]">Dependências</h3>
        <p className="mt-1 text-sm text-[var(--qm-muted)]">
          Escolha a ação que precisa terminar antes desta.
        </p>
        {canMutate ? (
          <form
            className="mt-3 space-y-2"
            data-testid="execution-dependency-form"
            onSubmit={(e) => void submitDependency(e)}
          >
            <label className="block text-sm font-semibold">
              Buscar por descrição, responsável, origem, sprint ou situação
              <input
                className="qm-field mt-1"
                type="search"
                placeholder="Busque por descrição, responsável, origem, sprint ou situação"
                value={predSearch}
                onChange={(e) => setPredSearch(e.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold">
              Ação predecessora
              <select
                className="qm-field mt-1"
                value={predId}
                onChange={(e) => setPredId(e.target.value)}
              >
                <option value="">Selecione a ação…</option>
                {predecessorCandidates.map((c) => (
                  <option key={c.action_item_id} value={c.action_item_id}>
                    {describeCandidate(c)}
                  </option>
                ))}
              </select>
            </label>
            {predecessorCandidates.length === 0 ? (
              <p className="text-xs text-[var(--qm-muted)]">
                Nenhuma ação disponível para vincular com esse filtro.
              </p>
            ) : null}
            <button
              type="submit"
              className="qm-btn-secondary"
              disabled={createDependency.isPending || !predId}
            >
              Vincular
            </button>
          </form>
        ) : null}
        <ul className="mt-4 space-y-2 text-sm" data-testid="execution-dependency-list">
          {dependencies.length === 0 ? (
            <li className="text-[var(--qm-muted)]">Nenhuma dependência ativa.</li>
          ) : (
            dependencies.map((d) => {
              const predecessor = cardsById.get(d.predecessor_action_item_id);
              const label =
                d.dependency_type === "blocks" ? "Bloqueia esta ação" : "Relacionada";
              return (
                <li
                  key={d.id}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--qm-line)] pb-2"
                >
                  <span className="flex-1">
                    <Link
                      to={`/execution/cards/${d.predecessor_action_item_id}`}
                      className="underline"
                    >
                      {predecessor?.description ?? "Ação predecessora"}
                    </Link>{" "}
                    <span className="text-[var(--qm-muted)]">
                      · {label}
                      {predecessor ? ` · ${STATUS_LABELS[predecessor.status]}` : ""}
                    </span>
                  </span>
                  {canMutate ? (
                    <button
                      type="button"
                      className="qm-btn-secondary !px-2 !py-1 text-xs"
                      disabled={deleteDependency.isPending}
                      onClick={() => void deleteDependency.mutateAsync(d.id)}
                    >
                      Remover
                    </button>
                  ) : null}
                </li>
              );
            })
          )}
        </ul>
      </section>
    </div>
  );
}
