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
type ConfirmResult = { batchId: string; created: number; enriched: number; unchanged: number; notImported: number; accountAttestation?: string };

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

function directionLabel(value: string): string {
  if (value === "IN") return "Entrada";
  if (value === "OUT") return "Saída";
  return "Sem direção";
}

function eventLabel(value: string): string {
  return EVENT_LABEL[value] ?? value;
}

export function StatementPage({ path }: { path: string }) {
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
        ? " A origem ficou registrada como declaração do operador, sem validação automática do Mercado Pago."
        : " A referência do arquivo conferiu com o vínculo gravado, sem consulta ao Mercado Pago.";
      setNotice(
        `Gravação concluída. Criadas: ${result.created}. Enriquecidas: ${result.enriched}. Inalteradas: ${result.unchanged}. Não importadas: ${result.notImported}. Nenhuma conciliação foi confirmada.${attestation}`,
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
        hint="Observação da conta da empresa. O relatório de liquidação usa ponto e vírgula, moeda nas colunas e a data de aprovação. O CSV de laboratório, com vírgula, continua separado e não é o formato real. Confirmar a importação não concilia nem cria saldo."
        action={
          canWriteAccounts() ? (
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
          ) : null
        }
      />
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
          De
          <input type="date" value={from} onChange={(event) => { setFrom(event.target.value); setPageIndex(0); }} />
        </label>
        <label>
          Até
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
          <p>Esta conta ainda não tem referência externa. O vínculo é sintético neste laboratório e não guarda segredo.</p>
          <label>
            Referência externa
            <input value={externalRef} onChange={(event) => setExternalRef(event.target.value)} />
          </label>
          <label>
            Procedência
            <input value={provenance} onChange={(event) => setProvenance(event.target.value)} />
          </label>
          <button type="submit" disabled={busy}>Gravar vínculo</button>
        </form>
      ) : null}
      {linked ? <p className="hint">Referência vinculada: {links.find((item) => item.accountId === accountId)?.externalRef}. O vínculo não consulta o Mercado Pago. A iniciativa permanece não atribuída.</p> : null}
      {preview ? (
        <PreviewPanel
          preview={preview}
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
          <p className="statement-totals">
            {page.totalBasisText ?? "Soma do líquido dos eventos de fluxo monetário confirmados neste perfil. Não é variação do saldo total nem do disponível."} Entradas de fluxo: {formatMinor(page.creditMinor)} ({page.creditCount}). Saídas de fluxo: {formatMinor(page.debitMinor)} ({page.debitCount}). Líquidos ausentes: {page.amountAbsentCount}. Os totais valem para o filtro inteiro.
          </p>
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
                <span>Criadas {batch.createdCount}, enriquecidas {batch.enrichedCount}, inalteradas {batch.unchangedCount}, não importadas {batch.rejectedCount}.</span>
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
  selected,
  evidence,
  busy,
  onEvidence,
  onToggle,
  onConfirm,
  onCancel,
}: {
  preview: Preview;
  selected: number[];
  evidence: string;
  busy: boolean;
  onEvidence: (value: string) => void;
  onToggle: (lineNumber: number, checked: boolean) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <section className="statement-preview" aria-label="Prévia do arquivo">
      <h2>Prévia</h2>
      <p>Perfil {preview.profileId}. Período lido: {formatDateBr(preview.periodFrom)} – {formatDateBr(preview.periodTo)}. Nenhuma linha foi gravada.</p>
      {preview.fileDiagnostic ? <p className="error" role="alert">{preview.fileDiagnostic}</p> : null}
      {preview.blockReason && preview.blockReason !== preview.fileDiagnostic ? <p className="error" role="alert">{preview.blockReason}</p> : null}
      {preview.issues.length > 0 ? (
        <ul>
          {preview.issues.map((issue) => (
            <li key={`${issue.lineNumber}-${issue.code}-${issue.message}`}>Linha {issue.lineNumber}: {issue.message}</li>
          ))}
        </ul>
      ) : null}
      <table className="desktop-table statement-table">
        <thead>
          <tr>
            <th>Importar</th>
            <th>Data</th>
            <th>Descrição</th>
            <th>Tipo</th>
            <th>Direção</th>
            <th className="num">Valor</th>
          </tr>
        </thead>
        <tbody>
          {preview.rows.map((row) => (
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
              <td>{formatDateBr(row.effectiveOn)}</td>
              <td className="desc">{row.description || "Sem descrição"}</td>
              <td>{eventLabel(row.eventKind)}</td>
              <td>{directionLabel(row.direction)}</td>
              <td className="num">{money(row.netMinor, row.netAbsent, !preview.currencyAssumed)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="cards statement-cards">
        {preview.rows.map((row) => (
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
            <p className="desc">{row.description || "Sem descrição"}</p>
            <p>{directionLabel(row.direction)} · {eventLabel(row.eventKind)}{row.eligible ? "" : " · Não importável"}</p>
          </li>
        ))}
      </ul>
      {preview.accountEvidenceRequired ? (
        <label>
          Declaração do operador sobre a origem do arquivo. Não valida a conta no Mercado Pago.
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
  const [error, setError] = useState("");
  useEffect(() => {
    void request<Line>(`/api/v1/statement-lines/${id}?${companyQuery()}`)
      .then(setLine)
      .catch((caught: ApiError) => setError(caught.message));
  }, [id]);
  if (error) {
    return <p className="error" role="alert">{error}</p>;
  }
  if (!line) {
    return <p className="hint">Carregando linha…</p>;
  }
  return (
    <section className="statement">
      <PageHeader title="Linha do extrato" hint="Observação externa. A sugestão não quita o recebimento." action={<button type="button" className="secondary" onClick={() => navigate("/financial-accounts/statement")}>Voltar</button>} />
      <dl className="facts">
        <div><dt>Data</dt><dd>{formatDateBr(line.effectiveOn)}</dd></div>
        <div><dt>Descrição</dt><dd className="desc">{line.description || "Sem descrição"}</dd></div>
        <div><dt>Direção</dt><dd>{directionLabel(line.direction)}</dd></div>
        <div><dt>Tipo</dt><dd>{eventLabel(line.eventKind)}</dd></div>
        <div><dt>Bruto</dt><dd>{money(line.grossMinor, line.grossAbsent)}</dd></div>
        <div><dt>Tarifa</dt><dd>{money(line.feeMinor, line.feeAbsent)}</dd></div>
        <div><dt>Líquido</dt><dd>{money(line.netMinor, line.netAbsent)}</dd></div>
        <div><dt>Classificação</dt><dd>Não classificada</dd></div>
        <div><dt>Iniciativa</dt><dd>Não atribuída</dd></div>
        <div><dt>Efeito</dt><dd>{line.balanceEffect === "AVAILABILITY_ONLY" ? "Só disponibilidade, sem nova receita" : line.balanceEffect === "AFFECTS" ? "Entra na soma do fluxo monetário" : "Efeito ainda não definido"}</dd></div>
      </dl>
      <p className="hint">A data gravada é a de aprovação no relatório de liquidação e a data do arquivo no CSV de laboratório. A tarifa desta linha não é somada de novo ao líquido.</p>
      {!line.grossAbsent && !line.feeAbsent && !line.netAbsent && line.grossMinor != null && line.feeMinor != null && line.netMinor != null && line.grossMinor - line.feeMinor !== (line.direction === "OUT" ? -line.netMinor : line.netMinor) && line.grossMinor + line.feeMinor !== (line.direction === "OUT" ? -line.netMinor : line.netMinor) ? (
        <p>Bruto, tarifa e líquido foram preservados como vieram no arquivo. A diferença não foi ajustada.</p>
      ) : null}
      <h2>Sugestões</h2>
      {line.suggestions.length === 0 ? <p>Sem sugestão.</p> : (
        <ul>
          {line.suggestions.map((item) => (
            <li key={`${item.receiptId}-${item.namespace}`}>
              {item.strength === "WEAK" ? "Sugestão fraca" : "Candidato qualificado"}. {item.reason} {item.divergence}
            </li>
          ))}
        </ul>
      )}
      {line.originalRows && line.originalRows.length > 0 ? (
        <details>
          <summary>Linha original do arquivo</summary>
          {line.originalRows.map((raw) => <p key={raw} className="desc">{raw}</p>)}
        </details>
      ) : null}
    </section>
  );
}
