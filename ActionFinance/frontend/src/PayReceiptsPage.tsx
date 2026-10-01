import { useCallback, useEffect, useState } from "react";
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
import { canWrite } from "./session";
import { PageHeader } from "./ui/PageHeader";

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
      return "Concluído sem novidades";
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

function amountText(item: PayReceiptItem) {
  if (item.amountAbsent || item.amountMinor == null) {
    return "Valor não informado";
  }
  return formatMinor(item.amountMinor);
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
        homolog: true,
        createsFinancialMovement: false,
        latestRun: result.run,
        items: result.items,
      });
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

  if (denied) {
    return (
      <section className="pay-receipts" data-state="denied">
        <PageHeader title="Recebimentos do Pay" />
        <p role="alert">Acesso negado para esta empresa.</p>
      </section>
    );
  }

  if (detailId && detail) {
    return (
      <section className="pay-receipts pay-receipts-detail">
        <PageHeader title="Recebimento importado" />
        <p className="hint">Importar não movimenta dinheiro nem baixa título. Aprovado na origem não é saldo disponível.</p>
        <dl className="facts homolog-lookup">
          <div>
            <dt>Referência</dt>
            <dd>{detail.item.orderReference}</dd>
          </div>
          <div>
            <dt>Transação</dt>
            <dd>{detail.item.transactionId}</dd>
          </div>
          <div>
            <dt>Processador</dt>
            <dd>{detail.item.processorReference || "Não informado"}</dd>
          </div>
          <div>
            <dt>Valor</dt>
            <dd>{amountText(detail.item)}</dd>
          </div>
          <div>
            <dt>Situação na origem</dt>
            <dd>{statusLabel(detail.item.normalizedStatus)}</dd>
          </div>
          <div>
            <dt>Ambiente</dt>
            <dd>{detail.item.environment}</dd>
          </div>
          <div>
            <dt>Identificação</dt>
            <dd>{detail.item.testLabeled ? "Dado de teste" : "Não rotulado como teste"}</dd>
          </div>
          <div>
            <dt>Revisão da origem</dt>
            <dd>{detail.item.originRevision ? formatDateBr(detail.item.originRevision) : "Não informada"}</dd>
          </div>
        </dl>
        {detail.run?.monitorUrl ? (
          <p>
            <a className="btn-link" href={detail.run.monitorUrl} target="_blank" rel="noreferrer">
              Ver execução na Spider
            </a>
          </p>
        ) : null}
        <h2>Histórico de atualização</h2>
        {detail.history.length === 0 ? (
          <p>Nenhuma revisão gravada.</p>
        ) : (
          <ol className="history">
            {detail.history.map((row) => (
              <li key={row.id}>
                {formatDateBr(row.observedAt)} · {statusLabel(row.normalizedStatus)} ·{" "}
                {row.amountMinor == null ? "Valor não informado" : formatMinor(row.amountMinor)}
              </li>
            ))}
          </ol>
        )}
      </section>
    );
  }

  const run = data?.latestRun;
  return (
    <section className="pay-receipts" data-state={loading ? "loading" : run?.status?.toLowerCase() || "empty"}>
      <PageHeader title="Recebimentos do Pay" />
      <p className="hint">
        Sincronizar importa transações externas de teste. Não cria título, não baixa e não altera saldo. Testes não entram
        em totais operacionais.
      </p>
      <div className="pay-receipts-toolbar">
        <p>
          Empresa autorizada · ambiente <strong>{data?.environment || "—"}</strong>
        </p>
        {canWrite() ? (
          <button type="button" className="btn-primary" onClick={() => void synchronize()} disabled={busy || loading}>
            {busy ? "Sincronizando…" : "Sincronizar recebimentos"}
          </button>
        ) : (
          <p>Somente o perfil autorizado inicia a sincronização.</p>
        )}
      </div>
      {loading ? <p role="status">Carregando recebimentos…</p> : null}
      {error ? (
        <p role="alert" className="error" data-tone="danger">
          {error}
        </p>
      ) : null}
      {run ? (
        <section className={`sync-result tone-${run.status === "FAILED" || run.status === "PARTIAL" ? "warn" : "info"}`}>
          <p>
            <strong>{runLabel(run.status)}</strong>
          </p>
          <p>
            Importados {run.importedCount} · atualizados {run.updatedCount} · em revisão {run.reviewCount}
          </p>
          {run.lastError ? <p>{run.lastError}</p> : null}
          {run.monitorUrl ? (
            <p>
              <a className="btn-link" href={run.monitorUrl} target="_blank" rel="noreferrer">
                Ver execução na Spider
              </a>
            </p>
          ) : null}
        </section>
      ) : !loading ? (
        <p>Nenhuma sincronização ainda. Os recebimentos importados aparecerão aqui.</p>
      ) : null}
      {!loading && data && data.items.length === 0 ? <p>Nenhum recebimento importado para esta empresa.</p> : null}
      {data && data.items.length > 0 ? (
        <>
          <table className="pay-receipts-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Referência</th>
                <th>Valor</th>
                <th>Situação na origem</th>
                <th>Teste</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.originUpdatedAt ? formatDateBr(item.originUpdatedAt) : "Não informada"}</td>
                  <td>
                    <button type="button" className="btn-link" onClick={() => onNavigate(`/pay-receipts/${item.id}`)}>
                      {item.orderReference}
                    </button>
                  </td>
                  <td>{amountText(item)}</td>
                  <td>
                    <span className="status status--open">{statusLabel(item.normalizedStatus)}</span>
                  </td>
                  <td>{item.testLabeled ? "Teste" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pay-receipts-cards">
            {data.items.map((item) => (
              <article key={item.id} className="pay-receipt-card">
                <p>
                  <button type="button" className="btn-link" onClick={() => onNavigate(`/pay-receipts/${item.id}`)}>
                    {item.orderReference}
                  </button>
                </p>
                <p>{item.originUpdatedAt ? formatDateBr(item.originUpdatedAt) : "Data não informada"}</p>
                <p>{amountText(item)}</p>
                <p>{statusLabel(item.normalizedStatus)}</p>
                <p>{item.testLabeled ? "Dado de teste" : "Sem rótulo de teste"}</p>
              </article>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
