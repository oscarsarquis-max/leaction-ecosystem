import { useEffect, useMemo, useState } from "react";
import { adminRequest } from "./api";

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

export type AgendaEntry = {
  id: string;
  source: string;
  reference: string;
  customer_name: string | null;
  composition: string;
  quantity: number | null;
  stage: string;
  payment: string;
  pending: string | null;
  pending_kind?: string;
  href: string;
};

export type AgendaDay = {
  date: string;
  orders: number;
  open_orders: number;
  historical_orders: number;
  pending_requests: number;
  bread_units: number;
  open: AgendaEntry[];
  historical: AgendaEntry[];
  pending: AgendaEntry[];
  cancelled: AgendaEntry[];
};

export type ProductionAgendaData = {
  timezone: string;
  year: number;
  month: number;
  today: string;
  days: AgendaDay[];
  undated: AgendaEntry[];
};

type Props = {
  refreshToken: string;
  onOpen: (href: string) => void;
};

function monthLabel(year: number, month: number): string {
  const raw = new Intl.DateTimeFormat("pt-BR", {
    month: "long",
    year: "numeric",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(Date.UTC(year, month - 1, 15)));
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function shiftMonth(year: number, month: number, delta: number): { year: number; month: number } {
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1 };
}

function EntryList({
  title,
  entries,
  onOpen,
}: {
  title: string;
  entries: AgendaEntry[];
  onOpen: (href: string) => void;
}) {
  if (entries.length === 0) {
    return null;
  }
  return (
    <div>
      <h3>{title}</h3>
      <ul className="admin-agenda-list">
        {entries.map((entry) => (
          <li key={`${entry.source}-${entry.id}`}>
            <p>
              <strong>{entry.reference}</strong> · {entry.customer_name || "Cliente não informado"}
            </p>
            <p>
              {entry.composition}
              {entry.quantity != null ? ` · ${entry.quantity} pães` : ""}
            </p>
            <p>
              {entry.stage} · {entry.payment}
              {entry.pending ? ` · ${entry.pending}` : ""}
            </p>
            <button type="button" className="admin-link" onClick={() => onOpen(entry.href)}>
              {entry.source === "date_request" ? "Abrir solicitação" : "Abrir pedido"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ProductionAgenda({ refreshToken, onOpen }: Props) {
  const [cursor, setCursor] = useState<{ year: number; month: number } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [data, setData] = useState<ProductionAgendaData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCancelled, setShowCancelled] = useState(false);
  const year = cursor?.year ?? data?.year;
  const month = cursor?.month ?? data?.month;

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (cursor) {
      params.set("year", String(cursor.year));
      params.set("month", String(cursor.month));
    }
    const query = params.toString();
    adminRequest<ProductionAgendaData>(
      `/api/v1/admin/ops/production-agenda${query ? `?${query}` : ""}`,
    )
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setData(payload);
        setError(null);
        setSelected((current) => current ?? payload.today);
      })
      .catch(() => {
        if (!cancelled) {
          setError("Não foi possível carregar a agenda de produção.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [cursor, refreshToken]);

  const selectedDay = useMemo(
    () => data?.days.find((day) => day.date === selected) ?? null,
    [data, selected],
  );
  const shownYear = year ?? data?.year ?? 2026;
  const shownMonth = month ?? data?.month ?? 1;
  const first = new Date(Date.UTC(shownYear, shownMonth - 1, 1));
  const mondayOffset = (first.getUTCDay() + 6) % 7;
  const cells: Array<AgendaDay | null> = [
    ...Array.from({ length: mondayOffset }, () => null),
    ...(data && data.year === shownYear && data.month === shownMonth ? data.days : []),
  ];

  return (
    <section className="admin-agenda" aria-labelledby="admin-agenda-title">
      <div className="admin-agenda-head">
        <h2 id="admin-agenda-title">Agenda de produção</h2>
        <button
          type="button"
          className="admin-secondary"
          onClick={() => {
            if (!data) {
              return;
            }
            const [todayYear, todayMonth] = data.today.split("-").map(Number);
            setCursor({ year: todayYear, month: todayMonth });
            setSelected(data.today);
          }}
        >
          Hoje
        </button>
      </div>
      <div className="admin-agenda-layout">
        <div className="admin-agenda-calendar">
          <div className="admin-agenda-nav">
            <button
              type="button"
              aria-label="Mês anterior"
              onClick={() => setCursor(shiftMonth(shownYear, shownMonth, -1))}
            >
              ‹
            </button>
            <p>{monthLabel(shownYear, shownMonth)}</p>
            <button
              type="button"
              aria-label="Próximo mês"
              onClick={() => setCursor(shiftMonth(shownYear, shownMonth, 1))}
            >
              ›
            </button>
          </div>
          <div className="admin-agenda-grid">
            {WEEKDAYS.map((label) => (
              <span key={label}>{label}</span>
            ))}
            {cells.map((day, index) =>
              day ? (
                <button
                  key={day.date}
                  type="button"
                  className={`admin-agenda-day${day.date === selected ? " is-selected" : ""}${day.date === data?.today ? " is-today" : ""}`}
                  aria-pressed={day.date === selected}
                  onClick={() => setSelected(day.date)}
                >
                  <span>{Number(day.date.slice(8))}</span>
                  {day.orders > 0 ? <small>{day.orders} ped.</small> : null}
                  {day.bread_units > 0 ? <small>{day.bread_units} pães</small> : null}
                  {day.pending_requests > 0 ? <small>{day.pending_requests} solic.</small> : null}
                </button>
              ) : (
                <span key={`empty-${index}`} />
              ),
            )}
          </div>
          <p className="admin-agenda-legend">
            Pedido usa a data da fornada combinada. Solicitação pendente não é reserva.
          </p>
          {error ? (
            <p className="admin-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
        <div className="admin-agenda-side">
          {selectedDay ? (
            <>
              <h3>
                {selectedDay.date.split("-").reverse().join("/")}
                {selectedDay.orders > 0 ? ` · ${selectedDay.orders} pedido(s)` : ""}
                {selectedDay.bread_units > 0 ? ` · ${selectedDay.bread_units} pães` : ""}
              </h3>
              <EntryList title="Em aberto" entries={selectedDay.open} onOpen={onOpen} />
              <EntryList title="Solicitações pendentes" entries={selectedDay.pending} onOpen={onOpen} />
              <EntryList title="Concluídos" entries={selectedDay.historical} onOpen={onOpen} />
              {selectedDay.cancelled.length > 0 ? (
                <button type="button" className="admin-link" onClick={() => setShowCancelled((value) => !value)}>
                  {showCancelled ? "Ocultar cancelados" : "Ver cancelados deste dia"}
                </button>
              ) : null}
              {showCancelled ? (
                <EntryList title="Cancelados" entries={selectedDay.cancelled} onOpen={onOpen} />
              ) : null}
              {selectedDay.open.length + selectedDay.pending.length + selectedDay.historical.length === 0 ? (
                <p className="admin-muted">Nenhum compromisso aberto neste dia.</p>
              ) : null}
            </>
          ) : (
            <p className="admin-muted">Selecione um dia.</p>
          )}
          <EntryList title="Sem data definida" entries={data?.undated ?? []} onOpen={onOpen} />
        </div>
      </div>
    </section>
  );
}
