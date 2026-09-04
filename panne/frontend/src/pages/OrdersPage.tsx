import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { Order } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { formatTargetQuantity, statusLabel } from "../format";
import { canOfferFloorExecution, floorExecutionHint } from "../orderListActions";
import { useOrganization } from "../session/OrganizationContext";

function productLabel(order: Order): string {
  const name = order.product?.display_name?.trim();
  return name || "Produto ausente";
}

function planLabel(order: Order): string {
  const code = order.plan?.public_code?.trim();
  if (code) return code;
  if (order.plan_id) return "Plano sem código legível";
  return "—";
}

export function OrdersPage() {
  const { api, hasPermission, active } = useOrganization();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Order[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<"carregando" | "ok" | "erro">("carregando");
  const [error, setError] = useState<unknown>(null);
  const status = params.get("status") ?? "";
  const canReadProducts = hasPermission("product.read");

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
    setItems([]);
    setCursor(null);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, status, active?.organization_id]);

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
            <option value="in_weighing">Em pesagem</option>
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
                <th>Produto</th>
                <th>Código</th>
                <th>Plano</th>
                <th>Alvo</th>
                <th>Prioridade</th>
                <th>Estado</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((order) => {
                const detailTo = status
                  ? `/ordens/${order.id}?from_status=${encodeURIComponent(status)}`
                  : `/ordens/${order.id}`;
                const codeLabel = `Abrir detalhe da ordem ${order.public_code}`;
                const detailActionLabel = `Detalhe da ordem ${order.public_code}`;
                const executeLabel = `Executar ordem ${order.public_code}`;
                const showExecute = canOfferFloorExecution(order.status, hasPermission);
                const execHint = floorExecutionHint(order.status);
                const productTo = order.product?.id ? `/produtos/${order.product.id}` : null;
                return (
                  <tr key={order.id}>
                    <td>
                      {productTo && canReadProducts ? (
                        <Link to={productTo} aria-label={`Abrir produto ${productLabel(order)}`}>
                          {productLabel(order)}
                        </Link>
                      ) : (
                        productLabel(order)
                      )}
                    </td>
                    <td>
                      <Link to={detailTo} aria-label={codeLabel}>
                        {order.public_code}
                      </Link>
                    </td>
                    <td>
                      {order.plan?.id ? (
                        <Link
                          to={`/planejamento/${order.plan.id}`}
                          aria-label={`Abrir plano ${planLabel(order)}`}
                        >
                          {planLabel(order)}
                        </Link>
                      ) : (
                        planLabel(order)
                      )}
                    </td>
                    <td>{formatTargetQuantity(order.target_quantity, order.target_mode)}</td>
                    <td>{order.priority}</td>
                    <td>
                      <StatusBadge tone="neutro" label={statusLabel(order.status)} />
                    </td>
                    <td>
                      <Link to={detailTo} aria-label={detailActionLabel}>
                        Detalhe
                      </Link>
                      {showExecute ? (
                        <>
                          {" · "}
                          <Link
                            to={`/producao/ordens/${order.id}/executar`}
                            aria-label={executeLabel}
                          >
                            Executar
                          </Link>
                        </>
                      ) : execHint ? (
                        <span className="meta"> · {execHint}</span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
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
