import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { BoardCard, BoardFilters } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { actionLabel, formatDateTime, formatDecimal, shiftLabel, statusLabel, todayIso } from "../format";
import { useOrganization } from "../session/OrganizationContext";

function toneForStatus(status: string): "sucesso" | "atencao" | "erro" | "info" | "neutro" {
  if (status === "completed") return "sucesso";
  if (status === "cancelled" || status === "short_closed") return "erro";
  if (status === "on_hold" || status === "delayed") return "atencao";
  if (status === "in_progress" || status === "in_weighing") return "info";
  return "neutro";
}

export function BoardPage() {
  const { api, active } = useOrganization();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; cards: BoardCard[]; updatedAt: string }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  const filters = useMemo<BoardFilters>(
    () => ({
      operational_date: params.get("operational_date") ?? todayIso(),
      establishment_id: params.get("establishment_id") ?? undefined,
      shift: params.get("shift") ?? undefined,
      area: params.get("area") ?? undefined,
      product_id: params.get("product_id") ?? undefined,
      status: params.get("status") ?? undefined,
      priority: params.get("priority") ?? undefined,
      q: params.get("q") ?? undefined,
    }),
    [params],
  );

  function setFilter(key: keyof BoardFilters, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "operational_date" && !next.get("operational_date")) {
      next.set("operational_date", todayIso());
    }
    setParams(next, { replace: true });
  }

  async function load() {
    setState({ kind: "carregando" });
    try {
      const response = await api.getBoard(filters);
      setState({ kind: "ok", cards: response.data, updatedAt: new Date().toISOString() });
    } catch (error) {
      if (error instanceof ApiError && error.code === "cancelado") return;
      setState({ kind: "erro", error });
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, active?.organization_id, params.toString()]);

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Quadro de produção</h1>
          <p className="meta">
            {active?.display_name}. Projeção operacional, sem custos. Linhas compactas para
            aproveitar a área útil.
          </p>
        </div>
        <div>
          <button type="button" className="ghost" onClick={() => void load()}>
            Atualizar
          </button>
          {state.kind === "ok" ? (
            <p className="meta">Atualizado às {formatDateTime(state.updatedAt)}</p>
          ) : null}
        </div>
      </div>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <label>
          Data
          <input
            type="date"
            value={filters.operational_date ?? ""}
            onChange={(event) => setFilter("operational_date", event.target.value)}
          />
        </label>
        <label>
          Estabelecimento
          <input
            value={filters.establishment_id ?? ""}
            onChange={(event) => setFilter("establishment_id", event.target.value)}
          />
        </label>
        <label>
          Turno
          <select value={filters.shift ?? ""} onChange={(event) => setFilter("shift", event.target.value)}>
            <option value="">Todos</option>
            <option value="morning">Manhã</option>
            <option value="afternoon">Tarde</option>
            <option value="night">Noite</option>
          </select>
        </label>
        <label>
          Área/estação
          <input value={filters.area ?? ""} onChange={(event) => setFilter("area", event.target.value)} />
        </label>
        <label>
          Produto
          <input
            value={filters.product_id ?? ""}
            onChange={(event) => setFilter("product_id", event.target.value)}
          />
        </label>
        <label>
          Estado
          <select
            value={filters.status ?? ""}
            onChange={(event) => setFilter("status", event.target.value)}
          >
            <option value="">Todos</option>
            <option value="released">Liberada</option>
            <option value="in_weighing">Em pesagem</option>
            <option value="in_progress">Em execução</option>
            <option value="on_hold">Em espera</option>
            <option value="completed">Concluída</option>
          </select>
        </label>
        <label>
          Prioridade
          <input
            inputMode="numeric"
            value={filters.priority ?? ""}
            onChange={(event) => setFilter("priority", event.target.value)}
          />
        </label>
        <label>
          Código ou texto
          <input value={filters.q ?? ""} onChange={(event) => setFilter("q", event.target.value)} />
        </label>
      </form>
      {state.kind === "carregando" ? <LoadingState>Carregando o quadro…</LoadingState> : null}
      {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => void load()} /> : null}
      {state.kind === "ok" && state.cards.length === 0 ? (
        <EmptyState>Não há ordens para os filtros atuais nesta organização.</EmptyState>
      ) : null}
      {state.kind === "ok" && state.cards.length > 0 ? (
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
              {state.cards.map((card) => (
                <tr
                  key={card.order.id}
                  className={card.blocked ? "blocked" : undefined}
                  tabIndex={0}
                  onClick={() => navigate(`/ordens/${card.order.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") navigate(`/ordens/${card.order.id}`);
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
                    {formatDecimal(card.quantity)} {card.target_mode === "mass" ? "g" : card.target_mode}
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
                  <td>{actionLabel(card.next_action)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
