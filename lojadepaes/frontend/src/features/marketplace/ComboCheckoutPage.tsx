import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";
import { StorefrontLayout } from "../../components/StorefrontLayout";
import { formatCents } from "../../lib/money";
import { ApiError } from "../../services/http";
import { BakeCalendar } from "../../shop/BakeCalendar";
import type { CalendarDay } from "../../shop/calendarApi";
import { newIdempotencyKey, readStoredContact, writeStoredContact } from "../../shop/contactStorage";
import {
  DeliveryAddressFields,
  addressFieldErrors,
  emptyDeliveryAddress,
  type DeliveryAddressInput,
} from "../../shop/DeliveryAddressFields";
import { PreferredTimeField } from "../../shop/PreferredTimeField";
import { PartnerBadge } from "./PartnerBadge";
import { PartnerPhoto } from "./PartnerPhoto";
import { COMBO_HOUSE_FREIGHT_CENTS, comboPrice } from "./comboPricing";
import {
  COMBO_MAX_QUANTITY,
  comboOrderHref,
  fetchCombo,
  partnerDelivers,
  partnerEarliestDate,
  submitComboOrder,
  type ComboSummary,
} from "./comboApi";
import { deliveryLine } from "./publicApi";
import "./marketplace-public.css";
import "./combo.css";

type Props = { comboId: string };

function storeToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

const DATE_LABEL = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });

function dateLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return DATE_LABEL.format(new Date(Date.UTC(y, m - 1, d)));
}

function LockIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

type QtyProps = { label: string; value: number; onChange: (next: number) => void };

/** Contador compacto com rótulo próprio (há dois na mesma tela: pães e item do parceiro). */
function ComboQty({ label, value, onChange }: QtyProps) {
  return (
    <div className="cmb-qty" role="group" aria-label={label}>
      <button
        type="button"
        aria-label={`Diminuir ${label.toLowerCase()}`}
        disabled={value <= 1}
        onClick={() => onChange(value - 1)}
      >
        −
      </button>
      <output aria-live="polite">{value}</output>
      <button
        type="button"
        aria-label={`Aumentar ${label.toLowerCase()}`}
        disabled={value >= COMBO_MAX_QUANTITY}
        onClick={() => onChange(value + 1)}
      >
        +
      </button>
    </div>
  );
}

