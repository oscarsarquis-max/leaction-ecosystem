import { useCallback, useEffect, useMemo, useState } from "react";
import { listExecutions, isTerminalState, getExecutionOperationalEvents } from "./api";
import {
  MOCK_SCENARIOS,
  buildCanonicalRequest,
  newIdempotencyKey,
  newTraceparent,
} from "./scenarios";
import { submitMockScenario } from "./api";
import { useExecutionPolling } from "./useExecutionPolling";
import {
  StateBadge,
  JourneyMap,
  TimelineView,
  OperationalTimelineView,
  InspectorTabs,
  shortId,
  formatDuration,
  formatWhen,
} from "./components";
import ImplementationCockpit from "./ImplementationCockpit";
import PresentationMode from "./PresentationMode";

const NAV = [
  { id: "overview", label: "Visão geral" },
  { id: "executions", label: "Execuções" },
  { id: "detail", label: "Detalhe" },
  { id: "implementation", label: "Implementação" },
  { id: "presentation", label: "Apresentação" },
  { id: "lab", label: "Laboratório Mock" },
];

export default function ConsoleShell() {
  const [view, setView] = useState("overview");
  const [items, setItems] = useState([]);
  const [listError, setListError] = useState(null);
  const [consoleUnavailable, setConsoleUnavailable] = useState(false);
  const [listStatus, setListStatus] = useState("idle");
  const [cursor, setCursor] = useState({});
  const [filters, setFilters] = useState({ limit: 20, states: [], routeCode: "" });
  const [selectedId, setSelectedId] = useState(null);
  const [pollPaused, setPollPaused] = useState(false);
  const [lastListAt, setLastListAt] = useState(null);
  const [labMsg, setLabMsg] = useState(null);
  const [labBusy, setLabBusy] = useState(false);
  const [operationalEvents, setOperationalEvents] = useState(null);
  const [operationalEventsError, setOperationalEventsError] = useState(null);

  const refreshList = useCallback(
    async (nextCursor = {}) => {
      const controller = new AbortController();
      setListStatus("loading");
      try {
        const data = await listExecutions(filters, nextCursor, { signal: controller.signal });
        setItems(data.items || []);
        setCursor({
          cursorStartedAt: data.nextCursorStartedAt || undefined,
          cursorExecutionId: data.nextCursorExecutionId || undefined,
        });
        setListError(null);
        setConsoleUnavailable(false);
        setListStatus("ok");
        setLastListAt(new Date());
      } catch (e) {
        setListError(e);
        setConsoleUnavailable(Boolean(e.consoleUnavailable));
        setListStatus("error");
      }
    },
    [filters],
  );

  useEffect(() => {
    refreshList({});
  }, [refreshList]);

  useEffect(() => {
    if (view !== "detail" || !selectedId) {
      setOperationalEvents(null);
      setOperationalEventsError(null);
      return undefined;
    }
    const controller = new AbortController();
    setOperationalEvents(null);
    setOperationalEventsError(null);
    getExecutionOperationalEvents(selectedId, { signal: controller.signal })
      .then((data) => {
        setOperationalEvents(data.items || []);
        setOperationalEventsError(null);
      })
      .catch((e) => {
        if (e.name === "AbortError") return;
        setOperationalEvents([]);
        setOperationalEventsError(e);
      });
    return () => controller.abort();
  }, [view, selectedId, pollPaused]);

  const pollingEnabled = view === "detail" && Boolean(selectedId);
  const { detail, error: detailError, updatedAt, status: pollStatus } = useExecutionPolling(
    selectedId,
    {
      enabled: pollingEnabled,
      minIntervalMs: 1000,
      paused: pollPaused,
    },
  );

  const sampleStats = useMemo(() => {
    const byState = {};
    let waits = 0;
    let callbacks = 0;
    for (const it of items) {
      byState[it.state] = (byState[it.state] || 0) + 1;
      if (it.waitState) waits += 1;
      if (it.callbackState) callbacks += 1;
    }
    return { byState, waits, callbacks, sampleSize: items.length };
  }, [items]);

  async function runScenario(scenario) {
    setLabBusy(true);
    setLabMsg(null);
    try {
      const idem = newIdempotencyKey(scenario.id);
      const tp = newTraceparent();
      const body = buildCanonicalRequest(scenario, { idempotencyKey: idem, traceparent: tp });
      const res = await submitMockScenario(body, { idempotencyKey: idem, traceparent: tp });
      const executionId = res.executionId || res.executionRef || res.id;
      setLabMsg({
        ok: true,
        text: executionId
          ? `Submetido. executionId=${executionId}`
          : `Submetido. Resposta: ${JSON.stringify(res).slice(0, 200)}`,
      });
      if (executionId) {
        setSelectedId(executionId);
        setView("detail");
        setPollPaused(false);
      }
      await refreshList({});
    } catch (e) {
      setLabMsg({
        ok: false,
        text:
          e.status === 404
            ? "Submit canônico indisponível (habilite spider.canonical.http.enabled + local-demo). Não há fallback legado."
            : e.message || "Falha ao submeter cenário",
      });
    } finally {
      setLabBusy(false);
    }
  }

  function openDetail(id) {
    setSelectedId(id);
    setPollPaused(false);
    setView("detail");
  }

  return (
    <div className="obs-shell console-shell">
      <header className="obs-top">
        <div>
          <p className="obs-brand">Spider · Console Operacional Canônico</p>
          <h1>Observação do Data Plane</h1>
          <p className="obs-sub">
            Read model autorizado sobre execuções persistidas — sem simulação por sleep e sem endpoint
            legado nesta jornada.
          </p>
          <p>
            <span className="pill mock-badge">DEMONSTRAÇÃO MOCK</span>
          </p>
        </div>
        <nav className="console-nav" aria-label="Navegação principal">
          {NAV.map((n) => (
            <button
              key={n.id}
              type="button"
              className={view === n.id ? "nav-btn active" : "nav-btn"}
              onClick={() => setView(n.id)}
            >
              {n.label}
            </button>
          ))}
        </nav>
      </header>

      {consoleUnavailable && (
        <div className="banner warn" role="status">
          Console indisponível: API `/v1/console` off ou não autorizada. Habilite{" "}
          <code>spider.console.enabled</code> + <code>spider.console.http.enabled</code> (e auth
          local-demo se necessário).
        </div>
      )}

      {view === "overview" && (
        <section className="panel-card" aria-labelledby="ov-title">
          <h2 id="ov-title">Visão geral (amostra paginada)</h2>
          <p className="muted">
            Contagens derivadas da página atual ({sampleStats.sampleSize} itens) — não são SLI/SLO.
          </p>
          <div className="stat-row">
            <div>
              <span className="muted">Waits na amostra</span>
              <strong>{sampleStats.waits}</strong>
            </div>
            <div>
              <span className="muted">Callbacks na amostra</span>
              <strong>{sampleStats.callbacks}</strong>
            </div>
            <div>
              <span className="muted">Última atualização</span>
              <strong>{lastListAt ? lastListAt.toLocaleTimeString() : "—"}</strong>
            </div>
          </div>
          <ul className="state-counts">
            {Object.entries(sampleStats.byState).map(([k, v]) => (
              <li key={k}>
                <StateBadge state={k} /> × {v}
              </li>
            ))}
          </ul>
          <button type="button" className="cta" onClick={() => refreshList({})}>
            Atualizar amostra
          </button>
        </section>
      )}

      {view === "executions" && (
        <section className="panel-card" aria-labelledby="ex-title">
          <h2 id="ex-title">Execuções</h2>
          <form
            className="filter-row"
            onSubmit={(e) => {
              e.preventDefault();
              refreshList({});
            }}
          >
            <label>
              Route
              <input
                value={filters.routeCode}
                onChange={(e) => setFilters((f) => ({ ...f, routeCode: e.target.value }))}
              />
            </label>
            <label>
              States (CSV)
              <input
                placeholder="RUNNING,WAITING_EXTERNAL"
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    states: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }))
                }
              />
            </label>
            <button type="submit" className="cta">
              Filtrar
            </button>
            <button type="button" className="ghost" onClick={() => refreshList({})}>
              Atualizar
            </button>
            <button
              type="button"
              className="ghost"
              disabled={!cursor.cursorExecutionId}
              onClick={() => refreshList(cursor)}
            >
              Próxima página
            </button>
          </form>
          {listStatus === "loading" && <p role="status">Carregando…</p>}
          {listError && <p className="error">{listError.message}</p>}
          {!items.length && listStatus === "ok" && <p className="muted">Nenhuma execução nesta página.</p>}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Estado</th>
                  <th scope="col">Execução</th>
                  <th scope="col">Rota</th>
                  <th scope="col">Início</th>
                  <th scope="col">Duração</th>
                  <th scope="col">Indicadores</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.executionId}>
                    <td>
                      <StateBadge state={it.state} technicalStatus={it.technicalStatus} />
                    </td>
                    <td>
                      <button type="button" className="linkish" onClick={() => openDetail(it.executionId)}>
                        {shortId(it.executionId)}
                      </button>
                    </td>
                    <td>{it.routeRef || it.operationRef || "—"}</td>
                    <td title={it.startedAt}>{formatWhen(it.startedAt)}</td>
                    <td>{formatDuration(it.durationMs)}</td>
                    <td>
                      {it.waitState ? <span className="pill">wait</span> : null}{" "}
                      {it.callbackState ? <span className="pill">callback</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {view === "detail" && (
        <section className="panel-card" aria-labelledby="dt-title">
          <div className="detail-head">
            <h2 id="dt-title">Detalhe da execução</h2>
            <div className="detail-actions">
              <button type="button" className="ghost" onClick={() => setView("executions")}>
                Voltar
              </button>
              <button type="button" className="ghost" onClick={() => setPollPaused((p) => !p)}>
                {pollPaused ? "Retomar polling" : "Pausar polling"}
              </button>
            </div>
          </div>
          {!selectedId && <p className="muted">Selecione uma execução na lista ou no laboratório.</p>}
          {detailError && <p className="error">{detailError.message}</p>}
          {detail && (
            <>
              <div className="detail-summary">
                <StateBadge
                  state={detail.summary?.state}
                  technicalStatus={detail.summary?.technicalStatus}
                />
                <span title={detail.summary?.executionId}>{shortId(detail.summary?.executionId)}</span>
                <span>{detail.summary?.routeRef}</span>
                <span>{formatDuration(detail.summary?.durationMs)}</span>
                <span className="muted" aria-live="polite">
                  {pollStatus}
                  {updatedAt ? ` · ${updatedAt.toLocaleTimeString()}` : ""}
                  {isTerminalState(detail.summary?.state) ? " · terminal" : ""}
                </span>
              </div>
              <h3>Journey map</h3>
              <JourneyMap plan={detail.plan} steps={detail.steps} />
              <h3>Timeline</h3>
              <TimelineView timeline={detail.timeline} />
              <h3>Operational Timeline</h3>
              <OperationalTimelineView
                events={operationalEvents}
                error={operationalEventsError}
              />
              <h3>Inspectors</h3>
              <InspectorTabs detail={detail} />
            </>
          )}
        </section>
      )}

      {view === "implementation" && <ImplementationCockpit />}

      {view === "presentation" && (
        <PresentationMode
          onOpenExecution={(id) => {
            setSelectedId(id);
            setPollPaused(false);
            setView("detail");
          }}
        />
      )}

      {view === "lab" && (
        <section className="panel-card" aria-labelledby="lab-title">
          <h2 id="lab-title">Laboratório Mock</h2>
          <p className="muted">
            Dispara <code>POST /v1/canonical/executions</code> — nunca{" "}
            <code>/v1/products/orchestrate</code>. Idempotency key só em memória.
          </p>
          <ul className="scenario-grid">
            {MOCK_SCENARIOS.map((s) => (
              <li key={s.id}>
                <h3>{s.label}</h3>
                <p className="muted">{s.description}</p>
                <button
                  type="button"
                  className="cta"
                  disabled={labBusy}
                  onClick={() => runScenario(s)}
                >
                  Executar
                </button>
              </li>
            ))}
          </ul>
          {labMsg && (
            <p className={labMsg.ok ? "ok" : "error"} role="status">
              {labMsg.text}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
