import { useEffect, useRef, useState } from "react";
import { companyQuery, request, type ApiError } from "./api";
import { formatMinor } from "./money";
import { canWrite, getSession, subscribeSession } from "./session";

type Side = {
  receivableCount: number;
  receivableMinor: string;
  payableCount: number;
  payableMinor: string;
};

type CalDay = Side & {
  date: string;
  inMonth: boolean;
  today: boolean;
  overdue: boolean;
  collected: boolean;
};

type CalItem = {
  id: string;
  direction: string;
  description: string;
  dueDate: string | null;
  counterparty: string | null;
  residualMinor: string;
  partial: boolean;
  partialLabel: string | null;
  overdue: boolean;
  account: string;
};

type CalendarBody = {
  businessDate: string;
  zone: string;
  month: string;
  monthLabel: string;
  monthFrom: string;
  monthTo: string;
  coverage: string;
  monthTotalScope: string;
  direction: string;
  selectedDay: string | null;
  focus: string;
  notice: string | null;
  days: CalDay[];
  monthTotals: Side & { differenceMinor: string };
  differenceMeaning: string;
  undated: Side;
  undatedNote: string;
  overdueOutside: Side;
  items: { total: number; items: CalItem[] };
  page: number;
  size: number;
  accountNote: string;
};

type Load = "loading" | "ready" | "error" | "denied";

type Query = { mes: string; dia: string; direcao: string; pagina: number; foco: string };

const WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"];
const WEEK_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

function saoPauloToday() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function readCalendar(): Query {
  const params = new URLSearchParams(window.location.search);
  const today = saoPauloToday();
  const requestedMonth = params.get("mes") ?? "";
  const mes = /^\d{4}-\d{2}$/.test(requestedMonth) ? requestedMonth : today.slice(0, 7);
  const requestedDay = params.get("dia") ?? "";
  const dia = /^\d{4}-\d{2}-\d{2}$/.test(requestedDay) ? requestedDay : (today.startsWith(mes) ? today : `${mes}-01`);
  const requestedDirection = params.get("direcao") ?? "";
  const direcao = requestedDirection === "RECEIVABLE" || requestedDirection === "PAYABLE" ? requestedDirection : "";
  const pagina = Math.max(0, Math.floor(Number(params.get("pagina") || "0")) || 0);
  const requestedFocus = params.get("foco") ?? "DAY";
  const foco = requestedFocus === "UNDATED" || requestedFocus === "OVERDUE_OUTSIDE" ? requestedFocus : "DAY";
  return { mes, dia, direcao, pagina, foco };
}

function calendarUrl(query: Query) {
  const params = new URLSearchParams();
  params.set("vista", "calendario");
  params.set("mes", query.mes);
  if (query.dia) params.set("dia", query.dia);
  if (query.direcao) params.set("direcao", query.direcao);
  if (query.pagina > 0) params.set("pagina", String(query.pagina));
  if (query.foco !== "DAY") params.set("foco", query.foco);
  return `/financial-accounts/agenda?${params.toString()}`;
}

function monthGrid(month: string) {
  const [year, monthNumber] = month.split("-").map(Number);
  const start = new Date(Date.UTC(year, monthNumber - 1, 1));
  const end = new Date(Date.UTC(year, monthNumber, 0));
  const lead = (start.getUTCDay() + 6) % 7;
  const tail = end.getUTCDay() === 0 ? 0 : 7 - end.getUTCDay();
  const cursor = new Date(start);
  cursor.setUTCDate(cursor.getUTCDate() - lead);
  const last = new Date(end);
  last.setUTCDate(last.getUTCDate() + tail);
  const dates: string[] = [];
  for (let day = new Date(cursor); day <= last; day.setUTCDate(day.getUTCDate() + 1)) {
    dates.push(day.toISOString().slice(0, 10));
  }
  return dates;
}

