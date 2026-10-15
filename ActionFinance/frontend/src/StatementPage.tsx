import { useCallback, useEffect, useRef, useState } from "react";
import { companyQuery, request, type ApiError } from "./api";
import { formatDateBr, formatMinor } from "./money";
import { canWriteAccounts, getSession } from "./session";
import { PageHeader } from "./ui/PageHeader";

type Account = { id: string; name: string };
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

function rowState(row: PreviewRow, issues: Issue[]): string {
  const codes = issues.filter((issue) => issue.lineNumber === row.lineNumber).map((issue) => issue.code);
  if (codes.includes("IDENTITY_INSUFFICIENT")) {
    return "Em revisão";
  }
  if (row.availability === "UNRELEASED") {
    return "Não liberada";
  }
  if (!row.eligible) {
    return "Em revisão";
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
  const [accountId, setAccountId] = useState("");
  const [links, setLinks] = useState<Link[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [page, setPage] = useState<LinePage | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [direction, setDirection] = useState("");
  const [eventKind, setEventKind] = useState("");
  const [importStatus, setImportStatus] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [evidence, setEvidence] = useState("");
  const [externalRef, setExternalRef] = useState("");
  const [provenance, setProvenance] = useState("");
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState("");
  const [withdrawId, setWithdrawId] = useState("");
  const [withdrawReason, setWithdrawReason] = useState("");
  const idempotency = useRef("");
  const companyId = getSession()?.companyId;

  const load = useCallback(() => {
    if (!accountId) {
      return;
    }
    const filter = [
      `accountId=${accountId}`,
      from ? `from=${from}` : "",
      to ? `to=${to}` : "",
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
        setPage(lines);
        setBatches(history);
        setLinks(refs);
        setError("");
      })
      .catch((caught: ApiError) => setError(caught.message));
  }, [accountId, direction, eventKind, from, importStatus, pageIndex, suggestion, to]);

  useEffect(() => {
    void request<Account[]>(`/api/v1/financial-accounts?${companyQuery()}`)
      .then((items) => {
        setAccounts(items);
        setAccountId((current) => current || items[0]?.id || "");
      })
      .catch((caught: ApiError) => setError(caught.message));
  }, [companyId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    idempotency.current = crypto.randomUUID();
    setSelected(preview?.rows.filter((row) => row.eligible).map((row) => row.lineNumber) ?? []);
  }, [preview]);

  const narrowed = Boolean(from || to || direction || eventKind || importStatus || suggestion);
  const linked = links.some((item) => item.accountId === accountId);

  async function onFile(file: File | undefined) {
    if (!file || !accountId) {
      return;
    }
    setBusy(true);
    setNotice("");
    setError("");
    setFileName(file.name);
    const body = new FormData();
    body.append("file", file);
    try {
      const next = await request<Preview>(`/api/v1/statement-previews?${companyQuery(`accountId=${accountId}`)}`, {
        method: "POST",
        body,
      });
      setPreview(next);
    } catch (caught) {
      setPreview(null);
      setError((caught as ApiError).message);
    } finally {
      setBusy(false);
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

  return (
    <section className="statement">
      <PageHeader
        title="Extrato"
        hint="Importe o relatório da sua conta para conferir as movimentações."
        action={
          canWriteAccounts() ? (
            <div className="statement-import">
              <label className="file-action">
                <input
                  className="sr-only"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => {
                    void onFile(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
                Importar arquivo
              </label>
              <p className="statement-formats">CSV da conta, com vírgula ou ponto e vírgula.</p>
            </div>
          ) : null
        }
      />
      <details className="statement-technical">
        <summary>Detalhes técnicos</summary>
        <p>Relatório de liquidação: ponto e vírgula, moeda nas colunas e data de aprovação. O outro CSV aceito usa vírgula. Perfis mp-settlement-v2-csv-1 e mp-account-money-csv-1. Parser 1.</p>
      </details>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
      <div className="statement-filters">
        <label>
          Conta
          <select
            value={accountId}
            onChange={(event) => {
              setAccountId(event.target.value);
              setPageIndex(0);
              setPreview(null);
            }}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>{account.name}</option>
            ))}
          </select>
        </label>
        <label>
          Data inicial
          <input type="date" value={from} onChange={(event) => { setFrom(event.target.value); setPageIndex(0); }} />
        </label>
        <label>
          Data final
          <input type="date" value={to} onChange={(event) => { setTo(event.target.value); setPageIndex(0); }} />
        </label>
        <label>
          Direção
          <select value={direction} onChange={(event) => { setDirection(event.target.value); setPageIndex(0); }}>
            <option value="">Todas</option>
            <option value="IN">Entrada</option>
            <option value="OUT">Saída</option>
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
      {page && page.imported === 0 && page.total === 0 && !narrowed ? (
        <p className="empty">Extrato não importado.</p>
      ) : null}
      {page && page.total === 0 && (narrowed || page.imported > 0) ? (
        <p className="empty">Nenhuma linha neste filtro.</p>
      ) : null}
      {page && page.total > 0 ? (
        <>
          <p className="statement-totals">Considera apenas as linhas indicadas. Não representa o saldo da conta.</p>
          <div className="statement-summary" aria-label="Total parcial">
            <div><span>Entradas</span><strong>{formatMinor(page.creditMinor)} <span className="count-aux">{page.creditCount}</span></strong></div>
            <div><span>Saídas</span><strong>{formatMinor(page.debitMinor)} <span className="count-aux">{page.debitCount}</span></strong></div>
            <div><span>Fora do total</span><strong>{page.excludedFromPartialCount ?? 0}</strong></div>
            <div><span>Em revisão</span><strong>{page.reviewCount ?? 0}</strong></div>
            <div><span>Líquidos ausentes</span><strong>{page.amountAbsentCount}</strong></div>
          </div>
          <p className="hint">No lote do arquivo dá para ver quais entram e quais ficam de fora. Sem categoria e sem iniciativa continuam na lista.</p>
          <table className="desktop-table statement-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Tipo</th>
                <th>Direção</th>
                <th className="num">Valor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((line) => (
                <tr key={line.id}>
                  <td>{formatDateBr(line.effectiveOn)}</td>
                  <td className="desc">{line.description || "Sem descrição"}</td>
                  <td>{eventLabel(line.eventKind)}</td>
                  <td>{directionLabel(line.direction)}</td>
                  <td className="num">{money(line.netMinor, line.netAbsent)}</td>
                  <td><button type="button" onClick={() => navigate(`/financial-accounts/statement/${line.id}`)}>Abrir</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cards statement-cards">
            {page.items.map((line) => (
              <li key={line.id} className="movement-card statement-card">
                <div className="statement-card-top">
                  <span>{formatDateBr(line.effectiveOn)}</span>
                  <strong className="num">{money(line.netMinor, line.netAbsent)}</strong>
                </div>
                <p className="desc">{line.description || "Sem descrição"}</p>
                <p>{directionLabel(line.direction)} · {eventLabel(line.eventKind)} · Não classificada · Não atribuída</p>
                <button type="button" onClick={() => navigate(`/financial-accounts/statement/${line.id}`)}>Abrir</button>
              </li>
            ))}
          </ul>
          <div className="pager">
            <button type="button" disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}>Anterior</button>
            <span>Página {pageIndex + 1}</span>
            <button type="button" disabled={(pageIndex + 1) * page.size >= page.total} onClick={() => setPageIndex((value) => value + 1)}>Seguinte</button>
          </div>
        </>
      ) : null}
      <h2>Lotes</h2>
      {batches.length === 0 ? <p className="hint">Nenhum lote nesta conta.</p> : (
        <ul className="statement-batches">
          {batches.map((batch) => (
            <li key={batch.id}>
              <strong>{batch.fileName}</strong>
              <span>{batch.status === "CONFIRMED" ? "Confirmado" : batch.status === "WITHDRAWN" ? "Retirado" : "Prévia"}</span>
              <span>{formatDateBr(batch.periodFrom)} – {formatDateBr(batch.periodTo)}</span>
                {batch.status === "CONFIRMED" || batch.status === "WITHDRAWN" ? (
                  <>
                    <span>Criadas {batch.createdCount}, enriquecidas {batch.enrichedCount}, inalteradas {batch.unchangedCount}, em revisão {batch.rejectedCount}.</span>
                    <button type="button" className="secondary" onClick={() => navigate(`/financial-accounts/statement/batches/${batch.id}`)}>Abrir lote</button>
                  </>
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
      )}
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
  const inReview = preview.rows.filter((row) => rowState(row, preview.issues) === "Em revisão").length;
  const visible = preview.rows.filter((row) => {
    if (filter === "UNRELEASED") return row.availability === "UNRELEASED";
    if (filter === "REVIEW") return rowState(row, preview.issues) === "Em revisão";
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
        <div><span>Em revisão</span><strong>{inReview}</strong></div>
      </div>
      <p className="statement-consequence">Todas as linhas são preservadas. As ambíguas ficam em revisão. Importar não realiza pagamento nem confirma conciliação.</p>
      <div className="statement-filters statement-filter-buttons" role="group" aria-label="Filtrar ocorrências">
        <button type="button" className="secondary" aria-pressed={filter === "ALL"} onClick={() => setFilter("ALL")}>Todas ({preview.rows.length})</button>
        <button type="button" className="secondary" aria-pressed={filter === "IDENTIFIED"} onClick={() => setFilter("IDENTIFIED")}>Identificadas ({identified})</button>
        <button type="button" className="secondary" aria-pressed={filter === "REVIEW"} onClick={() => setFilter("REVIEW")}>Em revisão ({inReview})</button>
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
          {busy ? "Gravando…" : "Confirmar linhas selecionadas"}
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
        <div><span>Em revisão</span><strong>{batch.inReviewCount}</strong></div>
      </div>
      <div className="statement-filters statement-filter-buttons" role="group" aria-label="Filtrar o lote">
        <button type="button" className="secondary" aria-pressed={filter === "ALL"} onClick={() => setFilter("ALL")}>Todas ({batch.occurrences.length})</button>
        <button type="button" className="secondary" aria-pressed={filter === "IDENTIFIED"} onClick={() => setFilter("IDENTIFIED")}>Identificadas ({identified})</button>
        <button type="button" className="secondary" aria-pressed={filter === "REVIEW"} onClick={() => setFilter("REVIEW")}>Em revisão ({batch.inReviewCount})</button>
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
              <td>{row.consolidation === "IN_REVIEW" ? "Em revisão" : row.availability === "UNRELEASED" ? "Não liberada" : "Identificada"}</td>
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
