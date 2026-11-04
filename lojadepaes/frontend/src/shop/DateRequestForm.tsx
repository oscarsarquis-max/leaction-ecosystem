import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError } from "../services/http";
import { previewCalendar, type CalendarDay, type CalendarLine } from "./calendarApi";
import { isSellableDay } from "./calendarDays";
import { goStorefront } from "./checkoutApi";
import { newIdempotencyKey, readStoredContact, writeStoredContact } from "./contactStorage";
import { fetchOperations } from "./operationsApi";
import { trackEvent } from "./tracking";
import { submitDateRequest } from "./suggestionsApi";

type Props = {
  selectedDate: string | null;
  lines: CalendarLine[];
  cartCount: number;
  calendarReady?: boolean;
  closureNoticeVisibleAbove?: boolean;
  /** Escolhe o dia no calendário da própria página (usado quando o carrinho já está aberto). */
  onChooseDate?: (date: string) => void;
};

export const DATE_AVAILABLE_MESSAGE = "Esta data está disponível. Finalize o pedido pelo carrinho.";
const PREFERRED_DATE_KEY = "lojadepaes_preferred_date";
const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

export const DATE_REQUEST_EXPLANATION =
  "Sugira uma data. A Loja avalia a possibilidade e responde por e-mail. Esta solicitação ainda não confirma a fornada.";

export const QUANTITY_REQUIRED_MESSAGE = "Informe a quantidade de pães: 1 ou mais.";

export function parseIntendedQuantity(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed || !/^[1-9]\d*$/.test(trimmed)) {
    return null;
  }
  return Number(trimmed);
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.message && error.message !== "resposta-invalida") {
    return error.message;
  }
  return "Não foi possível enviar a solicitação agora.";
}

export function DateRequestForm({
  selectedDate,
  lines,
  cartCount,
  calendarReady = true,
  closureNoticeVisibleAbove = false,
  onChooseDate,
}: Props) {
  const stored = useMemo(() => readStoredContact(), []);
  const [enabled, setEnabled] = useState(false);
  const [businessDate, setBusinessDate] = useState("");
  const [closureNotice, setClosureNotice] = useState<string | null>(null);
  const [desiredDate, setDesiredDate] = useState(selectedDate ?? "");
  const [name, setName] = useState(stored.name);
  const [email, setEmail] = useState(stored.email);
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [idempotency, setIdempotency] = useState(newIdempotencyKey);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [day, setDay] = useState<CalendarDay | null>(null);
  const [refusedAsAvailable, setRefusedAsAvailable] = useState<string | null>(null);
  const linesKey = JSON.stringify(lines);

  // Avalia a data digitada com o mesmo calendário da vitrine (qualquer mês, não só o que está na tela).
  useEffect(() => {
    setDay(null);
    if (!enabled || !ISO_DAY.test(desiredDate) || (businessDate && desiredDate < businessDate)) {
      return;
    }
    let cancelled = false;
    Promise.resolve(previewCalendar({ start: desiredDate, end: desiredDate, selected: desiredDate, lines }))
      .then((payload) => {
        if (!cancelled) {
          setDay(payload?.days?.find((item) => item.date === desiredDate) ?? null);
        }
      })
      .catch(() => {
        /* sem resposta do calendário: o servidor decide no envio */
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, desiredDate, businessDate, linesKey]);

  useEffect(() => {
    let cancelled = false;
    fetchOperations()
      .then((status) => {
        if (cancelled) {
          return;
        }
        setEnabled(status.date_requests_enabled);
        setBusinessDate(status.business_date ?? "");
        setClosureNotice(status.closure_notice ?? null);
      })
      .catch(() => {
        if (!cancelled) {
          setEnabled(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedDate) {
      setDesiredDate(selectedDate);
    }
  }, [selectedDate]);

  if (!enabled) {
    return null;
  }

  const showIsolatedNotice = Boolean(closureNotice && calendarReady && !closureNoticeVisibleAbove);
  const dateIsAvailable =
    refusedAsAvailable === desiredDate || Boolean(day && day.date === desiredDate && isSellableDay(day));

  function goToCart() {
    sessionStorage.setItem(PREFERRED_DATE_KEY, desiredDate);
    if (window.location.pathname === "/pedido/novo") {
      onChooseDate?.(desiredDate);
      document.querySelector(".checkout-form")?.scrollIntoView({ block: "start" });
      return;
    }
    goStorefront("/pedido/novo");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (dateIsAvailable) {
      return;
    }
    let intended: number | undefined;
    if (cartCount === 0) {
      const parsed = parseIntendedQuantity(quantity);
      if (parsed === null) {
        setSendError(QUANTITY_REQUIRED_MESSAGE);
        return;
      }
      intended = parsed;
    }
    setSending(true);
    setSendError(null);
    try {
      const result = await submitDateRequest({
        desired_date: desiredDate,
        customer_name: name,
        customer_email: email,
        intended_quantity: intended,
        message: note.trim() || undefined,
        idempotency_key: idempotency,
        lines: lines
          .filter((line) => line.kind === "product" && line.variant_id)
          .map((line) => ({ variant_id: line.variant_id as string, quantity: line.quantity })),
      });
      writeStoredContact(name, email);
      trackEvent("data_solicitar", {
        idUsuario: result.id,
        dados: { data_solicitada: result.desired_date },
      });
      setSent(result.message);
      setIdempotency(newIdempotencyKey());
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.status === 409 && reason.message === DATE_AVAILABLE_MESSAGE) {
        setRefusedAsAvailable(desiredDate);
      } else {
        setSendError(requestErrorMessage(reason));
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bake-calendar-request">
      <h4>Precisa de outra data?</h4>
      <p>{DATE_REQUEST_EXPLANATION}</p>
      {showIsolatedNotice ? <p>{closureNotice}</p> : null}
      {sent ? <p className="fornada-success">{sent}</p> : null}
      <form className="fornada-form" onSubmit={handleSubmit}>
        <label>
          Data desejada
          <input
            type="date"
            required
            min={businessDate || undefined}
            value={desiredDate}
            onChange={(event) => setDesiredDate(event.target.value)}
          />
        </label>
        <label>
          Nome
          <input
            value={name}
            required
            maxLength={160}
            autoComplete="name"
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          E-mail
          <input
            type="email"
            value={email}
            required
            maxLength={254}
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        {cartCount > 0 ? (
          <p className="fornada-note">Vamos considerar os pães já escolhidos na sua seleção.</p>
        ) : (
          <label>
            Quantidade pretendida
            <input
              type="number"
              step={1}
              inputMode="numeric"
              placeholder="Informe quantos pães"
              value={quantity}
              onChange={(event) => {
                setQuantity(event.target.value);
                if (sendError === QUANTITY_REQUIRED_MESSAGE) {
                  setSendError(null);
                }
              }}
            />
          </label>
        )}
        <label>
          Mensagem (opcional)
          <textarea value={note} maxLength={2000} rows={3} onChange={(event) => setNote(event.target.value)} />
        </label>
        {sendError ? (
          <p className="fornada-note" role="alert">
            {sendError}
          </p>
        ) : null}
        {dateIsAvailable ? (
          <div className="bake-calendar-request-available" role="status">
            <p>{DATE_AVAILABLE_MESSAGE}</p>
            <button type="button" className="primary" onClick={goToCart}>
              Ir para o carrinho
            </button>
          </div>
        ) : (
          <button type="submit" className="primary" disabled={sending}>
            {sending ? "Enviando…" : "Enviar solicitação"}
          </button>
        )}
      </form>
    </div>
  );
}
