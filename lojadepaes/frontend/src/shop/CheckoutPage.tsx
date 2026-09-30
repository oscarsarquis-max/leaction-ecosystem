import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { formatCents } from "../lib/money";
import { AdaptationLineEditor } from "./AdaptationRequest";
import { BakeCalendar } from "./BakeCalendar";
import { useCart } from "./CartContext";
import type { CalendarDay } from "./calendarApi";
import {
  checkoutErrorMessage,
  goStorefront,
  quoteOrder,
  saveOrderToken,
  submitOrder,
  type StorefrontQuote,
} from "./checkoutApi";
import { DeliveryAddressFields, emptyDeliveryAddress } from "./DeliveryAddressFields";
import { HouseFidelityCheckout } from "./HouseFidelityCheckout";
import { PreferredTimeField } from "./PreferredTimeField";
import { QuantityField } from "./QuantityField";
import { storefrontItemsFromLines } from "./selection";
import { newIdempotencyKey, readStoredContact, writeStoredContact } from "./contactStorage";
import { getTrackingSessionId } from "./tracking";

const PREFERRED_DATE_KEY = "lojadepaes_preferred_date";
const PREFERRED_TIME_KEY = "lojadepaes_preferred_time";
const IDEMPOTENCY_KEY = "lojadepaes_checkout_idempotency";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function checkoutIdempotencyKey(): string {
  const existing = sessionStorage.getItem(IDEMPOTENCY_KEY);
  if (existing) {
    return existing;
  }
  const created = newIdempotencyKey();
  sessionStorage.setItem(IDEMPOTENCY_KEY, created);
  return created;
}

