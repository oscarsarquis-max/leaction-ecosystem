import { useState } from "react";
import type { AttendanceBoard, AttendanceSummary, BoardMetric } from "./types";

type Props = {
  data: AttendanceSummary | null;
  loading: boolean;
  error: string | null;
  activeLens: string;
  onRefresh: () => void;
  onSelectLens: (lens: string) => void;
  onOpenHistory?: () => void;
};

type HistoryProps = {
  data: AttendanceSummary | null;
  error: string | null;
  open: boolean;
  activeLens: string;
  onToggle: () => void;
  onSelectLens: (lens: string) => void;
};

function stageTone(lens: string): string {
  if (!lens.startsWith("stage:")) {
    return "";
  }
  return ` is-${lens.slice("stage:".length).replaceAll("_", "-")}`;
}

function Chevron({ open }: { open: boolean }) {
  return <span aria-hidden="true">{open ? "▴" : "▾"}</span>;
}

function MetricLine({
  metric,
  active,
  emphasize = false,
  onSelect,
}: {
  metric: BoardMetric;
  active: boolean;
  emphasize?: boolean;
  onSelect: (lens: string) => void;
}) {
  const quiet = metric.count === 0;
  return (
    <button
      type="button"
      className={`admin-cycle-line${stageTone(metric.lens)}${active ? " is-current" : ""}${quiet ? " is-quiet" : ""}${emphasize && !quiet ? " is-live" : ""}`}
      aria-pressed={active}
      onClick={() => onSelect(metric.lens)}
    >
      <span>{metric.label}</span>
      <span className="admin-cycle-line-count">{metric.count}</span>
      {active ? <span className="admin-board-flag">Filtro ativo</span> : null}
    </button>
  );
}

function StageNode({
  metric,
  active,
  caption,
  onSelect,
}: {
  metric: BoardMetric;
  active: boolean;
  caption?: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={`admin-cycle-step${stageTone(metric.lens)}${active ? " is-current" : ""}`}
      aria-pressed={active}
      onClick={onSelect}
    >
      <span className="admin-cycle-dot">{metric.count}</span>
      <span className="admin-cycle-name">
        {metric.label}
        {caption ? <small>{caption}</small> : null}
        {active ? <small className="admin-board-flag">Filtro ativo</small> : null}
      </span>
    </button>
  );
}

function BoardView({
  board,
  activeLens,
  onSelectLens,
  onOpenHistory,
}: {
  board: AttendanceBoard;
  activeLens: string;
  onSelectLens: (lens: string) => void;
  onOpenHistory?: () => void;
}) {
  const [pendingOpen, setPendingOpen] = useState(false);
  const [payOpen, setPayOpen] = useState(false);
  const delivered = board.history.find((metric) => metric.lens === "stage:delivered");
  const ready = (board.exceptions ?? []).find((metric) => metric.lens === "stage:ready_legacy" && metric.count > 0);

  return (
    <>
      <div className="admin-cycle-track" aria-label="Etapas do pedido">
        {board.stages.map((metric) => (
          <div className="admin-cycle-stop" key={metric.lens}>
            <StageNode
              metric={metric}
              active={activeLens === metric.lens}
              onSelect={() => onSelectLens(metric.lens)}
            />
          </div>
        ))}
        {delivered ? (
          <div className="admin-cycle-stop" key={delivered.lens}>
            <StageNode
              metric={delivered}
              caption="No histórico"
              active={activeLens === delivered.lens}
              onSelect={() => {
                onSelectLens(delivered.lens);
                onOpenHistory?.();
              }}
            />
          </div>
        ) : null}
      </div>

      {ready ? (
        <button
          type="button"
          className={`admin-cycle-ready${activeLens === ready.lens ? " is-current" : ""}`}
          aria-pressed={activeLens === ready.lens}
          onClick={() => onSelectLens(ready.lens)}
        >
          <span>{ready.label}</span>
          <span className="admin-cycle-line-count">{ready.count}</span>
        </button>
      ) : null}

      <div className="admin-cycle-support">
        <button
          type="button"
          className="admin-cycle-toggle"
          aria-expanded={pendingOpen}
          aria-controls="admin-pending-detail"
          onClick={() => setPendingOpen((open) => !open)}
        >
          Pendências <Chevron open={pendingOpen} />
        </button>
        <button
          type="button"
          className="admin-cycle-toggle"
          aria-expanded={payOpen}
          aria-controls="admin-active-pay-detail"
          onClick={() => setPayOpen((open) => !open)}
        >
          Pagamentos dos ativos <Chevron open={payOpen} />
        </button>
      </div>

      <div id="admin-pending-detail" className="admin-cycle-detail" hidden={!pendingOpen}>
        {pendingOpen ? (
          <>
            <p className="admin-muted">{board.pending_note}</p>
            <div className="admin-cycle-lines" aria-label="Pendências">
              {board.pendings.map((metric) => (
                <MetricLine
                  key={metric.lens}
                  metric={metric}
                  active={activeLens === metric.lens}
                  emphasize
                  onSelect={onSelectLens}
                />
              ))}
            </div>
          </>
        ) : null}
      </div>

      <div id="admin-active-pay-detail" className="admin-cycle-detail" hidden={!payOpen}>
        {payOpen ? (
          board.work_payments ? (
            <>
              <p className="admin-muted">
                Estas classes são só dos pedidos vigentes. Pagamento não muda a etapa e não inicia a produção.
              </p>
              <div className="admin-cycle-lines" aria-label="Pagamentos dos ativos">
                {board.work_payments.map((metric) => (
                  <MetricLine
                    key={metric.lens}
                    metric={metric}
                    active={activeLens === metric.lens}
                    onSelect={onSelectLens}
                  />
                ))}
              </div>
              {board.work_payment_orders != null ? (
                <p className="admin-muted">Soma deste recorte: {board.work_payment_orders}.</p>
              ) : null}
            </>
          ) : (
            <p className="admin-error" role="alert">
              O pagamento dos ativos não veio nesta leitura.
            </p>
          )
        ) : null}
      </div>
    </>
  );
}

