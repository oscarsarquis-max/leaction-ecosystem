import { useEffect, useRef, useState } from "react";
import { companyQuery, request, type ApiError } from "./api";
import { formatMinor } from "./money";
import { getSession, subscribeSession } from "./session";

type Bucket = { id: string; label: string; count: number; residualMinor: string };
type AgendaItem = {
  id: string;
  direction: string;
  description: string;
  dueDate: string | null;
  counterparty: string | null;
  residualMinor: string;
  account: string;
};
type Agenda = {
  businessDate: string;
  zone: string;
  bucket: string;
  direction: string;
  notice: string | null;
  accountNote: string;
  buckets: Bucket[];
  items: { total: number; items: AgendaItem[] };
  page: number;
  size: number;
};
type ReviewBatch = { batchId: string; fileName: string; occurrenceCount: number };
type Exclusion = { reason: string; label: string; count: number; accounts: { name: string; detail: string; knownMinor?: string }[] };
type Summary = {
  businessDate: string;
  zone: string;
  periodFrom: string;
  periodTo: string;
  note: string;
  scopes?: { obligations: string; realized: string; conference: string; position: string };
  obligations: {
    available: boolean;
    receivableOpenMinor?: string;
    receivableOpenCount?: number;
    receivableOverdueMinor?: string;
    receivableOverdueCount?: number;
    payableOpenMinor?: string;
    payableOpenCount?: number;
    payableOverdueMinor?: string;
    payableOverdueCount?: number;
    draftCount?: number;
    draftNote?: string;
  };
  realized: {
    available: boolean;
    receivedMinor?: string;
    receivedCount?: number;
    paidMinor?: string;
    paidCount?: number;
    meaning?: string;
  };
  conference: {
    available: boolean;
    eligibleCount?: number;
    partialCount?: number;
    divergentCount?: number;
    reviewCount?: number;
    reviewUnit?: string;
    reviewNote?: string;
    reviewBatches?: ReviewBatch[];
    meaning?: string;
  };
  position: {
    available: boolean;
    known?: boolean;
    label?: string;
    knownMinor?: string;
    coveredAccounts?: number;
    accountCount?: number;
    exclusions?: Exclusion[];
    source?: string;
    limit?: string;
    guidance?: string | null;
    asOf?: string;
  };
};

type Load = "loading" | "ready" | "error" | "denied";

const BUCKETS = ["OVERDUE", "TODAY", "NEXT_7", "NEXT_30", "UNDATED"];

