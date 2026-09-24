import { useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "./api";

type EventRow = { action: string; actor_ref: string | null; detail: string | null; created_at: string };
type RequestRow = {
  id: string;
  status: string;
  desired_date: string;
  proposed_date: string | null;
  customer_name: string;
  customer_email: string;
  intended_quantity: number | null;
  message: string | null;
  admin_note: string | null;
  cart_context: Array<{ product_name: string; variant_name: string; quantity: number }> | null;
  created_at: string;
  events: EventRow[];
};

const STATUS: Record<string, string> = {
  pending: "Pendente de avaliação",
  alternative_proposed: "Alternativa proposta",
  closed: "Encerrada",
};

function errorMessage(error: unknown): string {
  if (error instanceof AdminApiError) {
    return error.message;
  }
  return "Não foi possível atualizar as solicitações.";
}

export function DateRequestsPanel() {
  const [items, setItems] = useState<RequestRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<Record<string, string>>({});
  const [proposed, setProposed] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  async function refresh() {
    try {
      const data = await adminRequest<{ items: RequestRow[] }>("/api/v1/admin/date-requests");
      setItems(data.items);
      setError(null);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function act(id: string, action: "propose" | "close") {
    setBusy(`${action}-${id}`);
    try {
      const data = await adminRequest<RequestRow>(`/api/v1/admin/date-requests/${id}`, {
        method: "POST",
        body: JSON.stringify({
          action,
          proposed_date: action === "propose" ? proposed[id] || null : null,
          note: note[id] || null,
        }),
      });
      setItems((current) => current.map((item) => (item.id === id ? data : item)));
      setError(null);
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="admin-date-requests agenda-card" aria-labelledby="date-requests-title">
      <h2 id="date-requests-title">Clientes que pediram outra data</h2>
      <p className="admin-lead">
        São pedidos para avaliar uma data diferente. Você pode analisar e responder; isso ainda não
        confirma uma encomenda.
      </p>
      {error ? <p className="admin-error">{error}</p> : null}
      {items.length === 0 ? <p className="admin-empty">Nenhum cliente solicitou outra data até agora.</p> : null}
      <ul className="admin-date-request-list">
        {items.map((item) => (
          <li key={item.id} className="admin-date-request">
            <p>
              <strong>{item.customer_name}</strong> · {item.customer_email}
            </p>
            <p>
              Data desejada {item.desired_date}
              {item.proposed_date ? ` · alternativa ${item.proposed_date}` : ""} ·{" "}
              {STATUS[item.status] ?? item.status}
            </p>
            <p>Quantidade {item.intended_quantity ?? "não informada"}</p>
            {item.message ? <p>{item.message}</p> : null}
            {item.cart_context && item.cart_context.length > 0 ? (
              <p>
                Seleção:{" "}
                {item.cart_context
                  .map((line) => `${line.quantity}× ${line.product_name} (${line.variant_name})`)
                  .join("; ")}
              </p>
            ) : null}
            <ol>
              {item.events.map((event) => (
                <li key={`${event.created_at}-${event.action}`}>
                  {event.created_at}: {event.action}
                  {event.detail ? ` — ${event.detail}` : ""}
                </li>
              ))}
            </ol>
            {item.status !== "closed" ? (
              <div className="admin-date-request-actions">
                <label>
                  Data alternativa
                  <input
                    type="date"
                    value={proposed[item.id] ?? ""}
                    onChange={(event) => setProposed((current) => ({ ...current, [item.id]: event.target.value }))}
                  />
                </label>
                <label>
                  Nota
                  <input
                    value={note[item.id] ?? ""}
                    onChange={(event) => setNote((current) => ({ ...current, [item.id]: event.target.value }))}
                  />
                </label>
                <button
                  type="button"
                  className="admin-secondary"
                  disabled={busy !== null}
                  onClick={() => void act(item.id, "propose")}
                >
                  Propor outra data
                </button>
                <button
                  type="button"
                  className="admin-text"
                  disabled={busy !== null}
                  onClick={() => void act(item.id, "close")}
                >
                  Encerrar
                </button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
