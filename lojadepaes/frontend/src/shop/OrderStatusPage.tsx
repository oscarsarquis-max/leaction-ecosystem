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
  addressFieldErrors,
  emptyDeliveryAddress,
  formatDeliveryAddress,
  maskPostalCode,
  type DeliveryAddressInput,
} from "./DeliveryAddressFields";

const PENDING_ADDRESS_KEY = "lojadepaes_pending_address";

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
      return "Recebemos seu pagamento. A Loja está avaliando sua encomenda e confirmará a data.";
    case "accepted":
      return order.financially_settled
        ? "O pagamento foi recebido e a data da fornada já está reservada."
        : "A Loja aceitou o pedido e reservou a data.";
    case "payment_processing":
      return "Estamos aguardando a confirmação do pagamento.";
    case "payment_failed":
      return "Esta tentativa de pagamento não foi concluída. Você pode tentar de novo.";
    case "date_alternative":
      return "A Loja sugeriu outra data. Você pode aceitá-la abaixo.";
    case "cancelled":
      return "Este pedido foi cancelado.";
    case "awaiting_bakery":
      return "Aguardando avaliação de A Loja. Isso ainda não reserva a fornada nem libera o pagamento.";
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
  const [address, setAddress] = useState<DeliveryAddressInput>(emptyDeliveryAddress);
  const [addressOpen, setAddressOpen] = useState(false);
  const [addressReady, setAddressReady] = useState(false);
  const [addressSaved, setAddressSaved] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof DeliveryAddressInput, string>>>({});

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
    if (!order || addressReady) {
      return;
    }
    const pending = sessionStorage.getItem(PENDING_ADDRESS_KEY);
    if (pending) {
      try {
        setAddress(JSON.parse(pending) as DeliveryAddressInput);
        sessionStorage.removeItem(PENDING_ADDRESS_KEY);
        setAddressReady(true);
        return;
      } catch {
        sessionStorage.removeItem(PENDING_ADDRESS_KEY);
      }
    }
    if (order.delivery_address) {
      setAddress({
        delivery_street: order.delivery_address.street || "",
        delivery_number: order.delivery_address.number || "",
        delivery_complement: order.delivery_address.complement || "",
        delivery_district: order.delivery_address.district || "",
        delivery_city: order.delivery_address.city || "",
        delivery_state: order.delivery_address.state || "",
        delivery_postal_code: maskPostalCode(order.delivery_address.postal_code || ""),
      });
    }
    setAddressReady(true);
  }, [order, addressReady]);

  useEffect(() => {
    if (!order || order.financially_settled || !order.payment.external_reference || order.payment.financial_status !== "pending") {
      return;
    }
    const timer = window.setInterval(() => {
      void reconcileStorefrontOrder(reference)
        .then((payload) => setOrder(payload))
        .catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [reference, order?.financially_settled, order?.payment.external_reference, order?.payment.financial_status]);

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
    const invalid = addressFieldErrors(address);
    if (Object.keys(invalid).length) {
      setFieldErrors(invalid);
      setError("Revise os dados de entrega destacados.");
      setAddressSaved(false);
      return;
    }
    setBusy(true);
    setError(null);
    setAddressSaved(false);
    try {
      const payload = await saveDeliveryAddress(reference, address);
      setOrder(payload);
      setFieldErrors({});
      setAddressOpen(false);
      setAddressSaved(true);
    } catch (reason: unknown) {
      setError(checkoutErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function verifyPayment() {
    setBusy(true);
    setError(null);
    try {
      const payload = await reconcileStorefrontOrder(reference);
      setOrder(payload);
    } catch {
      setError("Não foi possível consultar o pagamento. Isso não marca o pedido como pago.");
    } finally {
      setBusy(false);
    }
  }

  async function pay(method: "pix" | "card", replace = false) {
    setBusy(true);
    setError(null);
    try {
      if (replace) {
        const current = await reconcileStorefrontOrder(reference);
        setOrder(current);
        if (current.financially_settled) {
          return;
        }
      }
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
  const canPay = Boolean(order?.payment_available) && !order?.financially_settled;

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
          {new URLSearchParams(window.location.search).get("enviado") === "1" ? (
            <div className="receipt">
              <p>
                Pedido recebido: <strong>{order.public_reference}</strong>
              </p>
              {!order.confirmed ? <p>Pedido recebido. Aguarde o aceite da Loja para pagar.</p> : null}
              {order.confirmed && !order.financially_settled ? (
                <p>Pedido aceito. Falta concluir o pagamento.</p>
              ) : null}
              <p>O recarregar desta página não envia o pedido de novo.</p>
              <a className="primary" href={`/pedido/${order.public_reference}`}>
                Ver meu pedido
              </a>
              <button type="button" className="text-button" onClick={() => goStorefront("/")}>
                Voltar à loja
              </button>
            </div>
          ) : null}
          <section className="order-status-section">
          <h2>Resumo</h2>
          <p>{visitorCopy(order)}</p>
          <p>
            {order.total_cents === 0
              ? "Sem valor a pagar — benefício de fidelidade"
              : order.financially_settled
                ? "Pagamento: Pago"
                : "Pagamento: Aguardando confirmação"}
          </p>
          <p>
            {order.confirmed
              ? "Encomenda: Data reservada"
              : "Encomenda: Aguardando avaliação de A Loja"}
          </p>
          {order.items.some((item) => item.adaptation && item.adaptation.status === "pending") ? (
            <p>Adaptação: Aguardando avaliação</p>
          ) : null}
          {!order.financially_settled && order.payment.financial_status === "pending" ? (
            <button type="button" className="text-button" disabled={busy} onClick={() => void verifyPayment()}>
              Verificar pagamento
            </button>
          ) : null}
          {order.payment.sanitized_error && !order.financially_settled ? (
            <p className="tip" role="status">
              {/verifica|indisponível|falha na verificação/i.test(order.payment.sanitized_error)
                ? "Estamos verificando seu pagamento. Se você já pagou, não pague novamente."
                : order.payment.sanitized_error}
            </p>
          ) : null}
          <p className="selection-total">
            Total {order.total_cents == null ? "—" : formatCents(order.total_cents)}
            {order.requested_date
              ? ` · ${order.confirmed ? "data aceita" : "data pedida"} ${formatAskedDate(order.requested_date)}`
              : ""}
          </p>
          <p>
            Horário solicitado: {order.preferred_time ? `${order.preferred_time} (preferência)` : "Sem preferência informada"}
          </p>
          {order.fulfillment_modality === "pickup" ? (
            <p>Retirada (pedido anterior)</p>
          ) : (
            <p>O pedido será entregue no endereço indicado.</p>
          )}
          </section>
          <section className="order-status-section" aria-labelledby="order-payment-heading">
          <h2 id="order-payment-heading">Pagamento</h2>
          {order.financially_settled ? (
            <p className="tip" role="status">
              {order.payment.amount_paid_cents != null && order.payment.method
                ? `Pagamento recebido — ${formatCents(order.payment.amount_paid_cents)} — ${order.payment.method === "pix" ? "Pix" : "Cartão"}.`
                : "Pagamento recebido. Não há nova cobrança neste pedido."}
            </p>
          ) : null}
          {!order.financially_settled && order.payment.method ? (
            <p className="tip" role="status">
              Aguardando confirmação do pagamento.
            </p>
          ) : null}
          {canPay ? (
            <div className="checkout-methods">
              <p>Como prefere pagar? O endereço abaixo não impede esta etapa.</p>
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
          {!order.financially_settled && !canPay ? (
            <p className="tip" role="status">
              {order.payment_unavailable_reason ||
                error ||
                "Não há ação de pagamento neste momento. Isso não é um checkout vazio."}
            </p>
          ) : null}
          <ul className="selection-list checkout-lines">
            {order.items.map((item, index) => (
              <li key={item.id ?? `${item.product_name}-${item.variant_name}-${index}`}>
                <div>
                  <strong>
                    {item.origin === "custom" ? "Pão personalizado · " : ""}
                    {item.origin === "custom" ? item.variant_name : item.product_name}
                  </strong>
                  <span>
                    {item.origin === "custom" ? `Fermentação e preparo: ${item.product_name}` : item.variant_name}
                    {item.weight_grams ? ` · ${item.weight_grams} g` : ""}
                    {item.unit_cents ? ` · ${formatCents(item.unit_cents)}` : ""}
                  </span>
                  {item.origin === "custom" && item.ingredients?.length ? (
                    <span>
                      Farinha:{" "}
                      {item.ingredients
                        .filter((extra) => extra.assistant_role === "flour")
                        .map((extra) => extra.name)
                        .join(", ") || "não informada no pedido"}
                      {item.ingredients.some((extra) => extra.assistant_role !== "flour")
                        ? ` · Complementos: ${item.ingredients
                            .filter((extra) => extra.assistant_role !== "flour")
                            .map((extra) => extra.name)
                            .join(", ")}`
                        : ""}
                    </span>
                  ) : null}
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
                          <strong>Resposta de A Loja:</strong> {item.adaptation.bakery_response}
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
          </section>
          <section className="order-status-section">
          <h2>Entrega</h2>
          {addressSaved ? (
            <p className="tip" role="status">
              Endereço de entrega salvo.
            </p>
          ) : null}
          {order.delivery_pending ? (
            <p className="tip" role="status">
              Dados de entrega pendentes. Você pode pagar agora e completar o endereço neste mesmo acesso.
            </p>
          ) : null}
          {order.delivery_address && !order.delivery_pending ? (
            <p>
              Entrega em {formatDeliveryAddress(order.delivery_address)}
            </p>
          ) : null}
          {order.delivery_address && order.delivery_pending ? (
            <p>
              Endereço incompleto: {formatDeliveryAddress(order.delivery_address)}{" "}
              <button type="button" className="text-button" onClick={() => setAddressOpen(true)}>
                Completar endereço
              </button>
            </p>
          ) : null}
          {order.fulfillment_modality !== "pickup" &&
          (order.delivery_pending || addressOpen) ? (
            <form className="checkout-form" onSubmit={(event) => void saveAddress(event)} noValidate>
              <DeliveryAddressFields
                value={address}
                onChange={setAddress}
                note={order.confirmed ? "accepted" : "checkout"}
                errors={fieldErrors}
              />
              <button className="primary" type="submit" disabled={busy}>
                Salvar endereço de entrega
              </button>
            </form>
          ) : null}
          </section>
          <button type="button" className="text-button" onClick={() => goStorefront("/")}>
            Voltar à vitrine
          </button>
        </>
      ) : null}
    </main>
  );
}
