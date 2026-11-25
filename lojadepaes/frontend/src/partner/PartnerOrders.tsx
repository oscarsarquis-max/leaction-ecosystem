import { useCallback, useEffect, useState, type FormEvent } from "react";
import { formatCents } from "../lib/money";
import { Button } from "../admin/shell/Button";
import type { Partner } from "../admin/marketplace/types";
import { PartnerApiError, partnerApi, type PartnerOrder } from "./partnerApi";

type Props = { onBack: () => void; partner?: Partner; onPayout?: () => void };

const STATUS: Record<string, { label: string; tone: string }> = {
  submitted: { label: "Aguardando você", tone: "c-acc" },
  accepted: { label: "Confirmado", tone: "c-prod" },
  refused: { label: "Recusado", tone: "c-none" },
  expired: { label: "Prazo vencido", tone: "c-warn" },
  cancelled: { label: "Cancelado", tone: "c-none" },
  delivered: { label: "Entregue", tone: "c-prod" },
};

const FILTERS: Array<[string, string]> = [
  ["open", "Para decidir"],
  ["accepted", "Confirmados"],
  ["done", "Encerrados"],
];

const DAY = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit", timeZone: "UTC" });
const STAMP = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

function dayLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return DAY.format(new Date(Date.UTC(y, m - 1, d)));
}

function inFilter(order: PartnerOrder, filter: string): boolean {
  if (filter === "open") return order.status === "submitted";
  if (filter === "accepted") return order.status === "accepted";
  return ["refused", "expired", "cancelled", "delivered"].includes(order.status);
}

function errorText(reason: unknown, fallback: string): string {
  return reason instanceof PartnerApiError ? reason.message : fallback;
}

