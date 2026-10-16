import { useCallback, useEffect, useMemo, useState } from "react";
import {
  loadPayReceiptDetail,
  loadPayReceipts,
  syncPayReceipts,
  type ApiError,
  type PayReceiptItem,
  type PayReceiptOverview,
  type PayReceiptRun,
} from "./api";
import { formatDateBr, formatMinor } from "./money";
import { canWrite, getSession } from "./session";
import { CompactRef } from "./ui/CompactRef";
import { PageHeader } from "./ui/PageHeader";

const FILTER_KEY = "af.payReceiptFilters";

type ReceiptFilters = {
  q: string;
  from: string;
  to: string;
  status: string;
  pending: string;
  application: string;
  method: string;
};

const emptyFilters = (): ReceiptFilters => ({
  q: "",
  from: "",
  to: "",
  status: "",
  pending: "",
  application: "",
  method: "",
});

function readFilters(): ReceiptFilters {
  const next = emptyFilters();
  const params = new URLSearchParams(window.location.search);
  let fromStore: Partial<ReceiptFilters> = {};
  try {
    const stored = sessionStorage.getItem(FILTER_KEY);
    fromStore = stored ? (JSON.parse(stored) as Partial<ReceiptFilters>) : {};
  } catch {
    fromStore = {};
  }
  next.q = params.get("q") ?? fromStore.q ?? "";
  next.from = params.get("from") ?? fromStore.from ?? "";
  next.to = params.get("to") ?? fromStore.to ?? "";
  next.status = params.get("status") ?? fromStore.status ?? "";
  next.pending = params.get("pending") ?? fromStore.pending ?? "";
  next.application = params.get("application") ?? fromStore.application ?? "";
  next.method = params.get("method") ?? fromStore.method ?? "";
  return next;
}

function persistFilters(filters: ReceiptFilters) {
  sessionStorage.setItem(FILTER_KEY, JSON.stringify(filters));
  if (!window.location.pathname.startsWith("/pay-receipts") || window.location.pathname !== "/pay-receipts") {
    return;
  }
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.status) params.set("status", filters.status);
  if (filters.pending) params.set("pending", filters.pending);
  if (filters.application) params.set("application", filters.application);
  if (filters.method) params.set("method", filters.method);
  const search = params.toString();
  const next = search ? `/pay-receipts?${search}` : "/pay-receipts";
  if (`${window.location.pathname}${window.location.search}` !== next) {
    window.history.replaceState(null, "", next);
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "CONFIRMED":
      return "Aprovado na origem";
    case "IN_PROGRESS":
      return "Pendente na origem";
    case "REFUNDED":
      return "Reembolsado na origem";
    case "REFUSED":
      return "Recusado na origem";
    case "REVIEW_REQUIRED":
      return "Em revisão";
    default:
      return status || "Não informado";
  }
}

function runLabel(status: string) {
  switch (status) {
    case "SUCCESS":
      return "Sincronização concluída";
    case "EMPTY":
      return "Sincronização sem alteração";
    case "PARTIAL":
      return "Sincronização parcial — é possível retomar";
    case "FAILED":
      return "Sincronização indisponível";
    case "RUNNING":
      return "Sincronizando…";
    default:
      return status;
  }
}

function classificationLabel(value?: string | null) {
  switch (value) {
    case "REAL":
      return "Operação real comprovada";
    case "TEST":
      return "Teste comprovado";
    case "INDETERMINATE":
      return "Indeterminada — sem evidência de ambiente";
    default:
      return value || "Não informada";
  }
}

function amountText(item: PayReceiptItem) {
  if (item.amountAbsent || item.amountMinor == null) {
    return "Não informado";
  }
  return formatMinor(item.amountMinor);
}

function paidMissing(item: PayReceiptItem) {
  return item.paidAmountAbsent === true || item.paidAmountMinor == null;
}

function paidText(item: PayReceiptItem) {
  if (paidMissing(item)) {
    return "Não informado";
  }
  return formatMinor(item.paidAmountMinor);
}

