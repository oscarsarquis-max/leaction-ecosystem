import { useCallback, useEffect, useRef, useState } from "react";
import { companyQuery, request, type ApiError } from "./api";
import { formatDateBr, formatMinor } from "./money";
import { canWriteAccounts, getSession, subscribeSession } from "./session";
import { PageHeader } from "./ui/PageHeader";

type Account = { id: string; name: string; active?: boolean };
type DayBucket = { date: string; creditMinor: string; debitMinor: string };
type Suggestion = { receiptId: string; strength: string; namespace: string; reason: string; divergence: string };
type Line = {
  id: string;
  accountId: string;
  sourceId: string;
  recordType: string;
  externalReference: string | null;
  description: string | null;
  effectiveOn: string | null;
  direction: string;
  eventKind: string;
  balanceEffect: string;
  grossMinor: number | null;
  grossAbsent: boolean;
  feeMinor: number | null;
  feeAbsent: boolean;
  netMinor: number | null;
  netAbsent: boolean;
  classificationState: string;
  initiativeState: string;
  importStatus: string;
  suggestions: Suggestion[];
  originalRows?: string[];
};
type LinePage = {
  page: number;
  size: number;
  total: number;
  creditMinor: string;
  creditCount: number;
  debitMinor: string;
  debitCount: number;
  availabilityCount: number;
  amountAbsentCount: number;
  excludedFromPartialCount?: number;
  reviewCount?: number;
  undatedCreditMinor?: string;
  undatedDebitMinor?: string;
  totalBasisText?: string;
  items: Line[];
  imported: number;
  days?: DayBucket[];
  agenda?: "NONE" | "UNAVAILABLE";
  reviews?: ReviewRow[];
};
type ReviewRow = {
  lineNumber: number;
  exclusionCode: string | null;
  description: string | null;
  effectiveOn: string | null;
  direction: string;
  netMinor: number | null;
  netAbsent: boolean;
  grossMinor: number | null;
  grossAbsent: boolean;
  feeMinor: number | null;
  feeAbsent: boolean;
  sourceId: string;
  batchId: string;
  eventKind: string;
};
type Issue = { lineNumber: number; code: string; message: string };
type PreviewRow = {
  lineNumber: number;
  description: string | null;
  effectiveOn: string | null;
  direction: string;
  eventKind: string;
  netMinor: number | null;
  netAbsent: boolean;
  eligible: boolean;
  availability?: string;
  balanceEffect?: string | null;
  externalReference?: string | null;
  grossMinor?: number | null;
  grossAbsent?: boolean;
  feeMinor?: number | null;
  feeAbsent?: boolean;
};
type Preview = {
  id: string;
  previewToken: string;
  profileId: string;
  recognized: boolean;
  fileDiagnostic: string | null;
  blockReason: string | null;
  confirmBlocked: boolean;
  accountEvidenceRequired: boolean;
  currencyAssumed: boolean;
  periodFrom: string | null;
  periodTo: string | null;
  rows: PreviewRow[];
  issues: Issue[];
  identityConfirmationRequired?: boolean;
  identityMismatch?: boolean;
  fileAccountRef?: string | null;
};
type Batch = {
  id: string;
  fileName: string;
  status: string;
  profileId?: string;
  periodFrom: string | null;
  periodTo: string | null;
  createdCount: number;
  enrichedCount: number;
  unchangedCount: number;
  rejectedCount: number;
  withdrawReason: string | null;
};
type ConfirmResult = {
  batchId: string;
  created: number;
  enriched: number;
  unchanged: number;
  notImported: number;
  preserved: number;
  inReview: number;
  partialTotalText?: string;
  accountAttestation?: string;
};
type Occurrence = {
  lineNumber: number;
  availability: string;
  consolidation: string;
  exclusionCode: string | null;
  inPartialTotal: boolean;
  lineId: string | null;
  sourceId: string;
  description: string | null;
  effectiveOn: string | null;
  direction: string;
  eventKind: string;
  grossMinor: number | null;
  grossAbsent: boolean;
  feeMinor: number | null;
  feeAbsent: boolean;
  netMinor: number | null;
  netAbsent: boolean;
  eventIdentified: boolean;
};
type BatchDetail = {
  id: string;
  fileName: string;
  status: string;
  profileId: string;
  periodFrom: string | null;
  periodTo: string | null;
  preservedCount: number;
  consolidatedCount: number;
  partialCount: number;
  inReviewCount: number;
  partialTotalText: string;
  documentIdentityText: string;
  occurrences: Occurrence[];
};

const EVENT_LABEL: Record<string, string> = {
  SETTLEMENT: "Pagamento aprovado",
  FEE: "Tarifa",
  REFUND: "Estorno",
  RELEASE: "Liberação",
  CHARGEBACK: "Contestação",
  WITHDRAWAL: "Saque",
  TRANSFER: "Transferência",
  PAYOUT: "Pagamento enviado",
  HOLD: "Bloqueio",
  UNBLOCK: "Desbloqueio",
  INFO: "Informação",
};

function statementHome(): string {
  const params = new URLSearchParams(window.location.search);
  const back = new URLSearchParams();
  for (const key of ["conta", "de", "ate", "q", "vista", "pagina"]) {
    const value = params.get(key);
    if (value) {
      back.set(key, value);
    }
  }
  const text = back.toString();
  return text ? `/financial-accounts/statement?${text}` : "/financial-accounts/statement";
}