export function CheckoutPage() {
  const cart = useCart();
  const [date, setDate] = useState<string | null>(() => sessionStorage.getItem(PREFERRED_DATE_KEY));
  const [preferredTime, setPreferredTime] = useState(() => sessionStorage.getItem(PREFERRED_TIME_KEY) ?? "");
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null);
  const [quote, setQuote] = useState<StorefrontQuote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [quoting, setQuoting] = useState(false);
  const quoteSeq = useRef(0);
  const stored = readStoredContact();
  const [name, setName] = useState(stored.name);
  const [email, setEmail] = useState(stored.email);
  const [phone, setPhone] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const [note, setNote] = useState("");
  const [address, setAddress] = useState(emptyDeliveryAddress);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fidelityOptIn, setFidelityOptIn] = useState(false);
  const [applyCredit, setApplyCredit] = useState(false);
  const [creditVariantId, setCreditVariantId] = useState("");
  const available = useMemo(
    () => cart.resolved.filter((line) => line.available),
    [cart.resolved],
  );

  const hasCustom = cart.lines.some((line) => line.custom);
  const calendarLines = useMemo(
    () =>
      cart.lines.map((line) =>
        line.custom
          ? { kind: "custom" as const, dough_type_id: line.custom.doughTypeId, quantity: line.quantity }
          : { kind: "product" as const, variant_id: line.variantId, quantity: line.quantity },
      ),
    [cart.lines],
  );

  useEffect(() => {
    if (!date || available.length === 0) {
      setQuote(null);
      setQuoting(false);
      return;
    }
    const seq = ++quoteSeq.current;
    setQuoting(true);
    quoteOrder({
      requested_date: date,
      items: storefrontItemsFromLines(available),
      apply_fidelity_credit: applyCredit,
      fidelity_variant_id: creditVariantId || undefined,
    })
      .then((payload) => {
        if (seq !== quoteSeq.current) {
          return;
        }
        setQuote(payload);
        setQuoteError(null);
      })
      .catch((reason: unknown) => {
        if (seq !== quoteSeq.current) {
          return;
        }
        setQuote(null);
        setQuoteError(checkoutErrorMessage(reason));
      })
      .finally(() => {
        if (seq === quoteSeq.current) {
          setQuoting(false);
        }
      });
  }, [available, date, applyCredit, creditVariantId]);

  const chooseDate = useCallback((next: string) => {
    setDate(next);
    sessionStorage.setItem(PREFERRED_DATE_KEY, next);
  }, []);

  const changePreferredTime = useCallback((next: string) => {
    setPreferredTime(next);
    if (next) {
      sessionStorage.setItem(PREFERRED_TIME_KEY, next);
    } else {
      sessionStorage.removeItem(PREFERRED_TIME_KEY);
    }
  }, []);

  const rememberSelectedDay = useCallback((day: CalendarDay | null) => {
    setSelectedDay(day);
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!date || !quote) {
      return;
    }
    if (!name.trim()) {
      setFieldError("Informe o nome de quem pede.");
      nameRef.current?.focus();
      return;
    }
    if (!EMAIL_RE.test(email.trim())) {
      setFieldError("Informe um e-mail para acompanhar o pedido.");
      emailRef.current?.focus();
      return;
    }
    setBusy(true);
    setSubmitError(null);
    setFieldError(null);
    try {
      const order = await submitOrder({
        requested_date: date,
        items: storefrontItemsFromLines(available),
        quoted_cents: quote.total_cents,
        customer_name: name.trim(),
        customer_email: email.trim(),
        customer_phone: phone || undefined,
        customer_note: note,
        preferred_time: preferredTime || undefined,
        ...address,
        idempotency_key: checkoutIdempotencyKey(),
        id_sessao: getTrackingSessionId(),
        fidelity_opt_in: fidelityOptIn,
        apply_fidelity_credit: applyCredit,
        fidelity_variant_id: creditVariantId || undefined,
      });
      if (order.access_token) {
        saveOrderToken(order.public_reference, order.access_token);
      }
      writeStoredContact(name.trim(), email.trim());
      sessionStorage.removeItem(IDEMPOTENCY_KEY);
      cart.clear();
      goStorefront(`/pedido/${order.public_reference}?enviado=1`);
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
        A data escolhida é uma preferência e só fica reservada depois que A Loja aceitar o pedido.
        Pagar não confirma a fornada. A modalidade disponível é a retirada.
        {hasCustom
          ? " Depois do aceite, você poderá pagar por Pix ou cartão."
          : " Uma solicitação de adaptação não altera o preço mostrado."}
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
                <QuantityField
                  value={line.quantity}
                  onChange={(quantity) => cart.changeQuantity(line.key, quantity)}
                />
                <span>{formatCents(line.unitCents)} cada</span>
                <span>{formatCents(line.lineCents)}</span>
                <button type="button" className="text-button" onClick={() => cart.remove(line.key)}>
                  Remover
                </button>
              </li>
            ))}
          </ul>
          <div className="checkout-schedule">
            <BakeCalendar
              lines={calendarLines}
              selectedDate={date}
              onSelectDate={chooseDate}
              onSelectedDayChange={rememberSelectedDay}
              layout="checkout"
            />
            <PreferredTimeField
              value={preferredTime}
              onChange={changePreferredTime}
              modality="pickup"
              windows={selectedDay?.windows}
            />
          </div>
          {quoting ? (
            <p className="tip" role="status">
              Recalculando o total…
            </p>
          ) : null}
          {quoteError ? <p className="tip">{quoteError}</p> : null}
          {quote ? (
            <div className="selection-total">
              <p>Subtotal {formatCents(quote.subtotal_cents)}</p>
              {quote.discount_cents ? (
                <p>Crédito fidelidade −{formatCents(quote.discount_cents)}</p>
              ) : null}
              <p>
                {quote.total_cents === 0
                  ? "Sem valor a pagar — benefício de fidelidade"
                  : `Total ${formatCents(quote.total_cents)}`}{" "}
                · {quote.date_label}
              </p>
            </div>
          ) : null}
          <p>
            <button type="button" className="text-button" onClick={() => cart.setOpen(true)}>
              Editar carrinho
            </button>
          </p>
          <form className="checkout-form" onSubmit={handleSubmit} noValidate>
            <label>
              Nome de quem pede
              <input
                ref={nameRef}
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                maxLength={160}
                aria-invalid={fieldError?.includes("nome") ? true : undefined}
              />
            </label>
            <label>
              E-mail para acompanhar o pedido
              <input
                ref={emailRef}
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                maxLength={254}
                aria-invalid={fieldError?.includes("e-mail") ? true : undefined}
              />
            </label>
            <p className="fornada-note">
              Usaremos este e-mail para avisar sobre a avaliação do seu pão e enviar o acesso ao pagamento após o aceite.
            </p>
            <label>
              Telefone (opcional)
              <input value={phone} onChange={(event) => setPhone(event.target.value)} maxLength={40} />
            </label>
            <label>
              Observação (opcional)
              <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} rows={3} />
            </label>
            <DeliveryAddressFields value={address} onChange={setAddress} />
            <HouseFidelityCheckout
              optIn={fidelityOptIn}
              onOptIn={setFidelityOptIn}
              applyCredit={applyCredit}
              onApplyCredit={setApplyCredit}
              creditVariantId={creditVariantId}
              onCreditVariantId={setCreditVariantId}
              eligibleItems={quote?.eligible_credit_items ?? []}
              creditNotice={quote?.credit_notice ?? null}
              creditLabel={quote?.credit_label ?? null}
              quoteReady={Boolean(quote)}
            />
            {fieldError ? (
              <p className="tip" role="alert">
                {fieldError}
              </p>
            ) : null}
            {submitError ? (
              <p className="tip" role="alert">
                {submitError}
              </p>
            ) : null}
            {hasCustom ? (
              <p className="fornada-note">Após o aceite de A Loja, você poderá pagar por Pix ou cartão.</p>
            ) : null}
            {!quote && !quoteError ? (
              <p className="tip" role="status">
                {date ? "Consultando se esta data comporta o pedido." : "Escolha um dia de produção para enviar o pedido."}
              </p>
            ) : null}
            {quote?.notice ? <p className="fornada-note">{quote.notice}</p> : null}
            <button className="primary" type="submit" disabled={busy || quoting || !quote}>
              {busy ? "Enviando…" : hasCustom ? "Enviar pedido para avaliação" : "Enviar pedido"}
            </button>
          </form>
        </>
      )}
    </main>
  );
}
