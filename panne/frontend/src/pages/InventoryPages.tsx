import { type ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CountMentor, PurchaseMentor } from "../components/InventoryMentors";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

type Row = Record<string, unknown>;

function tone(status: string): "sucesso" | "atencao" | "erro" | "info" {
  if (["available", "posted", "approved", "issued", "received", "reserved", "closed"].includes(status)) return "sucesso";
  if (["partial", "partially_received", "draft", "submitted", "counting", "review"].includes(status)) return "atencao";
  if (["blocked", "expired", "rejected", "cancelled", "failed"].includes(status)) return "erro";
  return "info";
}

function useItems(path: string) {
  const { api, active } = useOrganization();
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: Row[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  function load() {
    setState({ kind: "carregando" });
    api
      .listInventory(path)
      .then((body) => setState({ kind: "ok", items: body.items }))
      .catch((error) => setState({ kind: "erro", error }));
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, active?.organization_id]);
  return { state, load, api };
}

function Screen({
  title,
  lede,
  path,
  children,
}: {
  title: string;
  lede: string;
  path: string;
  children?: (items: Row[], reload: () => void) => ReactNode;
}) {
  const { state, load } = useItems(path);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") {
    return <ErrorState error={state.error} onRetry={load} />;
  }
  return (
    <div className="stage">
      <div>
        <h1>{title}</h1>
        <p className="lede">{lede}</p>
        {state.items.length === 0 ? <EmptyState>Não há registros nesta organização.</EmptyState> : null}
        {children ? children(state.items, load) : null}
      </div>
    </div>
  );
}