export function AttendanceSummaryPanel({
  data,
  loading,
  error,
  activeLens,
  onRefresh,
  onSelectLens,
  onOpenHistory,
}: Props) {
  const board = data?.board;
  const zone = board
    ? board.timezone === "America/Sao_Paulo"
      ? "horário de Brasília"
      : board.timezone
    : "";
  return (
    <section className="admin-summary" aria-labelledby="admin-summary-title">
      <div className="admin-summary-head">
        <div>
          <h2 id="admin-summary-title">Ciclo dos pedidos</h2>
          {board ? (
            <p className="admin-ops-now">
              <span className="admin-board-count">{board.operational_total}</span>
              <span>
                vigentes agora
                <span className="admin-muted">
                  {" "}
                  · Atualizado {board.updated_label}, {zone}.
                </span>
              </span>
            </p>
          ) : null}
        </div>
        <div className="admin-cycle-head-actions">
          {activeLens ? (
            <button type="button" className="admin-secondary" onClick={() => onSelectLens("")}>
              Limpar filtro
            </button>
          ) : null}
          <button type="button" className="admin-secondary" onClick={onRefresh} disabled={loading}>
            Atualizar
          </button>
        </div>
      </div>
      {loading && !data ? <p className="admin-muted">Carregando resumo…</p> : null}
      {loading && data ? <p className="admin-muted">Atualizando resumo…</p> : null}
      {error && data ? (
        <p className="admin-error" role="alert">
          A última atualização falhou. Os números abaixo são da leitura anterior e estão
          desatualizados. {error}{" "}
          <button type="button" className="admin-link" onClick={onRefresh}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {error && !data ? (
        <p className="admin-error" role="alert">
          Não foi possível carregar o resumo. {error}{" "}
          <button type="button" className="admin-link" onClick={onRefresh}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {board ? (
        <BoardView
          board={board}
          activeLens={activeLens}
          onSelectLens={onSelectLens}
          onOpenHistory={onOpenHistory}
        />
      ) : data ? (
        <p className="admin-error" role="alert">
          O resumo gerencial não veio nesta leitura.
        </p>
      ) : null}
      {data?.owner_alerts && data.owner_alerts.failures.length > 0 ? (
        <p className="admin-error" role="status">
          {data.owner_alerts.failures.length} alerta(s) do proprietário sem entrega.
        </p>
      ) : null}
    </section>
  );
}

export function AttendanceHistoryPanel({
  data,
  error,
  open,
  activeLens,
  onToggle,
  onSelectLens,
}: HistoryProps) {
  const board = data?.board;
  return (
    <section className="admin-cycle-history" aria-labelledby="admin-history-toggle">
      <button
        id="admin-history-toggle"
        type="button"
        className="admin-cycle-history-toggle"
        aria-expanded={open}
        aria-controls="admin-history-detail"
        onClick={onToggle}
      >
        Consultar histórico <Chevron open={open} />
      </button>
      <div id="admin-history-detail" className="admin-cycle-detail" hidden={!open}>
        {open && error && board ? (
          <p className="admin-error" role="alert">
            Os números abaixo estão desatualizados. {error}
          </p>
        ) : null}
        {open && !board ? (
          <p className="admin-error" role="alert">
            O histórico não veio nesta leitura.
          </p>
        ) : null}
        {open && board ? (
          <>
            <h3>Histórico</h3>
            <div className="admin-cycle-lines" aria-label="Histórico">
              {board.history.map((metric) => (
                <MetricLine
                  key={metric.lens}
                  metric={metric}
                  active={activeLens === metric.lens}
                  onSelect={onSelectLens}
                />
              ))}
            </div>
            <h3>{board.payment_scope_label || "Financeiro de todo o histórico"}</h3>
            <p className="admin-muted">{board.payment_orders} pedido(s) classificados aqui.</p>
            <div className="admin-cycle-lines" aria-label="Pagamento">
              {board.payments.map((metric) => (
                <MetricLine
                  key={metric.lens}
                  metric={metric}
                  active={activeLens === metric.lens}
                  onSelect={onSelectLens}
                />
              ))}
            </div>
            <div className="admin-cycle-lines" aria-label="Outros estados financeiros">
              {board.payment_other.map((metric) => (
                <MetricLine
                  key={metric.lens}
                  metric={metric}
                  active={activeLens === metric.lens}
                  onSelect={onSelectLens}
                />
              ))}
            </div>
            <details className="admin-ops-help">
              <summary>Critérios deste resumo</summary>
              <p>{board.scope}</p>
              {board.composition_note ? <p>{board.composition_note}</p> : null}
              {board.legacy_note ? <p>{board.legacy_note}</p> : null}
              <p>{board.pending_note}</p>
              <p>{board.payment_note}</p>
              <p>
                As setas mostram o caminho habitual. Os números são os pedidos que estão em cada etapa
                agora. Pagamento dos vigentes usa o mesmo universo do fluxo e deixa o histórico de fora.
                Pago na etapa não inicia a produção.
              </p>
              {board.not_tracked.length > 0 ? (
                <ul className="admin-board-missing">
                  {board.not_tracked.map((item) => (
                    <li key={item.label}>
                      <strong>{item.label}</strong> não entram na linha: {item.reason}.
                    </li>
                  ))}
                </ul>
              ) : null}
            </details>
          </>
        ) : null}
      </div>
    </section>
  );
}