function pendingKindOf(item: PayReceiptItem) {
  if (item.pendingKind) {
    return item.pendingKind;
  }
  if (item.classification === "INDETERMINATE") {
    return "ENVIRONMENT_UNPROVEN";
  }
  if (item.normalizedStatus === "CONFIRMED" && paidMissing(item)) {
    return "PAID_AMOUNT_MISSING";
  }
  if (paidMissing(item) && (item.normalizedStatus === "IN_PROGRESS" || item.normalizedStatus === "REFUSED" || item.normalizedStatus === "REFUNDED")) {
    return "UNPAID_EXPECTED";
  }
  if (item.reviewRequired) {
    return "ORIGIN_REVIEW";
  }
  return "NONE";
}

function dayOf(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "";
}

function isPending(item: PayReceiptItem) {
  const kind = pendingKindOf(item);
  return kind === "ENVIRONMENT_UNPROVEN" || kind === "PAID_AMOUNT_MISSING" || kind === "ORIGIN_REVIEW";
}

function pendingText(item: PayReceiptItem) {
  switch (pendingKindOf(item)) {
    case "ENVIRONMENT_UNPROVEN":
      return "Falta evidência de ambiente";
    case "PAID_AMOUNT_MISSING":
      return "Valor pago não informado";
    case "ORIGIN_REVIEW":
      return "Em revisão na origem";
    case "UNPAID_EXPECTED":
      return "Pagamento ainda não confirmado";
    default:
      return "Nenhuma";
  }
}

const CHECKOUT_TECHNICAL_DOMAIN = "@amount.hub.local";

function isCheckoutTechnicalIdentity(label: string | null | undefined) {
  return Boolean(label && label.toLowerCase().endsWith(CHECKOUT_TECHNICAL_DOMAIN));
}

function applicationName(code: string | null | undefined) {
  if (!code) {
    return "Não informada";
  }
  if (code === "lojadepaes") {
    return "Loja de Pães";
  }
  return code;
}

function methodName(method: string | null | undefined) {
  if (!method) {
    return "Não informado";
  }
  if (method.toLowerCase() === "pix") {
    return "Pix";
  }
  return method;
}

function payerHeadline(item: PayReceiptItem) {
  if (!item.payerLabel || item.payerKind === "ABSENT" || isCheckoutTechnicalIdentity(item.payerLabel)) {
    return "Pagador não identificado";
  }
  if (item.payerKind === "EMAIL") {
    return item.payerLabel;
  }
  return "Identificação recebida";
}

function payerContact(item: PayReceiptItem) {
  if (!item.payerLabel || isCheckoutTechnicalIdentity(item.payerLabel) || item.payerKind === "ABSENT") {
    return null;
  }
  if (item.payerKind === "EMAIL") {
    return "E-mail informado pelo ActionHub Pay";
  }
  return item.payerLabel;
}

