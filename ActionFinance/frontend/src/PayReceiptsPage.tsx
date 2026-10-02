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
};

const emptyFilters = (): ReceiptFilters => ({ q: "", from: "", to: "", status: "", pending: "" });

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
    case "EMPTY":
      return "Sincronização concluída";
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

function paidText(item: PayReceiptItem) {
  if (item.paidAmountAbsent || item.paidAmountMinor == null) {
    return "Não informado";
  }
  return formatMinor(item.paidAmountMinor);
}

function dayOf(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "";
}

function isPending(item: PayReceiptItem) {
  return item.classification === "INDETERMINATE" || item.paidAmountAbsent === true || item.reviewRequired;
}

function pendingText(item: PayReceiptItem) {
  if (item.classification === "INDETERMINATE") {
    return "Falta evidência de ambiente";
  }
  if (item.paidAmountAbsent) {
    return "Valor pago não informado";
  }
  if (item.reviewRequired) {
    return "Em revisão na origem";
  }
  return "Nenhuma";
}

function matchesFilters(item: PayReceiptItem, filters: ReceiptFilters) {
  if (filters.q.trim()) {
    const needle = filters.q.trim().toLowerCase();
    const hay = [item.orderReference, item.transactionId, item.processorReference]
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
      <section className="pay-receipts pay-receipts-detail">
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
        </dl>
        {detail.item.classification === "INDETERMINATE" || detail.item.paidAmountAbsent ? (
          <section className="pending-box" aria-label="Pendência">
            <p>
              <strong>
                {detail.item.paidAmountAbsent ? "Valor pago não informado" : "Falta evidência de ambiente"}
              </strong>
            </p>
            <p>
              {detail.item.classification === "INDETERMINATE"
                ? "O registro fica fora do total operacional. A atualização lê a empresa na origem, não este item sozinho."
                : "A atualização lê a empresa na origem, não este item sozinho."}
            </p>
          </section>
        ) : null}
        <details>
          <summary>Dados do recebimento</summary>
          <dl className="facts">
            <div>
              <dt>Empresa</dt>
              <dd>{companyName}</dd>
            </div>
            <div>
              <dt>Contraparte</dt>
              <dd>Não informado</dd>
            </div>
            <div>
              <dt>Pedido / referência comercial</dt>
              <dd>
                <CompactRef value={detail.item.orderReference} />
              </dd>
            </div>
            <div>
              <dt>Transação na origem</dt>
              <dd>
                <CompactRef value={detail.item.transactionId} />
              </dd>
            </div>
            <div>
              <dt>Nome do processador</dt>
              <dd>Não informado</dd>
            </div>
            <div>
              <dt>ID da transação no processador</dt>
              <dd>{detail.item.processorReference ? <CompactRef value={detail.item.processorReference} /> : "Não informado"}</dd>
            </div>
            <div>
              <dt>Método</dt>
              <dd>Não informado</dd>
            </div>
            <div>
              <dt>Conta de destino</dt>
              <dd>Não informado</dd>
            </div>
            <div>
              <dt>Identificação de teste</dt>
              <dd>{detail.item.testLabeled ? "Dado de teste" : "Não rotulado como teste"}</dd>
            </div>
            <div>
              <dt>Classificação</dt>
              <dd>{classificationLabel(detail.item.classification)}</dd>
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
        </details>
        <details>
          <summary>Rastreio</summary>
          <dl className="facts">
            <div>
              <dt>Conexão</dt>
              <dd>Detalhe técnico da conexão. Ambiente da observação: {detail.item.environment || "Não informado"}.</dd>
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
    <section className="pay-receipts" data-state={loading ? "loading" : run?.status?.toLowerCase() || "empty"}>
      <PageHeader
        title="Recebimentos ActionHub Pay"
        hint="Sistema integrado. Não substitui o registro manual em A receber. Importar não cria título, não baixa e não altera saldo."
        action={
          canWrite() ? (
            <button type="button" onClick={() => void synchronize()} disabled={busy || loading}>
              {busy ? "Sincronizando…" : "Sincronizar"}
            </button>
          ) : (
            <p className="hint">Somente o perfil autorizado inicia a sincronização.</p>
          )
        }
      />
      {loading ? <p role="status">Carregando recebimentos…</p> : null}
      {error ? (
        <p role="alert" className="error" data-tone="danger">
          {error}
        </p>
      ) : null}
      {run ? (
        <p className={`sync-line${run.status === "FAILED" || run.status === "PARTIAL" ? " tone-warn" : ""}`}>
          {runLabel(run.status)}
          {run.status === "EMPTY" ? " · nenhum item novo" : ""}
          {" · "}
          {collection.length} registro{collection.length === 1 ? "" : "s"}
          {pendingNow > 0 ? ` · ${pendingNow} pendência${pendingNow === 1 ? "" : "s"}` : ""}
          {run.monitorUrl ? (
            <>
              {" · "}
              <a className="btn-link" href={run.monitorUrl} target="_blank" rel="noreferrer">
                Ver execução na Spider
              </a>
            </>
          ) : null}
        </p>
      ) : !loading ? (
        <p className="sync-line">Nenhuma sincronização ainda.</p>
      ) : null}
      {!loading && data && pendingNow > 0 && !run ? (
        <p className="sync-line pending-now">
          {pendingNow} pendência{pendingNow === 1 ? "" : "s"} — sem evidência de ambiente ou sem valor pago.
        </p>
      ) : null}
      <form
        className="filter-grid"
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
        <label>
          Atualização na origem, de
          <input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} />
        </label>
        <label>
          Atualização na origem, até
          <input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} />
        </label>
        <label>
          Situação na origem
          <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <option value="">Todas as situações presentes</option>
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
        <button
          type="button"
          className="secondary"
          onClick={() => setFilters(emptyFilters())}
          disabled={!filters.q && !filters.from && !filters.to && !filters.status && !filters.pending}
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
            <thead>
              <tr>
                <th>Origem / referência</th>
                <th>Contraparte</th>
                <th>Atualização na origem</th>
                <th className="num">Cobrado</th>
                <th className="num">Pago</th>
                <th>Situação</th>
                <th>Pendência</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <tr key={item.id} className={isPending(item) ? "is-pending" : undefined}>
                  <td>
                    <span className="origin-label">ActionHub Pay</span>
                    <button type="button" className="btn-link" onClick={() => onNavigate(`/pay-receipts/${item.id}`)}>
                      Abrir
                    </button>
                    <CompactRef value={item.orderReference} />
                  </td>
                  <td>Não informado</td>
                  <td>{item.originUpdatedAt ? formatDateBr(item.originUpdatedAt) : "Não informada"}</td>
                  <td className="num">{amountText(item)}</td>
                  <td className="num">{paidText(item)}</td>
                  <td>
                    <span className="status status--open">{statusLabel(item.normalizedStatus)}</span>
                  </td>
                  <td>{pendingText(item)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pay-receipts-cards">
            {visible.map((item) => (
              <article key={item.id} className={isPending(item) ? "pay-receipt-card is-pending" : "pay-receipt-card"}>
                <p className="origin-label">ActionHub Pay</p>
                <p>
                  <button type="button" className="btn-link" onClick={() => onNavigate(`/pay-receipts/${item.id}`)}>
                    Abrir recebimento
                  </button>
                </p>
                <CompactRef value={item.orderReference} />
                <p>Contraparte: Não informado</p>
                <p>Atualização na origem: {item.originUpdatedAt ? formatDateBr(item.originUpdatedAt) : "Não informada"}</p>
                <p className="money">Cobrado: {amountText(item)}</p>
                <p className="money">Pago: {paidText(item)}</p>
                <p>{statusLabel(item.normalizedStatus)}</p>
                <p>{pendingText(item)}</p>
                <p>{item.testLabeled ? "Dado de teste" : "Não rotulado como teste"}</p>
              </article>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
