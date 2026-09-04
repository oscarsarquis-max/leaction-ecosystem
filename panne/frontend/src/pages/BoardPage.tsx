import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { BoardCard, BoardContextCatalog, BoardFilters } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { config } from "../config";
import {
  actionLabel,
  boardDefaultOperationalDate,
  formatContextDate,
  formatDateTime,
  formatDecimal,
  shiftLabel,
  statusLabel,
} from "../format";
import {
  readOperationalContext,
  stripBoardQueryParams,
  writeOperationalContext,
  type OperationalContext,
} from "../session/operationalContext";
import { useAssistant } from "../assistant/AssistantContext";
import { useOrganization } from "../session/OrganizationContext";

function defaultBoardDate(): string {
  return boardDefaultOperationalDate(config.demoMode, config.demoAnchorDate);
}

const BUCKETS = [
  { id: "awaiting", label: "Aguardando liberação", match: (card: BoardCard) => ["draft", "scheduled", "released"].includes(card.order.status) },
  { id: "weighing", label: "Em pesagem", match: (card: BoardCard) => card.order.status === "in_weighing" },
  { id: "ready", label: "Prontas", match: (card: BoardCard) => card.order.status === "ready" && !card.blocked },
  { id: "running", label: "Em execução", match: (card: BoardCard) => card.order.status === "in_progress" },
  { id: "blocked", label: "Bloqueadas", match: (card: BoardCard) => card.blocked },
  { id: "done", label: "Concluídas", match: (card: BoardCard) => card.order.status === "completed" },
  { id: "short", label: "Encerradas parciais", match: (card: BoardCard) => card.order.status === "short_closed" },
] as const;

function toneForStatus(status: string): "sucesso" | "atencao" | "erro" | "info" | "neutro" {
  if (status === "completed") return "sucesso";
  if (status === "cancelled" || status === "short_closed") return "erro";
  if (status === "on_hold" || status === "delayed") return "atencao";
  if (status === "in_progress" || status === "in_weighing") return "info";
  return "neutro";
}

function stationOf(card: BoardCard): string {
  return card.current_step || "Sem estação";
}

