import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError } from "../services/http";
import { formatCents } from "../lib/money";
import type { CalendarLine } from "./calendarApi";
import { newIdempotencyKey, readStoredContact, writeStoredContact } from "./contactStorage";
import { fetchOperations } from "./operationsApi";
import { trackEvent } from "./tracking";
import { fetchSuggestions, submitDateRequest, type SuggestionItem, type SuggestionsPayload } from "./suggestionsApi";

type Props = {
  selectedDate: string | null;
  lines: CalendarLine[];
  cartCount: number;
};

function priceLabel(item: SuggestionItem): string {
  if (item.price.cents === null) {
    return "Preço a definir";
  }
  const formatted = formatCents(item.price.cents);
  return item.price_is_from ? `A partir de ${formatted}` : formatted;
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.message && error.message !== "resposta-invalida") {
    return error.message;
  }
  return "Não foi possível enviar a solicitação agora.";
}

export function FornadaPanel({ selectedDate, lines, cartCount }: Props) {
  const [data, setData] = useState<SuggestionsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const stored = useMemo(() => readStoredContact(), []);
  const minDate = useMemo(() => {
    const local = new Date();
    const month = String(local.getMonth() + 1).padStart(2, "0");
    const day = String(local.getDate()).padStart(2, "0");
    return `${local.getFullYear()}-${month}-${day}`;
  }, []);
  const [desiredDate, setDesiredDate] = useState(selectedDate ?? "");
  const [name, setName] = useState(stored.name);
  const [email, setEmail] = useState(stored.email);
  const [quantity, setQuantity] = useState("2");
  const [note, setNote] = useState("");
  const [idempotency, setIdempotency] = useState(newIdempotencyKey);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [dateRequestsEnabled, setDateRequestsEnabled] = useState(false);
  const [operationsReady, setOperationsReady] = useState(false);
  const [operationsError, setOperationsError] = useState(false);
  const [operationsAttempt, setOperationsAttempt] = useState(0);
  const [suggestionsAttempt, setSuggestionsAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchOperations()
      .then((status) => {
        if (!cancelled) {
          setDateRequestsEnabled(status.date_requests_enabled);
          setOperationsError(false);
          setOperationsReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDateRequestsEnabled(false);
          setOperationsError(true);
          setOperationsReady(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [operationsAttempt]);

  useEffect(() => {
    if (selectedDate) {
      setDesiredDate(selectedDate);
    }
  }, [selectedDate]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    fetchSuggestions({ selected: selectedDate, lines })
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError("Não foi possível carregar as sugestões agora.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [lines, selectedDate, suggestionsAttempt]);

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
      setFormOpen(false);
    } catch (reason: unknown) {
      setSendError(requestErrorMessage(reason));
    } finally {
      setSending(false);
    }
  }

  return (
    <aside className="fornada-panel" aria-labelledby="fornada-panel-title">
      <h3 id="fornada-panel-title">{data?.title ?? "Vagas nesta fornada"}</h3>
      {loading ? <p className="fornada-note">Consultando as vagas desta fornada…</p> : null}
      {error ? (
        <p className="fornada-note" role="alert">
          {error}{" "}
          <button type="button" className="text-button" onClick={() => setSuggestionsAttempt((current) => current + 1)}>
            Tentar as sugestões de novo
          </button>
        </p>
      ) : null}
      {!loading && !error && data?.message ? <p className="fornada-note">{data.message}</p> : null}
      {!loading && !error && data && data.items.length > 0 ? (
        <ul className="fornada-suggestions">
          {data.items.map((item) => (
            <li key={item.slug}>
              <article className="fornada-card">
                {item.image_url ? (
                  <img src={item.image_url} alt={item.image_alt || item.name} />
                ) : (
                  <div className="fornada-card-missing">Sem foto</div>
                )}
                <div>
                  <h4>{item.name}</h4>
                  <p>
                    {item.presentation} · {priceLabel(item)}
                  </p>
                  <a className="text-button" href={item.href}>
                    Escolher este pão
                  </a>
                </div>
              </article>
            </li>
          ))}
        </ul>
      ) : null}
      {sent ? <p className="fornada-success">{sent}</p> : null}
      {dateRequestsEnabled ? (
        <div className="fornada-request">
          <p>Não encontrou uma data?</p>
          <button type="button" className="text-button" onClick={() => setFormOpen((open) => !open)}>
            Solicitar outra data
          </button>
        </div>
      ) : !operationsReady ? null : operationsError ? (
        <p className="fornada-note" role="alert">
          Não foi possível consultar as solicitações de data.{" "}
          <button type="button" className="text-button" onClick={() => setOperationsAttempt((current) => current + 1)}>
            Tentar de novo
          </button>
        </p>
      ) : (
        <p className="fornada-note">Solicitação de outra data indisponível no momento.</p>
      )}
      {formOpen && dateRequestsEnabled ? (
        <form className="fornada-form" onSubmit={handleSubmit}>
          <p>
            Conte a data que você tem em mente. Vamos avaliar a possibilidade e responder por e-mail. Esta
            solicitação ainda não confirma a fornada.
          </p>
          <label>
            Data desejada
            <input
              type="date"
              required
              min={minDate}
              value={desiredDate}
              onChange={(event) => setDesiredDate(event.target.value)}
            />
          </label>
          <label>
            Nome
            <input value={name} required maxLength={160} autoComplete="name" onChange={(event) => setName(event.target.value)} />
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
    </aside>
  );
}
