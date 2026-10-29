import { useEffect, useMemo, useState } from "react";
import { AdminApiError, adminRequest } from "./api";

type Commitment = { id: string; reference?: string; date: string | null; status: string; href: string };
type Closure = {
  id: string;
  start_date: string;
  end_date: string;
  first_eligible_date: string;
  blocked_until: string;
  pause_intake: boolean;
  internal_reason: string;
  public_notice: string;
  status: string;
  created_by: string;
  updated_by: string;
  created_at: string | null;
  updated_at: string | null;
  cancelled_at: string | null;
  cancelled_by: string | null;
  commitments: { orders: Commitment[]; date_requests: Commitment[]; order_count: number; date_request_count: number };
};
type EventRow = { id: string; action: string; actor_ref: string; created_at: string | null; detail: unknown };
type Notice = { tone: "saving" | "success" | "error"; text: string } | null;

function message(reason: unknown, fallback: string): string {
  return reason instanceof AdminApiError ? reason.message : fallback;
}

function statusLabel(status: string): string {
  if (status === "scheduled") return "Programado";
  if (status === "in_force") return "Em vigor";
  if (status === "concluded") return "Concluído";
  if (status === "cancelled") return "Reaberto";
  return status;
}

function formatDay(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long", year: "numeric" }).format(
    new Date(year, month - 1, day),
  );
}

function nextDay(value: string): string {
  if (!value) return "";
  const date = new Date(`${value}T12:00:00`);
  date.setDate(date.getDate() + 1);
  return date.toISOString().slice(0, 10);
}