export function PartnerOrders({ onBack, partner, onPayout }: Props) {
  // Recebimento pelo Mercado Pago ligado e conta ainda não conectada: confirmar fica bloqueado (o backend também recusa).
  const needsPayout = partner?.mp_connected === false;
  const [orders, setOrders] = useState<PartnerOrder[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("open");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [refusing, setRefusing] = useState<{ id: string; reason: string } | null>(null);
  const [refuseError, setRefuseError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setOrders(await partnerApi.orders());
    } catch (reason) {
      setError(errorText(reason, "Não foi possível carregar os pedidos."));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(order: PartnerOrder, action: "accept" | "delivered", message: string) {
    setBusyId(order.id);
    setError(null);
    setFlash(null);
    try {
      const updated = action === "accept" ? await partnerApi.acceptOrder(order.id) : await partnerApi.deliveredOrder(order.id);
      setOrders((current) => (current ?? []).map((row) => (row.id === order.id ? updated : row)));
      setFlash(message);
    } catch (reason) {
      setError(errorText(reason, "Não foi possível atualizar o pedido."));
    } finally {
      setBusyId(null);
    }
  }

  async function refuse(event: FormEvent) {
    event.preventDefault();
    if (!refusing) return;
    if (!refusing.reason.trim()) {
      setRefuseError("Diga ao cliente por que não vai dar.");
      return;
    }
    setBusyId(refusing.id);
    setRefuseError(null);
    try {
      const updated = await partnerApi.refuseOrder(refusing.id, refusing.reason.trim());
      setOrders((current) => (current ?? []).map((row) => (row.id === refusing.id ? updated : row)));
      setRefusing(null);
      setFlash("Pedido recusado. O cliente foi avisado; o pão da Loja continua.");
    } catch (reason) {
      setRefuseError(errorText(reason, "Não foi possível recusar o pedido."));
    } finally {
      setBusyId(null);
    }
  }

  const visible = (orders ?? []).filter((order) => inFilter(order, filter));
  const count = (key: string) => (orders ?? []).filter((order) => inFilter(order, key)).length;

  return (
    <>
      <a
        className="mkt-back"
        href="/parceiro"
        onClick={(event) => {
          event.preventDefault();
          onBack();
        }}
      >
        ← Meus produtos
      </a>
      <header className="admin-page-header">
        <div>
          <h1>Pedidos</h1>
          <p>
            Pedidos de combos com o seu produto. Confirme até o prazo; depois do aceite o cliente paga a sua parte direto a
            você e você entrega na data da fornada.
          </p>
        </div>
      </header>

      {needsPayout ? (
        <div className="ptn-banner ptn-banner-action" role="status">
          <span>
            <strong>Conecte sua conta do Mercado Pago para confirmar pedidos.</strong> É nela que o cliente paga a sua parte.
          </span>
          {onPayout ? (
            <Button variant="primary" onClick={onPayout}>
              Conectar agora
            </Button>
          ) : null}
        </div>
      ) : null}

      <nav className="mkt-tabs" aria-label="Filtrar pedidos">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={filter === key ? "mkt-tab is-on" : "mkt-tab"}
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
          >
            {label}
            {orders ? <span className="mkt-tab-count">{count(key)}</span> : null}
          </button>
        ))}
      </nav>

      {flash ? (
        <p className="mkt-ok" role="status">
          {flash}
        </p>
      ) : null}
      {error ? (
        <p className="mkt-alert" role="alert">
          {error}{" "}
          <button type="button" className="mkt-link" onClick={() => void load()}>
            Tentar de novo
          </button>
        </p>
      ) : null}

      {orders === null && !error ? (
        <div className="admin-card mkt-skel" aria-busy="true">
          <span className="mkt-sr">Carregando…</span>
        </div>
      ) : null}

      {orders && visible.length === 0 ? (
        <div className="admin-card mkt-empty">
          <p className="mkt-empty-title">
            {filter === "open" ? "Nenhum pedido esperando você." : "Nada por aqui ainda."}
          </p>
          <p className="mkt-muted">Quando um cliente escolher uma combo com o seu produto, o pedido aparece aqui.</p>
        </div>
      ) : null}

      {visible.length ? (
        <ul className="ptn-orders" aria-label="Pedidos">
          {visible.map((order) => {
            const status = STATUS[order.status] ?? { label: order.status, tone: "c-none" };
            const receive = order.item_cents + (order.freight_cents ?? 0) - order.fee_cents;
            const isRefusing = refusing?.id === order.id;
            return (
              <li key={order.id} className="admin-card ptn-order">
                <div className="ptn-order-top">
                  <div className="ptn-order-what">
                    <strong>
                      {order.item_quantity > 1 ? `${order.item_quantity} × ` : ""}
                      {order.product_name}
                    </strong>
                    <span className="mkt-muted">
                      Pedido {order.public_reference} · com {order.house_product_name}
                    </span>
                  </div>
                  <span className={`admin-chip ${status.tone}`}>
                    <span className="dot" aria-hidden="true" />
                    {status.label}
                  </span>
                </div>

                <div className="ptn-order-grid">
                  <dl className="ptn-order-info">
                    <dt>Entrega</dt>
                    <dd>{dayLabel(order.requested_date)}</dd>
                    <dt>Cliente</dt>
                    <dd>{order.customer_name}</dd>
                    <dt>Endereço</dt>
                    <dd>{order.address_line}</dd>
                    {order.status === "submitted" && order.accept_deadline ? (
                      <>
                        <dt>Confirme até</dt>
                        <dd>{STAMP.format(new Date(order.accept_deadline))}</dd>
                      </>
                    ) : null}
                    {order.refuse_reason ? (
                      <>
                        <dt>Motivo</dt>
                        <dd>{order.refuse_reason}</dd>
                      </>
                    ) : null}
                  </dl>
                  <dl className="ptn-price" aria-label={`Seu recebimento no pedido ${order.public_reference}`}>
                    <dt>Seu produto{order.item_quantity > 1 ? ` (${order.item_quantity} un.)` : ""}</dt>
                    <dd>{formatCents(order.item_cents)}</dd>
                    <dt>Seu frete</dt>
                    <dd>{order.freight_cents ? formatCents(order.freight_cents) : "—"}</dd>
                    <dt>Taxa combo</dt>
                    <dd>− {formatCents(order.fee_cents)}</dd>
                    <dt className="ptn-price-total">Você recebe</dt>
                    <dd className="ptn-price-total">{formatCents(receive)}</dd>
                  </dl>
                </div>

                {order.status === "submitted" && !isRefusing ? (
                  <div className="mkt-row">
                    <Button
                      variant="primary"
                      disabled={busyId === order.id || needsPayout}
                      title={needsPayout ? "Conecte sua conta do Mercado Pago para confirmar" : undefined}
                      onClick={() => void act(order, "accept", "Pedido confirmado. O cliente recebe o pagamento da sua parte.")}
                    >
                      Confirmar entrega nesta data
                    </Button>
                    <Button disabled={busyId === order.id} onClick={() => setRefusing({ id: order.id, reason: "" })}>
                      Não consigo
                    </Button>
                  </div>
                ) : null}

                {isRefusing && refusing ? (
                  <form className="mkt-subform" onSubmit={(event) => void refuse(event)} aria-label="Recusar pedido">
                    <label className="mkt-field">
                      Motivo (o cliente vê)
                      <input
                        className="mkt-input"
                        maxLength={200}
                        value={refusing.reason}
                        placeholder="Ex.: sem estoque para essa data"
                        onChange={(event) => setRefusing({ ...refusing, reason: event.target.value })}
                      />
                    </label>
                    {refuseError ? (
                      <p className="mkt-alert" role="alert">
                        {refuseError}
                      </p>
                    ) : null}
                    <div className="mkt-row">
                      <Button type="submit" disabled={busyId === order.id}>
                        Recusar pedido
                      </Button>
                      <Button onClick={() => setRefusing(null)}>Voltar</Button>
                    </div>
                  </form>
                ) : null}

                {order.status === "accepted" ? (
                  <div className="mkt-row">
                    <Button
                      disabled={busyId === order.id}
                      onClick={() => void act(order, "delivered", "Entrega registrada. Obrigado!")}
                    >
                      Marcar como entregue
                    </Button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </>
  );
}
