import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError } from "../services/http";
import type { CalendarLine } from "./calendarApi";
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
};

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

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
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
      setSendError(requestErrorMessage(reason));
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
        <button type="submit" className="primary" disabled={sending}>
          {sending ? "Enviando…" : "Enviar solicitação"}
        </button>
      </form>
    </div>
  );
}