function countWords(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function matchesFilters(item: PayReceiptItem, filters: ReceiptFilters) {
  if (filters.q.trim()) {
    const needle = filters.q.trim().toLowerCase();
    const hay = [
      item.orderReference,
      item.transactionId,
      item.processorReference,
      item.payerLabel,
      item.commercialApplication,
      applicationName(item.commercialApplication),
      item.commercialDescription,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    if (!hay.includes(needle)) {
      return false;
    }
  }
  if (filters.status && item.normalizedStatus !== filters.status) {
    return false;
  }
  if (filters.application && item.commercialApplication !== filters.application) {
    return false;
  }
  if (filters.method && item.paymentMethod !== filters.method) {
    return false;
  }
  if (filters.pending === "yes" && !isPending(item)) {
    return false;
  }
  if (filters.pending === "no" && isPending(item)) {
    return false;
  }
  const day = dayOf(item.originUpdatedAt);
  if (filters.from && (!day || day < filters.from)) {
    return false;
  }
  if (filters.to && (!day || day > filters.to)) {
    return false;
  }
  return true;
}

export function PayReceiptsPage({
  path,
  onNavigate,
}: {
  path: string;
  onNavigate: (to: string) => void;
}) {
  const detailId = path.match(/^\/pay-receipts\/([^/]+)$/)?.[1] ?? null;
  const [data, setData] = useState<PayReceiptOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [filters, setFilters] = useState<ReceiptFilters>(() => readFilters());
  const [detail, setDetail] = useState<{
    item: PayReceiptItem;
    history: Array<{
      id: string;
      observedAt: string;
      originalStatus: string | null;
      normalizedStatus: string;
      amountMinor: string | null;
      currency: string | null;
      reviewRequired: boolean;
      originRevision: string | null;
      correlationId: string | null;
    }>;
    run: PayReceiptRun | null;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setDenied(false);
    try {
      setData(await loadPayReceipts());
    } catch (caught) {
      const api = caught as ApiError;
      if (api.status === 403) {
        setDenied(true);
      } else {
        setError(api.message || "Não foi possível carregar os recebimentos importados.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    persistFilters(filters);
  }, [filters]);

  useEffect(() => {
    if (!detailId) {
      setDetail(null);
      return;
    }
    void loadPayReceiptDetail(detailId)
      .then((body) => setDetail({ item: body.item, history: body.history, run: body.run }))
      .catch(() => setError("Não foi possível abrir o detalhe deste recebimento."));
  }, [detailId]);

  async function synchronize() {
    setBusy(true);
    setError("");
    try {
      const result = await syncPayReceipts(data?.environment);
      setData({
        environment: result.run.environment,
        homolog: data?.environment === "PRODUCTION" ? false : true,
        createsFinancialMovement: false,
        latestRun: result.run,
        items: result.items,
        reviews: result.reviews || [],
      });
      await load();
    } catch (caught) {
      const api = caught as ApiError;
      if (api.status === 409) {
        setError(api.message || "Já existe uma sincronização em andamento.");
      } else if (api.status === 403) {
        setDenied(true);
      } else {
        setError(api.message || "A sincronização falhou. Os itens já importados foram preservados.");
        await load();
      }
    } finally {
      setBusy(false);
    }
  }

  const collection = useMemo(() => {
    const items = data?.items ?? [];
    const reviews = data?.reviews ?? [];
    const seen = new Set<string>();
    return [...items, ...reviews].filter((item) => {
      if (seen.has(item.id)) {
        return false;
      }
      seen.add(item.id);
      return true;
    });
  }, [data]);

  const visible = useMemo(() => collection.filter((item) => matchesFilters(item, filters)), [collection, filters]);
  const pendingNow = collection.filter(isPending).length;
  const statuses = useMemo(() => Array.from(new Set(collection.map((item) => item.normalizedStatus).filter(Boolean))).sort(), [collection]);
  const applications = useMemo(
    () => Array.from(new Set(collection.map((item) => item.commercialApplication).filter(Boolean) as string[])).sort(),
    [collection],
  );
  const methods = useMemo(
    () => Array.from(new Set(collection.map((item) => item.paymentMethod).filter(Boolean) as string[])).sort(),
    [collection],
  );

  if (denied) {
    return (
      <section className="pay-receipts" data-state="denied">
        <PageHeader title="Recebimentos ActionHub Pay" />
        <p role="alert">Acesso negado para esta empresa.</p>
      </section>
    );
  }

  if (detailId && detail) {
    const companyName = getSession()?.companies?.find((company) => company.id === detail.item.companyId)?.name ?? "Não informado";
    return (
      <section className="pay-receipts pay-receipts-detail fluxo">
        <p>
          <button type="button" className="btn-link" onClick={() => onNavigate("/pay-receipts")}>
            Voltar aos recebimentos
          </button>
        </p>
        <PageHeader
          title="Recebimento observado"
          hint="ActionHub Pay · observação externa. Aprovado na origem não é baixa nem saldo disponível."
          action={
            canWrite() ? (
              <button type="button" className="secondary" onClick={() => void synchronize()} disabled={busy}>
                {busy ? "Sincronizando…" : "Atualizar da origem"}
              </button>
            ) : null
          }
        />
        <dl className="value-band">
          <div>
            <dt>Valor cobrado</dt>
            <dd className="money">{amountText(detail.item)}</dd>
          </div>
          <div>
            <dt>Valor pago</dt>
            <dd className="money">{paidText(detail.item)}</dd>
          </div>
          <div>
            <dt>Situação na origem</dt>
            <dd>{statusLabel(detail.item.normalizedStatus)}</dd>
          </div>
          <div>
            <dt>Pendência</dt>
            <dd>{pendingText(detail.item)}</dd>
          </div>
        </dl>
        <dl className="facts receipt-essentials">
          <div>
            <dt>Aplicação</dt>
            <dd>{applicationName(detail.item.commercialApplication)}</dd>
          </div>
          <div>
            <dt>Descrição</dt>
            <dd>{detail.item.commercialDescription || "Não informada"}</dd>
          </div>
          <div>
            <dt>Pagador</dt>
            <dd>
              {payerHeadline(detail.item)}
              {payerContact(detail.item) ? <span className="hint"> · {payerContact(detail.item)}</span> : null}
            </dd>
          </div>
          <div>
            <dt>Sistema integrado</dt>
            <dd>ActionHub Pay</dd>
          </div>
          <div>
            <dt>Método</dt>
            <dd>{methodName(detail.item.paymentMethod)}</dd>
          </div>
          <div>
            <dt>Processador</dt>
            <dd>{detail.item.processorName || "Não evidenciado pela origem"}</dd>
          </div>
          <div>
            <dt>Situação no processador</dt>
            <dd>{detail.item.providerStatus || "Não informada"}</dd>
          </div>
          <div>
            <dt>Atualização na origem</dt>
            <dd>{detail.item.originUpdatedAt ? formatDateBr(detail.item.originUpdatedAt) : "Não informada"}</dd>
          </div>
          <div>
            <dt>Criação na origem</dt>
            <dd>{detail.item.originCreatedAt ? formatDateBr(detail.item.originCreatedAt) : "Não informada"}</dd>
          </div>
        </dl>
        {isPending(detail.item) ? (
          <section className="pending-box" aria-label="Pendência">
            <p>
              <strong>{pendingText(detail.item)}</strong>
            </p>
            <p>
              {pendingKindOf(detail.item) === "ENVIRONMENT_UNPROVEN"
                ? "O registro fica fora do total operacional. A atualização lê a empresa na origem, não este item sozinho."
                : "A atualização lê a empresa na origem, não este item sozinho. Aprovado na origem não é baixa nem saldo disponível."}
            </p>
          </section>
        ) : null}
        <details>
          <summary>Rastreio técnico</summary>
          <dl className="facts">
            <div>
              <dt>Referência do recebimento</dt>
              <dd>
                <CompactRef value={detail.item.orderReference || detail.item.transactionId} copyLabel="Copiar referência" />
              </dd>
            </div>
            {isCheckoutTechnicalIdentity(detail.item.payerLabel) ? (
              <div>
                <dt>Referência técnica do checkout</dt>
                <dd>
                  <CompactRef value={detail.item.payerLabel || ""} copyLabel="Copiar referência" />
                  <span className="hint">
                    {" "}
                    Identificador gerado pelo checkout avulso para o cadastro interno. Não é endereço de contato.
                  </span>
                </dd>
              </div>
            ) : null}
            <div>
              <dt>Código da aplicação</dt>
              <dd>{detail.item.commercialApplication || "Não informado"}</dd>
            </div>
            <div>
              <dt>Empresa no Finance</dt>
              <dd>{companyName}</dd>
            </div>
            <div>
              <dt>Referência do pedido</dt>
              <dd>
                <CompactRef value={detail.item.orderReference} />
              </dd>
            </div>
            <div>
              <dt>ID da transação no processador</dt>
              <dd>{detail.item.processorReference ? <CompactRef value={detail.item.processorReference} /> : "Não informado pela origem"}</dd>
            </div>
            <div>
              <dt>Conta de destino</dt>
              <dd>Não coletada neste contrato — distinta do recebedor no processador</dd>
            </div>
            <div>
              <dt>Classificação de ambiente</dt>
              <dd>{classificationLabel(detail.item.classification)}</dd>
            </div>
            <div>
              <dt>Identificação de teste</dt>
              <dd>{detail.item.testLabeled ? "Dado de teste" : "Não rotulado como teste"}</dd>
            </div>
            <div>
              <dt>Ambiente da observação</dt>
              <dd>{detail.item.environment || "Não informado"}</dd>
            </div>
            <div>
              <dt>Revisão técnica da origem</dt>
              <dd>{detail.item.originRevision || "Não informada"}</dd>
            </div>
            <div>
              <dt>Motivo da classificação</dt>
              <dd>{detail.item.classificationReason || "Não informado"}</dd>
            </div>
            <div>
              <dt>Correlação</dt>
              <dd>{detail.item.lastCorrelationId || "Não informada"}</dd>
            </div>
          </dl>
          {detail.run?.monitorUrl ? (
            <p>
              <a className="btn-link" href={detail.run.monitorUrl} target="_blank" rel="noreferrer">
                Ver execução na Spider
              </a>
            </p>
          ) : null}
        </details>
        <details>
          <summary>Histórico</summary>
          {detail.history.length === 0 ? (
            <p>Nenhuma revisão gravada.</p>
          ) : (
            <ol className="history">
              {detail.history.map((row) => (
                <li key={row.id}>
                  {formatDateBr(row.observedAt)} · {statusLabel(row.normalizedStatus)} ·{" "}
                  {row.amountMinor == null ? "Não informado" : formatMinor(row.amountMinor)}
                </li>
              ))}
            </ol>
          )}
        </details>
      </section>
    );
  }

  const run = data?.latestRun;
  return (
    <section className="pay-receipts fluxo" data-state={loading ? "loading" : run?.status?.toLowerCase() || "empty"}>
      <PageHeader
        title="Recebimentos ActionHub Pay"
        hint="Informações recebidas do ActionHub Pay. Não são o extrato da conta nem valores já conciliados. Não criam título, não baixam obrigação e não alteram saldo. O total armazenado não entra no realizado do livro."
        action={
          canWrite() && data?.receiptSyncSuspended !== true ? (
            <button type="button" onClick={() => void synchronize()} disabled={busy || loading}>
              {busy ? "Sincronizando…" : "Sincronizar"}
            </button>
          ) : data?.receiptSyncSuspended === true ? (
            <p className="hint">Sincronismo temporariamente suspenso durante a migração da Spider.</p>
          ) : (
            <p className="hint">Somente o perfil autorizado inicia a sincronização.</p>
          )
        }
      />
      {data?.receiptSyncSuspended ? (
        <p role="status" className="sync-line tone-warn">
          Sincronismo temporariamente suspenso durante a migração da Spider. Os registros abaixo são dados armazenados, não o resultado de uma tentativa atual.
        </p>
      ) : null}
      {loading ? <p role="status">Carregando recebimentos…</p> : null}
      {error ? (
        <p role="alert" className="error" data-tone="danger">
          {error}
        </p>
      ) : null}
      {run ? (
        <div className={`sync-line${run.status === "FAILED" || run.status === "PARTIAL" ? " tone-warn" : ""}`}>
          <p>
            {runLabel(run.status)}
            {run.status === "EMPTY"
              ? run.pageCount > 0
                ? " · a origem respondeu e nenhum campo novo foi gravado"
                : " · a origem não devolveu registros"
              : ""}
            {run.status === "FAILED" || run.status === "PARTIAL"
              ? ` às ${formatDateBr(run.finishedAt || run.startedAt)}`
              : ""}
          </p>
          {run.status === "FAILED" || run.status === "PARTIAL" ? (
            <p>
              Última tentativa: {run.status === "FAILED" ? "rejeitada pela Spider" : "parcial"} às{" "}
              {formatDateBr(run.finishedAt || run.startedAt)}
              {run.lastError ? ` — ${run.lastError}` : ""}
            </p>
          ) : null}
          {data?.lastSuccessfulRun ? (
            <p>Última sincronização concluída: {formatDateBr(data.lastSuccessfulRun.finishedAt || data.lastSuccessfulRun.startedAt)}</p>
          ) : null}
          <p>
            {countWords(collection.length, "registro", "registros")}
            {pendingNow > 0 ? ` · ${countWords(pendingNow, "com pendência", "com pendências")}` : ""}
          </p>
          {run.status === "SUCCESS" ? (
            <p>
              Última tentativa: {countWords(run.importedCount, "incluído", "incluídos")} ·{" "}
              {countWords(run.updatedCount, "atualizado", "atualizados")}
            </p>
          ) : null}
          {(run.status === "FAILED" || run.status === "PARTIAL") && (run.importedCount ?? 0) === 0 ? (
            <p>Nenhum dado novo foi importado nesta tentativa. Os registros acima já estavam armazenados.</p>
          ) : null}
          <p className="sync-meta">
            Ambiente: {data?.environment || run.environment || "não informado"}
            {data?.homolog ? " · origem sandbox/homologação" : ""}
            {run.monitorUrl ? (
              <>
                {" · "}
                <a className="btn-link" href={run.monitorUrl} target="_blank" rel="noreferrer">
                  Ver execução na Spider
                </a>
              </>
            ) : null}
          </p>
        </div>
      ) : !loading ? (
        <p className="sync-line">Nenhuma sincronização ainda.</p>
      ) : null}
      {!loading && data && pendingNow > 0 && !run ? (
        <p className="sync-line pending-now">
          {pendingNow} pendência{pendingNow === 1 ? "" : "s"} — sem evidência de ambiente ou sem valor pago.
        </p>
      ) : null}
      <div className="pv-layout">
      <div>
      <form
        className="receipt-filters"
        onSubmit={(event) => {
          event.preventDefault();
        }}
      >
        <label>
          Buscar referência
          <input
            value={filters.q}
            onChange={(event) => setFilters({ ...filters, q: event.target.value })}
            autoComplete="off"
          />
        </label>
        <div className="receipt-period" role="group" aria-labelledby="origin-period">
          <span id="origin-period">Atualização na origem</span>
          <div>
            <label>
              De
              <input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} />
            </label>
            <label>
              Até
              <input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} />
            </label>
          </div>
        </div>
        <label>
          Situação
          <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <option value="">Todas</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {statusLabel(status)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Pendência
          <select value={filters.pending} onChange={(event) => setFilters({ ...filters, pending: event.target.value })}>
            <option value="">Todas</option>
            <option value="yes">Com pendência</option>
            <option value="no">Sem pendência</option>
          </select>
        </label>
        <label>
          Aplicação
          <select value={filters.application} onChange={(event) => setFilters({ ...filters, application: event.target.value })}>
            <option value="">Todas</option>
            {applications.map((application) => (
              <option key={application} value={application}>
                {applicationName(application)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Método
          <select value={filters.method} onChange={(event) => setFilters({ ...filters, method: event.target.value })}>
            <option value="">Todos</option>
            {methods.map((method) => (
              <option key={method} value={method}>
                {methodName(method)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="secondary filter-clear"
          onClick={() => setFilters(emptyFilters())}
          disabled={
            !filters.q && !filters.from && !filters.to && !filters.status && !filters.pending && !filters.application && !filters.method
          }
        >
          Limpar
        </button>
      </form>
      {!loading && data && collection.length === 0 ? <p>Nenhum recebimento importado para esta empresa.</p> : null}
      {!loading && collection.length > 0 && visible.length === 0 ? (
        <p>Nenhum registro corresponde aos filtros atuais.</p>
      ) : null}
      {visible.length > 0 ? (
        <>
          <table className="desktop-table pay-receipts-table">
            <colgroup>
              <col className="col-receipt" />
              <col className="col-payer" />
              <col className="col-pay" />
              <col className="col-when" />
              <col className="col-values" />
              <col className="col-state" />
              <col className="col-action" />
            </colgroup>
            <thead>
              <tr>
                <th>Recebimento</th>
                <th>Pagador</th>
                <th>Pagamento</th>
                <th>Atualização na origem</th>
                <th className="num">Valores</th>
                <th>Situação</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <tr key={item.id} className={isPending(item) ? "is-pending" : undefined}>
                  <td>
                    <p className="receipt-title">{applicationName(item.commercialApplication)}</p>
                    <p className="receipt-clamp">{item.commercialDescription || "Descrição não informada"}</p>
                    <p className="origin-label receipt-system">ActionHub Pay</p>
                    <p className="receipt-ref">
                      <CompactRef value={item.orderReference || item.transactionId} copyLabel="Copiar referência" />
                    </p>
                  </td>
                  <td>{payerHeadline(item)}</td>
                  <td>
                    <span>{methodName(item.paymentMethod)}</span>
                    {item.processorName ? <span className="origin-label">{item.processorName}</span> : null}
                  </td>
                  <td>{item.originUpdatedAt ? formatDateBr(item.originUpdatedAt) : "Não informada"}</td>
                  <td className="num">
                    <div className="amount-stack">
                      <span>Cobrado {amountText(item)}</span>
                      <span>Pago {paidText(item)}</span>
                    </div>
                  </td>
                  <td>
                    <span className="status status--open">{statusLabel(item.normalizedStatus)}</span>
                    <span className="origin-label">{pendingText(item)}</span>
                  </td>
                  <td>
                    <button type="button" className="btn-link" onClick={() => onNavigate(`/pay-receipts/${item.id}`)}>
                      Abrir detalhes
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pay-receipts-cards">
            {visible.map((item) => (
              <article key={item.id} className={isPending(item) ? "pay-receipt-card is-pending" : "pay-receipt-card"}>
                <p className="receipt-title">{applicationName(item.commercialApplication)}</p>
                <p>{item.commercialDescription || "Descrição não informada"}</p>
                <p className="origin-label">ActionHub Pay</p>
                <p>{statusLabel(item.normalizedStatus)}</p>
                <p>{pendingText(item)}</p>
                <p className="money">Cobrado: {amountText(item)}</p>
                <p className="money">Pago: {paidText(item)}</p>
                <p>Pagador: {payerHeadline(item)}</p>
                <p>
                  Método: {methodName(item.paymentMethod)}
                  {item.processorName ? ` · ${item.processorName}` : ""}
                </p>
                <CompactRef value={item.orderReference || item.transactionId} copyLabel="Copiar referência" />
                <p>
                  <button type="button" className="btn-link" onClick={() => onNavigate(`/pay-receipts/${item.id}`)}>
                    Abrir detalhes
                  </button>
                </p>
              </article>
            ))}
          </div>
        </>
      ) : null}
      </div>
      <aside className="pv-card">
        <h2>Cobertura da integração</h2>
        {loading ? <p role="status">Carregando…</p> : (
          <>
            <p className="pv-metric"><span>Armazenados</span><strong>{collection.length}</strong></p>
            <p className="pv-metric"><span>Com pendência</span><strong>{pendingNow}</strong></p>
            <p>Última tentativa: {run ? formatDateBr(run.finishedAt || run.startedAt) : "Nenhuma"}.</p>
            {run?.status === "SUCCESS" ? (
              <p>Nesta tentativa: {countWords(run.importedCount, "incluído", "incluídos")} e {countWords(run.updatedCount, "atualizado", "atualizados")}. Não é o total armazenado.</p>
            ) : null}
            {run?.status === "EMPTY" ? <p>Sincronização vazia não enriquece os registros antigos.</p> : null}
            <p className="fx-caption">O total armazenado não entra no realizado do livro nem no extrato.</p>
          </>
        )}
      </aside>
      </div>
    </section>
  );
}
