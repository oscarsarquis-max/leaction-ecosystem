import { useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "./api";
import { formatDay } from "./format";

type RequestRow = {
  id: string;
  public_reference?: string;
  status: string;
  desired_date: string;
  customer_name: string;
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
  const [pending, setPending] = useState(0);

  useEffect(() => {
    adminRequest<{ items: RequestRow[]; pending_count?: number }>("/api/v1/admin/date-requests")
      .then((data) => {
        setItems(data.items);
        setPending(
          data.pending_count ??
            data.items.filter(
              (item) =>
                item.status === "pending" ||
                item.status === "alternative_proposed" ||
                item.status === "awaiting_details",
            )
              .length,
        );
        setError(null);
      })
      .catch((reason: unknown) => {
        setError(errorMessage(reason));
      });
  }, []);

  useEffect(() => {
    if (window.location.hash === "#date-requests") {
      document.getElementById("date-requests")?.scrollIntoView({ block: "start" });
    }
  }, [items.length]);

  const open = items.filter(
    (item) =>
      item.status === "pending" || item.status === "alternative_proposed" || item.status === "awaiting_details",
  );

  return (
    <section
      id="date-requests"
      className="admin-date-requests agenda-card"
      aria-labelledby="date-requests-title"
    >
      <h2 id="date-requests-title">Solicitações de data</h2>
      <p className="admin-lead">
        O atendimento acontece na fila de Pedidos. A Agenda permanece para configurar a produção.
      </p>
      {error ? <p className="admin-error">{error}</p> : null}
      <p>
        {pending === 0
          ? "Nenhuma solicitação aguardando resposta."
          : pending === 1
            ? "Há 1 solicitação aguardando resposta."
            : `Há ${pending} solicitações aguardando resposta.`}
      </p>
      {open.length > 0 ? (
        <ul className="admin-date-request-list">
          {open.slice(0, 4).map((item) => (
            <li key={item.id}>
              {item.public_reference || item.customer_name} · {formatDay(item.desired_date)}
            </li>
          ))}
        </ul>
      ) : null}
      <a className="admin-primary" href="/admin/pedidos">
        Atender em Pedidos
      </a>
    </section>
  );
}
