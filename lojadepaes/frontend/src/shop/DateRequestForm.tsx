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
};

function requestErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.message && error.message !== "resposta-invalida") {
    return error.message;
  }
  return "Não foi possível enviar a solicitação agora.";
}

export function DateRequestForm({ selectedDate, lines, cartCount }: Props) {
  const stored = useMemo(() => readStoredContact(), []);
  const [enabled, setEnabled] = useState(false);
  const [businessDate, setBusinessDate] = useState("");
  const [open, setOpen] = useState(false);
  const [desiredDate, setDesiredDate] = useState(selectedDate ?? "");
  const [name, setName] = useState(stored.name);
  const [email, setEmail] = useState(stored.email);
  const [quantity, setQuantity] = useState("2");
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

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setSendError(null);
    try {
      const result = await submitDateRequest({
        desired_date: desiredDate,
        customer_name: name,
        customer_email: email,
        intended_quantity: cartCount > 0 ? undefined : Number(quantity),
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
      setOpen(false);
    } catch (reason: unknown) {
      setSendError(requestErrorMessage(reason));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bake-calendar-request">
      <h4>Precisa de outra data?</h4>
      <p>
        Inclusive para hoje, você pode sugerir uma data. A padaria avalia a possibilidade antes de
        confirmar.
      </p>
      {sent ? <p className="fornada-success">{sent}</p> : null}
      <button type="button" className="text-button" onClick={() => setOpen((current) => !current)}>
        Sugerir uma data
      </button>
      {open ? (
        <form className="fornada-form" onSubmit={handleSubmit}>
          <p>
            Conte a data que você tem em mente. Vamos avaliar a possibilidade e responder por e-mail.
            Esta solicitação ainda não confirma a fornada.
          </p>
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
                min={1}
                required
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
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
      ) : null}
    </div>
  );
}