function addDays(iso: string, amount: number) {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

function shiftMonth(month: string, amount: number) {
  const [year, monthNumber] = month.split("-").map(Number);
  const date = new Date(Date.UTC(year, monthNumber - 1 + amount, 1));
  return date.toISOString().slice(0, 7);
}

function longDate(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  const utc = new Date(Date.UTC(year, month - 1, day));
  const weekday = WEEKDAYS[(utc.getUTCDay() + 6) % 7];
  return `${weekday.charAt(0).toUpperCase()}${weekday.slice(1)}, ${day} de ${MONTHS[month - 1]} de ${year}`;
}

function monthTitle(month: string) {
  const [year, monthNumber] = month.split("-").map(Number);
  const name = MONTHS[monthNumber - 1];
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} de ${year}`;
}

function brDate(value: string | null | undefined) {
  if (!value) return "Sem data";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function companyName() {
  const session = getSession();
  return session?.companies.find((company) => company.id === session.companyId)?.name ?? "Empresa";
}

function sideCount(side: Side, direction: string) {
  return direction === "PAYABLE" ? side.payableCount : side.receivableCount;
}

function monthEnd(month: string) {
  const [year, monthNumber] = month.split("-").map(Number);
  const last = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  return `${month}-${String(last).padStart(2, "0")}`;
}

function shownSide(ready: boolean, data: CalendarBody | null, side: "RECEIVABLE" | "PAYABLE") {
  if (!ready || !data) return "—";
  if (data.direction !== "ALL" && data.direction !== side) return "Fora deste filtro";
  const count = side === "PAYABLE" ? data.monthTotals.payableCount : data.monthTotals.receivableCount;
  const minor = side === "PAYABLE" ? data.monthTotals.payableMinor : data.monthTotals.receivableMinor;
  return `${formatMinor(minor)} · ${count}`;
}

function IconIn() {
  return (
    <svg className="cal-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M8 2.2v9.2M4.4 8.2 8 11.8l3.6-3.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconOut() {
  return (
    <svg className="cal-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M8 13.8V4.6M4.4 7.8 8 4.2l3.6 3.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconClock() {
  return (
    <svg className="cal-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle cx="8" cy="8" r="5.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8 5.1V8.2l2.1 1.3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function dayLabel(iso: string, day: CalDay | undefined, ready: boolean) {
  const parts = [longDate(iso)];
  if (!ready || !day?.collected) return `${parts[0]}, carregando`;
  if (day.today) parts.push("hoje");
  if (day.receivableCount > 0) parts.push(`A receber, ${day.receivableCount}, ${formatMinor(day.receivableMinor)}`);
  if (day.payableCount > 0) parts.push(`A pagar, ${day.payableCount}, ${formatMinor(day.payableMinor)}`);
  if (day.receivableCount === 0 && day.payableCount === 0) parts.push("nenhum vencimento");
  if (day.overdue && (day.receivableCount > 0 || day.payableCount > 0)) parts.push("vencido");
  return parts.join(", ");
}

export function CalendarAgenda({ onNavigate }: { onNavigate: (path: string) => void }) {
  const initial = readCalendar();
  const [query, setQuery] = useState<Query>(initial);
  const [data, setData] = useState<CalendarBody | null>(null);
  const [status, setStatus] = useState<Load>("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [companyId, setCompanyId] = useState(getSession()?.companyId ?? "");
  const requestId = useRef(0);
  const keyboardMove = useRef(false);

  useEffect(() => subscribeSession(() => setCompanyId(getSession()?.companyId ?? "")), []);

  useEffect(() => {
    const url = calendarUrl(readCalendar());
    if (`${window.location.pathname}${window.location.search}` !== url) {
      window.history.replaceState(null, "", url);
    }
  }, []);

  useEffect(() => {
    const onPop = () => setQuery(readCalendar());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    const id = ++requestId.current;
    setStatus("loading");
    setError("");
    const params = [
      `month=${query.mes}`,
      query.dia ? `day=${query.dia}` : "",
      query.direcao ? `direction=${query.direcao}` : "",
      `focus=${query.foco}`,
      `page=${query.pagina}`,
      "size=8",
    ].filter(Boolean).join("&");
    void request<CalendarBody>(`/api/v1/treasury/calendar?${companyQuery(params)}`)
      .then((body) => {
        if (id !== requestId.current) return;
        setData(body);
        setStatus("ready");
      })
      .catch((caught: ApiError) => {
        if (id !== requestId.current) return;
        setData(null);
        setStatus(caught.status === 403 ? "denied" : "error");
        setError(caught.status === 403 ? "Esta sessão não consulta a agenda." : "Não foi possível consultar a agenda.");
      });
  }, [query, attempt, companyId]);

  useEffect(() => {
    if (!keyboardMove.current) return;
    keyboardMove.current = false;
    document.getElementById(`cal-day-${query.dia}`)?.focus();
  }, [query.dia, query.mes]);

  const go = (next: Query) => {
    const url = calendarUrl(next);
    if (`${window.location.pathname}${window.location.search}` !== url) {
      window.history.pushState(null, "", url);
    }
    setQuery(next);
  };

  const ready = status === "ready" && data?.month === query.mes && data.focus === query.foco;
  const days = ready ? data.days : monthGrid(query.mes).map((date) => ({
    date,
    inMonth: date.startsWith(query.mes),
    today: false,
    overdue: false,
    collected: false,
    receivableCount: 0,
    receivableMinor: "",
    payableCount: 0,
    payableMinor: "",
  }));
  const byDate = new Map(days.map((day) => [day.date, day]));
  const selected = byDate.get(query.dia);
  const monthEmpty = Boolean(ready && data && data.direction === "ALL" && data.monthTotals.receivableCount === 0 && data.monthTotals.payableCount === 0);
  const filteredEmpty = Boolean(ready && data && data.direction !== "ALL" && sideCount(data.monthTotals, data.direction) === 0);
  const outsideCount = (data?.overdueOutside.receivableCount ?? 0) + (data?.overdueOutside.payableCount ?? 0);
  const undatedCount = (data?.undated.receivableCount ?? 0) + (data?.undated.payableCount ?? 0);
  const reference = data?.businessDate ?? saoPauloToday();

  const openTitle = (item: CalItem) => {
    const retorno = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    const base = item.direction === "PAYABLE" ? "/payables" : "/receivables";
    onNavigate(`${base}/${item.id}?retorno=${retorno}`);
  };

  const openForm = (direction: "receivables" | "payables") => {
    onNavigate(`/${direction}/new?vencimento=${query.dia}`);
  };

  const moveDay = (event: React.KeyboardEvent<HTMLButtonElement>, date: string) => {
    const step = ({ ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 } as Record<string, number>)[event.key];
    if (!step) return;
    event.preventDefault();
    keyboardMove.current = true;
    const next = addDays(date, step);
    go({ ...query, mes: next.slice(0, 7), dia: next, pagina: 0, foco: "DAY" });
  };

  return (
    <article className="fluxo cal-agenda">
      <h1 id="page-title" tabIndex={-1}>Agenda financeira</h1>
      <p>Veja os recebimentos e pagamentos previstos por vencimento.</p>
      <p className="pv-muted">{companyName()}. Compromissos em aberto da empresa. Período {brDate(`${query.mes}-01`)} a {brDate(monthEnd(query.mes))}. Referência {brDate(reference)}.</p>
      {ready && data ? <p className="fx-caption">Fuso aplicado internamente ({data.zone}). {data.monthTotalScope}</p> : null}
      {ready && data?.notice ? <p role="status">{data.notice}</p> : null}
      {status === "loading" ? <p className="pv-muted" role="status">Carregando a agenda…</p> : null}
      {status === "error" || status === "denied" ? (
        <p className="error" role="alert">
          {error}{" "}
          {status === "error" ? <button type="button" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button> : null}
        </p>
      ) : null}
      <div className="cal-controls">
        <div className="cal-month">
          <button type="button" className="secondary" onClick={() => {
            const mes = shiftMonth(query.mes, -1);
            const dia = reference.startsWith(mes) ? reference : `${mes}-01`;
            go({ ...query, mes, dia, pagina: 0, foco: "DAY" });
          }}>Mês anterior</button>
          <h2>{monthTitle(query.mes)}</h2>
          <button type="button" onClick={() => go({ ...query, mes: reference.slice(0, 7), dia: reference, pagina: 0, foco: "DAY" })}>Hoje</button>
          <button type="button" className="secondary" onClick={() => {
            const mes = shiftMonth(query.mes, 1);
            const dia = reference.startsWith(mes) ? reference : `${mes}-01`;
            go({ ...query, mes, dia, pagina: 0, foco: "DAY" });
          }}>Mês seguinte</button>
        </div>
        <div className="cal-switch" role="group" aria-label="Vista da agenda">
          <button type="button" aria-pressed="true">Calendário</button>
          <button type="button" className="secondary" aria-pressed="false" onClick={() => {
            window.history.pushState(null, "", "/financial-accounts/agenda?vista=lista&faixa=OVERDUE");
            window.dispatchEvent(new PopStateEvent("popstate"));
          }}>Lista</button>
        </div>
        <div className="cal-switch" role="group" aria-label="Direção">
          {([
            ["", "Todos"],
            ["RECEIVABLE", "A receber"],
            ["PAYABLE", "A pagar"],
          ] as const).map(([value, label]) => (
            <button key={label} type="button" className={query.direcao === value ? undefined : "secondary"} aria-pressed={query.direcao === value} onClick={() => go({ ...query, direcao: value, pagina: 0 })}>{label}</button>
          ))}
        </div>
      </div>
      <div className="pv-layout">
        <section className="pv-card cal-board">
          <ul className="cal-legend">
            <li className="cal-in"><IconIn /> A receber</li>
            <li className="cal-out"><IconOut /> A pagar</li>
            <li className="cal-warn"><IconClock /> Vencido</li>
            <li><span className="cal-mark is-today" aria-hidden="true" /> Hoje</li>
            <li><span className="cal-mark is-selected" aria-hidden="true" /> Dia selecionado</li>
          </ul>
          <div className="cal-grid" role="grid" aria-label={`Calendário de ${monthTitle(query.mes)}`}>
            {WEEK_SHORT.map((label, index) => (
              <div key={label} className="cal-weekday" role="columnheader">{label}<span className="cal-sr">{WEEKDAYS[index]}</span></div>
            ))}
            {days.map((day) => {
              const total = day.receivableCount + day.payableCount;
              return (
                <button
                  key={day.date}
                  id={`cal-day-${day.date}`}
                  type="button"
                  role="gridcell"
                  className={`cal-day${day.inMonth ? "" : " is-outside"}${day.date === reference ? " is-today" : ""}${day.date === query.dia && query.foco === "DAY" ? " is-selected" : ""}`}
                  aria-selected={day.date === query.dia && query.foco === "DAY"}
                  aria-label={dayLabel(day.date, day.collected ? day : undefined, Boolean(ready))}
                  onClick={() => go({ ...query, mes: day.date.slice(0, 7), dia: day.date, pagina: 0, foco: "DAY" })}
                  onKeyDown={(event) => moveDay(event, day.date)}
                >
                  <span className="cal-num">{Number(day.date.slice(8))}</span>
                  {day.collected && day.receivableCount > 0 ? (
                    <span className="cal-line cal-in"><IconIn /><span className="cal-words">A receber</span> · {day.receivableCount}<span className="cal-amount"> · {formatMinor(day.receivableMinor)}</span></span>
                  ) : null}
                  {day.collected && day.payableCount > 0 ? (
                    <span className="cal-line cal-out"><IconOut /><span className="cal-words">A pagar</span> · {day.payableCount}<span className="cal-amount"> · {formatMinor(day.payableMinor)}</span></span>
                  ) : null}
                  {day.collected && day.overdue && total > 0 ? <span className="cal-line cal-warn"><IconClock /><span className="cal-words">Vencido</span></span> : null}
                  {day.collected && total > 2 ? <span className="cal-more">Ver todos · {total}</span> : null}
                  {!day.collected ? <span className="cal-line">—</span> : null}
                </button>
              );
            })}
          </div>
          {monthEmpty ? <p>Nenhum vencimento neste mês.</p> : null}
          {filteredEmpty ? (
            <p>Nenhum vencimento neste mês para este filtro. <button type="button" className="secondary" onClick={() => go({ ...query, direcao: "", pagina: 0 })}>Limpar filtro</button></p>
          ) : null}
          {monthEmpty && canWrite() ? (
            <div className="cal-actions">
              <button type="button" onClick={() => openForm("receivables")}>Novo recebimento</button>
              <button type="button" onClick={() => openForm("payables")}>Novo pagamento</button>
            </div>
          ) : null}
          {ready && outsideCount > 0 ? (
            <button type="button" className="cal-aside-link" onClick={() => go({ ...query, foco: "OVERDUE_OUTSIDE", pagina: 0 })}>
              <IconClock /> Vencidos fora deste mês · {outsideCount}
              {data ? ` · a receber ${formatMinor(data.overdueOutside.receivableMinor)} · a pagar ${formatMinor(data.overdueOutside.payableMinor)}` : ""}
            </button>
          ) : null}
          {ready && undatedCount > 0 ? (
            <button type="button" className="cal-aside-link" onClick={() => go({ ...query, foco: "UNDATED", pagina: 0 })}>
              Sem vencimento · {undatedCount}. Estes compromissos não entram em um dia.
            </button>
          ) : null}
        </section>
        <aside className="pv-card cal-side">
          <h2>Resumo do mês</h2>
          <p className="pv-metric"><span className="cal-in"><IconIn /> A receber</span><strong>{shownSide(Boolean(ready), data, "RECEIVABLE")}</strong></p>
          <p className="pv-metric"><span className="cal-out"><IconOut /> A pagar</span><strong>{shownSide(Boolean(ready), data, "PAYABLE")}</strong></p>
          {ready && data?.direction === "ALL" ? (
            <>
              <p className="cal-diff">Diferença prevista <strong>{formatMinor(data.monthTotals.differenceMinor)}</strong></p>
              <p className="fx-caption">{data.differenceMeaning}</p>
            </>
          ) : null}
          <h2>{query.foco === "UNDATED" ? "Sem vencimento" : query.foco === "OVERDUE_OUTSIDE" ? "Vencidos fora deste mês" : longDate(query.dia)}</h2>
          {query.foco === "DAY" && ready && data && data.items.total === 0 ? <p>Nenhum vencimento neste dia.</p> : null}
          {query.foco !== "DAY" && ready && data && data.items.total === 0 ? <p>Nenhum compromisso neste recorte.</p> : null}
          {ready && data && data.items.total > 0 ? (
            <ul className="cal-items">
              {data.items.items.map((item) => (
                <li key={item.id}>
                  <button type="button" className={`cal-item ${item.direction === "PAYABLE" ? "is-out" : "is-in"}`} onClick={() => openTitle(item)}>
                    <strong>{item.counterparty || "Não informado"}</strong>
                    <span>{item.description}</span>
                    <span>{item.direction === "PAYABLE" ? "A pagar" : "A receber"} · restante {formatMinor(item.residualMinor)}</span>
                    <span>Vencimento {brDate(item.dueDate)}{item.partialLabel ? ` · ${item.partialLabel}` : ""}{item.overdue ? " · Vencido" : ""}</span>
                    <span>{item.account}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {ready && data && data.items.total > data.size ? (
            <div className="pager">
              <button type="button" className="secondary" disabled={query.pagina === 0} onClick={() => go({ ...query, pagina: query.pagina - 1 })}>Anterior</button>
              <span>{data.items.total} compromissos</span>
              <button type="button" className="secondary" disabled={(query.pagina + 1) * data.size >= data.items.total} onClick={() => go({ ...query, pagina: query.pagina + 1 })}>Próximo</button>
            </div>
          ) : null}
          {ready && data ? <p className="fx-caption">{data.accountNote}</p> : null}
          {query.foco === "DAY" && canWrite() && !filteredEmpty ? (
            <div className="cal-actions">
              <button type="button" className="secondary" onClick={() => openForm("receivables")}>Novo recebimento</button>
              <button type="button" className="secondary" onClick={() => openForm("payables")}>Novo pagamento</button>
            </div>
          ) : null}
        </aside>
      </div>
    </article>
  );
}
