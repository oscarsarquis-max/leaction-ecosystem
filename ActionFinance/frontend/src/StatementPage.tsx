import { useCallback, useEffect, useRef, useState } from "react";
import { companyQuery, request, type ApiError } from "./api";
import { formatDateBr, formatMinor } from "./money";
import { canWriteAccounts, getSession, subscribeSession } from "./session";
import { PageHeader } from "./ui/PageHeader";

type Account = { id: string; name: string; active?: boolean };
type DayBucket = { date: string; creditMinor: string; debitMinor: string };
type Link = { id: string; accountId: string; externalRef: string; provenance: string };
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
  if (direction === "OUT") {
    return `↓ − ${formatted}`;
  }
  if (direction === "IN") {
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

const REVIEW = "Precisa de revisão";

function rowState(row: PreviewRow, issues: Issue[]): string {
  const codes = issues.filter((issue) => issue.lineNumber === row.lineNumber).map((issue) => issue.code);
  if (codes.includes("IDENTITY_INSUFFICIENT")) {
    return REVIEW;
  }
  if (row.availability === "UNRELEASED") {
    return "Não liberada";
  }
  if (!row.eligible) {
    return REVIEW;
  }
  if (row.availability === "RELEASED") {
    return "Liberada";
  }
  return "Identificada";
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
  if ((api.message ?? "").includes("referência externa")) {
    return "Esta conta ainda não está identificada no relatório. Informe a referência que aparece no arquivo e selecione o relatório de novo.";
  }
  return api.message || "Não foi possível preparar a prévia.";
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

function FlowChart({ days, onPick }: { days: DayBucket[]; onPick: (from: string, to: string) => void }) {
  const points = chartPoints(days);
  if (points.length === 0) {
    return null;
  }
  const max = points.reduce((current, point) => {
    const sum = BigInt(point.credit) + BigInt(point.debit);
    return sum > current ? sum : current;
  }, 1n);
  return (
    <div className="statement-chart" role="group" aria-label="Entradas e saídas no período">
      {points.map((point) => {
        const credit = Number((BigInt(point.credit) * 72n) / max);
        const debit = Number((BigInt(point.debit) * 72n) / max);
        return (
          <button
            key={point.key}
            type="button"
            className="statement-bar"
            onClick={() => onPick(point.from, point.to)}
            title={`${formatDateBr(point.from)} a ${formatDateBr(point.to)}: entradas ${formatMinor(point.credit)}, saídas ${formatMinor(point.debit)}`}
          >
            <span className="statement-bar-in" style={{ height: `${point.credit === "0" ? 0 : Math.max(credit, 2)}px` }} />
            <span className="statement-bar-out" style={{ height: `${point.debit === "0" ? 0 : Math.max(debit, 2)}px` }} />
            <span className="statement-bar-label">{point.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function AccountPanel({
  page,
  onPick,
  onReview,
  dateCaption,
}: {
  page: LinePage;
  onPick: (from: string, to: string) => void;
  onReview: () => void;
  dateCaption: string;
}) {
  const diff = differenceMinor(page.creditMinor, page.debitMinor);
  const ambiguous = (page.reviews ?? []).filter((row) => row.exclusionCode === "IDENTITY_INSUFFICIENT").length;
  return (
    <aside className="statement-panel" aria-label="Análise da conta">
      <h2>Análise do período</h2>
      <p className="statement-metric"><span>Entradas identificadas</span><strong className="money-in">{signedMoney(page.creditMinor, "IN")}</strong></p>
      <p className="statement-metric"><span>Saídas identificadas</span><strong className="money-out">{signedMoney(page.debitMinor, "OUT")}</strong></p>
      <p className="statement-metric"><span>Diferença no período</span><strong className={diff.startsWith("-") ? "money-out" : "money-in"}>{signedMoney(diff.replace(/^-/, ""), diff.startsWith("-") ? "OUT" : "IN")}</strong></p>
      <p className="hint">Considera as linhas elegíveis importadas. Não representa o saldo da conta.</p>
      <h2>Evolução</h2>
      <p className="statement-legend"><span className="money-in">↑ Entradas</span><span className="money-out">↓ Saídas</span><span>Reais · {dateCaption}</span></p>
      <FlowChart days={page.days ?? []} onPick={onPick} />
      <h2>Próxima ação</h2>
      {(page.reviewCount ?? 0) > 0 ? (
        <div className="statement-action">
          <p>{ambiguous > 0 ? "Há operações com a mesma referência e valores diferentes." : "Há ocorrências que ainda precisam de conferência."}</p>
          <p className="hint">Elas ficam fora do total até a dúvida ser resolvida.</p>
          <button type="button" onClick={onReview}>Ver pendências</button>
        </div>
      ) : (
        <p className="hint">Nenhuma pendência de revisão neste recorte.</p>
      )}
      <h2>Posição e compromissos</h2>
      <p>Saldo da conta não apurado. O relatório não cobre a posição da conta.</p>
      <p>{page.agenda === "NONE" ? "Nenhum título registrado." : "Informação indisponível. Os títulos não estão vinculados a esta conta."}</p>
      <p>Investimentos indisponíveis. Não há classificação nem fonte de posição.</p>
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
    <aside className="statement-panel" aria-label="Detalhe da movimentação">
      <button type="button" className="secondary" onClick={onBack}>Voltar à análise</button>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {!line && !error ? <p className="hint">Carregando linha…</p> : null}
      {line ? (
        <>
          <h2 className="desc">{line.description || "Sem descrição"}</h2>
          <p className={line.direction === "OUT" ? "money-out" : "money-in"}>{signedMoney(line.netMinor, line.direction, line.netAbsent)}</p>
          <p>{directionLabel(line.direction)} · {lineSituation(line)}</p>
          <div className="statement-split">
            <div><span>Bruto</span><strong className="num">{money(line.grossMinor, line.grossAbsent)}</strong></div>
            <div><span>Tarifa</span><strong className="num">{money(line.feeMinor, line.feeAbsent)}</strong></div>
          </div>
          <dl className="facts">
            <div><dt>Data do relatório</dt><dd>{formatDateBr(line.effectiveOn)}</dd></div>
            <div><dt>Referência</dt><dd>{line.externalReference || "Não informada"}</dd></div>
            <div><dt>Categoria</dt><dd>Não classificada</dd></div>
            <div><dt>Iniciativa</dt><dd>Não atribuída</dd></div>
          </dl>
          <p className="hint">A sugestão, quando existe, ainda não é conciliação.</p>
        </>
      ) : null}
    </aside>
  );
}

function ReviewSide({ review, related, onBack }: { review: ReviewRow; related: ReviewRow[]; onBack: () => void }) {
  return (
    <aside className="statement-panel" aria-label="Detalhe da ocorrência">
      <button type="button" className="secondary" onClick={onBack}>Voltar à análise</button>
      <h2 className="desc">{review.description || "Sem descrição"}</h2>
      <p className="review-chip">{shortReason(review.exclusionCode) || "Precisa de revisão"}</p>
      <p className="hint">Estas ocorrências permanecem separadas. Nenhuma foi escolhida como a verdadeira.</p>
      <ul>
        {related.map((row) => (
          <li key={`${row.batchId}-${row.lineNumber}`}>
            {formatDateBr(row.effectiveOn)} · {signedMoney(row.netMinor, row.direction, row.netAbsent)}
          </li>
        ))}
      </ul>
      <p className="hint">A referência pode ser conferida no arquivo de origem. Não há ação para resolver esta dúvida aqui.</p>
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
  const [links, setLinks] = useState<Link[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [page, setPage] = useState<LinePage | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [query, setQuery] = useState("");
  const [direction, setDirection] = useState("");
  const [eventKind, setEventKind] = useState("");
  const [importStatus, setImportStatus] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [listView, setListView] = useState<"ALL" | "IDENTIFIED" | "REVIEW">("ALL");
  const [selectedLineId, setSelectedLineId] = useState("");
  const [selectedReview, setSelectedReview] = useState<ReviewRow | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [evidence, setEvidence] = useState("");
  const [externalRef, setExternalRef] = useState("");
  const [provenance, setProvenance] = useState("");
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
  accountIdRef.current = accountId;
  const [, setSessionTick] = useState(0);
  const companyId = getSession()?.companyId;

  useEffect(() => subscribeSession(() => setSessionTick((value) => value + 1)), []);

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
    setLinks([]);
    setFileName("");
    setPreparing(false);
    setFrom("");
    setTo("");
    setQuery("");
    setDirection("");
    setEventKind("");
    setImportStatus("");
    setSuggestion("");
    setPageIndex(0);
    void request<Account[]>(`/api/v1/financial-accounts?${companyQuery()}`)
      .then((items) => {
        if (generation !== accountRequest.current || getSession()?.companyId !== requestedCompany) {
          return;
        }
        setAccounts(items);
        setAccountsStatus("ready");
        const eligible = items.filter((item) => item.active !== false);
        setAccountId(eligible.length === 1 ? eligible[0].id : "");
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
      setLinks([]);
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
      request<Link[]>(`/api/v1/statement-links?${companyQuery(`accountId=${accountId}`)}`),
    ])
      .then(([lines, history, refs]) => {
        if (generation !== loadRequest.current) {
          return;
        }
        setPage(lines);
        setBatches(history);
        setLinks(refs);
      })
      .catch((caught: ApiError) => {
        if (generation !== loadRequest.current || caught.code === "STALE") {
          return;
        }
        setError(caught.message);
      });
  }, [accountId, direction, eventKind, from, importStatus, pageIndex, query, suggestion, to]);

  useEffect(() => {
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
  const linked = links.some((item) => item.accountId === accountId);
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
    setBusy(true);
    setPreparing(true);
    setNotice("");
    setError("");
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

  async function saveLink() {
    setBusy(true);
    setError("");
    try {
      await request(`/api/v1/statement-links?${companyQuery()}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountId, externalRef, provenance }),
      });
      setExternalRef("");
      setProvenance("");
      load();
    } catch (caught) {
      setError((caught as ApiError).message);
    } finally {
      setBusy(false);
    }
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

  function openLine(id: string) {
    if (window.matchMedia("(max-width: 1099px)").matches) {
      navigate(`/financial-accounts/statement/${id}`);
      return;
    }
    setSelectedReview(null);
    setSelectedLineId(id);
  }

  function openReview(row: ReviewRow) {
    if (window.matchMedia("(max-width: 1099px)").matches) {
      navigate(`/financial-accounts/statement/batches/${row.batchId}`);
      return;
    }
    setSelectedLineId("");
    setSelectedReview(row);
  }

  const reviews = page?.reviews ?? [];
  const identifiedCount = (page?.creditCount ?? 0) + (page?.debitCount ?? 0);
  const dateCaption = batches[0]?.profileId ? dateLabel(batches[0].profileId) : "data do relatório importado";
  const visibleLines = (page?.items ?? []).filter((line) => listView !== "IDENTIFIED" || lineSituation(line) === "No total");

  return (
    <section className="statement">
      <PageHeader
        title="Extrato da conta"
        action={
          <div className="statement-import">
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
            {importReason() ? <p className="hint">{importReason()}</p> : null}
          </div>
        }
      />
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
      {accountReady && selectedAccount ? (
        <p className="statement-context">
          <strong>{selectedAccount.name}</strong>
          <span>conta da empresa · Real</span>
          {batches[0]?.profileId ? <span>{dateLabel(batches[0].profileId)}. Não é data de caixa.</span> : null}
          {batches.find((item) => item.status === "CONFIRMED") ? <span>Última importação manual: {batches.find((item) => item.status === "CONFIRMED")?.fileName}</span> : null}
        </p>
      ) : null}
      {accountsStatus === "ready" && eligibleAccounts.length > 1 ? (
        <label className="statement-account">
          De qual conta é este relatório?
          <select
            value={accountId}
            disabled={busy}
            onChange={(event) => {
              if (preview) {
                setNotice("A prévia anterior foi descartada porque a conta mudou.");
              }
              setAccountId(event.target.value);
              setPreview(null);
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
      ) : null}
      {justCreated && accountReady ? (
        <div className="notice">
          <p>Conta cadastrada. Você pode adicionar outra conta ou importar um relatório.</p>
          <button type="button" className="secondary" onClick={() => navigate("/financial-accounts/new?return=statement")}>Adicionar outra conta</button>
        </div>
      ) : null}
      {preparing ? <p className="notice" role="status">{fileName} — Preparando prévia…</p> : null}
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
      {accountId && !linked && canWriteAccounts() ? (
        <form
          className="statement-link"
          onSubmit={(event) => {
            event.preventDefault();
            void saveLink();
          }}
        >
          <p>Esta conta ainda não está identificada no arquivo. Informe a referência que aparece no relatório. A importação só confirma quando essa referência confere, ou quando você declara a origem. Nada é associado automaticamente.</p>
          <label>
            Referência no relatório
            <input value={externalRef} onChange={(event) => setExternalRef(event.target.value)} />
          </label>
          <label>
            De onde veio a referência
            <input value={provenance} onChange={(event) => setProvenance(event.target.value)} />
          </label>
          <button type="submit" disabled={busy}>Gravar vínculo</button>
        </form>
      ) : null}
      {linked ? <p className="hint">Referência desta conta: {links.find((item) => item.accountId === accountId)?.externalRef}.</p> : null}
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
          onCancel={() => setPreview(null)}
        />
      ) : null}
      {accountReady && page && page.imported === 0 && page.total === 0 && !narrowed && !preview ? (
        <div className="statement-prepare">
          <h2>Importe seu primeiro relatório</h2>
          <p>Selecione o relatório baixado do Mercado Pago. Você poderá conferir os dados antes de confirmar.</p>
        </div>
      ) : null}
      {hasData && page ? (
        <>
          <div className="statement-panel-compact" aria-label="Resumo do período">
            <p><span>Entradas identificadas</span><strong className="money-in">{signedMoney(page.creditMinor, "IN")}</strong></p>
            <p><span>Saídas identificadas</span><strong className="money-out">{signedMoney(page.debitMinor, "OUT")}</strong></p>
            <p><span>Diferença no período</span><strong>{formatMinor(differenceMinor(page.creditMinor, page.debitMinor))}</strong></p>
          </div>
          <div className="statement-layout">
            <div className="statement-main">
              <div className="statement-period">
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
              </div>
              <div className="statement-views" role="group" aria-label="Vistas do extrato">
                <button type="button" className="secondary" aria-pressed={listView === "ALL"} onClick={() => setListView("ALL")}>Todas · {page.total} linhas</button>
                <button type="button" className="secondary" aria-pressed={listView === "IDENTIFIED"} onClick={() => setListView("IDENTIFIED")}>Identificadas · {identifiedCount} linhas</button>
                <button type="button" className="secondary" aria-pressed={listView === "REVIEW"} onClick={() => setListView("REVIEW")}>Em revisão · {reviews.length} ocorrências</button>
              </div>
              <p className="hint">A vista não muda o total. Linha é o evento gravado; ocorrência em revisão permanece no arquivo e fora do total.</p>
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
              {narrowed ? <p className="hint">Entradas, saídas, gráfico e lista usam este recorte.</p> : null}
              {listView !== "REVIEW" && visibleLines.length === 0 ? <p className="empty">Nenhuma linha neste filtro.</p> : null}
              {listView !== "REVIEW" && visibleLines.length > 0 ? (
                <>
                  <p className="statement-totals">Considera as linhas elegíveis importadas. Não representa o saldo da conta.</p>
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
                          <td>{lineSituation(line) === "Precisa de revisão" ? <span className="review-chip">{lineSituation(line)}</span> : lineSituation(line)}</td>
                          <td className={`num ${line.direction === "OUT" ? "money-out" : "money-in"}`}>{signedMoney(line.netMinor, line.direction, line.netAbsent)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <ul className="cards statement-cards">
                    {visibleLines.map((line) => (
                      <li key={line.id} className="movement-card statement-card">
                        <button type="button" className="statement-card-button" onClick={() => openLine(line.id)}>
                          <span>{formatDateBr(line.effectiveOn)}</span>
                          <strong className={line.direction === "OUT" ? "money-out" : "money-in"}>{signedMoney(line.netMinor, line.direction, line.netAbsent)}</strong>
                          <span className="desc">{line.description || "Sem descrição"}</span>
                          {lineSituation(line) === "Precisa de revisão" ? <span className="review-chip">{lineSituation(line)}</span> : <span>{lineSituation(line)}</span>}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <div className="pager">
                    <button type="button" disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}>Anterior</button>
                    <span>Página {pageIndex + 1} · {page.total} linhas</span>
                    <button type="button" disabled={(pageIndex + 1) * page.size >= page.total} onClick={() => setPageIndex((value) => value + 1)}>Seguinte</button>
                  </div>
                </>
              ) : null}
              {listView !== "IDENTIFIED" && reviews.length > 0 ? (
                <div className="statement-reviews">
                  <h2>Ocorrências em revisão</h2>
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
                dateCaption={dateCaption}
                onPick={(start, end) => { setFrom(start); setTo(end); setPageIndex(0); }}
                onReview={() => setListView("REVIEW")}
              />
            )}
          </div>
        </>
      ) : null}
    </section>
  );
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
  onCancel,
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
  onCancel: () => void;
}) {
  const [filter, setFilter] = useState("ALL");
  const identified = preview.rows.filter((row) => row.eligible).length;
  const inReview = preview.rows.filter((row) => rowState(row, preview.issues) === REVIEW).length;
  const visible = preview.rows.filter((row) => {
    if (filter === "UNRELEASED") return row.availability === "UNRELEASED";
    if (filter === "REVIEW") return rowState(row, preview.issues) === REVIEW;
    if (filter === "IDENTIFIED") return row.eligible;
    if (filter.startsWith("CODE:")) return codesFor(preview.issues, row.lineNumber).includes(filter.slice(5));
    return true;
  });
  const groups = new Map<string, Issue[]>();
  for (const issue of preview.issues) {
    const current = groups.get(issue.code) ?? [];
    current.push(issue);
    groups.set(issue.code, current);
  }
  return (
    <section className="statement-preview" aria-label="Prévia do arquivo">
      <h2>Prévia</h2>
      <div className="statement-summary">
        <div><span>Arquivo</span><strong className="statement-summary-text">{fileName || "Arquivo enviado"}</strong></div>
        <div><span>Conta</span><strong className="statement-summary-text">{accountName || "Conta selecionada"}</strong></div>
        <div><span>Período</span><strong className="statement-summary-text">{formatDateBr(preview.periodFrom)} – {formatDateBr(preview.periodTo)}</strong></div>
        <div><span>Data usada</span><strong className="statement-summary-text">{dateLabel(preview.profileId)}</strong></div>
        <div><span>Linhas lidas</span><strong>{preview.rows.length}</strong></div>
        <div><span>Identificadas</span><strong>{identified}</strong></div>
        <div><span>Precisa de revisão</span><strong>{inReview}</strong></div>
      </div>
      <p className="statement-consequence">Todas as linhas são preservadas. As ambíguas ficam em revisão. Importar não realiza pagamento nem confirma conciliação.</p>
      <div className="statement-filters statement-filter-buttons" role="group" aria-label="Filtrar ocorrências">
        <button type="button" className="secondary" aria-pressed={filter === "ALL"} onClick={() => setFilter("ALL")}>Todas ({preview.rows.length})</button>
        <button type="button" className="secondary" aria-pressed={filter === "IDENTIFIED"} onClick={() => setFilter("IDENTIFIED")}>Identificadas ({identified})</button>
        <button type="button" className="secondary" aria-pressed={filter === "REVIEW"} onClick={() => setFilter("REVIEW")}>Precisa de revisão ({inReview})</button>
        <button type="button" className="secondary" aria-pressed={filter === "UNRELEASED"} onClick={() => setFilter("UNRELEASED")}>Não liberadas ({preview.rows.filter((row) => row.availability === "UNRELEASED").length})</button>
      </div>
      <p className="hint">Os filtros se cruzam. Uma linha identificada ainda pode estar sem liberação, sem classificação e sem conciliação.</p>
      {preview.fileDiagnostic ? <p className="error" role="alert">{preview.fileDiagnostic}</p> : null}
      {preview.blockReason && preview.blockReason !== preview.fileDiagnostic ? <p className="error" role="alert">{preview.blockReason}</p> : null}
      {[...groups.entries()].map(([code, items]) => {
        const messages = [...new Set(items.map((issue) => issue.message))];
        return (
          <div key={code} className="statement-issue">
            <p>{items.length === 1 ? "1 linha" : `${items.length} linhas`}: {shortReason(code)}.</p>
            <button type="button" className="secondary" onClick={() => setFilter(`CODE:${code}`)}>Ver essas linhas</button>
            <details>
              <summary>Motivo completo</summary>
              {messages.map((message) => <p key={message}>{message}</p>)}
            </details>
          </div>
        );
      })}
      <table className="desktop-table statement-table">
        <thead>
          <tr>
            <th>Importar</th>
            <th className="col-date">{dateLabel(preview.profileId)}</th>
            <th>Descrição</th>
            <th>Tipo</th>
            <th>Estado</th>
            <th>Motivo da pendência</th>
            <th>Direção</th>
            <th className="num">Valor</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => (
            <tr key={row.lineNumber}>
              <td>
                <input
                  type="checkbox"
                  aria-label={`Linha ${row.lineNumber}`}
                  checked={selected.includes(row.lineNumber)}
                  disabled={!row.eligible}
                  onChange={(event) => onToggle(row.lineNumber, event.target.checked)}
                />
              </td>
              <td className="col-date">{formatDateBr(row.effectiveOn)}</td>
              <td className="desc" title={row.description || undefined}>{row.description || "Sem descrição"}</td>
              <td>{eventLabel(row.eventKind)}</td>
              <td>{rowState(row, preview.issues)}</td>
              <td title={preview.issues.filter((issue) => issue.lineNumber === row.lineNumber).map((issue) => issue.message).join(" ")}>{shortReason(codesFor(preview.issues, row.lineNumber)[0] ?? null) || "—"}</td>
              <td>{directionLabel(row.direction)}</td>
              <td className="num">{money(row.netMinor, row.netAbsent, !preview.currencyAssumed)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="cards statement-cards">
        {visible.map((row) => (
          <li key={row.lineNumber} className="movement-card statement-card">
            <div className="statement-card-top">
              <label>
                <input
                  type="checkbox"
                  aria-label={`Linha ${row.lineNumber}`}
                  checked={selected.includes(row.lineNumber)}
                  disabled={!row.eligible}
                  onChange={(event) => onToggle(row.lineNumber, event.target.checked)}
                />
                {" "}{formatDateBr(row.effectiveOn)}
              </label>
              <strong className="num">{money(row.netMinor, row.netAbsent, !preview.currencyAssumed)}</strong>
            </div>
            <p className="desc" title={row.description || undefined}>{row.description || "Sem descrição"}</p>
            <p>{directionLabel(row.direction)} · {eventLabel(row.eventKind)} · {rowState(row, preview.issues)} · {shortReason(codesFor(preview.issues, row.lineNumber)[0] ?? null) || "Sem pendência"} · Não classificada · Não atribuída</p>
          </li>
        ))}
      </ul>
      {preview.accountEvidenceRequired ? (
        <label>
          Declaração sua sobre a origem do arquivo. Ela não confirma a titularidade sozinha.
          <textarea value={evidence} onChange={(event) => onEvidence(event.target.value)} />
        </label>
      ) : null}
      <div className="actions">
        <button type="button" disabled={busy || preview.confirmBlocked || selected.length === 0} onClick={onConfirm}>
          {busy ? "Gravando…" : "Importar este relatório"}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>Cancelar prévia</button>
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
    <section className="statement">
      <PageHeader title="Linha do extrato" hint="A sugestão aproxima esta linha de um recebimento e ainda não é conciliação." action={<button type="button" className="secondary" onClick={() => navigate("/financial-accounts/statement")}>Voltar</button>} />
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
    <section className="statement">
      <PageHeader
        title="Lote do extrato"
        hint={batch.fileName}
        action={<button type="button" className="secondary" onClick={() => navigate("/financial-accounts/statement")}>Voltar</button>}
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
