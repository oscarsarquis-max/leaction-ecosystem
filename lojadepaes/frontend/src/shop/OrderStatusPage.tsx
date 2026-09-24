import { useEffect, useState, type FormEvent } from "react";
import { formatCents } from "../lib/money";
import { adaptationStatusLabel, reasonLabel } from "./AdaptationRequest";
import {
  acceptProposedDate,
  checkoutErrorMessage,
  fetchStorefrontOrder,
  goStorefront,
  reconcileStorefrontOrder,
  respondAdaptation,
  saveDeliveryAddress,
  startStorefrontCheckout,
  type StorefrontCheckout,
  type StorefrontOrder,
} from "./checkoutApi";
import {
  DeliveryAddressFields,
  emptyDeliveryAddress,
  formatDeliveryAddress,
  type DeliveryAddressInput,
} from "./DeliveryAddressFields";
import { fetchOperations } from "./operationsApi";

type Props = { reference: string };

function formatAskedDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  if (!year || !month || !day) return iso;
  return new Date(year, month - 1, day).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatPaymentDeadline(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function visitorCopy(order: StorefrontOrder): string {
  switch (order.visitor_state) {
    case "paid_awaiting_accept":
      return "Recebemos o pagamento. Isso ainda não confirma a data da fornada.";
    case "accepted":
      return order.financially_settled
        ? "O pagamento foi recebido e a data da fornada já está reservada."
        : "A padaria aceitou o pedido e reservou a data.";
    case "payment_processing":
      return "Estamos aguardando a confirmação do pagamento.";
    case "payment_failed":
      return "Esta tentativa de pagamento não foi concluída. Você pode tentar de novo.";
    case "date_alternative":
      return "A padaria sugeriu outra data. Você pode aceitá-la abaixo.";
    case "cancelled":
      return "Este pedido foi cancelado.";
    default:
      return order.notice;
  }
}

export function OrderStatusPage({ reference }: Props) {
  const [order, setOrder] = useState<StorefrontOrder | null>(null);
  const [checkout, setCheckout] = useState<StorefrontCheckout | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [paymentsEnabled, setPaymentsEnabled] = useState(false);
  const [address, setAddress] = useState<DeliveryAddressInput>(emptyDeliveryAddress);
  const [addressOpen, setAddressOpen] = useState(false);

  useEffect(() => {
    fetchOperations()
      .then((status) => setPaymentsEnabled(status.payments_enabled === true))
      .catch(() => setPaymentsEnabled(false));
  }, []);

  async function load() {
    try {
      const payload = await fetchStorefrontOrder(reference);
      setOrder(payload);
      setError(null);
    } catch (reason: unknown) {
      setError(checkoutErrorMessage(reason));
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [reference]);

  useEffect(() => {
    if (!order || order.financially_settled || order.confirmed) {
      return;
    }
    const timer = window.setInterval(() => {
      void reconcileStorefrontOrder(reference)
        .then((payload) => setOrder(payload))
        .catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [order, reference]);

  async function answerAdaptation(itemId: string, decision: "accept_alternative" | "decline") {
    setBusy(true);
    setError(null);
    try {
      const payload = await respondAdaptation(reference, itemId, decision);
      setOrder(payload);
    } catch (reason: unknown) {
      setError(checkoutErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveAddress(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = await saveDeliveryAddress(reference, address);
      setOrder(payload);
      setAddressOpen(false);
    } catch (reason: unknown) {
      setError(checkoutErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function pay(method: "pix" | "card", replace = false) {
    setBusy(true);
    setError(null);
    try {
      const result = await startStorefrontCheckout(reference, method, replace);
      setCheckout(result);
      if (method === "card" && result.checkout_url) {
        window.location.assign(result.checkout_url);
        return;
      }
      await load();
    } catch (reason: unknown) {
      setError(checkoutErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const pix = checkout?.pix ?? order?.payment.pix ?? null;
  const canPay =
    paymentsEnabled &&
    order?.status === "submitted" &&
    !order.financially_settled &&
    !order.confirmed;

  return (
    <main className="checkout-page">
      <p className="eyebrow">Pedido {reference}</p>
      <h1>Acompanhar pedido</h1>
      {error ? (
        <p className="tip" role="alert">
          {error}
        </p>
      ) : null}
      {!order && !error ? <p>Carregando seu pedido…</p> : null}
      {order ? (
        <>
          <p>{visitorCopy(order)}</p>
          <p className="selection-total">
            Total {order.total_cents == null ? "—" : formatCents(order.total_cents)}
            {order.requested_date ? ` · data pedida ${formatAskedDate(order.requested_date)}` : ""}
          </p>
          {order.delivery_address ? (
            <p>
              Entrega em {formatDeliveryAddress(order.delivery_address)}
              {order.status === "submitted" && !order.financially_settled ? (
                <>
                  {" "}
                  <button type="button" className="text-button" onClick={() => setAddressOpen(true)}>
                    Corrigir endereço
                  </button>
                </>
              ) : null}
            </p>
          ) : null}
          {(!order.delivery_address || addressOpen) &&
          order.status === "submitted" &&
          !order.financially_settled ? (
            <form className="checkout-form" onSubmit={(event) => void saveAddress(event)}>
              <DeliveryAddressFields value={address} onChange={setAddress} />
              <button className="primary" type="submit" disabled={busy}>
                Salvar endereço de entrega
              </button>
            </form>
          ) : null}
          <ul className="selection-list checkout-lines">
            {order.items.map((item, index) => (
              <li key={item.id ?? `${item.product_name}-${item.variant_name}-${index}`}>
                <div>
                  <strong>{item.product_name}</strong>
                  <span>{item.variant_name}</span>
                  {item.adaptation ? (
                    <div className="adaptation-order-block">
                      <p className="adaptation-line-note">
                        <strong>Adaptação solicitada</strong>
                        {reasonLabel(item.adaptation.reason) ? ` · ${reasonLabel(item.adaptation.reason)}` : ""}
                        {item.quantity > 1 ? ` · vale para as ${item.quantity} unidades desta linha` : ""}
                      </p>
                      <p>{item.adaptation.customer_text}</p>
                      <p className="adaptation-help">{adaptationStatusLabel(item.adaptation.status, item.adaptation.client_decision)}</p>
                      {item.adaptation.bakery_response ? (
                        <p>
                          <strong>Resposta da padaria:</strong> {item.adaptation.bakery_response}
                        </p>
                      ) : null}
                      {item.adaptation.status === "alternative_proposed" &&
                      item.adaptation.client_decision !== "declined" &&
                      item.id &&
                      order.status === "submitted" ? (
                        <div className="adaptation-line-actions">
                          <button
                            type="button"
                            className="primary"
                            disabled={busy}
                            onClick={() => void answerAdaptation(item.id as string, "accept_alternative")}
                          >
                            Concordar com a alternativa
                          </button>
                          <button
                            type="button"
                            className="text-button"
                            disabled={busy}
                            onClick={() => void answerAdaptation(item.id as string, "decline")}
                          >
                            Recusar a alternativa
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
                <span>{item.quantity} un.</span>
                <span>{formatCents(item.line_cents)}</span>
              </li>
            ))}
          </ul>
          {order.visitor_state === "date_alternative" && order.proposed_date ? (
            <button type="button" className="primary" disabled={busy} onClick={() => void acceptProposedDate(reference).then(setOrder)}>
              Aceitar a data {order.proposed_date}
            </button>
          ) : null}
          {canPay ? (
            <div className="checkout-methods">
              <p>Como prefere pagar?</p>
              <div className="checkout-method-row">
                <button type="button" className="primary" disabled={busy} onClick={() => void pay("pix")}>
                  Pagar com Pix
                </button>
                <button type="button" className="primary" disabled={busy} onClick={() => void pay("card")}>
                  Pagar com cartão
                </button>
              </div>
              {order.payment.method && order.payment.financial_status === "pending" ? (
                <button
                  type="button"
                  className="text-button"
                  disabled={busy}
                  onClick={() => void pay(order.payment.method === "pix" ? "card" : "pix", true)}
                >
                  Trocar método
                </button>
              ) : null}
            </div>
          ) : null}
          {order && !order.financially_settled && (pix?.qr_code || pix?.qr_code_base64) ? (
            <section className="pix-box" aria-label="Pagamento Pix">
              <h2>Pagar com Pix</h2>
              <p>
                Valor: <strong>{order.total_cents == null ? "—" : formatCents(order.total_cents)}</strong>
              </p>
              <ol className="pix-steps">
                <li>Abra o aplicativo do seu banco.</li>
                <li>Escolha Pix e escaneie o QR, ou copie o código e cole no aplicativo.</li>
                <li>Confira o valor e o nome de quem recebe antes de confirmar o pagamento.</li>
              </ol>
              <p>Esta tela não marca o pedido como pago. A confirmação chega pelo banco.</p>
              {pix.qr_code_base64 ? (
                <img
                  className="pix-qr"
                  alt="QR Code Pix para escanear no aplicativo do banco"
                  src={`data:image/png;base64,${pix.qr_code_base64}`}
                />
              ) : null}
              {pix.qr_code ? (
                <label>
                  Código Pix
                  <textarea readOnly value={pix.qr_code} rows={4} />
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => {
                      void navigator.clipboard.writeText(pix.qr_code || "").then(() => setCopied(true));
                    }}
                  >
                    {copied ? "Código copiado" : "Copiar código"}
                  </button>
                </label>
              ) : null}
              {pix.date_of_expiration ? (
                <p className="demo">Pague até {formatPaymentDeadline(pix.date_of_expiration)}.</p>
              ) : null}
            </section>
          ) : null}
          <button type="button" className="text-button" onClick={() => goStorefront("/")}>
            Voltar à vitrine
          </button>
        </>
      ) : null}
    </main>
  );
}