export function ComboCheckoutPage({ comboId }: Props) {
  const uid = useId();
  const stored = useMemo(() => readStoredContact(), []);
  const [combo, setCombo] = useState<ComboSummary | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");
  const [variantId, setVariantId] = useState("");
  const [breadQty, setBreadQty] = useState(1);
  const [itemQty, setItemQty] = useState(1);
  const [date, setDate] = useState<string | null>(null);
  const [day, setDay] = useState<CalendarDay | null>(null);
  const [preferredTime, setPreferredTime] = useState("");
  const [address, setAddress] = useState<DeliveryAddressInput>(emptyDeliveryAddress);
  const [name, setName] = useState(stored.name);
  const [email, setEmail] = useState(stored.email);
  const [phone, setPhone] = useState("");
  const [idempotency] = useState(newIdempotencyKey);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCombo(comboId)
      .then((data) => {
        if (cancelled) return;
        if (!data?.bread?.variants?.length || !data.product) {
          setState("missing");
          return;
        }
        setCombo(data);
        setVariantId(data.bread.variants[0].id);
        setState("ready");
        document.title = `${data.bread.name} + ${data.product.name} — Loja de Pães`;
      })
      .catch(() => {
        if (!cancelled) setState("missing");
      });
    return () => {
      cancelled = true;
    };
  }, [comboId]);

  if (state === "loading") {
    return (
      <StorefrontLayout>
        <main className="cmb-page" aria-busy="true">
          <p className="mkp-muted">Carregando a combo…</p>
        </main>
      </StorefrontLayout>
    );
  }

  if (state === "missing" || !combo) {
    return (
      <StorefrontLayout>
        <main className="cmb-page">
          <h1 className="cmb-title">Esta combo não está disponível</h1>
          <p className="mkp-muted">Ela pode ter saído da vitrine. Veja os pães da casa e as combinações de hoje.</p>
          <p>
            <a className="cmb-link" href="/">
              Voltar para a página principal
            </a>
          </p>
        </main>
      </StorefrontLayout>
    );
  }

  const variant = combo.bread.variants.find((item) => item.id === variantId) ?? combo.bread.variants[0];
  // Preço do acordo (quando a Loja definiu) vale para qualquer apresentação; senão, o preço da vitrine.
  const breadUnit = combo.house_unit_price_cents ?? variant.price_cents;
  const price = comboPrice(breadQty * breadUnit, [
    { itemCents: itemQty * combo.product.price_cents, freightCents: combo.delivery.freight_cents },
  ]);
  const earliest = partnerEarliestDate(combo.delivery, storeToday());
  const brand = combo.partner.brand_name;

  function validate(): Record<string, string> {
    const found: Record<string, string> = {};
    if (!date) found.date = "Escolha a data da fornada no calendário.";
    else if (date < earliest) found.date = `${brand} precisa de pelo menos ${combo!.delivery.days ?? 0} dia(s). Escolha a partir de ${dateLabel(earliest)}.`;
    if (!name.trim()) found.name = "Informe o nome de quem pede.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) found.email = "Informe um e-mail válido.";
    const addr = addressFieldErrors(address);
    Object.entries(addr).forEach(([key, value]) => {
      if (value) found[key] = value;
    });
    if (!addr.delivery_city && !partnerDelivers(combo!.delivery, address.delivery_city, address.delivery_district)) {
      found.delivery_city = `${brand} entrega em ${combo!.delivery.cities.join(", ") || "outras regiões"}.`;
    }
    return found;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitError(null);
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) {
      const first = formRef.current?.querySelector<HTMLElement>("[aria-invalid='true']");
      first?.focus();
      if (!first) formRef.current?.querySelector<HTMLElement>(".cmb-error")?.scrollIntoView({ block: "center" });
      return;
    }
    setSending(true);
    try {
      const created = await submitComboOrder(combo!.id, {
        ...address,
        variant_id: variant.id,
        bread_quantity: breadQty,
        item_quantity: itemQty,
        requested_date: date as string,
        preferred_time: preferredTime,
        customer_name: name.trim(),
        customer_email: email.trim(),
        customer_phone: phone.trim(),
        idempotency_key: idempotency,
        quoted_cents: price.totalCents,
      });
      writeStoredContact(name.trim(), email.trim());
      window.location.assign(comboOrderHref(created.combo_ref, created.token));
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        setSubmitError("O preço ou a data mudaram enquanto você escolhia. Confira o resumo e envie de novo.");
        fetchCombo(combo!.id)
          .then(setCombo)
          .catch(() => undefined);
      } else if (reason instanceof ApiError && reason.status === 422 && reason.message) {
        setSubmitError(reason.message);
      } else {
        setSubmitError("Não foi possível enviar o pedido agora. Tente de novo em instantes.");
      }
      setSending(false);
    }
  }

  const fid = (key: string) => `${uid}-${key}`;

  return (
    <StorefrontLayout>
      <main className="cmb-page">
        <p className="eyebrow">Combinação da casa</p>
        <h1 className="cmb-title">
          {combo.bread.name} <span className="cmb-plus">+</span> {combo.product.name}
        </h1>
        <PartnerBadge partner={combo.partner} />

        <div className="cmb-grid">
          <form className="cmb-form" onSubmit={(event) => void submit(event)} noValidate ref={formRef}>
            <section className="cmb-step" aria-labelledby={fid("s1")}>
              <h2 id={fid("s1")}>
                <span className="cmb-n" aria-hidden="true">
                  1
                </span>
                Data da fornada
              </h2>
              <p className="mkp-muted">
                O pão sai na fornada que você escolher. {brand} entrega no mesmo dia
                {combo.delivery.days ? `, com pelo menos ${combo.delivery.days} dia(s) de antecedência` : ""}.
              </p>
              <BakeCalendar
                lines={[{ kind: "product", quantity: breadQty, variant_id: variant.id }]}
                selectedDate={date}
                onSelectDate={(next) => {
                  setDate(next);
                  setErrors((current) => ({ ...current, date: "" }));
                }}
                onSelectedDayChange={setDay}
                layout="checkout"
              />
              {errors.date ? (
                <p className="cmb-error" role="alert">
                  {errors.date}
                </p>
              ) : null}
              <PreferredTimeField value={preferredTime} onChange={setPreferredTime} modality="delivery" windows={day?.windows} />
            </section>

            <section className="cmb-step" aria-labelledby={fid("s2")}>
              <h2 id={fid("s2")}>
                <span className="cmb-n" aria-hidden="true">
                  2
                </span>
                Entrega
              </h2>
              <p className="mkp-muted">O mesmo endereço vale para o pão e para {combo.product.name.toLowerCase()}.</p>
              <DeliveryAddressFields
                value={address}
                onChange={(next) => {
                  setAddress(next);
                  setErrors((current) => {
                    const copy = { ...current };
                    Object.keys(next).forEach((key) => delete copy[key]);
                    return copy;
                  });
                }}
                errors={errors}
                note="required"
              />
            </section>

            <section className="cmb-step" aria-labelledby={fid("s3")}>
              <h2 id={fid("s3")}>
                <span className="cmb-n" aria-hidden="true">
                  3
                </span>
                Seus dados
              </h2>
              <div className="cmb-fields">
                <label htmlFor={fid("name")}>Nome de quem pede</label>
                <input
                  id={fid("name")}
                  autoComplete="name"
                  maxLength={160}
                  value={name}
                  aria-invalid={errors.name ? true : undefined}
                  onChange={(event) => setName(event.target.value)}
                />
                {errors.name ? <p className="cmb-error">{errors.name}</p> : null}
                <label htmlFor={fid("email")}>E-mail para acompanhar o pedido</label>
                <input
                  id={fid("email")}
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  value={email}
                  aria-invalid={errors.email ? true : undefined}
                  onChange={(event) => setEmail(event.target.value)}
                />
                {errors.email ? <p className="cmb-error">{errors.email}</p> : null}
                <label htmlFor={fid("phone")}>Telefone (opcional)</label>
                <input
                  id={fid("phone")}
                  type="tel"
                  autoComplete="tel"
                  maxLength={40}
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
              </div>
            </section>

            {submitError ? (
              <p className="cmb-alert" role="alert">
                {submitError}
              </p>
            ) : null}
            <button type="submit" className="primary cmb-submit" disabled={sending}>
              {sending ? "Enviando…" : "Enviar pedido da combo"}
            </button>
            <p className="cmb-after">
              Nada é cobrado agora. A Loja e {brand} confirmam a data; depois você recebe os pagamentos por e-mail.
            </p>
          </form>

          <aside className="cmb-summary" aria-labelledby={fid("sum")}>
            <h2 id={fid("sum")} className="cmb-summary-title">
              Sua combo
            </h2>
            <div className="cmb-item">
              <div>
                <strong>{combo.bread.name}</strong>
                {combo.bread.variants.length > 1 ? (
                  <label className="cmb-variant">
                    <span className="mkp-sr">Apresentação</span>
                    <select value={variant.id} onChange={(event) => setVariantId(event.target.value)}>
                      {combo.bread.variants.map((item) => (
                        <option key={item.id} value={item.id}>
                          {combo.house_unit_price_cents == null ? `${item.name} — ${formatCents(item.price_cents)}` : item.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <span className="mkp-muted">{variant.name}</span>
                )}
                <span className="mkp-muted cmb-unit">{formatCents(breadUnit)} cada</span>
                <ComboQty label="Quantidade de pães" value={breadQty} onChange={setBreadQty} />
              </div>
              <span>{formatCents(breadQty * breadUnit)}</span>
            </div>
            <div className="cmb-item">
              <PartnerPhoto className="cmb-thumb" src={combo.product.photos[0]} alt={combo.product.name} />
              <div>
                <strong>{combo.product.name}</strong>
                <span className="mkp-muted">por {brand}</span>
                <span className="mkp-muted cmb-unit">{formatCents(combo.product.price_cents)} cada</span>
                <ComboQty label={`Quantidade de ${combo.product.name}`} value={itemQty} onChange={setItemQty} />
              </div>
              <span>{formatCents(itemQty * combo.product.price_cents)}</span>
            </div>
            <dl className="cmb-lines" aria-label="Entregas">
              <div>
                <dt>Entrega do pão · Loja de Pães</dt>
                <dd>{formatCents(COMBO_HOUSE_FREIGHT_CENTS)}</dd>
              </div>
              <div>
                <dt>Entrega · {brand}</dt>
                <dd>{combo.delivery.freight_cents ? formatCents(combo.delivery.freight_cents) : "grátis"}</dd>
              </div>
            </dl>
            <p className="cmb-total">
              <span>Total</span>
              <strong>{formatCents(price.totalCents)}</strong>
            </p>
            <p className="cmb-date">{date ? `Fornada de ${dateLabel(date)}` : "Escolha a data da fornada"}</p>
            <p className="cmb-note">{deliveryLine(combo.delivery, formatCents)}.</p>
            <p className="cmb-trust">
              <LockIcon />
              Você paga em {price.payments} partes, cada uma direto a quem entrega, pelo Mercado Pago, só depois do aceite.
            </p>
          </aside>
        </div>
      </main>
    </StorefrontLayout>
  );
}
