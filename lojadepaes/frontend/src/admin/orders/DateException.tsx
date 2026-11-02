import { useEffect, useState } from "react";
import { adminRequest, bakeryTimeZone } from "../api";
import { formatShortDay } from "../format";
import type { OrderDetail, ScheduleException } from "../types";

export type RescheduleBody = {
  date: string;
  reason: string;
  origin: "customer" | "store";
  notify_customer: boolean;
  allow_closed_day: boolean;
};

function bakeryToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: bakeryTimeZone(),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function messageOf(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Não foi possível concluir.";
}

export function ScheduleLine({ exception }: { exception?: ScheduleException | null }) {
  if (!exception) {
    return null;
  }
  const actor = exception.actor ? ` Por ${exception.actor}.` : "";
  const reason = exception.reason ? ` Motivo: ${exception.reason}.` : "";
  return (
    <p>
      Solicitado para {formatShortDay(exception.requested_date)} · Entrega em{" "}
      {formatShortDay(exception.operational_date)} — {exception.label.toLowerCase()}.{actor}
      {reason}
    </p>
  );
}

export function QueueDateMark({ exception }: { exception?: ScheduleException | null }) {
  if (!exception?.short_label) {
    return null;
  }
  const title = `${exception.label}. Solicitado para ${formatShortDay(exception.requested_date)}`;
  return (
    <span className="queue-exception" title={title}>
      <span className="queue-sr">{title}</span>
      <span aria-hidden="true">{exception.short_label}</span>
    </span>
  );
}

export function ReschedulePanel({
  order,
  busy,
  onClose,
  onSubmit,
}: {
  order: OrderDetail;
  busy: boolean;
  onClose: () => void;
  onSubmit: (body: RescheduleBody) => Promise<void>;
}) {
  const completed = order.status === "completed";
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const [origin, setOrigin] = useState<"customer" | "store">("customer");
  const [notify, setNotify] = useState(!completed);
  const [allowClosed, setAllowClosed] = useState(false);
  const [occupancy, setOccupancy] = useState<string | null>(null);
  const [closed, setClosed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!date) {
      setOccupancy(null);
      setClosed(false);
      return;
    }
    let cancel = false;
    adminRequest<{ committed_physical: number; daily_physical_limit: number; is_open: boolean }>(
      `/api/v1/admin/schedule/days/${date}`,
    )
      .then((day) => {
        if (cancel) return;
        setOccupancy(`${day.committed_physical} de ${day.daily_physical_limit} pães`);
        setClosed(!day.is_open);
        if (day.is_open) setAllowClosed(false);
      })
      .catch(() => {
        if (!cancel) setOccupancy(null);
      });
    return () => {
      cancel = true;
    };
  }, [date]);

  const today = bakeryToday();
  const past = Boolean(date) && !completed && date < today;
  const blocked = !date || !reason.trim() || past || (closed && !allowClosed);

  return (
    <form
      className="admin-cancel"
      onSubmit={(event) => {
        event.preventDefault();
        if (blocked) return;
        setError(null);
        void onSubmit({
          date,
          reason: reason.trim(),
          origin,
          notify_customer: completed ? false : notify,
          allow_closed_day: allowClosed,
        }).catch((caught) => setError(messageOf(caught)));
      }}
    >
      <p>Data atual: {order.production_local_date ? formatShortDay(order.production_local_date) : "sem data"}</p>
      <label>
        Nova data
        <input type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
      </label>
      {occupancy ? <p>Ocupação da data escolhida: {occupancy}</p> : null}
      {past ? <p className="admin-error" role="alert">A data nova não pode ser anterior a hoje.</p> : null}
      {closed ? (
        <label className="admin-check">
          <input
            type="checkbox"
            checked={allowClosed}
            onChange={(event) => setAllowClosed(event.target.checked)}
          />
          Reservar mesmo fora dos dias de produção
        </label>
      ) : null}
      <fieldset>
        <legend>Origem da mudança</legend>
        <label className="admin-check">
          <input type="radio" name="date-origin" checked={origin === "customer"} onChange={() => setOrigin("customer")} />
          A pedido do cliente
        </label>
        <label className="admin-check">
          <input type="radio" name="date-origin" checked={origin === "store"} onChange={() => setOrigin("store")} />
          Pela loja
        </label>
      </fieldset>
      <label>
        Motivo
        <textarea value={reason} onChange={(event) => setReason(event.target.value)} required maxLength={280} rows={3} />
      </label>
      {completed ? null : (
        <label className="admin-check">
          <input type="checkbox" checked={notify} onChange={(event) => setNotify(event.target.checked)} />
          Avisar o cliente por e-mail
        </label>
      )}
      {error ? <p className="admin-error" role="alert">{error}</p> : null}
      <div className="admin-actions">
        <button className="admin-primary" type="submit" disabled={busy || blocked}>
          Confirmar exceção de data
        </button>
        <button className="admin-secondary" type="button" onClick={onClose}>
          Voltar
        </button>
      </div>
    </form>
  );
}