export function BoardPage() {
  const { api, active, me, hasPermission } = useOrganization();
  const { publishLive } = useAssistant();
  const [params, setParams] = useSearchParams();
  const userHint = me?.display_name || "sessao";
  const canReadProducts = hasPermission("product.read");
  const [catalog, setCatalog] = useState<BoardContextCatalog | null>(null);
  const [context, setContext] = useState<OperationalContext | null>(null);
  const [editingContext, setEditingContext] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [view, setView] = useState<"fluxo" | "lista" | "estacao">("lista");
  const [selected, setSelected] = useState<BoardCard | null>(null);
  const [confirmChange, setConfirmChange] = useState(false);
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; cards: BoardCard[]; updatedAt: string }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const prevOrgRef = useRef<string | null>(null);
  const catalogOrgRef = useRef<string | null>(null);
  const loadGenerationRef = useRef(0);

  const filters = useMemo<BoardFilters>(() => {
    // Só confiar em query/contexto depois do catálogo da org ativa confirmar o estabelecimento.
    // Com catalog=null (troca de org), `!catalog` antes aceitava establishment_id residual da URL.
    const catalogAligned =
      Boolean(catalog) &&
      Boolean(active?.organization_id) &&
      catalogOrgRef.current === active?.organization_id;
    const rawEstablishment = params.get("establishment_id") ?? context?.establishment_id ?? undefined;
    const establishmentAllowed =
      !rawEstablishment ||
      Boolean(catalogAligned && catalog!.establishments.some((row) => row.id === rawEstablishment));
    const trustScopedFilters = Boolean(catalogAligned && establishmentAllowed);
    return {
      operational_date: trustScopedFilters
        ? (params.get("operational_date") ?? context?.operational_date ?? defaultBoardDate())
        : (context?.operational_date ?? defaultBoardDate()),
      establishment_id: trustScopedFilters ? rawEstablishment : undefined,
      shift: trustScopedFilters
        ? (params.get("shift") ?? context?.shift ?? undefined)
        : undefined,
      area: trustScopedFilters
        ? (params.get("area") ?? (context?.area ? context.area : undefined))
        : undefined,
      product_id: trustScopedFilters ? (params.get("product_id") ?? undefined) : undefined,
      status: trustScopedFilters ? (params.get("status") ?? undefined) : undefined,
      priority: trustScopedFilters ? (params.get("priority") ?? undefined) : undefined,
      q: trustScopedFilters ? (params.get("q") ?? undefined) : undefined,
    };
  }, [params, context, catalog, active?.organization_id]);

  function setFilter(key: keyof BoardFilters, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "operational_date" && !next.get("operational_date")) {
      next.set("operational_date", filters.operational_date || defaultBoardDate());
    }
    setParams(next, { replace: true });
  }

  useEffect(() => {
    if (!active?.organization_id) return;
    const orgId = active.organization_id;
    const previous = prevOrgRef.current;
    const orgChanged = previous !== null && previous !== orgId;
    prevOrgRef.current = orgId;
    catalogOrgRef.current = orgId;

    let cancelled = false;

    if (orgChanged) {
      // sessionStorage já foi limpo em selectOrganization; URL e estado local ainda carregavam a org anterior.
      setCatalog(null);
      setContext(null);
      setSelected(null);
      setEditingContext(false);
      setConfirmChange(false);
      setParams((prev) => stripBoardQueryParams(prev), { replace: true });
    } else if (previous === null) {
      setContext(readOperationalContext(orgId, userHint));
    }

    void api
      .getBoardContext()
      .then((row) => {
        if (cancelled || catalogOrgRef.current !== orgId) return;
        setCatalog(row.data);
      })
      .catch((error) => {
        if (cancelled || catalogOrgRef.current !== orgId) return;
        if (error instanceof ApiError && error.code === "cancelado") return;
        setCatalog({
          establishments: [],
          shifts: [
            { code: "morning", label: "Manhã" },
            { code: "afternoon", label: "Tarde" },
            { code: "night", label: "Noite" },
          ],
          areas: [
            { code: "fornos", label: "Fornos" },
            { code: "masseira", label: "Masseira" },
          ],
        });
      });

    return () => {
      cancelled = true;
    };
  }, [api, active?.organization_id, userHint, setParams]);

  // Descarta contexto/URL se o estabelecimento não pertence ao catálogo da org ativa.
  useEffect(() => {
    if (!active?.organization_id || !catalog) return;
    const estId = params.get("establishment_id") ?? context?.establishment_id;
    if (!estId) return;
    if (catalog.establishments.some((row) => row.id === estId)) return;
    if (context) {
      writeOperationalContext(active.organization_id, userHint, null);
      setContext(null);
    }
    if (params.get("establishment_id") || params.get("shift") || params.get("area") || params.get("operational_date")) {
      setParams(stripBoardQueryParams(params), { replace: true });
    }
  }, [active?.organization_id, catalog, context, params, setParams, userHint]);

  // Demo: aplicar contexto válido da org ativa (âncora + 1º estabelecimento do catálogo + manhã).
  useEffect(() => {
    if (!config.demoMode || !active?.organization_id || !catalog) return;
    if (catalogOrgRef.current !== active.organization_id) return;
    if (readOperationalContext(active.organization_id, userHint)) return;
    const place = catalog.establishments[0];
    if (!place) return;
    const suggested: OperationalContext = {
      operational_date: config.demoAnchorDate,
      establishment_id: place.id,
      establishment_name: place.display_name,
      shift: "morning",
      area: "",
    };
    writeOperationalContext(active.organization_id, userHint, suggested);
    setContext(suggested);
    const url = new URLSearchParams();
    url.set("operational_date", suggested.operational_date);
    url.set("establishment_id", suggested.establishment_id);
    url.set("shift", suggested.shift);
    setParams(url, { replace: true });
  }, [active?.organization_id, catalog, setParams, userHint]);

  async function load() {
    const generation = ++loadGenerationRef.current;
    setState({ kind: "carregando" });
    try {
      const response = await api.getBoard(filters);
      if (generation !== loadGenerationRef.current) return;
      setState({ kind: "ok", cards: response.data, updatedAt: new Date().toISOString() });
    } catch (error) {
      if (generation !== loadGenerationRef.current) return;
      if (error instanceof ApiError && error.code === "cancelado") return;
      setState({ kind: "erro", error });
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, active?.organization_id, params.toString(), context?.establishment_id, context?.shift, context?.area, context?.operational_date, catalog]);

  function saveContext(next: OperationalContext) {
    if (!active?.organization_id) return;
    writeOperationalContext(active.organization_id, userHint, next);
    setContext(next);
    setEditingContext(false);
    const url = new URLSearchParams(params);
    url.set("operational_date", next.operational_date);
    url.set("establishment_id", next.establishment_id);
    url.set("shift", next.shift);
    if (next.area) url.set("area", next.area);
    else url.delete("area");
    setParams(url, { replace: true });
  }

  function requestChangeContext() {
    if (selected) {
      setConfirmChange(true);
      return;
    }
    setEditingContext(true);
  }

  useEffect(() => {
    if (state.kind === "carregando") {
      publishLive({ pageKind: "loading", next: "Aguardar o quadro." });
      return;
    }
    if (state.kind === "erro") {
      publishLive({ pageKind: "error", blocked: "Quadro indisponível.", next: "Atualizar." });
      return;
    }
    if (selected) {
      publishLive({
        pageKind: "ok",
        entityLabel: selected.order.public_code,
        status: statusLabel(selected.order.status),
        blocked: selected.blocked ? "Ordem bloqueada." : "",
        next: actionLabel(selected.next_action),
      });
      return;
    }
    if (!context) {
      publishLive({ pageKind: "empty", pending: "Contexto do turno ausente.", next: "Definir contexto." });
      return;
    }
    if (state.kind === "ok" && state.cards.length === 0) {
      publishLive({ pageKind: "empty", pending: "Nenhuma ordem neste recorte.", next: "Limpar filtros ou abrir planejamento." });
      return;
    }
    publishLive({ pageKind: "ok", entityLabel: "turno", next: "Abrir uma ordem ou filtrar o quadro." });
  }, [state, selected, context, publishLive]);

  const cards = state.kind === "ok" ? state.cards : [];
  const filteredEmpty = state.kind === "ok" && cards.length === 0 && Boolean(filters.q || filters.status || filters.product_id);
  const noPlan = state.kind === "ok" && cards.length === 0 && !filteredEmpty;
  const establishments = catalog?.establishments ?? [];
  const filterEstablishmentId = filters.establishment_id;
  const orphanEstablishment =
    Boolean(filterEstablishmentId) &&
    establishments.length > 0 &&
    !establishments.some((row) => row.id === filterEstablishmentId);
  const noEstablishments = Boolean(catalog) && establishments.length === 0;
  const areaLabel = context?.area
    ? catalog?.areas.find((row) => row.code === context.area)?.label || context.area
    : "Todas as áreas";

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Quadro de produção</h1>
          <p className="lede">Central do turno: contexto primeiro, filtros depois. Sem custos.</p>
        </div>
        <div>
          <button type="button" className="ghost" onClick={() => void load()}>
            Atualizar
          </button>
          {state.kind === "ok" ? (
            <p className="meta">Dados até {formatDateTime(state.updatedAt)}</p>
          ) : null}
        </div>
      </div>

      {context && !editingContext ? (
        <p className="context-strip">
          {formatContextDate(context.operational_date)} · {context.establishment_name} · {shiftLabel(context.shift)} · {areaLabel}
          {" "}
          <button type="button" className="ghost" onClick={requestChangeContext}>
            Trocar contexto
          </button>
        </p>
      ) : (
        <form
          className="panel"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const establishmentId = String(data.get("establishment_id") || "");
            const place = establishments.find((row) => row.id === establishmentId);
            if (!place) return;
            saveContext({
              operational_date: String(data.get("operational_date") || defaultBoardDate()),
              establishment_id: place.id,
              establishment_name: place.display_name,
              shift: String(data.get("shift") || "morning"),
              area: String(data.get("area") || ""),
            });
          }}
        >
          <h2>Definir contexto do turno</h2>
          <p>
            {config.demoMode
              ? `Cenário demonstrativo: data-âncora ${config.demoAnchorDate}, primeiro estabelecimento do catálogo, turno manhã. Área opcional (na API filtra só o código público).`
              : "Escolha catálogos. Sem digitar identificador."}
          </p>
          <div className="grid-2">
            <label>
              Data operacional
              <input name="operational_date" type="date" defaultValue={filters.operational_date || defaultBoardDate()} required />
            </label>
            <label>
              Estabelecimento
              <select
                key={`est-${active?.organization_id || "none"}-${establishments.map((row) => row.id).join(",")}`}
                name="establishment_id"
                defaultValue={context?.establishment_id || establishments[0]?.id || ""}
                required
              >
                {establishments.map((row) => (
                  <option key={row.id} value={row.id}>{row.display_name}</option>
                ))}
              </select>
            </label>
            <label>
              Turno
              <select
                key={`shift-${active?.organization_id || "none"}`}
                name="shift"
                defaultValue={context?.shift || "morning"}
              >
                {(catalog?.shifts ?? []).map((row) => (
                  <option key={row.code} value={row.code}>{row.label}</option>
                ))}
              </select>
            </label>
            <label>
              Área ou estação
              <select
                key={`area-${active?.organization_id || "none"}`}
                name="area"
                defaultValue={context?.area || ""}
              >
                <option value="">Todas as áreas</option>
                {(catalog?.areas ?? []).map((row) => (
                  <option key={row.code} value={row.code}>{row.label}</option>
                ))}
              </select>
            </label>
          </div>
          <button type="submit" className="primary">Usar este contexto</button>
        </form>
      )}

      <div className="stat-grid">
        {BUCKETS.map((bucket) => {
          const count = cards.filter(bucket.match).length;
          const on = filters.status === bucket.id;
          return (
            <button
              key={bucket.id}
              type="button"
              className={`stat-card ${on ? "is-on" : ""}`}
              onClick={() => {
                if (bucket.id === "blocked") setFilter("status", on ? "" : "on_hold");
                else if (bucket.id === "awaiting") setFilter("status", on ? "" : "released");
                else if (bucket.id === "weighing") setFilter("status", on ? "" : "in_weighing");
                else if (bucket.id === "ready") setFilter("status", on ? "" : "ready");
                else if (bucket.id === "running") setFilter("status", on ? "" : "in_progress");
                else if (bucket.id === "done") setFilter("status", on ? "" : "completed");
                else setFilter("status", on ? "" : "short_closed");
              }}
            >
              <span>{bucket.label}</span>
              <strong>{count}</strong>
            </button>
          );
        })}
      </div>

      <div className="view-toggle" role="group" aria-label="Visualização">
        <button type="button" className={`chip ${view === "fluxo" ? "is-on" : ""}`} aria-pressed={view === "fluxo"} onClick={() => setView("fluxo")}>Fluxo por estado</button>
        <button type="button" className={`chip ${view === "lista" ? "is-on" : ""}`} aria-pressed={view === "lista"} onClick={() => setView("lista")}>Lista gerencial</button>
        <button type="button" className={`chip ${view === "estacao" ? "is-on" : ""}`} aria-pressed={view === "estacao"} onClick={() => setView("estacao")}>Por estação</button>
      </div>

      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <label>
          Código ou texto
          <input value={filters.q ?? ""} onChange={(event) => setFilter("q", event.target.value)} />
        </label>
        <button type="button" className="chip" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((open) => !open)}>
          {filtersOpen ? "Recolher filtros" : "Filtros temporários"}
        </button>
        {filters.q || filters.status || filters.product_id ? (
          <button type="button" className="ghost" onClick={() => {
            const next = new URLSearchParams(params);
            next.delete("q");
            next.delete("status");
            next.delete("product_id");
            next.delete("priority");
            setParams(next, { replace: true });
          }}>
            Limpar filtros
          </button>
        ) : null}
        {filtersOpen ? (
          <>
            <label>
              Produto
              <input value={filters.product_id ?? ""} onChange={(event) => setFilter("product_id", event.target.value)} list="board-products" />
              <datalist id="board-products">
                {[...new Set(cards.map((card) => card.product.display_name))].map((name) => (
                  <option key={name} value={name} />
                ))}
              </datalist>
            </label>
            <label>
              Estado
              <select value={filters.status ?? ""} onChange={(event) => setFilter("status", event.target.value)}>
                <option value="">Todos</option>
                <option value="released">Liberada</option>
                <option value="in_weighing">Em pesagem</option>
                <option value="ready">Pronta</option>
                <option value="in_progress">Em execução</option>
                <option value="on_hold">Em espera</option>
                <option value="completed">Concluída</option>
                <option value="short_closed">Encerrada parcial</option>
              </select>
            </label>
            <label>
              Prioridade
              <input inputMode="numeric" value={filters.priority ?? ""} onChange={(event) => setFilter("priority", event.target.value)} />
            </label>
            <label>
              Bloqueio
              <select value={filters.status === "on_hold" ? "blocked" : ""} onChange={(event) => setFilter("status", event.target.value === "blocked" ? "on_hold" : "")}>
                <option value="">Todos</option>
                <option value="blocked">Com bloqueio ou ocorrência</option>
              </select>
            </label>
          </>
        ) : null}
      </form>

      {state.kind === "carregando" ? <LoadingState>Carregando o quadro…</LoadingState> : null}
      {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => void load()} /> : null}
      {orphanEstablishment ? (
        <div className="empty-card" role="status">
          O estabelecimento do contexto anterior não pertence a esta organização. O filtro foi descartado.
        </div>
      ) : null}
      {noEstablishments ? (
        <div className="empty-card" role="status">
          Esta organização não tem estabelecimento autorizado para o quadro.
        </div>
      ) : null}
      {!context && !editingContext && !orphanEstablishment ? (
        <div className="empty-card" role="status">
          Contexto ainda não definido. O quadro lê a organização, mas o turno fica mais claro com a faixa.
          <div><button type="button" className="primary" onClick={() => setEditingContext(true)}>Definir contexto</button></div>
        </div>
      ) : null}
      {filteredEmpty ? (
        <EmptyState>
          Os filtros eliminaram os resultados. <button type="button" className="ghost" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Limpar filtros</button>
        </EmptyState>
      ) : null}
      {noPlan && !filteredEmpty && !orphanEstablishment ? (
        <EmptyState>
          Não há ordens para os filtros atuais nesta organização. <Link to="/planejamento">Abrir planejamento</Link>
        </EmptyState>
      ) : null}

      {state.kind === "ok" && cards.length > 0 && view === "fluxo" ? (
        <div className="cards">
          {BUCKETS.map((bucket) => {
            const rows = cards.filter(bucket.match);
            if (!rows.length) return null;
            return (
              <article key={bucket.id} className="card">
                <h2>{bucket.label}</h2>
                <ul className="list">
                  {rows.map((card) => (
                    <li key={card.order.id}>
                      <button type="button" className="ghost" onClick={() => setSelected(card)}>
                        {card.order.public_code} · {card.product.display_name}
                      </button>
                    </li>
                  ))}
                </ul>
              </article>
            );
          })}
        </div>
      ) : null}

      {state.kind === "ok" && cards.length > 0 && view === "estacao" ? (
        <div className="cards">
          {[...new Set(cards.map(stationOf))].map((station) => (
            <article key={station} className="card">
              <h2>{station}</h2>
              <ul className="list">
                {cards.filter((card) => stationOf(card) === station).map((card) => (
                  <li key={card.order.id}>
                    <button type="button" className="ghost" onClick={() => setSelected(card)}>
                      {card.order.public_code} · {statusLabel(card.order.status)}
                    </button>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : null}

      {state.kind === "ok" && cards.length > 0 ? (
        <div className="table-wrap">
          <table>
            <caption className="visually-hidden">Ordens do quadro de produção</caption>
            <thead>
              <tr>
                <th>Produto</th>
                <th>Ordem / batelada</th>
                <th>Alvo</th>
                <th>Horário</th>
                <th>Estado</th>
                <th>Etapa</th>
                <th>Bloqueio</th>
                <th>Próxima ação</th>
              </tr>
            </thead>
            <tbody>
              {cards.map((card) => (
                <tr
                  key={card.order.id}
                  className={card.blocked ? "blocked" : undefined}
                  tabIndex={0}
                  onClick={() => setSelected(card)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") setSelected(card);
                  }}
                >
                  <td>{card.product.display_name}</td>
                  <td>
                    {card.order.public_code}
                    <div className="meta">
                      {card.batches.map((batch) => batch.operational_code).join(", ") || "Sem batelada"}
                    </div>
                  </td>
                  <td>
                    {formatDecimal(card.quantity)} {card.target_mode === "mass" ? "g" : card.target_mode === "units" ? "un" : card.target_mode}
                  </td>
                  <td>
                    {formatDateTime(card.planned_start_at)}
                    <div className="meta">{shiftLabel(card.shift)}</div>
                  </td>
                  <td>
                    <StatusBadge tone={toneForStatus(card.order.status)} label={statusLabel(card.order.status)} />
                    {card.delayed ? (
                      <div>
                        <StatusBadge tone="atencao" label="Atrasada" />
                      </div>
                    ) : null}
                  </td>
                  <td>{card.current_step ?? "—"}</td>
                  <td>
                    {card.blocked ? "Bloqueada" : "Livre"}
                    {card.open_occurrences ? ` · ${card.open_occurrences} ocorrência(s)` : ""}
                  </td>
                  <td>
                    {actionLabel(card.next_action)}
                    <div>
                      <Link
                        to={`/producao/ordens/${card.order.id}/executar`}
                        onClick={(event) => event.stopPropagation()}
                      >
                        Executar
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {selected ? (
        <>
          <button type="button" className="order-drawer-mask" aria-label="Fechar ordem" onClick={() => setSelected(null)} />
          <aside className="order-drawer" role="dialog" aria-label="Ordem selecionada">
            <h2>{selected.order.public_code}</h2>
            <p>
              {canReadProducts && selected.product.id ? (
                <Link to={`/produtos/${selected.product.id}`}>{selected.product.display_name}</Link>
              ) : (
                selected.product.display_name
              )}
            </p>
            <p className="meta">
              {formatDecimal(selected.quantity)}{" "}
              {selected.target_mode === "mass" ? "g" : selected.target_mode === "units" ? "un" : selected.target_mode} ·
              prioridade {selected.order.priority}
            </p>
            <p>
              <StatusBadge tone={toneForStatus(selected.order.status)} label={statusLabel(selected.order.status)} />
              {" "}
              {selected.blocked ? <StatusBadge tone="erro" label="Bloqueada" /> : <StatusBadge tone="sucesso" label="Livre" />}
            </p>
            <p>Próxima ação: {actionLabel(selected.next_action)}</p>
            <p>
              <Link className="primary" to={`/producao/ordens/${selected.order.id}/executar`}>Executar</Link>
              {" "}
              <Link className="ghost" to={`/ordens/${selected.order.id}`}>Detalhe</Link>
            </p>
            <button type="button" className="ghost" onClick={() => setSelected(null)}>Fechar</button>
          </aside>
        </>
      ) : null}

      {confirmChange ? (
        <div className="confirm" role="alertdialog" aria-label="Confirmar troca de contexto">
          <p>Há uma ordem aberta na gaveta. Trocar o contexto agora?</p>
          <button type="button" className="primary" onClick={() => { setSelected(null); setConfirmChange(false); setEditingContext(true); }}>Trocar</button>
          <button type="button" className="ghost" onClick={() => setConfirmChange(false)}>Cancelar</button>
        </div>
      ) : null}

    </section>
  );
}