export function InventoryOverviewPage() {
  const { hasPermission } = useOrganization();
  const { state, load } = useItems("/inventory/balances");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  const first = state.items[0];
  const physical = first ? String(first.physical_quantity ?? "ausente") : "ausente";
  const reserved = first ? String(first.reserved_quantity ?? "ausente") : "ausente";
  const available = first ? String(first.available_quantity ?? "ausente") : "ausente";
  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Estoque</h1>
            <p className="lede">
              Saldo físico é a soma das movimentações. Reservado ainda está no local. Disponível é físico menos reserva.
              Em trânsito não entra no físico. Ausência de saldo não é zero.
            </p>
          </div>
        </div>
        <div className="cards">
          <article className="card">
            <h2>Físico</h2>
            <p>{physical || "ausente"}</p>
          </article>
          <article className="card">
            <h2>Reservado</h2>
            <p>{reserved || "ausente"}</p>
          </article>
          <article className="card">
            <h2>Disponível</h2>
            <p>{available || "ausente"}</p>
          </article>
          <article className="card">
            <h2>Em trânsito</h2>
            <p>Pedidos emitidos e ainda não recebidos.</p>
          </article>
        </div>
        {hasPermission("inventory.read") ? (
          <p>
            <Link className="primary" to="/componentes/estoque/posicao">
              Abrir posição
            </Link>
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function InventoryPositionPage() {
  return (
    <Screen
      title="Posição de estoque"
      lede="Tabela por item, local e lote. Sem valor contábil."
      path="/inventory/balances"
    >
      {(items) => (
        <div className="table-wrap">
          <table>
            <caption>Posição reconciliável com o ledger</caption>
            <thead>
              <tr>
                <th>Item</th>
                <th>Local</th>
                <th>Lote</th>
                <th>Físico</th>
                <th>Reservado</th>
                <th>Disponível</th>
                <th>Unidade</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={String(row.id)}>
                  <td>{String(row.item_label || "item sem nome")}</td>
                  <td>{String(row.location_label || "local sem nome")}</td>
                  <td>{String(row.lot_code || "lote sem código")}</td>
                  <td>{String(row.physical_quantity)}</td>
                  <td>{String(row.reserved_quantity)}</td>
                  <td>{String(row.available_quantity)}</td>
                  <td>{String(row.unit_code)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Screen>
  );
}

export function InventoryLotsPage() {
  const { hasPermission } = useOrganization();
  return (
    <Screen title="Lotes e validade" lede="Lote vencido ou bloqueado não é sugerido sem override auditável." path="/inventory/lots">
      {(items) => (
        <ul>
          {items.map((row) => (
            <li key={String(row.id)}>
              <strong>{String(row.internal_lot_code)}</strong>{" "}
              <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
              {row.item_label ? <span className="meta"> {String(row.item_label)}</span> : null}
              {row.expires_on ? <span className="meta"> validade {String(row.expires_on)}</span> : <span className="meta"> validade ausente</span>}
              {hasPermission("inventory.lot.manage") ? <span className="visually-hidden">gestão de lote autorizada</span> : null}
            </li>
          ))}
        </ul>
      )}
    </Screen>
  );
}

export function InventoryReservationsPage() {
  return (
    <Screen title="Reservas" lede="Reserva não altera o saldo físico. Ordem antiga exige adoção humana." path="/inventory/reservations">
      {(items) => (
        <ul>
          {items.map((row) => (
            <li key={String(row.id)}>
              <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />{" "}
              necessário {String(row.required_quantity)} · reservado {String(row.reserved_quantity)}
              {row.adopted ? <span className="meta"> adoção histórica</span> : null}
            </li>
          ))}
        </ul>
      )}
    </Screen>
  );
}

export function InventoryMovementsPage() {
  return (
    <Screen title="Movimentações" lede="Ledger append-only. Erro se corrige com reversão, nunca com edição." path="/inventory/movements">
      {(items) => (
        <ol>
          {items.map((row) => (
            <li key={String(row.id)}>
              {String(row.movement_type)} · {String(row.canonical_quantity)} · {String(row.origin_type)}
            </li>
          ))}
        </ol>
      )}
    </Screen>
  );
}

export function InventoryPicksPage() {
  const { api, hasPermission } = useOrganization();
  const { state, load } = useItems("/inventory/picks");
  const [orderId, setOrderId] = useState("");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Separação</h1>
        <p className="lede">FEFO sugere. A pessoa confirma o lote real. Sem QR obrigatório neste ciclo.</p>
        {state.items.length === 0 ? <EmptyState>Não há listas de separação.</EmptyState> : null}
        <ul>
          {state.items.map((row) => (
            <li key={String(row.id)}>
              {String(row.public_code)} <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
              <button type="button" className="ghost" onClick={() => window.print()}>
                Imprimir lista
              </button>
            </li>
          ))}
        </ul>
        {hasPermission("inventory.separate") ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              api
                .catalogCommand("/inventory/picks", { body: { production_order_id: orderId, lines: [] } })
                .then(load)
                .catch(() => load());
            }}
          >
            <label>
              Ordem
              <input value={orderId} onChange={(event) => setOrderId(event.target.value)} />
            </label>
            <button type="submit" className="primary">
              Confirmar separação
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
}

export function InventoryCountsPage() {
  const { api, hasPermission } = useOrganization();
  const { state, load } = useItems("/inventory/counts");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Inventários</h1>
        <p className="lede">Contagem física com corte, escopo congelado e ajuste só por movimento. Reabertura é proibida.</p>
        {state.items.length === 0 ? <EmptyState>Não há sessões de inventário.</EmptyState> : null}
        <ul>
          {state.items.map((row) => (
            <li key={String(row.id)}>
              {String(row.public_code)} <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} />
              {Array.isArray(row.variances)
                ? row.variances.map((item) => (
                    <span key={String((item as Row).scope_id)} className="meta">
                      {" "}
                      divergência {String((item as Row).variance ?? "ausente")}
                    </span>
                  ))
                : null}
              {hasPermission("inventory.count.approve") && String(row.status) !== "closed" ? (
                <button
                  type="button"
                  className="primary"
                  onClick={() =>
                    api
                      .catalogCommand(`/inventory/counts/${row.id}/approve`, { ifMatch: Number(row.row_version) })
                      .then(load)
                      .catch(load)
                  }
                >
                  Aprovar e ajustar
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      <CountMentor step={state.items.length ? 3 : 0} />
    </div>
  );
}

export function ProcurementNeedsPage() {
  const { api, hasPermission } = useOrganization();
  const [data, setData] = useState<Row | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    api
      .catalogCommand<{ data: Row }>("/inventory/replenishment", { body: { horizon_days: 7 } })
      .then((body) => setData(body.data))
      .catch(setError);
  }, [api]);
  if (error) return <ErrorState error={error} />;
  if (!data && hasPermission("procurement.read")) return <LoadingState />;
  const items = (data?.items as Row[]) || [];
  return (
    <div className="stage">
      <div>
        <h1>Necessidades</h1>
        <p className="lede">Sugestão determinística. Não há compra automática nem previsão por IA.</p>
        {items.length === 0 ? <EmptyState>Não há necessidade calculada ou faltam dados explícitos.</EmptyState> : null}
        <ul>
          {items.map((row) => (
            <li key={String(row.inventory_item_id)}>
              {String(row.item_label || "item sem nome")} · sugerido {String(row.suggested_quantity)} · lacunas{" "}
              {JSON.stringify(row.gaps)}
            </li>
          ))}
        </ul>
      </div>
      <PurchaseMentor step={0} />
    </div>
  );
}

export function ProcurementListPage({
  title,
  path,
  lede,
}: {
  title: string;
  path: string;
  lede: string;
}) {
  const { hasPermission } = useOrganization();
  const showPrice = hasPermission("supplier.price.record") || hasPermission("procurement.order.manage");
  return (
    <Screen title={title} lede={lede} path={path}>
      {(items) => (
        <ul>
          {items.map((row) => (
            <li key={String(row.id)}>
              {String(row.public_code || "código ausente")}{" "}
              {row.status ? <StatusBadge tone={tone(String(row.status))} label={statusLabel(String(row.status))} /> : null}
              {row.supplier_name ? <span className="meta"> {String(row.supplier_name)}</span> : null}
              {showPrice && row.items && Array.isArray(row.items)
                ? (row.items as Row[]).map((item) =>
                    item.unit_price ? <span key={String(item.id)} className="meta"> {String(item.unit_price)}</span> : null,
                  )
                : null}
            </li>
          ))}
        </ul>
      )}
    </Screen>
  );
}

export function ProcurementQuotesPage() {
  const { api } = useOrganization();
  const { state, load } = useItems("/procurement/quotations");
  const [compared, setCompared] = useState<Row[]>([]);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Cotações</h1>
        <p className="lede">Comparação por preço unitário e prazo. Nenhuma escolha automática de fornecedor.</p>
        {state.items.length === 0 ? <EmptyState>Não há cotações registradas.</EmptyState> : null}
        <ul>
          {state.items.map((row) => (
            <li key={String(row.id)}>
              fornecedor {String(row.supplier_name || "sem nome")} · prazo {String(row.lead_time_days ?? "ausente")}
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="primary"
          onClick={() => {
            const first = state.items[0]?.items as Row[] | undefined;
            const itemId = first?.[0]?.inventory_item_id;
            if (!itemId) return;
            api.listInventory("/procurement/quotations/compare", { inventory_item_id: String(itemId) }).then((body) => {
              setCompared(body.items);
            });
          }}
        >
          Comparar
        </button>
        {compared.length ? (
          <table>
            <caption>Comparação determinística</caption>
            <thead>
              <tr>
                <th>Fornecedor</th>
                <th>Preço unitário</th>
                <th>Prazo</th>
                <th>Escolhido</th>
              </tr>
            </thead>
            <tbody>
              {compared.map((row) => (
                <tr key={String(row.quotation_id)}>
                  <td>{String(row.supplier_name || "sem nome")}</td>
                  <td>{String(row.unit_price)}</td>
                  <td>{String(row.lead_time_days ?? "ausente")}</td>
                  <td>{row.chosen ? "não automático" : "não"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
      <PurchaseMentor step={5} />
    </div>
  );
}