export function VoidPanel({
  order,
  busy,
  onClose,
  onSubmit,
}: {
  order: OrderDetail;
  busy: boolean;
  onClose: () => void;
  onSubmit: (body: { original_order_id: string; reason: string }) => Promise<void>;
}) {
  const preset = order.duplicate_candidates?.[0];
  const [originalId, setOriginalId] = useState(preset?.id ?? "");
  const [reference, setReference] = useState(preset?.public_reference ?? "");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hits, setHits] = useState<Array<{ id: string; public_reference: string }>>(
    preset ? [{ id: preset.id, public_reference: preset.public_reference }] : [],
  );

  return (
    <form
      className="admin-cancel"
      onSubmit={(event) => {
        event.preventDefault();
        if (!originalId || !reason.trim()) return;
        setError(null);
        void onSubmit({ original_order_id: originalId, reason: reason.trim() }).catch((caught) =>
          setError(messageOf(caught)),
        );
      }}
    >
      <p>
        A vaga é liberada, o pagamento local sem provedor é cancelado e o pedido sai da fila. O status registrado não
        muda. Nenhum e-mail é enviado.
      </p>
      <label>
        Pedido original
        <input
          value={reference}
          onChange={(event) => setReference(event.target.value)}
          aria-label="Referência do pedido original"
        />
      </label>
      <button
        type="button"
        className="admin-secondary"
        onClick={() => {
          const needle = reference.trim();
          if (!needle) return;
          void adminRequest<{ items: Array<{ id: string; public_reference: string; source?: string }> }>(
            `/api/v1/admin/orders?reference=${encodeURIComponent(needle)}&status=all`,
          )
            .then((data) => {
              const found = (data.items || []).filter(
                (item) => item.source !== "date_request" && item.public_reference === needle,
              );
              setHits(found);
              if (found[0]) setOriginalId(found[0].id);
              if (!found.length) setError("Nenhum pedido com essa referência.");
            })
            .catch((caught) => setError(messageOf(caught)));
        }}
      >
        Buscar
      </button>
      {hits.length > 0 ? (
        <label>
          Seleção
          <select value={originalId} onChange={(event) => setOriginalId(event.target.value)}>
            {hits.map((item) => (
              <option key={item.id} value={item.id}>
                {item.public_reference}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label>
        Motivo
        <textarea value={reason} onChange={(event) => setReason(event.target.value)} required maxLength={280} rows={3} />
      </label>
      {error ? <p className="admin-error" role="alert">{error}</p> : null}
      <div className="admin-actions">
        <button className="admin-danger" type="submit" disabled={busy || !originalId || !reason.trim()}>
          Confirmar
        </button>
        <button className="admin-secondary" type="button" onClick={onClose}>
          Voltar
        </button>
      </div>
    </form>
  );
}

export function deliverySense(order: OrderDetail, today: string): "antecipada" | "adiada" {
  const requested = order.requested_date || order.production_local_date || today;
  return today < requested ? "antecipada" : "adiada";
}

export { bakeryToday };
