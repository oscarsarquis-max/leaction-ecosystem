import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  listExecutions,
  isTerminalState,
  getExecutionOperationalEvents,
  getImplementationStatus,
  getPresentationReadiness,
  getPlatformHealth,
  listCanonicalExecutions,
  submitMockScenario,
  extractCanonicalExecutionId,
} from "./api";
import {
  MOCK_SCENARIOS,
  buildCanonicalRequest,
  newIdempotencyKey,
  newTraceparent,
} from "./scenarios";
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
import ExecutionJourney from "./ExecutionJourney";
import { ConsoleNav } from "./ConsoleNav";
import ImplementationCockpit from "./ImplementationCockpit";
import PresentationMode from "./PresentationMode";
import OperationalCockpit from "./OperationalCockpit";
import FailureLab from "./FailureLab";
import WorkerRuntime from "./WorkerRuntime";
import CapacityResilience from "./CapacityResilience";

const PRIMARY_SCENARIO =
  MOCK_SCENARIOS.find((s) => s.id === "RETRY_THEN_SUCCESS") || MOCK_SCENARIOS[0];

export default function ConsoleShell() {
  const [view, setView] = useState("home");
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
  const [platform, setPlatform] = useState({
    status: "idle",
    productVersion: null,
    health: null,
    presentation: null,
    runtime: "SIMULATED_INFRASTRUCTURE",
    integrations: "MOCK_ONLY",
    error: null,
  });
  const [canonicalItems, setCanonicalItems] = useState(null);
  const [canonicalError, setCanonicalError] = useState(null);

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
    if (view !== "home") {
      return undefined;
    }
    const controller = new AbortController();
    setPlatform((p) => ({ ...p, status: "loading", error: null }));
    setCanonicalError(null);
    Promise.all([
      getImplementationStatus({ signal: controller.signal }).catch((e) => ({ __error: e })),
      getPresentationReadiness({ signal: controller.signal }).catch((e) => ({ __error: e })),
      getPlatformHealth({ signal: controller.signal }).catch((e) => ({ __error: e })),
      listCanonicalExecutions({ signal: controller.signal }).catch((e) => ({ __error: e })),
    ]).then(([impl, ready, health, canonical]) => {
      if (controller.signal.aborted) return;
      const implErr = impl && impl.__error;
      const readyErr = ready && ready.__error;
      const healthErr = health && health.__error;
      const canonicalErr = canonical && canonical.__error;
      setPlatform({
        status: implErr || readyErr || healthErr ? "error" : "ok",
        productVersion: implErr ? null : impl.productVersion,
        health: healthErr ? null : health.status,
        presentation: readyErr ? null : ready.ready ? "READY" : "NOT_READY",
        runtime: "SIMULATED_INFRASTRUCTURE",
        integrations: (ready && ready.boundary) || "MOCK_ONLY",
        error: implErr || readyErr || healthErr || null,
      });
      if (canonicalErr) {
        setCanonicalItems([]);
        setCanonicalError(canonicalErr);
      } else {
        setCanonicalItems(canonical.items || []);
        setCanonicalError(null);
      }
    });
    return () => controller.abort();
  }, [view]);

  const journeySurface = view === "home" || view === "detail";
  const pollingEnabled = journeySurface && Boolean(selectedId);
  const { detail, error: detailError, updatedAt, status: pollStatus } = useExecutionPolling(
    selectedId,
    {
      enabled: pollingEnabled,
      minIntervalMs: 1000,
      paused: pollPaused,
    },
  );

  useEffect(() => {
    if (!journeySurface || !selectedId || pollPaused) {
      if (!selectedId) {
        setOperationalEvents(null);
        setOperationalEventsError(null);
      }
      return undefined;
    }
    const controller = new AbortController();
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
  }, [journeySurface, selectedId, pollPaused, updatedAt]);

  const journeyRef = useRef(null);

  useEffect(() => {
    if (view === "home" && selectedId && journeyRef.current) {
      journeyRef.current.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
    }
  }, [view, selectedId]);

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

  function followExecution(id, { stayOnHome } = {}) {
    setSelectedId(id);
    setPollPaused(false);
    if (!stayOnHome) {
      setView("detail");
    }
  }

  async function refreshCanonicalList() {
    try {
      const canonical = await listCanonicalExecutions();
      setCanonicalItems(canonical.items || []);
      setCanonicalError(null);
    } catch (e) {
      setCanonicalError(e);
    }
  }

  async function runScenario(scenario) {
    setLabBusy(true);
    setLabMsg(null);
    const idem = newIdempotencyKey(scenario.id);
    const tp = newTraceparent();
    const body = buildCanonicalRequest(scenario, { idempotencyKey: idem, traceparent: tp });
    const requestedId = extractCanonicalExecutionId(body.execution);
    try {
      const res = await submitMockScenario(body, { idempotencyKey: idem, traceparent: tp });
      const executionId = extractCanonicalExecutionId(res, requestedId);
      if (!executionId) {
        setLabMsg({
          ok: false,
          text: "A execução foi submetida, mas o identificador não veio no read model.",
        });
        return;
      }
      followExecution(executionId, { stayOnHome: view === "home" });
      setLabMsg({
        ok: true,
        text: `Execução iniciada — acompanhando ${executionId}`,
      });
      await refreshList({});
      if (view === "home") {
        await refreshCanonicalList();
      }
    } catch (e) {
      const recovered = extractCanonicalExecutionId(e.body);
      if (recovered) {
        followExecution(recovered, { stayOnHome: view === "home" });
        setLabMsg({
          ok: false,
          text: `Execução ${recovered} registrada — acompanhando o resultado técnico.`,
        });
      } else {
        setLabMsg({
          ok: false,
          text:
            e.status === 404
              ? "Submit canônico indisponível (habilite spider.canonical.http.enabled + local-demo). Não há fallback legado."
              : e.message || "Falha ao submeter cenário",
        });
      }
    } finally {
      setLabBusy(false);
    }
  }

  function openDetail(id) {
    followExecution(id, { stayOnHome: false });
  }

  function followOnHome(id) {
    followExecution(id, { stayOnHome: true });
  }

  return (
    <div className="obs-shell console-shell">
      <header className="obs-top">
        <div>
          <p className="obs-brand">SPIDER</p>
          <h1>{view === "home" ? "Home operacional" : "Console operacional"}</h1>
          <p className="obs-sub">
            {view === "home"
              ? "Ponto de entrada da jornada Mock: estado da plataforma, demonstração e últimas execuções."
              : "Read model autorizado sobre execuções persistidas — sem simulação por sleep e sem endpoint legado nesta jornada."}
          </p>
          <p>
            <span className="pill mock-badge">DEMONSTRAÇÃO MOCK</span>
          </p>
        </div>
        <ConsoleNav view={view} onChange={setView} />
      </header>

      {consoleUnavailable && (
        <div className="banner warn" role="status">
          Console indisponível: API `/v1/console` off ou não autorizada. Habilite{" "}
          <code>spider.console.enabled</code> + <code>spider.console.http.enabled</code> (e auth
          local-demo se necessário).
        </div>
      )}

      {view === "home" && (
        <section className="panel-card home-operational" aria-labelledby="home-title">
          <h2 id="home-title">SPIDER</h2>
          <div className="home-grid">
            <article className="home-status" aria-labelledby="plat-title">
              <h3 id="plat-title">Estado da plataforma</h3>
              {platform.status === "loading" && <p role="status">Carregando estado…</p>}
              {platform.error && (
                <p className="error" role="alert">
                  Não foi possível ler o estado da plataforma: {platform.error.message}
                </p>
              )}
              <dl className="platform-dl">
                <div>
                  <dt>Produto</dt>
                  <dd>Spider {platform.productVersion || "0.20.0"}</dd>
                </div>
                <div>
                  <dt>Health</dt>
                  <dd>{platform.health || "—"}</dd>
                </div>
                <div>
                  <dt>Presentation</dt>
                  <dd>{platform.presentation || "—"}</dd>
                </div>
                <div>
                  <dt>Runtime</dt>
                  <dd>{platform.runtime}</dd>
                </div>
                <div>
                  <dt>Integrations</dt>
                  <dd>{platform.integrations}</dd>
                </div>
              </dl>
            </article>
            <article aria-labelledby="action-title">
              <h3 id="action-title">{selectedId ? "Execução atual" : "Nova execução"}</h3>
              {selectedId ? (
                <div className="home-current-execution" data-testid="home-current-execution">
                  <p className="home-current-id" title={selectedId}>
                    {selectedId}
                  </p>
                  <StateBadge
                    state={detail?.summary?.state}
                    technicalStatus={detail?.summary?.technicalStatus}
                  />
                  {labMsg && (
                    <p className={labMsg.ok ? "ok" : "error"} role="status">
                      {labMsg.text}
                    </p>
                  )}
                </div>
              ) : (
                <p className="muted">
                  Reutiliza <code>POST /v1/canonical/executions</code> com o cenário{" "}
                  {PRIMARY_SCENARIO.label}.
                </p>
              )}
              <button
                type="button"
                className="cta"
                disabled={labBusy}
                onClick={() => runScenario(PRIMARY_SCENARIO)}
              >
                Executar demonstração
              </button>
              {labMsg && !selectedId && (
                <p className={labMsg.ok ? "ok" : "error"} role="status">
                  {labMsg.text}
                </p>
              )}
            </article>
          </div>
          {selectedId && (
            <article
              ref={journeyRef}
              className="home-journey"
              aria-label="Jornada da execução selecionada"
            >
              {detailError && <p className="error">{detailError.message}</p>}
              <ExecutionJourney
                heading="Jornada da execução"
                summary={detail?.summary || { executionId: selectedId, state: null }}
                timeline={detail?.timeline}
                steps={detail?.steps}
                waitInfo={detail?.waitInfo}
                callback={detail?.callback}
                operationalEvents={operationalEvents}
              />
              <p>
                <button type="button" className="ghost" onClick={() => openDetail(selectedId)}>
                  Ver detalhe técnico
                </button>
              </p>
            </article>
          )}
          <article aria-labelledby="recent-title">
            <h3 id="recent-title">Últimas execuções</h3>
            {canonicalError && (
              <p className="error" role="alert">
                Falha ao listar execuções canônicas ({canonicalError.status || "erro"}):{" "}
                {canonicalError.message}
              </p>
            )}
            {!canonicalError && canonicalItems && canonicalItems.length === 0 && (
              <p className="muted">Nenhuma execução visível neste recorte.</p>
            )}
            {canonicalItems && canonicalItems.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Execução</th>
                      <th scope="col">Status</th>
                      <th scope="col">Horário</th>
                      <th scope="col">Duração</th>
                      <th scope="col">Detalhe</th>
                    </tr>
                  </thead>
                  <tbody>
                    {canonicalItems.map((it) => (
                      <tr key={it.executionId}>
                        <td title={it.executionId}>{shortId(it.executionId)}</td>
                        <td>
                          <StateBadge state={it.state} technicalStatus={it.technicalStatus} />
                        </td>
                        <td title={it.startedAt}>{formatWhen(it.startedAt)}</td>
                        <td>{formatDuration(it.durationMs)}</td>
                        <td>
                          <button
                            type="button"
                            className="linkish"
                            onClick={() => followOnHome(it.executionId)}
                          >
                            Abrir
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </section>
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
                <h3>O que aconteceu?</h3>
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
              <h3>Por onde passou?</h3>
              <ExecutionJourney
                summary={detail.summary}
                timeline={detail.timeline}
                steps={detail.steps}
                waitInfo={detail.waitInfo}
                callback={detail.callback}
                operationalEvents={operationalEvents}
              />
              <h3>Mapa do plano</h3>
              <JourneyMap plan={detail.plan} steps={detail.steps} />
              <h3>Quando aconteceu?</h3>
              <TimelineView timeline={detail.timeline} />
              <h3>Operational Timeline</h3>
              <OperationalTimelineView
                events={operationalEvents}
                error={operationalEventsError}
              />
              <h3>O que tecnicamente ocorreu?</h3>
              <InspectorTabs detail={detail} />
            </>
          )}
        </section>
      )}

      {view === "implementation" && <ImplementationCockpit />}

      {view === "operational-health" && <OperationalCockpit />}

      {view === "failure-lab" && (
        <FailureLab
          onOpenExecution={(id) => {
            setSelectedId(id);
            setPollPaused(false);
            setView("detail");
          }}
        />
      )}

      {view === "worker-runtime" && <WorkerRuntime />}

      {view === "capacity" && <CapacityResilience />}

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