function navigate(to: string) {
  window.history.pushState(null, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function signedMoney(value: number | string | null, direction: string, absent = false, currencyKnown = true): string {
  if (absent || value == null || value === "") {
    return formatMinor(null);
  }
  const raw = String(value).replace(/^-/, "");
  const formatted = currencyKnown ? formatMinor(raw) : `${formatMinor(raw).replace(/^R\$\s?/, "")} · moeda não informada`;
  if (raw !== "0" && direction === "OUT") {
    return `↓ − ${formatted}`;
  }
  if (raw !== "0" && direction === "IN") {
    return `↑ + ${formatted}`;
  }
  return formatted;
}

function money(value: number | null, absent: boolean, currencyKnown = true): string {
  if (absent || value == null) {
    return formatMinor(null);
  }
  const formatted = formatMinor(String(value));
  if (currencyKnown) {
    return formatted;
  }
  return `${formatted.replace(/^R\$\s?/, "")} · moeda não informada`;
}

function dateLabel(profileId: string): string {
  if (profileId === "mp-settlement-v2-csv-1") return "Data de aprovação";
  if (profileId === "mp-account-money-csv-1") return "Data do arquivo";
  return "Data";
}

function codesFor(issues: Issue[], lineNumber: number): string[] {
  return issues.filter((issue) => issue.lineNumber === lineNumber).map((issue) => issue.code);
}

function shortReason(code: string | null): string {
  if (code === "IDENTITY_INSUFFICIENT") return "Identificação ambígua";
  if (code === "EFFECT_UNVERIFIED" || code === "UNRELEASED") return "Disponibilidade não confirmada";
  if (code === "DUPLICATE") return "Mesma ocorrência";
  if (code === "UNSUPPORTED_CURRENCY") return "Moeda sem regra";
  if (code === "AMOUNT_DIVERGENCE") return "Valores preservados";
  if (code === "NOT_SELECTED") return "Fora desta confirmação";
  if (code === "OUT_OF_TOTAL") return "Fora do total";
  if (code === "INVALID") return "Linha inválida";
  return "";
}

function inclusionLabel(included: boolean): string {
  return included ? "Entra no total" : "Fica de fora";
}

function reasonDetail(code: string | null): string {
  if (code === "IDENTITY_INSUFFICIENT") return "Há ocorrências relacionadas ainda não distinguidas.";
  if (code === "EFFECT_UNVERIFIED" || code === "UNRELEASED") return "A disponibilidade não foi confirmada. A linha continua no arquivo e fora do total.";
  if (code === "DUPLICATE") return "A mesma ocorrência já está no arquivo. Nenhum outro evento foi criado.";
  if (code === "NOT_SELECTED") return "Preservada no arquivo e não gravada como evento nesta confirmação.";
  if (code === "OUT_OF_TOTAL") return "Preservada e fora do total.";
  return "";
}

function directionLabel(value: string): string {
  if (value === "IN") return "Entrada";
  if (value === "OUT") return "Saída";
  return "Sem direção";
}

function eventLabel(value: string): string {
  return EVENT_LABEL[value] ?? value;
}

function fileErrorMessage(api: ApiError): string {
  if (api.status === 401 || api.code === "SESSION_EXPIRED") {
    return "Sua sessão expirou. Entre novamente para continuar.";
  }
  if (api.timeout || api.status === 0) {
    return "Não foi possível enviar o arquivo. Verifique a conexão e tente de novo.";
  }
  return api.message || "Não foi possível ler o relatório.";
}

function plainAmount(value: string): string {
  const raw = value.startsWith("-") ? value.slice(1) : value;
  if (raw === "0" || raw === "") {
    return formatMinor("0");
  }
  return formatMinor(raw);
}

function flowAmount(value: string, direction: "IN" | "OUT"): string {
  const raw = value.startsWith("-") ? value.slice(1) : value;
  if (raw === "0" || raw === "") {
    return formatMinor("0");
  }
  return signedMoney(raw, direction);
}

function differenceMinor(credit: string, debit: string): string {
  try {
    return (BigInt(credit || "0") - BigInt(debit || "0")).toString();
  } catch {
    return "0";
  }
}

function lineSituation(line: Line): string {
  if (line.importStatus === "WITHDRAWN") {
    return "Retirada";
  }
  if (line.netAbsent || line.balanceEffect !== "AFFECTS") {
    return "Precisa de revisão";
  }
  return "No total";
}

function chartPoints(days: DayBucket[]): { key: string; label: string; from: string; to: string; credit: string; debit: string }[] {
  if (days.length <= 14) {
    return days.map((day) => ({
      key: day.date,
      label: formatDateBr(day.date).slice(0, 5),
      from: day.date,
      to: day.date,
      credit: day.creditMinor,
      debit: day.debitMinor,
    }));
  }
  const weeks = new Map<string, { from: string; to: string; credit: bigint; debit: bigint }>();
  for (const day of days) {
    const date = new Date(`${day.date}T00:00:00`);
    const monday = new Date(date);
    monday.setDate(date.getDate() - ((date.getDay() + 6) % 7));
    const key = monday.toISOString().slice(0, 10);
    const current = weeks.get(key) ?? { from: day.date, to: day.date, credit: 0n, debit: 0n };
    current.from = current.from < day.date ? current.from : day.date;
    current.to = current.to > day.date ? current.to : day.date;
    current.credit += BigInt(day.creditMinor || "0");
    current.debit += BigInt(day.debitMinor || "0");
    weeks.set(key, current);
  }
  return [...weeks.entries()].map(([key, week]) => ({
    key,
    label: formatDateBr(week.from).slice(0, 5),
    from: week.from,
    to: week.to,
    credit: week.credit.toString(),
    debit: week.debit.toString(),
  }));
}

function barHeight(value: string, max: bigint): number {
  if (value === "0" || max <= 0n) {
    return 0;
  }
  const height = Number((BigInt(value) * 148n) / max);
  return Math.max(height, 4);
}

function FlowChart({
  days,
  activeFrom,
  activeTo,
  onPick,
}: {
  days: DayBucket[];
  activeFrom: string;
  activeTo: string;
  onPick: (from: string, to: string) => void;
}) {
  const points = chartPoints(days);
  if (points.length === 0) {
    return <p className="fx-note">Não há valores com data neste recorte. Nada foi colocado em uma data inventada.</p>;
  }
  const max = points.reduce((current, point) => {
    const credit = BigInt(point.credit || "0");
    const debit = BigInt(point.debit || "0");
    return credit > current ? credit : debit > current ? debit : current;
  }, 1n);
  const half = (max / 2n).toString();
  return (
    <div className="fx-chart">
      <div className="fx-chart-scale num" aria-hidden="true">
        <span>{formatMinor(max.toString())}</span>
        <span>{formatMinor(half)}</span>
        <span>{formatMinor("0")}</span>
      </div>
      <div className="fx-chart-bars" role="group" aria-label="Entradas e saídas no período, em reais">
        {points.map((point) => (
          <button
            key={point.key}
            type="button"
            className="statement-bar"
            aria-pressed={activeFrom === point.from && activeTo === point.to}
            onClick={() => onPick(point.from, point.to)}
            title={`${formatDateBr(point.from)} a ${formatDateBr(point.to)}: entradas ${formatMinor(point.credit)}, saídas ${formatMinor(point.debit)}`}
          >
            <span className="fx-bar-pair">
              <span className="statement-bar-in" style={{ height: `${barHeight(point.credit, max)}px` }} />
              <span className="statement-bar-out" style={{ height: `${barHeight(point.debit, max)}px` }} />
            </span>
            <span className="statement-bar-label">{point.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function AccountPanel({
  page,
  from,
  to,
  onPick,
  onReview,
  dateCaption,
}: {
  page: LinePage;
  from: string;
  to: string;
  onPick: (from: string, to: string) => void;
  onReview: () => void;
  dateCaption: string;
}) {
  const diff = differenceMinor(page.creditMinor, page.debitMinor);
  const ambiguous = (page.reviews ?? []).filter((row) => row.exclusionCode === "IDENTITY_INSUFFICIENT").length;
  const undatedIn = page.undatedCreditMinor ?? "0";
  const undatedOut = page.undatedDebitMinor ?? "0";
  const hasUndated = undatedIn !== "0" || undatedOut !== "0";
  const reviewTotal = page.reviewCount ?? (page.reviews ?? []).length;
  return (
    <aside className="fx-side" aria-label="Análise da conta">
      <section className="fx-card">
        <h2>Resumo do período</h2>
        <p className="fx-metric"><span>Entradas identificadas</span><strong className="money-in num">{flowAmount(page.creditMinor, "IN")}</strong></p>
        <p className="fx-metric"><span>Saídas identificadas</span><strong className="money-out num">{flowAmount(page.debitMinor, "OUT")}</strong></p>
        <p className="fx-metric"><span>Diferença no período</span><strong className={`num ${diff.startsWith("-") ? "money-out" : diff === "0" ? "" : "money-in"}`}>{diff.startsWith("-") ? flowAmount(diff, "OUT") : flowAmount(diff, "IN")}</strong></p>
        <p className="fx-note">Entradas menos saídas elegíveis. Não é saldo disponível nem posição no Mercado Pago.</p>
      </section>
      <section className="fx-card">
        <h2>Evolução</h2>
        <p className="fx-legend"><span><i style={{ background: "#1f5fa8" }} />↑ Entradas</span><span><i style={{ background: "#b4441c" }} />↓ Saídas</span><span>Reais · {dateCaption}</span></p>
        <FlowChart days={page.days ?? []} activeFrom={from} activeTo={to} onPick={onPick} />
        {hasUndated ? (
          <p className="fx-note">Fora do gráfico, sem data: entradas {plainAmount(undatedIn)} e saídas {plainAmount(undatedOut)}. Somadas ao gráfico, fecham o resumo.</p>
        ) : null}
        <div className="fx-action">
          <h2>Próxima ação</h2>
          {reviewTotal > 0 ? (
            <>
              <p>{ambiguous > 0 ? "Há operações com a mesma referência e valores diferentes." : "Há ocorrências que ainda precisam de conferência."}</p>
              <button type="button" onClick={onReview}>Ver pendências</button>
            </>
          ) : (
            <p className="fx-note">Nenhuma pendência de revisão neste recorte.</p>
          )}
        </div>
      </section>
      <section className="fx-card">
        <h2>Posição e compromissos</h2>
        <p className="fx-note">Saldo disponível, a receber, a pagar e investimentos não têm fonte, data e vínculo suficientes nesta conta. O extrato não apura essa posição.</p>
      </section>
    </aside>
  );
}

function LineSide({ id, onBack }: { id: string; onBack: () => void }) {
  const [line, setLine] = useState<Line | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void request<Line>(`/api/v1/statement-lines/${id}?${companyQuery()}`)
      .then((found) => { if (active) setLine(found); })
      .catch((caught: ApiError) => { if (active) setError(caught.message); });
    return () => { active = false; };
  }, [id]);
  return (
    <aside className="fx-side" aria-label="Detalhe da movimentação">
      <section className="fx-card">
      <button type="button" className="secondary" onClick={onBack}>Voltar à análise</button>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {!line && !error ? <p className="hint">Carregando linha…</p> : null}
      {line ? (
        <>
          <h2 className="desc">{line.description || "Sem descrição"}</h2>
          <p className={`fx-net num ${line.direction === "OUT" ? "money-out" : "money-in"}`}>{signedMoney(line.netMinor, line.direction, line.netAbsent)}</p>
          <p>{directionLabel(line.direction)} · {lineSituation(line)}</p>
          <div className="statement-split">
            <div><span>Bruto</span><strong className="num">{money(line.grossMinor, line.grossAbsent)}</strong></div>
            <div><span>Tarifa</span><strong className="num">{money(line.feeMinor, line.feeAbsent)}</strong></div>
          </div>
          <dl className="fx-pairs">
            <div><dt>Data do relatório</dt><dd>{formatDateBr(line.effectiveOn)}</dd></div>
            <div><dt>Referência</dt><dd>{line.externalReference || "Não informada"}</dd></div>
            <div><dt>Categoria</dt><dd>Não classificada</dd></div>
            <div><dt>Iniciativa</dt><dd>Não atribuída</dd></div>
          </dl>
          <p className="fx-note">A sugestão, quando existe, ainda não é conciliação.</p>
        </>
      ) : null}
      </section>
    </aside>
  );
}

function ReviewSide({ review, related, onBack }: { review: ReviewRow; related: ReviewRow[]; onBack: () => void }) {
  return (
    <aside className="fx-side" aria-label="Detalhe da ocorrência">
      <section className="fx-card">
      <button type="button" className="secondary" onClick={onBack}>Voltar à análise</button>
      <h2 className="desc">{review.description || "Sem descrição"}</h2>
      <div className="fx-amber">
        <strong>{shortReason(review.exclusionCode) || "Precisa de revisão"}</strong>
        <span>{reasonDetail(review.exclusionCode) || "Estas ocorrências permanecem separadas. Nenhuma foi escolhida como a verdadeira."}</span>
      </div>
      <ul>
        {related.map((row) => (
          <li key={`${row.batchId}-${row.lineNumber}`}>
            {formatDateBr(row.effectiveOn)} · {signedMoney(row.netMinor, row.direction, row.netAbsent)}
          </li>
        ))}
      </ul>
      <p className="fx-note">A referência pode ser conferida no arquivo de origem. Não há ação para resolver esta dúvida aqui.</p>
      </section>
    </aside>
  );
}

export function StatementPage({ path }: { path: string }) {
  const batch = /^\/financial-accounts\/statement\/batches\/([^/]+)$/.exec(path);
  if (batch) {
    return <BatchHistory id={batch[1]} />;
  }
  const detail = /^\/financial-accounts\/statement\/([^/]+)$/.exec(path);
  if (detail) {
    return <StatementDetail id={detail[1]} />;
  }
  return <StatementList />;
}

function StatementList() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsStatus, setAccountsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [accountsError, setAccountsError] = useState("");
  const [accountId, setAccountId] = useState("");
  const [batches, setBatches] = useState<Batch[]>([]);
  const [page, setPage] = useState<LinePage | null>(null);
  const [pageIndex, setPageIndex] = useState(() => Number(new URLSearchParams(window.location.search).get("pagina") || "0") || 0);
  const [from, setFrom] = useState(() => new URLSearchParams(window.location.search).get("de") ?? "");
  const [to, setTo] = useState(() => new URLSearchParams(window.location.search).get("ate") ?? "");
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("q") ?? "");
  const [direction, setDirection] = useState("");
  const [eventKind, setEventKind] = useState("");
  const [importStatus, setImportStatus] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [listView, setListView] = useState<"ALL" | "IDENTIFIED" | "REVIEW">(() => {
    const vista = new URLSearchParams(window.location.search).get("vista");
    return vista === "REVIEW" || vista === "IDENTIFIED" ? vista : "ALL";
  });
  const [selectedLineId, setSelectedLineId] = useState("");
  const [selectedReview, setSelectedReview] = useState<ReviewRow | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [evidence, setEvidence] = useState("");
  const [identity, setIdentity] = useState<Preview | null>(null);
  const [otherAccount, setOtherAccount] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [fileName, setFileName] = useState("");
  const [withdrawId, setWithdrawId] = useState("");
  const [withdrawReason, setWithdrawReason] = useState("");
  const idempotency = useRef("");
  const accountRequest = useRef(0);
  const loadRequest = useRef(0);
  const uploadRequest = useRef(0);
  const accountIdRef = useRef("");
  const heldFile = useRef<File | null>(null);
  const resubmit = useRef(false);
  accountIdRef.current = accountId;
  const [, setSessionTick] = useState(0);
  const companyId = getSession()?.companyId;

  useEffect(() => subscribeSession(() => setSessionTick((value) => value + 1)), []);

  useEffect(() => {
    const saved = sessionStorage.getItem("af-statement-scroll");
    if (!saved) {
      return;
    }
    sessionStorage.removeItem("af-statement-scroll");
    const y = Number(saved);
    requestAnimationFrame(() => window.scrollTo(0, Number.isFinite(y) ? y : 0));
  }, []);

  const loadAccounts = useCallback(() => {
    const generation = ++accountRequest.current;
    const requestedCompany = getSession()?.companyId;
    setAccountsStatus("loading");
    setAccountsError("");
    setAccounts([]);
    setAccountId("");
    setPreview(null);
    setPage(null);
    setBatches([]);
    setFileName("");
    setPreparing(false);
    void request<Account[]>(`/api/v1/financial-accounts?${companyQuery()}`)
      .then((items) => {
        if (generation !== accountRequest.current || getSession()?.companyId !== requestedCompany) {
          return;
        }
        setAccounts(items);
        setAccountsStatus("ready");
        const eligible = items.filter((item) => item.active !== false);
        const requested = new URLSearchParams(window.location.search).get("conta");
        const requestedAccount = eligible.find((item) => item.id === requested);
        setAccountId(requestedAccount ? requestedAccount.id : eligible.length === 1 ? eligible[0].id : "");
        setIdentity(null);
        setOtherAccount(false);
        heldFile.current = null;
      })
      .catch((caught: ApiError) => {
        if (generation !== accountRequest.current || caught.code === "STALE") {
          return;
        }
        setAccountsStatus("error");
        setAccountsError(caught.message);
      });
  }, []);

  const load = useCallback(() => {
    const generation = ++loadRequest.current;
    if (!accountId) {
      setPage(null);
      setBatches([]);
      return;
    }
    const filter = [
      `accountId=${accountId}`,
      from ? `from=${from}` : "",
      to ? `to=${to}` : "",
      query.trim() ? `q=${encodeURIComponent(query.trim())}` : "",
      direction ? `direction=${direction}` : "",
      eventKind ? `eventKind=${eventKind}` : "",
      importStatus ? `importStatus=${importStatus}` : "",
      suggestion ? `suggestion=${suggestion}` : "",
      `page=${pageIndex}`,
      "size=20",
    ]
      .filter(Boolean)
      .join("&");
    void Promise.all([
      request<LinePage>(`/api/v1/statement-lines?${companyQuery(filter)}`),
      request<Batch[]>(`/api/v1/statement-batches?${companyQuery(`accountId=${accountId}`)}`),
    ])
      .then(([lines, history]) => {
        if (generation !== loadRequest.current) {
          return;
        }
        setPage(lines);
        setBatches(history);
      })
      .catch((caught: ApiError) => {
        if (generation !== loadRequest.current || caught.code === "STALE") {
          return;
        }
        setError(caught.message);
      });
  }, [accountId, direction, eventKind, from, importStatus, pageIndex, query, suggestion, to]);

  const seenCompany = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (seenCompany.current && seenCompany.current !== companyId) {
      const url = new URL(window.location.href);
      ["conta", "de", "ate", "q", "vista", "pagina"].forEach((key) => url.searchParams.delete(key));
      window.history.replaceState(null, "", `${url.pathname}${url.search}`);
      setFrom("");
      setTo("");
      setQuery("");
      setDirection("");
      setEventKind("");
      setImportStatus("");
      setSuggestion("");
      setPageIndex(0);
      setListView("ALL");
      setSelectedLineId("");
      setSelectedReview(null);
    }
    seenCompany.current = companyId;
    loadAccounts();
  }, [companyId, loadAccounts]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    idempotency.current = crypto.randomUUID();
    setSelected(preview?.rows.filter((row) => row.eligible).map((row) => row.lineNumber) ?? []);
  }, [preview]);

  const narrowed = Boolean(from || to || query.trim() || direction || eventKind || importStatus || suggestion);
  const eligibleAccounts = accounts.filter((item) => item.active !== false);
  const selectedAccount = accounts.find((item) => item.id === accountId);
  const accountReady = accountsStatus === "ready" && Boolean(selectedAccount) && selectedAccount?.active !== false;
  const canImport = canWriteAccounts() && accountReady && !busy;
  const justCreated = new URLSearchParams(window.location.search).get("conta") === "criada";
  const hasData = Boolean(page && (page.imported > 0 || page.total > 0));

  function importReason(): string {
    if (!canWriteAccounts()) {
      return "Você não pode importar relatórios nesta empresa.";
    }
    if (accountsStatus === "loading") {
      return "Aguarde o carregamento das contas.";
    }
    if (accountsStatus === "error") {
      return "Não foi possível carregar as contas.";
    }
    if (eligibleAccounts.length === 0) {
      return accounts.some((item) => item.active === false)
        ? "Ative uma conta existente para importar."
        : "Cadastre uma conta para importar o relatório.";
    }
    if (!accountId) {
      return "Selecione a conta deste relatório.";
    }
    if (busy) {
      return "Aguarde a leitura do arquivo.";
    }
    return "";
  }

  async function onFile(file: File | undefined) {
    if (!file) {
      return;
    }
    if (!accountId || !accountReady) {
      setError("Cadastre ou selecione uma conta antes de importar o relatório.");
      return;
    }
    if (busy) {
      return;
    }
    const generation = ++uploadRequest.current;
    const requestedAccount = accountId;
    const requestedCompany = companyId;
    heldFile.current = file;
    setBusy(true);
    setPreparing(true);
    setNotice("");
    setError("");
    setIdentity(null);
    setOtherAccount(false);
    setFileName(file.name);
    const body = new FormData();
    body.append("file", file);
    try {
      const next = await request<Preview>(`/api/v1/statement-previews?${companyQuery(`accountId=${requestedAccount}`)}`, {
        method: "POST",
        body,
      });
      if (generation !== uploadRequest.current || getSession()?.companyId !== requestedCompany || requestedAccount !== accountIdRef.current) {
        setPreview(null);
        setError("A leitura anterior foi descartada porque a empresa ou a conta mudou.");
        return;
      }
      if (next.identityMismatch) {
        setPreview(null);
        setOtherAccount(true);
        return;
      }
      if (next.identityConfirmationRequired) {
        setPreview(null);
        setIdentity(next);
        return;
      }
      if (!next.recognized) {
        setError("Não conseguimos reconhecer este relatório. Baixe o relatório de liquidação no Mercado Pago e selecione esse arquivo.");
        return;
      }
      setPreview(next);
    } catch (caught) {
      const api = caught as ApiError;
      if (generation !== uploadRequest.current) {
        return;
      }
      if (api.code === "STALE" || getSession()?.companyId !== requestedCompany) {
        setPreview(null);
        setError("A leitura anterior foi descartada porque a empresa ou a conta mudou.");
        return;
      }
      setError(fileErrorMessage(api));
    } finally {
      if (generation === uploadRequest.current) {
        setBusy(false);
        setPreparing(false);
      }
    }
  }

  useEffect(() => {
    if (!resubmit.current || !accountId || !heldFile.current) {
      return;
    }
    resubmit.current = false;
    void onFile(heldFile.current);
  }, [accountId]);

  async function confirm() {
    if (!preview || busy) {
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await request<ConfirmResult>(
        `/api/v1/statement-previews/${preview.id}/confirm?${companyQuery()}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": idempotency.current },
          body: JSON.stringify({
            previewToken: preview.previewToken,
            lineNumbers: selected,
            accountEvidence: evidence,
          }),
        },
      );
      setPreview(null);
      const attestation = result.accountAttestation === "OPERATOR_DECLARATION"
        ? " A origem ficou como declaração sua."
        : " A referência do arquivo conferiu com a conta.";
      setNotice(
        `Arquivo preservado: ${result.preserved} linhas, ${result.inReview} em revisão. Nenhuma conciliação foi confirmada.${attestation}`,
      );
      load();
    } catch (caught) {
      setError((caught as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function confirmIdentity() {
    if (!identity || busy) {
      return;
    }
    const generation = ++uploadRequest.current;
    const requestedAccount = accountId;
    const requestedCompany = companyId;
    setBusy(true);
    setError("");
    try {
      const next = await request<Preview>(`/api/v1/statement-previews/${identity.id}/identify?${companyQuery()}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ previewToken: identity.previewToken }),
      });
      if (generation !== uploadRequest.current || getSession()?.companyId !== requestedCompany || requestedAccount !== accountIdRef.current) {
        setPreview(null);
        setIdentity(null);
        setError("A leitura anterior foi descartada porque a empresa ou a conta mudou.");
        return;
      }
      setIdentity(null);
      setPreview(next);
    } catch (caught) {
      const api = caught as ApiError;
      if (generation !== uploadRequest.current || api.code === "STALE" || getSession()?.companyId !== requestedCompany) {
        setPreview(null);
        setIdentity(null);
        return;
      }
      setError(api.message || "Não foi possível confirmar a conta do relatório.");
    } finally {
      if (generation === uploadRequest.current) {
        setBusy(false);
      }
    }
  }

  function cancelReading() {
    heldFile.current = null;
    setIdentity(null);
    setOtherAccount(false);
    setFileName("");
    setPreview(null);
  }

  async function withdraw(batchId: string) {
    setBusy(true);
    setError("");
    try {
      await request(`/api/v1/statement-batches/${batchId}/withdraw?${companyQuery()}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: withdrawReason }),
      });
      setWithdrawId("");
      setWithdrawReason("");
      setNotice("Importação retirada. O pagamento externo e o extrato de origem não foram alterados. Isto não é um estorno.");
      load();
    } catch (caught) {
      setError((caught as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  function statementQuery(): string {
    const params = new URLSearchParams();
    if (accountId) params.set("conta", accountId);
    if (from) params.set("de", from);
    if (to) params.set("ate", to);
    if (query.trim()) params.set("q", query.trim());
    if (listView !== "ALL") params.set("vista", listView);
    if (pageIndex) params.set("pagina", String(pageIndex));
    const text = params.toString();
    return text ? `?${text}` : "";
  }

  function openLine(id: string) {
    if (window.matchMedia("(max-width: 1099px)").matches) {
      sessionStorage.setItem("af-statement-scroll", String(window.scrollY));
      navigate(`/financial-accounts/statement/${id}${statementQuery()}`);
      return;
    }
    setSelectedReview(null);
    setSelectedLineId(id);
  }

  function openReview(row: ReviewRow) {
    if (window.matchMedia("(max-width: 1099px)").matches) {
      sessionStorage.setItem("af-statement-scroll", String(window.scrollY));
      navigate(`/financial-accounts/statement/batches/${row.batchId}${statementQuery()}`);
      return;
    }
    setSelectedLineId("");
    setSelectedReview(row);
  }

  const reviews = page?.reviews ?? [];
  const reviewTotal = page?.reviewCount ?? reviews.length;
  const identifiedCount = (page?.creditCount ?? 0) + (page?.debitCount ?? 0);
  const dateCaption = batches[0]?.profileId ? dateLabel(batches[0].profileId) : "data do relatório importado";
  const visibleLines = (page?.items ?? []).filter((line) => listView !== "IDENTIFIED" || lineSituation(line) === "No total");

  return (
    <section className="statement fluxo">
      <header className="fx-head">
        <div>
          <h1 id="page-title" tabIndex={-1}>{preview ? "Confira seu relatório" : "Extrato da conta"}</h1>
          {preview ? <p className="pv-sub">Revise as movimentações antes de importar.</p> : null}
        </div>
        <div className="fx-head-actions">
          {preview ? (
            <button type="button" className="secondary" onClick={() => { setPreview(null); setError(""); }}>Voltar ao extrato</button>
          ) : null}
        <label className="file-action" aria-disabled={!canImport}>
          <input
            className="sr-only"
            type="file"
            accept=".csv,text/csv"
            disabled={!canImport}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              void onFile(file);
            }}
          />
          Importar relatório
        </label>
        </div>
        {importReason() ? <p className="hint">{importReason()}</p> : null}
      </header>
      {accountsStatus === "loading" ? <p className="hint" role="status">Carregando as contas desta empresa.</p> : null}
      {accountsStatus === "error" ? (
        <div className="statement-prepare">
          <p className="error" role="alert">{accountsError || "Não foi possível carregar as contas."}</p>
          <button type="button" onClick={loadAccounts}>Tentar novamente</button>
        </div>
      ) : null}
      {accountsStatus === "ready" && accounts.length === 0 ? (
        canWriteAccounts() ? (
          <div className="statement-prepare">
            <h2>Vamos cadastrar suas contas financeiras</h2>
            <p>Comece pela conta que sua empresa usa para receber e pagar.</p>
            <button type="button" onClick={() => navigate("/financial-accounts/new?return=statement")}>Cadastrar primeira conta</button>
          </div>
        ) : (
          <p className="hint">O cadastro de contas não está disponível para o seu acesso nesta empresa.</p>
        )
      ) : null}
      {accountsStatus === "ready" && eligibleAccounts.length === 0 && accounts.length > 0 ? (
        <div className="statement-prepare">
          <p>Há contas inativas nesta empresa. Ative uma conta para importar um relatório.</p>
          {accounts.map((account) => (
            <button key={account.id} type="button" className="secondary" onClick={() => navigate(`/financial-accounts/${account.id}`)}>{account.name}</button>
          ))}
        </div>
      ) : null}
      {accountsStatus === "ready" && (accountReady || eligibleAccounts.length > 1) && (!preview || eligibleAccounts.length > 1) ? (
        <div className="fx-context">
          {eligibleAccounts.length > 1 ? (
            <label className="statement-account">
              {accountId ? "Conta" : "De qual conta é este relatório?"}
              <select
                value={accountId}
                disabled={busy}
                onChange={(event) => {
                  if (preview || identity) {
                    setNotice("A leitura anterior foi descartada porque a conta mudou.");
                  }
                  if (otherAccount && heldFile.current && event.target.value) {
                    resubmit.current = true;
                  }
                  setAccountId(event.target.value);
                  setPreview(null);
                  setIdentity(null);
                  setOtherAccount(false);
                  setPage(null);
                  setSelectedLineId("");
                  setSelectedReview(null);
                  setPageIndex(0);
                }}
              >
                <option value="">Selecione a conta</option>
                {eligibleAccounts.map((account) => (
                  <option key={account.id} value={account.id}>{account.name}</option>
                ))}
              </select>
            </label>
          ) : selectedAccount ? <strong>{selectedAccount.name}</strong> : null}
          {!preview && selectedAccount ? <span>conta da empresa · Real</span> : null}
          {!preview && batches[0]?.profileId ? <span>{dateLabel(batches[0].profileId)}. Não é data de caixa.</span> : null}
          {!preview && batches.find((item) => item.status === "CONFIRMED") ? <span>Última importação manual: {batches.find((item) => item.status === "CONFIRMED")?.fileName}</span> : null}
        </div>
      ) : null}
      {justCreated && accountReady ? (
        <div className="notice">
          <p>Conta cadastrada. Você pode adicionar outra conta ou importar um relatório.</p>
          <button type="button" className="secondary" onClick={() => navigate("/financial-accounts/new?return=statement")}>Adicionar outra conta</button>
        </div>
      ) : null}
      {preparing ? <p className="notice" role="status">{fileName} — Lendo seu relatório…</p> : null}
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
      {identity && selectedAccount ? (
        <section className="statement-prepare" aria-label="Confirmar conta do relatório">
          <h2>Este relatório pertence à conta {selectedAccount.name} da empresa {getSession()?.companies.find((company) => company.id === companyId)?.name ?? "selecionada"}?</h2>
          <p>Instituição do relatório: Mercado Pago. Isso não confirma a importação nem a titularidade no Mercado Pago.</p>
          <p>Período: {identity.periodFrom ? formatDateBr(identity.periodFrom) : "não informado"} a {identity.periodTo ? formatDateBr(identity.periodTo) : "não informado"}.</p>
          <p>Identificação encontrada: {identity.fileAccountRef || "não informada"}.</p>
          <div className="actions">
            <button type="button" disabled={busy} onClick={() => void confirmIdentity()}>Sim, é esta conta</button>
            <button type="button" className="secondary" onClick={cancelReading}>Cancelar</button>
          </div>
        </section>
      ) : null}
      {otherAccount ? (
        <section className="statement-prepare" aria-label="Relatório de outra conta">
          <h2>Este relatório parece ser de outra conta.</h2>
          <p>{eligibleAccounts.length > 1 ? "Escolha a conta correta acima ou cancele. A identificação já gravada não foi substituída." : "Não há outra conta nesta empresa. Cancele e use o relatório desta conta."}</p>
          <button type="button" className="secondary" onClick={cancelReading}>Cancelar</button>
        </section>
      ) : null}
      {preview ? (
        <PreviewPanel
          preview={preview}
          fileName={fileName}
          accountName={accounts.find((account) => account.id === accountId)?.name ?? ""}
          selected={selected}
          evidence={evidence}
          busy={busy}
          onEvidence={setEvidence}
          onToggle={(lineNumber, checked) => {
            setSelected((current) => checked ? [...current, lineNumber] : current.filter((item) => item !== lineNumber));
          }}
          onConfirm={() => void confirm()}
        />
      ) : null}
      {accountReady && page && page.imported === 0 && page.total === 0 && !narrowed && !preview && !identity && !otherAccount ? (
        <div className="statement-prepare">
          <h2>Importe seu primeiro relatório</h2>
          <p>Selecione o relatório baixado do Mercado Pago. Você poderá conferir os dados antes de confirmar.</p>
        </div>
      ) : null}
      {hasData && page && !preview ? (
        <>
          <div className="fx-tabs" role="tablist" aria-label="Vistas do extrato">
            <button type="button" role="tab" className="fx-tab" aria-selected={listView === "ALL"} onClick={() => setListView("ALL")}>Todas<span className="fx-count">{page.total} linhas</span></button>
            <button type="button" role="tab" className="fx-tab" aria-selected={listView === "IDENTIFIED"} onClick={() => setListView("IDENTIFIED")}>Identificadas<span className="fx-count">{identifiedCount} linhas</span></button>
            <button type="button" role="tab" className="fx-tab" aria-selected={listView === "REVIEW"} onClick={() => setListView("REVIEW")}>Em revisão<span className={`fx-count ${reviewTotal > 0 ? "is-review" : ""}`}>{reviewTotal} ocorrências</span></button>
          </div>
          <p className="fx-caption">Linha é o evento gravado. Ocorrência em revisão permanece no arquivo e fora do total. A vista não altera esse total.</p>
          <div className="statement-layout">
            <div className="fx-table-card">
              <div className="fx-toolbar">
                <label>
                  Busca
                  <input value={query} onChange={(event) => { setQuery(event.target.value); setPageIndex(0); }} placeholder="Descrição ou referência" />
                </label>
                <label>
                  Data inicial
                  <input type="date" value={from} onChange={(event) => { setFrom(event.target.value); setPageIndex(0); }} />
                </label>
                <label>
                  Data final
                  <input type="date" value={to} onChange={(event) => { setTo(event.target.value); setPageIndex(0); }} />
                </label>
                {from || to ? <button type="button" className="secondary" onClick={() => { setFrom(""); setTo(""); setPageIndex(0); }}>Limpar período</button> : null}
              <details className="statement-extra-filters">
                <summary>Filtros</summary>
                <div className="statement-filters">
                  <label>
                    Entradas e saídas
                    <select value={direction} onChange={(event) => { setDirection(event.target.value); setPageIndex(0); }}>
                      <option value="">Todas</option>
                      <option value="IN">Entradas</option>
                      <option value="OUT">Saídas</option>
                      <option value="NONE">Sem direção</option>
                    </select>
                  </label>
                  <label>
                    Tipo de evento
                    <select value={eventKind} onChange={(event) => { setEventKind(event.target.value); setPageIndex(0); }}>
                      <option value="">Todos</option>
                      {Object.entries(EVENT_LABEL).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Importação
                    <select value={importStatus} onChange={(event) => { setImportStatus(event.target.value); setPageIndex(0); }}>
                      <option value="">Todas</option>
                      <option value="ACTIVE">Importada</option>
                      <option value="WITHDRAWN">Retirada</option>
                    </select>
                  </label>
                  <label>
                    Sugestão
                    <select value={suggestion} onChange={(event) => { setSuggestion(event.target.value); setPageIndex(0); }}>
                      <option value="">Todas</option>
                      <option value="QUALIFIED">Qualificada</option>
                      <option value="WEAK">Fraca</option>
                      <option value="NONE">Sem sugestão</option>
                    </select>
                  </label>
                </div>
              </details>
              </div>
              {narrowed ? <p className="hint">Entradas, saídas, gráfico e lista usam este recorte.</p> : null}
              {listView !== "REVIEW" && visibleLines.length === 0 ? <p className="empty">Nenhuma linha neste filtro.</p> : null}
              {listView !== "REVIEW" && visibleLines.length > 0 ? (
                <>
                  <table className="desktop-table statement-table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Situação</th>
                        <th className="num">Líquido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleLines.map((line) => (
                        <tr key={line.id} className={selectedLineId === line.id ? "is-selected" : undefined}>
                          <td>{formatDateBr(line.effectiveOn)}</td>
                          <td className="desc">
                            <button type="button" className="statement-row-link" onClick={() => openLine(line.id)}>{line.description || "Sem descrição"}</button>
                            {line.externalReference ? <span className="hint">{line.externalReference}</span> : null}
                          </td>
                          <td>{lineSituation(line) === "Precisa de revisão" ? <span className="review-chip">{lineSituation(line)}</span> : <span className="fx-badge">{lineSituation(line)}</span>}</td>
                          <td className={`num ${line.direction === "OUT" ? "money-out" : "money-in"}`}>{signedMoney(line.netMinor, line.direction, line.netAbsent)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="statement-cards">
                    {visibleLines.map((line, index) => {
                      const label = line.effectiveOn ? formatDateBr(line.effectiveOn) : "Sem data";
                      const previous = visibleLines[index - 1];
                      const previousLabel = previous ? (previous.effectiveOn ? formatDateBr(previous.effectiveOn) : "Sem data") : "";
                      return (
                        <div key={line.id}>
                          {label !== previousLabel ? <p className="fx-day-label">{label}</p> : null}
                          <div className="statement-card">
                            <button type="button" className="statement-card-button" onClick={() => openLine(line.id)}>
                              <span className="desc">{line.description || "Sem descrição"}</span>
                              <strong className={`num ${line.direction === "OUT" ? "money-out" : "money-in"}`}>{signedMoney(line.netMinor, line.direction, line.netAbsent)}</strong>
                              {lineSituation(line) === "Precisa de revisão" ? <span className="review-chip">{lineSituation(line)}</span> : <span className="fx-badge">{lineSituation(line)}</span>}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="pager">
                    <button type="button" className="secondary" disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}>Anterior</button>
                    <span>Página {pageIndex + 1} · {page.total} linhas</span>
                    <button type="button" className="secondary" disabled={(pageIndex + 1) * page.size >= page.total} onClick={() => setPageIndex((value) => value + 1)}>Seguinte</button>
                  </div>
                </>
              ) : null}
              {listView === "REVIEW" && reviews.length < reviewTotal ? (
                <p className="fx-caption">A lista mostra as primeiras {reviews.length} de {reviewTotal} ocorrências. O total autorizado é {reviewTotal}.</p>
              ) : null}
              {listView === "REVIEW" && reviews.length === 0 ? <p className="empty">Nenhuma ocorrência em revisão neste recorte.</p> : null}
              {listView === "REVIEW" && reviews.length > 0 ? (
                <div className="statement-reviews">
                  <table className="desktop-table statement-table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Situação</th>
                        <th className="num">Líquido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reviews.map((row) => (
                        <tr key={`${row.batchId}-${row.lineNumber}`}>
                          <td>{formatDateBr(row.effectiveOn)}</td>
                          <td className="desc">
                            <button type="button" className="statement-row-link" onClick={() => openReview(row)}>{row.description || "Sem descrição"}</button>
                          </td>
                          <td><span className="review-chip">{shortReason(row.exclusionCode) || "Precisa de revisão"}</span></td>
                          <td className={`num ${row.direction === "OUT" ? "money-out" : "money-in"}`}>{signedMoney(row.netMinor, row.direction, row.netAbsent)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <ul className="cards statement-cards">
                    {reviews.map((row) => (
                      <li key={`${row.batchId}-${row.lineNumber}`}>
                        <button type="button" className="statement-card-button" onClick={() => openReview(row)}>
                          <span>{formatDateBr(row.effectiveOn)}</span>
                          <strong className={row.direction === "OUT" ? "money-out" : "money-in"}>{signedMoney(row.netMinor, row.direction, row.netAbsent)}</strong>
                          <span className="desc">{row.description || "Sem descrição"}</span>
                          <span className="review-chip">{shortReason(row.exclusionCode) || "Precisa de revisão"}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
            {selectedLineId ? (
              <LineSide id={selectedLineId} onBack={() => setSelectedLineId("")} />
            ) : selectedReview ? (
              <ReviewSide
                review={selectedReview}
                related={reviews.filter((row) => row.sourceId === selectedReview.sourceId)}
                onBack={() => setSelectedReview(null)}
              />
            ) : (
              <AccountPanel
                page={page}
                from={from}
                to={to}
                dateCaption={dateCaption}
                onPick={(start, end) => { setFrom(start); setTo(end); setPageIndex(0); }}
                onReview={() => setListView("REVIEW")}
              />
            )}
          </div>
          {batches.length > 0 ? (
            <details className="statement-history">
              <summary>Histórico de importações</summary>
              <ul className="statement-batches">
                {batches.map((batch) => (
                  <li key={batch.id}>
                    <strong>{batch.fileName}</strong>
                    <span>{batch.status === "CONFIRMED" ? "Confirmado" : batch.status === "WITHDRAWN" ? "Retirado" : "Prévia"}</span>
                    <span>{formatDateBr(batch.periodFrom)} – {formatDateBr(batch.periodTo)}</span>
                    {batch.status === "CONFIRMED" || batch.status === "WITHDRAWN" ? (
                      <button type="button" className="secondary" onClick={() => navigate(`/financial-accounts/statement/batches/${batch.id}`)}>Abrir importação</button>
                    ) : null}
                    {batch.withdrawReason ? <span>Motivo da retirada: {batch.withdrawReason}</span> : null}
                    {batch.status === "CONFIRMED" && canWriteAccounts() ? (
                      withdrawId === batch.id ? (
                        <span className="statement-withdraw">
                          <input value={withdrawReason} onChange={(event) => setWithdrawReason(event.target.value)} placeholder="Motivo da retirada" />
                          <button type="button" disabled={busy} onClick={() => void withdraw(batch.id)}>Confirmar retirada</button>
                        </span>
                      ) : (
                        <button type="button" className="secondary" onClick={() => setWithdrawId(batch.id)}>Retirar importação</button>
                      )
                    ) : null}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

const PREVIEW_PAGE = 8;

function dateHeading(profileId: string): string {
  return profileId === "mp-settlement-v2-csv-1" ? "Aprovação" : "Data";
}

function entersPartial(row: PreviewRow, profileId: string): boolean {
  if (!row.eligible || row.netAbsent || row.netMinor == null) {
    return false;
  }
  if (row.availability === "UNRELEASED") {
    return false;
  }
  if (row.balanceEffect && row.balanceEffect !== "AFFECTS") {
    return false;
  }
  if (profileId === "mp-settlement-v2-csv-1" && row.availability && row.availability !== "RELEASED") {
    return false;
  }
  return true;
}

function previewBadge(row: PreviewRow): { label: string; warn: boolean } {
  if (!row.eligible) {
    return { label: "Em revisão", warn: true };
  }
  if (row.availability === "UNRELEASED") {
    return { label: "Não liberada", warn: true };
  }
  return { label: "Pronta para importar", warn: false };
}

function lineReason(row: PreviewRow, issues: Issue[]): string {
  const own = issues.filter((issue) => issue.lineNumber === row.lineNumber);
  const codes = own.map((issue) => issue.code);
  const parts: string[] = [];
  if (codes.includes("IDENTITY_INSUFFICIENT")) {
    parts.push("Há outra ocorrência com a mesma referência e valor diferente. Elas não foram fundidas e ficam fora do total.");
  }
  if (codes.includes("EFFECT_UNVERIFIED") || row.availability === "UNRELEASED") {
    parts.push("A disponibilidade não foi confirmada. A linha permanece no arquivo e fora do total parcial.");
  }
  if (row.netAbsent || codes.includes("AMOUNT_ABSENT")) {
    parts.push("O valor não veio no arquivo. A ausência não foi tratada como zero.");
  }
  const human = own.map((issue) => issue.message).filter((message) => message && !/IS_RELEASED|SOURCE_ID|TRANSACTION_TYPE|SETTLEMENT_|FEE_AMOUNT|REAL_AMOUNT/.test(message));
  if (parts.length > 0) {
    return parts.join(" ");
  }
  if (human.length > 0) {
    return human.join(" ");
  }
  if (!row.eligible) {
    return "Esta linha fica fora do total.";
  }
  return "Sem pendência nesta linha.";
}

function reviewCopy(rows: PreviewRow[], issues: Issue[]): string | null {
  const review = rows.filter((row) => !row.eligible);
  const known = new Set(rows.map((row) => row.lineNumber));
  const attached = issues.filter((issue) => review.some((row) => row.lineNumber === issue.lineNumber) || !known.has(issue.lineNumber));
  const codes = [...attached.map((issue) => issue.code), ...review.flatMap((row) => codesFor(issues, row.lineNumber))];
  const raw = attached.find((issue) => issue.message)?.message ?? "";
  const technical = /IS_RELEASED|SOURCE_ID|TRANSACTION_TYPE|SETTLEMENT_|FEE_AMOUNT|REAL_AMOUNT/.test(raw);
  if (new Set(codes).size === 1 && raw && !technical) {
    return raw;
  }
  if (review.length === 0 && !raw) {
    return null;
  }
  if (codes.includes("IDENTITY_INSUFFICIENT")) {
    return "Há referências iguais com valores diferentes. Essas linhas ficam no arquivo e fora do total.";
  }
  if (codes.includes("AMOUNT_ABSENT") || review.some((row) => row.netAbsent)) {
    return "Há linhas sem valor. A ausência não foi tratada como zero e elas ficam fora do total.";
  }
  if (codes.includes("UNSUPPORTED_CURRENCY")) {
    return "Há moeda sem regra de conversão. Essas linhas ficam fora do total.";
  }
  if (codes.includes("AMOUNT_DIVERGENCE")) {
    return "Há valores que não fecham entre si. Eles foram preservados e ficam fora do total.";
  }
  if (codes.includes("DUPLICATE")) {
    return "Há ocorrência repetida. A repetida não entra no total.";
  }
  return "Essas linhas precisam de conferência e ficam fora do total.";
}

function PreviewPanel({
  preview,
  fileName,
  accountName,
  selected,
  evidence,
  busy,
  onEvidence,
  onToggle,
  onConfirm,
}: {
  preview: Preview;
  fileName: string;
  accountName: string;
  selected: number[];
  evidence: string;
  busy: boolean;
  onEvidence: (value: string) => void;
  onToggle: (lineNumber: number, checked: boolean) => void;
  onConfirm: () => void;
}) {
  const [filter, setFilter] = useState<"ALL" | "READY" | "REVIEW">("ALL");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [openLine, setOpenLine] = useState<number | null>(null);
  const readyCount = preview.rows.filter((row) => row.eligible).length;
  const reviewCount = preview.rows.filter((row) => !row.eligible).length;
  const unreleasedReady = preview.rows.filter((row) => row.eligible && row.availability === "UNRELEASED").length;
  const needle = query.trim().toLowerCase();
  const visible = preview.rows.filter((row) => {
    if (filter === "READY" && !row.eligible) return false;
    if (filter === "REVIEW" && row.eligible) return false;
    if (!needle) return true;
    return `${row.description ?? ""} ${row.externalReference ?? ""}`.toLowerCase().includes(needle);
  });
  const pageCount = Math.max(1, Math.ceil(visible.length / PREVIEW_PAGE));
  const safePage = Math.min(page, pageCount - 1);
  const slice = visible.slice(safePage * PREVIEW_PAGE, safePage * PREVIEW_PAGE + PREVIEW_PAGE);
  const open = preview.rows.find((row) => row.lineNumber === openLine) ?? null;
  const partial = preview.rows.filter((row) => selected.includes(row.lineNumber) && entersPartial(row, preview.profileId));
  let inflow = 0;
  let outflow = 0;
  for (const row of partial) {
    const amount = row.netMinor ?? 0;
    if (row.direction === "OUT") outflow += amount;
    else if (row.direction === "IN") inflow += amount;
  }
  const unreleasedSelected = preview.rows.filter((row) => selected.includes(row.lineNumber) && row.eligible && row.availability === "UNRELEASED").length;
  const reason = reviewCopy(preview.rows, preview.issues);
  const fileNote = [preview.blockReason, preview.fileDiagnostic].filter((item, index, all) => item && all.indexOf(item) === index).join(" ");
  const rangeStart = visible.length === 0 ? 0 : safePage * PREVIEW_PAGE + 1;
  const rangeEnd = Math.min(visible.length, (safePage + 1) * PREVIEW_PAGE);
  return (
    <section className="pv" aria-label="Conferência do arquivo">
      <div className="pv-context">
        <strong>{accountName || "Conta selecionada"}</strong>
        <span aria-hidden="true">·</span>
        <span>{formatDateBr(preview.periodFrom)} a {formatDateBr(preview.periodTo)}</span>
        <span className="pv-muted">{dateLabel(preview.profileId)}</span>
        <span className="pv-steps">1. Arquivo <span aria-hidden="true">→</span> <strong aria-current="step">2. Conferência</strong> <span aria-hidden="true">→</span> 3. Resultado</span>
      </div>
      <div className="pv-layout">
        <section className="pv-card">
          <div className="pv-card-head">
            <h2>Movimentações do arquivo</h2>
            <p>{preview.rows.length === 1 ? "1 linha lida" : `${preview.rows.length} linhas lidas`}</p>
          </div>
          <div className="pv-tabs" role="tablist" aria-label="Conferência das linhas">
            <button type="button" role="tab" className="pv-tab" aria-selected={filter === "ALL"} onClick={() => { setFilter("ALL"); setPage(0); }}>Todas<span className="pv-count">{preview.rows.length}</span></button>
            <button type="button" role="tab" className="pv-tab" aria-selected={filter === "READY"} onClick={() => { setFilter("READY"); setPage(0); }}>Prontas<span className="pv-count">{readyCount}</span></button>
            <button type="button" role="tab" className="pv-tab" aria-selected={filter === "REVIEW"} onClick={() => { setFilter("REVIEW"); setPage(0); }}>Em revisão<span className={`pv-count${reviewCount > 0 ? " is-warn" : ""}`}>{reviewCount}</span></button>
          </div>
          <p className="pv-caption">Pronta é a linha elegível para confirmar. Em revisão fica fora dessa confirmação. As contagens não se repetem.</p>
          {unreleasedReady > 0 ? <p className="pv-caption">Há linhas prontas ainda não liberadas. A conferência mostra essa condição; elas podem ser confirmadas e ficam fora do total parcial.</p> : null}
          <label className="pv-search">
            <span className="sr-only">Busca</span>
            <input value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} placeholder="Buscar descrição ou referência" />
          </label>
          <div className="pv-table-wrap">
            <table className="pv-table">
              <thead>
                <tr>
                  <th className="pv-check"><span className="sr-only">Seleção</span></th>
                  <th className="pv-date">{dateHeading(preview.profileId)}</th>
                  <th>Descrição</th>
                  <th className="pv-status">Conferência</th>
                  <th className="num">Valor líquido</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((row) => {
                  const badge = previewBadge(row);
                  return (
                    <tr key={row.lineNumber}>
                      <td className="pv-check">
                        <input
                          type="checkbox"
                          aria-label={`Linha ${row.lineNumber}`}
                          checked={selected.includes(row.lineNumber)}
                          disabled={!row.eligible}
                          onChange={(event) => onToggle(row.lineNumber, event.target.checked)}
                        />
                      </td>
                      <td className="pv-date">{formatDateBr(row.effectiveOn)}</td>
                      <td>
                        <button type="button" className="pv-desc" aria-label={`Abrir linha ${row.lineNumber}: ${row.description || "Sem descrição"}`} onClick={() => setOpenLine(row.lineNumber)}>
                          {row.description || "Sem descrição"}
                        </button>
                        {row.externalReference ? <span className="pv-ref">{row.externalReference}</span> : null}
                        <span className={`pv-mobile-status${badge.warn ? " is-warn" : ""}`}>{badge.label}</span>
                      </td>
                      <td className="pv-status"><span className={`pv-badge${badge.warn ? " is-warn" : ""}`}>{badge.label}</span></td>
                      <td className={`num${row.direction === "OUT" ? " is-out" : row.direction === "IN" ? " is-in" : ""}`}>{signedMoney(row.netMinor, row.direction, row.netAbsent, !preview.currencyAssumed)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {visible.length === 0 ? <p className="pv-caption">Nenhuma linha nesta vista.</p> : null}
          <div className="pv-foot">
            <span>{rangeStart}–{rangeEnd} de {visible.length} linhas</span>
            <div>
              <button type="button" className="secondary" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Anterior</button>
              <button type="button" className="secondary" disabled={safePage >= pageCount - 1} onClick={() => setPage(safePage + 1)}>Próximas</button>
            </div>
          </div>
        </section>
        <aside className="pv-rail">
          {open ? (
            <article className="pv-card pv-detail">
              <button type="button" className="secondary" onClick={() => setOpenLine(null)}>Voltar ao resumo</button>
              <p className="pv-kicker">Linha {open.lineNumber}</p>
              <h2>{open.description || "Sem descrição"}</h2>
              <p className={`pv-total${open.direction === "OUT" ? " is-out" : " is-in"}`}>{signedMoney(open.netMinor, open.direction, open.netAbsent, !preview.currencyAssumed)}</p>
              <dl>
                <div><dt>Data</dt><dd>{formatDateBr(open.effectiveOn)}</dd></div>
                <div><dt>Referência</dt><dd>{open.externalReference || "Não informada"}</dd></div>
                <div><dt>Conferência</dt><dd>{previewBadge(open).label}</dd></div>
                <div><dt>Motivo</dt><dd>{lineReason(open, preview.issues)}</dd></div>
                {open.grossMinor != null || open.grossAbsent ? <div><dt>Bruto</dt><dd>{money(open.grossMinor ?? null, open.grossAbsent === true, !preview.currencyAssumed)}</dd></div> : null}
                {open.feeMinor != null || open.feeAbsent ? <div><dt>Tarifa</dt><dd>{money(open.feeMinor ?? null, open.feeAbsent === true, !preview.currencyAssumed)}</dd></div> : null}
              </dl>
            </article>
          ) : (
            <>
              <article className="pv-card">
                <p className="pv-kicker">O que será importado</p>
                <p className="pv-eligible">{selected.length === 1 ? "1 movimentação selecionada" : `${selected.length} movimentações selecionadas`}</p>
                {preview.currencyAssumed ? <p className="pv-total">Moeda não informada</p> : <p className="pv-total is-in">{formatMinor(String(inflow))}</p>}
                <p className="pv-total-label">Entradas elegíveis</p>
                <div className="pv-rows">
                  <div><span>Saídas</span><strong>{preview.currencyAssumed ? "Moeda não informada" : formatMinor(String(outflow))}</strong></div>
                  <div><span>Diferença parcial</span><strong>{preview.currencyAssumed ? "Moeda não informada" : formatMinor(String(inflow - outflow))}</strong></div>
                </div>
                <p className="pv-note">Este total considera somente as movimentações prontas selecionadas que entram no fluxo. Não representa o saldo da conta.</p>
                {unreleasedSelected > 0 ? <p className="pv-note">Há linhas selecionadas ainda não liberadas. Elas podem ser confirmadas e ficam fora deste total.</p> : null}
                {fileNote ? <p className="pv-block" role="alert">{fileNote}</p> : null}
                {reason ? (
                  <div className="pv-alert">
                    <p>{reviewCount === 1 ? "1 linha em revisão." : `${reviewCount} linhas em revisão.`} {reason}</p>
                    <button type="button" className="pv-text" onClick={() => { setFilter("REVIEW"); setPage(0); setOpenLine(null); }}>Conferir essas linhas →</button>
                  </div>
                ) : null}
                {preview.accountEvidenceRequired ? (
                  <label className="pv-evidence">
                    Declaração sua sobre a origem do arquivo. Ela não confirma a titularidade sozinha.
                    <textarea value={evidence} onChange={(event) => onEvidence(event.target.value)} />
                  </label>
                ) : null}
                <button type="button" className="pv-commit" disabled={busy || preview.confirmBlocked || selected.length === 0} onClick={onConfirm}>
                  {busy ? "Confirmando…" : "Confirmar importação"}
                </button>
                <p className="pv-caption">A confirmação guarda {preview.rows.length} linhas. {selected.length} eventos selecionados entram na consolidação. Os demais permanecem no arquivo.</p>
              </article>
              <article className="pv-card">
                <h2>Sobre este arquivo</h2>
                <p><strong>{fileName || "Arquivo enviado"}</strong></p>
                <p className="pv-muted">{accountName || "Conta selecionada"}</p>
                <p>Todas as linhas são preservadas. As ambíguas ficam em revisão. Importar não realiza pagamento nem confirma conciliação.</p>
              </article>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}

function StatementDetail({ id }: { id: string }) {
  const [line, setLine] = useState<Line | null>(null);
  const [profileId, setProfileId] = useState("");
  const [fileName, setFileName] = useState("");
  const [accountName, setAccountName] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void request<Line & { batchId?: string }>(`/api/v1/statement-lines/${id}?${companyQuery()}`)
      .then((found) => {
        if (!active) return;
        setLine(found);
        void request<Account[]>(`/api/v1/financial-accounts?${companyQuery()}`)
          .then((accounts) => {
            if (!active) return;
            setAccountName(accounts.find((account) => account.id === found.accountId)?.name ?? "");
          })
          .catch(() => undefined);
        if (found.batchId) {
          void request<BatchDetail>(`/api/v1/statement-batches/${found.batchId}?${companyQuery()}`)
            .then((batch) => {
              if (!active) return;
              setProfileId(batch.profileId);
              setFileName(batch.fileName);
            })
            .catch(() => undefined);
        }
      })
      .catch((caught: ApiError) => {
        if (active) setError(caught.message);
      });
    return () => {
      active = false;
    };
  }, [id]);
  if (error) {
    return <p className="error" role="alert">{error}</p>;
  }
  if (!line) {
    return <p className="hint">Carregando linha…</p>;
  }
  const situation = line.importStatus === "WITHDRAWN"
    ? "Retirada"
    : line.balanceEffect === "AVAILABILITY_ONLY"
      ? "Disponibilidade não confirmada"
      : line.balanceEffect === "AFFECTS"
        ? "No total parcial"
        : "Fora do total";
  const pending = line.balanceEffect === "AFFECTS" ? "" : reasonDetail(line.balanceEffect === "AVAILABILITY_ONLY" ? "UNRELEASED" : "OUT_OF_TOTAL");
  return (
    <section className="statement fluxo">
      <PageHeader title="Linha do extrato" hint="A sugestão aproxima esta linha de um recebimento e ainda não é conciliação." action={<button type="button" className="secondary" onClick={() => navigate(statementHome())}>Voltar</button>} />
      <div className="statement-hero">
        <p className="statement-net">{money(line.netMinor, line.netAbsent)}</p>
        <p>{directionLabel(line.direction)} · {situation}</p>
        <div className="statement-split">
          <div><span>Bruto</span><strong className="num">{money(line.grossMinor, line.grossAbsent)}</strong></div>
          <div><span>Tarifa</span><strong className="num">{money(line.feeMinor, line.feeAbsent)}</strong></div>
        </div>
      </div>
      {!line.grossAbsent && !line.feeAbsent && !line.netAbsent && line.grossMinor != null && line.feeMinor != null && line.netMinor != null && line.grossMinor - line.feeMinor !== (line.direction === "OUT" ? -line.netMinor : line.netMinor) && line.grossMinor + line.feeMinor !== (line.direction === "OUT" ? -line.netMinor : line.netMinor) ? (
        <p>Bruto, tarifa e líquido foram preservados como vieram no arquivo. A diferença não foi ajustada.</p>
      ) : null}
      <dl className="facts">
        <div><dt>{dateLabel(profileId)}</dt><dd>{formatDateBr(line.effectiveOn)}</dd></div>
        <div><dt>Descrição</dt><dd className="desc">{line.description || "Sem descrição"}</dd></div>
        <div><dt>Conta</dt><dd>{accountName || "Conta da linha"}</dd></div>
        <div><dt>Origem</dt><dd>{fileName || eventLabel(line.eventKind)}</dd></div>
        <div><dt>Referência</dt><dd>{line.externalReference || "Não informada"}</dd></div>
        <div><dt>Categoria</dt><dd>Não classificada</dd></div>
        <div><dt>Iniciativa</dt><dd>Não atribuída</dd></div>
        {pending ? <div><dt>Motivo da pendência</dt><dd>{pending}</dd></div> : null}
      </dl>
      <h2>Sugestões</h2>
      {line.suggestions.length === 0 ? <p>Sem sugestão. Nenhuma conciliação foi feita.</p> : (
        <ul>
          {line.suggestions.map((item) => (
            <li key={`${item.receiptId}-${item.namespace}`}>
              Ainda não é conciliação. {item.strength === "WEAK" ? "Sugestão fraca" : "Candidato qualificado"}. {item.reason} {item.divergence}
            </li>
          ))}
        </ul>
      )}
      <details className="statement-technical">
        <summary>Identificação e linha original</summary>
        <p>Tipo {eventLabel(line.eventKind)}. {profileId ? `Perfil ${profileId}.` : ""}</p>
        {line.originalRows && line.originalRows.length > 0 ? line.originalRows.map((raw) => <p key={raw} className="desc">{raw}</p>) : <p>Linha original indisponível.</p>}
      </details>
    </section>
  );
}

function BatchHistory({ id }: { id: string }) {
  const [batch, setBatch] = useState<BatchDetail | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("ALL");
  useEffect(() => {
    void request<BatchDetail>(`/api/v1/statement-batches/${id}?${companyQuery()}`)
      .then(setBatch)
      .catch((caught: ApiError) => setError(caught.message));
  }, [id]);
  if (error) {
    return <p className="error" role="alert">{error}</p>;
  }
  if (!batch) {
    return <p className="hint">Carregando lote…</p>;
  }
  const visible = batch.occurrences.filter((row) => {
    if (filter === "REVIEW") return row.consolidation === "IN_REVIEW";
    if (filter === "UNRELEASED") return row.availability === "UNRELEASED";
    if (filter === "IDENTIFIED") return row.consolidation === "CONSOLIDATED";
    if (filter === "IN_TOTAL") return row.inPartialTotal;
    if (filter === "OUT_TOTAL") return !row.inPartialTotal;
    return true;
  });
  const identified = batch.occurrences.filter((row) => row.consolidation === "CONSOLIDATED").length;
  return (
    <section className="statement fluxo">
      <PageHeader
        title="Lote do extrato"
        hint={batch.fileName}
        action={<button type="button" className="secondary" onClick={() => navigate(statementHome())}>Voltar</button>}
      />
      <p className="statement-totals">Considera apenas as linhas indicadas. Não representa o saldo da conta.</p>
      <div className="statement-summary">
        <div><span>Período</span><strong className="statement-summary-text">{formatDateBr(batch.periodFrom)} – {formatDateBr(batch.periodTo)}</strong></div>
        <div><span>Data usada</span><strong className="statement-summary-text">{dateLabel(batch.profileId)}</strong></div>
        <div><span>Preservadas</span><strong>{batch.preservedCount}</strong></div>
        <div><span>Identificadas</span><strong>{identified}</strong></div>
        <div><span>No total</span><strong>{batch.partialCount}</strong></div>
        <div><span>Precisa de revisão</span><strong>{batch.inReviewCount}</strong></div>
      </div>
      <div className="statement-filters statement-filter-buttons" role="group" aria-label="Filtrar o lote">
        <button type="button" className="secondary" aria-pressed={filter === "ALL"} onClick={() => setFilter("ALL")}>Todas ({batch.occurrences.length})</button>
        <button type="button" className="secondary" aria-pressed={filter === "IDENTIFIED"} onClick={() => setFilter("IDENTIFIED")}>Identificadas ({identified})</button>
        <button type="button" className="secondary" aria-pressed={filter === "REVIEW"} onClick={() => setFilter("REVIEW")}>Precisa de revisão ({batch.inReviewCount})</button>
        <button type="button" className="secondary" aria-pressed={filter === "UNRELEASED"} onClick={() => setFilter("UNRELEASED")}>Não liberadas ({batch.occurrences.filter((row) => row.availability === "UNRELEASED").length})</button>
        <button type="button" className="secondary" aria-pressed={filter === "IN_TOTAL"} onClick={() => setFilter("IN_TOTAL")}>No total ({batch.partialCount})</button>
        <button type="button" className="secondary" aria-pressed={filter === "OUT_TOTAL"} onClick={() => setFilter("OUT_TOTAL")}>Fora do total ({batch.occurrences.length - batch.partialCount})</button>
      </div>
      <p className="hint">Os filtros se cruzam. Identificada ainda não significa classificada nem conciliada.</p>
      <table className="desktop-table statement-table">
        <thead>
          <tr>
            <th className="col-line">Linha</th>
            <th className="col-date">{dateLabel(batch.profileId)}</th>
            <th>Descrição</th>
            <th>Estado</th>
            <th>Direção</th>
            <th className="num">Líquido</th>
            <th>Inclusão no total</th>
            <th>Motivo da pendência</th>
            <th className="col-action"></th>
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => (
            <tr key={row.lineNumber}>
              <td className="col-line">{row.lineNumber}</td>
              <td className="col-date">{formatDateBr(row.effectiveOn)}</td>
              <td className="desc" title={row.description || undefined}>{row.description || "Sem descrição"}</td>
              <td>{row.consolidation === "IN_REVIEW" ? "Precisa de revisão" : row.availability === "UNRELEASED" ? "Não liberada" : "Identificada"}</td>
              <td>{directionLabel(row.direction)}</td>
              <td className="num">{money(row.netMinor, row.netAbsent)}</td>
              <td>{inclusionLabel(row.inPartialTotal)}</td>
              <td title={reasonDetail(row.inPartialTotal ? null : row.exclusionCode)}>{row.inPartialTotal ? "—" : shortReason(row.exclusionCode) || "Fora do total"}</td>
              <td className="col-action">{row.lineId ? <button type="button" onClick={() => navigate(`/financial-accounts/statement/${row.lineId}`)}>Abrir</button> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="cards statement-cards">
        {visible.map((row) => (
          <li key={row.lineNumber} className="movement-card statement-card">
            <div className="statement-card-top">
              <span>{formatDateBr(row.effectiveOn)}</span>
              <strong className="num">{money(row.netMinor, row.netAbsent)}</strong>
            </div>
            <p className="desc">{row.description || "Sem descrição"}</p>
            <p>{directionLabel(row.direction)} · {inclusionLabel(row.inPartialTotal)} · {row.inPartialTotal ? "Identificada" : shortReason(row.exclusionCode) || "Fora do total"}</p>
            <p>Não classificada · Não atribuída</p>
            {row.lineId ? <button type="button" onClick={() => navigate(`/financial-accounts/statement/${row.lineId}`)}>Abrir</button> : null}
          </li>
        ))}
      </ul>
      <details className="statement-technical">
        <summary>Detalhes técnicos</summary>
        <p>Perfil {batch.profileId}. {batch.documentIdentityText}</p>
      </details>
    </section>
  );
}
