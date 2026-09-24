import { useEffect, useMemo, useState, type FormEvent } from "react";
import { formatCents } from "../lib/money";
import { AdaptationLineEditor } from "./AdaptationRequest";
import { BakeCalendar } from "./BakeCalendar";
import { useCart } from "./CartContext";
import {
  checkoutErrorMessage,
  goStorefront,
  quoteOrder,
  saveOrderToken,
  submitOrder,
  type StorefrontQuote,
} from "./checkoutApi";
import { DeliveryAddressFields, emptyDeliveryAddress } from "./DeliveryAddressFields";
import { storefrontItemsFromLines } from "./selection";
import { getTrackingSessionId } from "./tracking";

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `lp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function CheckoutPage() {
  const cart = useCart();
  const [date, setDate] = useState<string | null>(null);
  const [quote, setQuote] = useState<StorefrontQuote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [address, setAddress] = useState(emptyDeliveryAddress);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const available = useMemo(
    () => cart.resolved.filter((line) => line.available),
    [cart.resolved],
  );

  const calendarLines = useMemo(
    () =>
      cart.lines.map((line) => ({
        kind: "product" as const,
        variant_id: line.variantId,
        quantity: line.quantity,
      })),
    [cart.lines],
  );

  useEffect(() => {
    if (!date || available.length === 0) {
      setQuote(null);
      return;
    }
    let cancelled = false;
    quoteOrder({
      requested_date: date,
      items: storefrontItemsFromLines(available),
    })
      .then((payload) => {
        if (!cancelled) {
          setQuote(payload);
          setQuoteError(null);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setQuote(null);
          setQuoteError(checkoutErrorMessage(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [available, date]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!date || !quote) {
      return;
    }
    setBusy(true);
    setSubmitError(null);
    try {
      const order = await submitOrder({
        requested_date: date,
        items: storefrontItemsFromLines(available),
        quoted_cents: quote.total_cents,
        customer_name: name,
        customer_email: email,
        customer_phone: phone || undefined,
        customer_note: note,
        ...address,
        idempotency_key: newIdempotencyKey(),
        id_sessao: getTrackingSessionId(),
      });
      if (order.access_token) {
        saveOrderToken(order.public_reference, order.access_token);
      }
      cart.clear();
      goStorefront(`/pedido/${order.public_reference}`);
    } catch (reason: unknown) {
      setSubmitError(checkoutErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="checkout-page">
      <p className="eyebrow">Pedido</p>
      <h1>Revisar e pedir</h1>
      <p className="checkout-lead">
        A data só fica reservada depois que a padaria aceitar o pedido. Pagar não confirma a fornada.
        Uma solicitação de adaptação não altera o preço mostrado; qualquer mudança de valor exigiria
        proposta explícita e concordância antes de nova cobrança.
      </p>
      {available.length === 0 ? (
        <p>
          Sua seleção está vazia.{" "}
          <button type="button" className="text-button" onClick={() => goStorefront("/")}>
            Voltar aos pães
          </button>
        </p>
      ) : (
        <>
          <ul className="selection-list checkout-lines">
            {available.map((line) => (
              <li key={line.key}>
                <div>
                  <strong>{line.productName}</strong>
                  <span>
                    {line.variantName}
                    {line.packLabel ? ` · ${line.packLabel}` : ""}
                  </span>
                  <AdaptationLineEditor line={line} />
                </div>
                <span>{line.quantity} un.</span>
                <span>{formatCents(line.lineCents)}</span>
              </li>
            ))}
          </ul>
          <BakeCalendar lines={calendarLines} selectedDate={date} onSelectDate={setDate} />
          {quoteError ? <p className="tip">{quoteError}</p> : null}
          {quote ? (
            <p className="selection-total">
              Total {formatCents(quote.total_cents)} · {quote.date_label}
            </p>
          ) : null}
          <form className="checkout-form" onSubmit={handleSubmit}>
            <label>
              Nome de quem recebe
              <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={160} />
            </label>
            <label>
              E-mail
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                maxLength={254}
              />
            </label>
            <label>
              Telefone (opcional)
              <input value={phone} onChange={(event) => setPhone(event.target.value)} maxLength={40} />
            </label>
            <label>
              Observação (opcional)
              <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} rows={3} />
            </label>
            <DeliveryAddressFields value={address} onChange={setAddress} />
            {submitError ? (
              <p className="tip" role="alert">
                {submitError}
              </p>
            ) : null}
            <button className="primary" type="submit" disabled={busy || !quote}>
              {busy ? "Enviando…" : "Enviar pedido"}
            </button>
          </form>
        </>
      )}
    </main>
  );
}