function brDate(value: string | null | undefined) {
  if (!value) return "Sem data";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function money(available: boolean, value: string | undefined) {
  if (!available || value == null || value === "") return "—";
  return formatMinor(value);
}

function count(available: boolean, value: number | undefined) {
  if (!available || value == null) return "—";
  return String(value);
}

function readAgenda() {
  const params = new URLSearchParams(window.location.search);
  const faixa = params.get("faixa") || "OVERDUE";
  const direcao = params.get("direcao") || "";
  const pagina = Number(params.get("pagina") || "0");
  const vista = params.get("vista") === "dia" ? "dia" : "lista";
  return {
    bucket: BUCKETS.includes(faixa) ? faixa : "OVERDUE",
    direction: direcao === "RECEIVABLE" || direcao === "PAYABLE" ? direcao : "",
    page: Number.isFinite(pagina) && pagina > 0 ? Math.floor(pagina) : 0,
    vista,
  };
}

function agendaUrl(bucket: string, direction: string, page: number, vista: string) {
  const params = new URLSearchParams();
  params.set("faixa", bucket);
  if (direction) params.set("direcao", direction);
  if (page > 0) params.set("pagina", String(page));
  if (vista === "dia") params.set("vista", "dia");
  return `/financial-accounts/agenda?${params.toString()}`;
}

export function TreasurySummaryPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [data, setData] = useState<Summary | null>(null);
  const [agenda, setAgenda] = useState<Agenda | null>(null);
  const [status, setStatus] = useState<Load>("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [companyId, setCompanyId] = useState(getSession()?.companyId ?? "");
  const requestId = useRef(0);

  useEffect(() => subscribeSession(() => setCompanyId(getSession()?.companyId ?? "")), []);

  useEffect(() => {
    const id = ++requestId.current;
    setStatus("loading");
    setError("");
    setData(null);
    setAgenda(null);
    void request<Summary>(`/api/v1/treasury/summary?${companyQuery()}`)
      .then((body) => {
        if (id !== requestId.current) return;
        setData(body);
        setStatus("ready");
      })
      .catch((caught: ApiError) => {
        if (id !== requestId.current) return;
        setData(null);
        setStatus(caught.status === 403 ? "denied" : "error");
        setError(caught.status === 403 ? "Esta sessão não consulta o resumo da tesouraria." : "Não foi possível consultar o resumo da tesouraria.");
      });
    void request<Agenda>(`/api/v1/treasury/agenda?${companyQuery("bucket=OVERDUE&size=5")}`)
      .then((body) => {
        if (id !== requestId.current || !body?.buckets) return;
        setAgenda(body);
      })
      .catch(() => {
        if (id === requestId.current) setAgenda(null);
      });
  }, [attempt, companyId]);

  const obligations = data?.obligations;
  const realized = data?.realized;
  const conference = data?.conference;
  const position = data?.position;
  const obligationsReady = status === "ready" && obligations?.available === true;
  const realizedReady = status === "ready" && realized?.available === true;
  const conferenceReady = status === "ready" && conference?.available === true;
  const positionReady = status === "ready" && position?.available === true;

  return (
    <article className="fluxo">
      <h1 id="page-title" tabIndex={-1}>Resumo da tesouraria</h1>
      {status === "loading" ? <p className="pv-muted" role="status">Carregando o resumo…</p> : null}
      {status === "ready" && data ? (
        <p className="pv-muted">
          Posição em {brDate(data.businessDate)}, fuso {data.zone}. Recebido e pago de {brDate(data.periodFrom)} a {brDate(data.periodTo)}. Cada cartão usa a própria data.
        </p>
      ) : null}
      {status === "error" || status === "denied" ? (
        <p className="error" role="alert">
          {error}{" "}
          {status === "error" ? <button type="button" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button> : null}
        </p>
      ) : null}
      {data ? <p className="fx-caption">{data.note}</p> : null}
      <div className="pv-layout">
        <section className="pv-card">
          <h2>O que pede ação</h2>
          <p className="fx-caption">{data?.scopes?.obligations}</p>
          {agenda && agenda.items.items.length > 0 ? (
            <ul className="cards">
              {agenda.items.items.map((item) => (
                <li key={item.id}>
                  <button type="button" className="statement-card" onClick={() => onNavigate(`${item.direction === "PAYABLE" ? "/payables" : "/receivables"}/${item.id}?retorno=${encodeURIComponent(agendaUrl("OVERDUE", "", 0, "lista"))}`)}>
                    <strong>{item.counterparty || "Não informado"}</strong>
                    <span>{item.description}</span>
                    <span>{brDate(item.dueDate)} · restante {formatMinor(item.residualMinor)} · {item.direction === "PAYABLE" ? "A pagar" : "A receber"}</span>
                    <span>{item.account}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : status === "ready" ? <p>Nenhum vencido exigível nesta empresa.</p> : null}
          <button type="button" className="secondary" onClick={() => onNavigate("/financial-accounts/agenda?faixa=OVERDUE")}>
            Abrir vencidos · {count(obligationsReady, obligations?.receivableOverdueCount)} a receber · {count(obligationsReady, obligations?.payableOverdueCount)} a pagar
          </button>
          <h2>Conferência</h2>
          <p className="fx-caption">{data?.scopes?.conference}</p>
          {conferenceReady ? (
            <>
              <button type="button" className="secondary" onClick={() => onNavigate("/financial-accounts/reconciliation?situacao=PARCIAL")}>
                Conciliação parcial · {conference?.partialCount}
              </button>
              <button type="button" className="secondary" onClick={() => onNavigate("/financial-accounts/reconciliation?situacao=DIVERGENCIA")}>
                Diferença em aberto · {conference?.divergentCount}
              </button>
              <p>{conference?.reviewCount} ocorrências em revisão. {conference?.reviewNote}</p>
              {(conference?.reviewBatches ?? []).map((batch) => (
                <button key={batch.batchId} type="button" className="secondary" onClick={() => onNavigate(`/financial-accounts/statement/batches/${batch.batchId}?revisao=1`)}>
                  Revisar {batch.fileName} · {batch.occurrenceCount} ocorrências
                </button>
              ))}
              <p className="fx-caption">{conference?.meaning}</p>
            </>
          ) : status === "ready" ? <p>A conferência do extrato não está disponível nesta sessão.</p> : null}
        </section>
        <aside className="pv-card">
          <h2>Posição</h2>
          <p className="fx-caption">{data?.scopes?.position}</p>
          {positionReady && position?.known ? (
            <>
              <p className="pv-total-label">{position.label}</p>
              <p className="pv-figure">{formatMinor(position.knownMinor)}</p>
              <p>{position.coveredAccounts} contas ativas entram nessa soma, de {position.accountCount} contas da empresa. Data {brDate(position.asOf)}.</p>
            </>
          ) : positionReady ? (
            <p><strong>{position?.label}</strong> {position?.guidance}</p>
          ) : status === "ready" ? <p>A posição das contas não está disponível nesta sessão.</p> : null}
          {positionReady && position?.exclusions && position.exclusions.length > 0 ? (
            <ul>
              {position.exclusions.map((group) => (
                <li key={group.reason}>
                  <strong>{group.label}</strong>
                  <ul>
                    {group.accounts.map((account) => (
                      <li key={`${group.reason}-${account.name}`}>
                        {account.name}. {account.detail}
                        {account.knownMinor != null ? ` Posição conhecida ${formatMinor(account.knownMinor)}.` : ""}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          ) : null}
          {positionReady ? <p className="fx-caption">{position?.source} {position?.limit}</p> : null}
          <button type="button" className="secondary" onClick={() => onNavigate("/financial-accounts")}>Consultar contas</button>
          <h2>Em aberto agora</h2>
          {obligationsReady ? (
            <>
              <p className="pv-metric"><span>A receber</span><strong>{formatMinor(obligations?.receivableOpenMinor)} · {obligations?.receivableOpenCount}</strong></p>
              <p className="pv-metric"><span>A pagar</span><strong>{formatMinor(obligations?.payableOpenMinor)} · {obligations?.payableOpenCount}</strong></p>
              <p className="fx-caption">{obligations?.draftNote} {obligations?.draftCount} rascunhos, fora do valor em aberto.</p>
            </>
          ) : status === "ready" ? <p>As obrigações não estão disponíveis nesta sessão.</p> : null}
          <button type="button" className="secondary" onClick={() => onNavigate("/receivables")}>Ver a receber</button>
          <button type="button" className="secondary" onClick={() => onNavigate("/payables")}>Ver a pagar</button>
          <h2>Registrado no Finance</h2>
          <p className="fx-caption">{data?.scopes?.realized}</p>
          {realizedReady ? (
            <>
              <p className="pv-metric"><span>Recebido</span><strong>{money(true, realized?.receivedMinor)} · {realized?.receivedCount}</strong></p>
              <p className="pv-metric"><span>Pago</span><strong>{money(true, realized?.paidMinor)} · {realized?.paidCount}</strong></p>
              <p className="fx-caption">{realized?.meaning}</p>
            </>
          ) : status === "ready" ? <p>O realizado não está disponível nesta sessão.</p> : null}
        </aside>
      </div>
    </article>
  );
}

export function AgendaPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const initial = readAgenda();
  const [bucket, setBucket] = useState(initial.bucket);
  const [direction, setDirection] = useState(initial.direction);
  const [page, setPage] = useState(initial.page);
  const [vista, setVista] = useState(initial.vista);
  const [data, setData] = useState<Agenda | null>(null);
  const [status, setStatus] = useState<Load>("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [companyId, setCompanyId] = useState(getSession()?.companyId ?? "");
  const requestId = useRef(0);

  useEffect(() => subscribeSession(() => setCompanyId(getSession()?.companyId ?? "")), []);

  useEffect(() => {
    const onPop = () => {
      const next = readAgenda();
      setBucket(next.bucket);
      setDirection(next.direction);
      setPage(next.page);
      setVista(next.vista);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    const id = ++requestId.current;
    setStatus("loading");
    setError("");
    const params = [`bucket=${bucket}`, `page=${page}`, "size=20", direction ? `direction=${direction}` : ""].filter(Boolean).join("&");
    void request<Agenda>(`/api/v1/treasury/agenda?${companyQuery(params)}`)
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
  }, [bucket, direction, page, attempt, companyId]);

  const go = (nextBucket: string, nextDirection: string, nextPage: number, nextVista = vista) => {
    const url = agendaUrl(nextBucket, nextDirection, nextPage, nextVista);
    if (`${window.location.pathname}${window.location.search}` !== url) {
      window.history.pushState(null, "", url);
    }
    setBucket(nextBucket);
    setDirection(nextDirection);
    setPage(nextPage);
    setVista(nextVista);
  };

  const openTitle = (item: AgendaItem) => {
    const retorno = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    const base = item.direction === "PAYABLE" ? "/payables" : "/receivables";
    onNavigate(`${base}/${item.id}?retorno=${retorno}`);
  };

  const groups = new Map<string, AgendaItem[]>();
  for (const item of data?.items.items ?? []) {
    const key = item.dueDate ?? "Sem data";
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }

  return (
    <article className="fluxo">
      <h1 id="page-title" tabIndex={-1}>Agenda</h1>
      {status === "loading" && !data ? <p className="pv-muted" role="status">Carregando a agenda…</p> : null}
      {status === "ready" && data ? (
        <p className="pv-muted">Dia de referência {brDate(data.businessDate)}, fuso {data.zone}. {data.accountNote}</p>
      ) : null}
      {data?.notice ? <p role="status">{data.notice}</p> : null}
      {status === "error" || status === "denied" ? (
        <p className="error" role="alert">
          {error}{" "}
          {status === "error" ? <button type="button" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button> : null}
        </p>
      ) : null}
      <div className="fx-tabs" role="tablist" aria-label="Faixa da agenda">
        {(data?.buckets ?? [
          { id: "OVERDUE", label: "Vencidos", count: -1, residualMinor: "" },
          { id: "TODAY", label: "Hoje", count: -1, residualMinor: "" },
          { id: "NEXT_7", label: "Próximos 7 dias", count: -1, residualMinor: "" },
          { id: "NEXT_30", label: "Do 8º ao 30º dia", count: -1, residualMinor: "" },
          { id: "UNDATED", label: "Sem data", count: -1, residualMinor: "" },
        ]).map((item) => (
          <button key={item.id} type="button" role="tab" className="fx-tab" aria-selected={bucket === item.id} onClick={() => go(item.id, direction, 0)}>
            {item.label}{item.count >= 0 ? ` · ${item.count} · ${formatMinor(item.residualMinor)}` : ""}
          </button>
        ))}
      </div>
      <div className="pv-context">
        <label>
          Recebimentos e pagamentos
          <select value={direction} onChange={(event) => go(bucket, event.target.value, 0)}>
            <option value="">Todos</option>
            <option value="RECEIVABLE">A receber</option>
            <option value="PAYABLE">A pagar</option>
          </select>
        </label>
        <button type="button" className="secondary" aria-pressed={vista === "lista"} onClick={() => go(bucket, direction, page, "lista")}>Lista</button>
        <button type="button" className="secondary" aria-pressed={vista === "dia"} onClick={() => go(bucket, direction, page, "dia")}>Por dia</button>
      </div>
      {status === "ready" && data && data.items.total === 0 ? (
        <p>Nenhum compromisso exigível nesta faixa. Rascunhos e cancelados não entram aqui.</p>
      ) : null}
      {status === "ready" && data && data.items.total > 0 && vista === "lista" ? (
        <ul className="cards">
          {data.items.items.map((item) => (
            <li key={item.id}>
              <button type="button" className="statement-card" onClick={() => openTitle(item)}>
                <strong>{item.counterparty || "Não informado"}</strong>
                <span>{item.description}</span>
                <span>{brDate(item.dueDate)} · restante {formatMinor(item.residualMinor)} · {item.direction === "PAYABLE" ? "A pagar" : "A receber"}</span>
                <span>{item.account}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {status === "ready" && data && data.items.total > 0 && vista === "dia" ? (
        <>
          <p className="fx-caption">Os dias abaixo são desta página. Os totais da faixa valem para o conjunto inteiro.</p>
          {[...groups.entries()].map(([day, items]) => (
            <section key={day}>
              <h2>{day === "Sem data" ? day : brDate(day)}</h2>
              <ul className="cards">
                {items.map((item) => (
                  <li key={item.id}>
                    <button type="button" className="statement-card" onClick={() => openTitle(item)}>
                      <strong>{item.counterparty || "Não informado"}</strong>
                      <span>{item.description}</span>
                      <span>restante {formatMinor(item.residualMinor)} · {item.account}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      ) : null}
      {status === "ready" && data && data.items.total > data.size ? (
        <div className="pager">
          <button type="button" className="secondary" disabled={page === 0} onClick={() => go(bucket, direction, page - 1)}>Anterior</button>
          <span>{data.items.total} compromissos nesta faixa</span>
          <button type="button" className="secondary" disabled={(page + 1) * data.size >= data.items.total} onClick={() => go(bucket, direction, page + 1)}>Próximo</button>
        </div>
      ) : null}
    </article>
  );
}