export function ClosurePanel() {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [firstEligible, setFirstEligible] = useState("");
  const [reason, setReason] = useState("Viagem");
  const [pauseIntake, setPauseIntake] = useState(false);
  const [items, setItems] = useState<Closure[]>([]);
  const [history, setHistory] = useState<Closure[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [eventsFor, setEventsFor] = useState<string | null>(null);
  const [commitments, setCommitments] = useState<Closure["commitments"] | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [confirmCancel, setConfirmCancel] = useState<string | null>(null);

  const summary = useMemo(() => {
    if (!start || !end || !firstEligible) return null;
    if (end < start) return "A data final não pode ser anterior à inicial.";
    if (firstEligible <= start) return "A primeira fornada elegível precisa ser depois do início.";
    const blockedUntil = nextDay(firstEligible);
    const until = firstEligible ? formatDay(new Date(new Date(`${firstEligible}T12:00:00`).getTime() - 86400000).toISOString().slice(0, 10)) : "";
    return {
      text: pauseIntake
        ? `Viagem de ${formatDay(start)} a ${formatDay(end)}. Datas bloqueadas até ${until}. Recebimento de novos pedidos também pausado nesse intervalo.`
        : `Viagem de ${formatDay(start)} a ${formatDay(end)}. Novas encomendas só para fornadas a partir de ${formatDay(firstEligible)}. ${until ? `Datas de ${formatDay(start)} a ${until} ficam indisponíveis.` : ""}`,
      blockedUntil: blockedUntil,
    };
  }, [start, end, firstEligible, pauseIntake]);

  async function reload() {
    const data = await adminRequest<{ items: Closure[]; history: Closure[] }>("/api/v1/admin/schedule/closures");
    setItems(data.items);
    setHistory(data.history);
  }

  useEffect(() => {
    void reload().catch((reason) => {
      setNotice({ tone: "error", text: message(reason, "Não foi possível carregar os fechamentos.") });
    });
  }, []);

  useEffect(() => {
    if (end && !firstEligible) {
      setFirstEligible(nextDay(end));
    }
  }, [end, firstEligible]);

  async function loadCommitments() {
    if (!start || !firstEligible) return;
    const data = await adminRequest<Closure["commitments"]>(
      `/api/v1/admin/schedule/closures/commitments?start=${start}&first_eligible_date=${firstEligible}`,
    );
    setCommitments(data);
  }

  async function program() {
    if (!summary || typeof summary === "string") {
      setNotice({ tone: "error", text: typeof summary === "string" ? summary : "Informe o intervalo." });
      return;
    }
    setNotice({ tone: "saving", text: "Programando…" });
    try {
      await loadCommitments();
      await adminRequest("/api/v1/admin/schedule/closures", {
        method: "POST",
        body: JSON.stringify({
          start_date: start,
          end_date: end,
          first_eligible_date: firstEligible,
          pause_intake: pauseIntake,
          internal_reason: reason,
        }),
      });
      await reload();
      setNotice({ tone: "success", text: "Fechamento programado. O calendário passa a usar estas datas." });
    } catch (error) {
      setNotice({ tone: "error", text: message(error, "Não foi possível programar o fechamento.") });
    }
  }

  async function reopen(id: string) {
    setNotice({ tone: "saving", text: "Reabrindo…" });
    try {
      await adminRequest(`/api/v1/admin/schedule/closures/${id}/cancel`, { method: "POST" });
      setConfirmCancel(null);
      await reload();
      setNotice({
        tone: "success",
        text: "Este bloqueio foi removido. A rotina e as outras exceções voltam a valer. O histórico permanece.",
      });
    } catch (error) {
      setNotice({ tone: "error", text: message(error, "Não foi possível reabrir o período.") });
    }
  }

  async function openEvents(id: string) {
    if (eventsFor === id) {
      setEventsFor(null);
      setEvents([]);
      return;
    }
    const data = await adminRequest<{ items: EventRow[] }>(`/api/v1/admin/schedule/closures/${id}/events`);
    setEventsFor(id);
    setEvents(data.items);
  }

  return (
    <article className="agenda-card agenda-card-closure">
      <div>
        <h2>Fechar um período</h2>
        <p className="agenda-help">
          Bloqueia novas encomendas para as datas do intervalo. Não cancela pedidos já feitos, não altera a rotina
          semanal e não desliga o site.
        </p>
        {notice ? (
          <p className={notice.tone === "error" ? "admin-error" : notice.tone === "success" ? "admin-success" : "admin-muted"}>
            {notice.text}
          </p>
        ) : null}
      </div>
      <div className="agenda-fields">
        <label className="agenda-field">
          Data inicial
          <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label className="agenda-field">
          Data final
          <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
        <label className="agenda-field">
          Primeira fornada elegível
          <input type="date" value={firstEligible} onChange={(event) => setFirstEligible(event.target.value)} />
        </label>
        <label className="agenda-field">
          Motivo interno
          <input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={120} />
        </label>
      </div>
      <label className="agenda-choice">
        <input type="checkbox" checked={pauseIntake} onChange={(event) => setPauseIntake(event.target.checked)} />
        Pausar também o recebimento de novos pedidos durante este período
      </label>
      <p className="agenda-help">
        Desmarcado, o cliente continua podendo pedir agora para fornadas a partir da primeira data elegível. Marcado,
        nenhuma encomenda nova entra enquanto o período estiver em vigor.
      </p>
      {typeof summary === "string" ? <p className="admin-error">{summary}</p> : null}
      {summary && typeof summary !== "string" ? <p className="agenda-summary">{summary.text}</p> : null}
      {commitments && (commitments.order_count > 0 || commitments.date_request_count > 0) ? (
        <p className="agenda-help">
          Já existem {commitments.order_count} pedido(s) e {commitments.date_request_count} solicitação(ões) nestas
          datas. Eles continuam exigindo atendimento.{" "}
          <a href="/admin/pedidos">Abrir Pedidos</a>
        </p>
      ) : null}
      <div className="agenda-actions">
        <button type="button" className="admin-secondary" onClick={() => void loadCommitments()} disabled={!start || !firstEligible}>
          Ver compromissos
        </button>
        <button type="button" className="admin-primary" disabled={notice?.tone === "saving"} onClick={() => void program()}>
          Programar fechamento
        </button>
      </div>
      {items.length > 0 ? (
        <ul className="agenda-preview">
          {items.map((item) => (
            <li key={item.id}>
              {formatDay(item.start_date)} a {formatDay(item.end_date)} · {statusLabel(item.status)} · bloqueio até{" "}
              {formatDay(item.blocked_until)} · {item.pause_intake ? "recebimento pausado" : "recebimento aberto"} ·{" "}
              {item.internal_reason}
              {item.commitments.order_count + item.commitments.date_request_count > 0
                ? ` · ${item.commitments.order_count + item.commitments.date_request_count} compromisso(s)`
                : ""}
              <span className="agenda-closure-row">
                <button type="button" className="admin-text" onClick={() => void openEvents(item.id)}>
                  {eventsFor === item.id ? "Ocultar alterações" : "Ver alterações"}
                </button>
                {item.status !== "cancelled" ? (
                  <button type="button" className="admin-text" onClick={() => setConfirmCancel(item.id)}>
                    Reabrir este bloqueio
                  </button>
                ) : null}
              </span>
              {confirmCancel === item.id ? (
                <p className="agenda-help">
                  Reabrir remove só este bloqueio. Não abre todos os dias nem apaga a rotina, outras exceções ou o
                  histórico.{" "}
                  <button type="button" className="admin-primary" onClick={() => void reopen(item.id)}>
                    Confirmar reabertura
                  </button>
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="agenda-help">Nenhum período programado.</p>
      )}
      {eventsFor && events.length > 0 ? (
        <ul className="agenda-preview">
          {events.map((item) => (
            <li key={item.id}>
              {item.created_at ? formatDay(item.created_at.slice(0, 10)) : ""} · {item.action} · {item.actor_ref}
            </li>
          ))}
        </ul>
      ) : null}
      <button type="button" className="admin-text" onClick={() => setShowHistory((current) => !current)}>
        {showHistory ? "Ocultar histórico" : "Ver histórico"}
      </button>
      {showHistory ? (
        history.length === 0 ? (
          <p className="agenda-help">Nenhum fechamento reaberto ainda.</p>
        ) : (
          <ul className="agenda-preview">
            {history.map((item) => (
              <li key={item.id}>
                {formatDay(item.start_date)} a {formatDay(item.end_date)} · {statusLabel(item.status)} ·{" "}
                {item.internal_reason} · {item.cancelled_by}
              </li>
            ))}
          </ul>
        )
      ) : null}
    </article>
  );
}
