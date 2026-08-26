import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { Order } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDecimal, statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

export function OrdersPage() {
  const { api } = useOrganization();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<Order[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<"carregando" | "ok" | "erro">("carregando");
  const [error, setError] = useState<unknown>(null);
  const status = params.get("status") ?? "";

  async function load(next?: string | null, append = false) {
    setState("carregando");
    try {
      const page = await api.listOrders({ status: status || undefined, cursor: next ?? undefined });
      setItems((current) => (append ? [...current, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setState("ok");
    } catch (err) {
      setError(err);
      setState("erro");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, status]);

  return (
    <section>
      <ListLive
        kind={state}
        empty={state === "ok" && items.length === 0}
        entityLabel={items[0]?.public_code || "ordem"}
        status={state === "ok" ? `${items.length} itens` : undefined}
      />
      <div className="page-head">
        <h1>Ordens</h1>
      </div>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <label>
          Estado
          <select
            value={status}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("status", event.target.value);
              else next.delete("status");
              setParams(next, { replace: true });
            }}
          >
            <option value="">Todos</option>
            <option value="draft">Rascunho</option>
            <option value="released">Liberada</option>
            <option value="in_progress">Em execução</option>
            <option value="completed">Concluída</option>
            <option value="cancelled">Cancelada</option>
          </select>
        </label>
      </form>
      {state === "carregando" && items.length === 0 ? <LoadingState /> : null}
      {state === "erro" ? <ErrorState error={error} onRetry={() => void load()} /> : null}
      {state === "ok" && items.length === 0 ? <EmptyState>Nenhuma ordem nesta organização.</EmptyState> : null}
      {items.length > 0 ? (
        <div className="table-wrap">
          <table>
            <caption className="visually-hidden">Lista de ordens</caption>
            <thead>
              <tr>
                <th>Código</th>
                <th>Plano</th>
                <th>Alvo</th>
                <th>Prioridade</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {items.map((order) => (
                <tr key={order.id} tabIndex={0} onClick={() => navigate(`/ordens/${order.id}`)}>
                  <td>{order.public_code}</td>
                  <td>{order.plan_id ?? "—"}</td>
                  <td>{formatDecimal(order.target_quantity)}</td>
                  <td>{order.priority}</td>
                  <td>
                    <StatusBadge tone="neutro" label={statusLabel(order.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {cursor ? (
        <button type="button" className="ghost" onClick={() => void load(cursor, true)}>
          Carregar mais
        </button>
      ) : null}
    </section>
  );
}
