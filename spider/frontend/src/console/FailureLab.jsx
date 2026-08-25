import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getFailureLabEvidence,
  getFailureLabRun,
  listFailureLabScenarios,
  startFailureLabRun,
} from "./api";

const POLL_INTERVAL_MS = 1500;
const MAX_POLL_ATTEMPTS = 120;

const CONFIRMATION_TEXT =
  "Este cenário criará execuções e eventos técnicos somente no ambiente Mock. Nenhum legado real será acessado.";

const RUN_STATUS_LABELS = {
  REQUESTED: "Solicitado",
  RUNNING: "Executando",
  OBSERVING: "Observando",
  VERIFIED: "Verificado",
  FAILED: "Falhou",
  TIMED_OUT: "Tempo esgotado",
  CANCELLED: "Cancelado",
  INCONCLUSIVE: "Inconclusivo",
};

const VERIFICATION_STATUS_LABELS = {
  PASSED: "Atendido",
  FAILED: "Não atendido",
  NOT_OBSERVED: "Não observado",
  NOT_APPLICABLE: "Não aplicável",
  INCONCLUSIVE: "Inconclusivo",
};

const CATEGORY_LABELS = {
  EXECUTION: "Execução",
  RETRY: "Retentativa",
  WAIT_RESUME: "Espera e retomada",
  CALLBACK: "Callback",
  SIGNAL: "Sinal externo",
  SECURITY: "Segurança",
  TELEMETRY: "Telemetria",
  OPERATIONAL_HEALTH: "Saúde operacional",
};

const COMPLETENESS_LABELS = {
  COMPLETE: "Completa",
  PARTIAL: "Parcial",
};

const JOURNEY_STEPS = [
  { code: "PREPARAR", label: "Preparar", statuses: ["REQUESTED"] },
  { code: "EXECUTAR", label: "Executar", statuses: ["RUNNING"] },
  { code: "OBSERVAR", label: "Observar", statuses: ["OBSERVING"] },
  {
    code: "VERIFICAR",
    label: "Verificar",
    statuses: ["VERIFIED", "FAILED", "TIMED_OUT", "CANCELLED", "INCONCLUSIVE"],
  },
];

const ACTIVE_RUN_STATUSES = new Set(["REQUESTED", "RUNNING", "OBSERVING"]);
const EVIDENCE_RUN_STATUSES = new Set(["VERIFIED", "FAILED", "INCONCLUSIVE"]);

export function isActiveRunStatus(status) {
  return ACTIVE_RUN_STATUSES.has(String(status || "").toUpperCase());
}

export function runStatusTone(status) {
  const value = String(status || "").toUpperCase();
  if (value === "VERIFIED") return "ok";
  if (value === "FAILED" || value === "TIMED_OUT") return "danger";
  if (value === "INCONCLUSIVE" || value === "CANCELLED") return "warn";
  if (ACTIVE_RUN_STATUSES.has(value)) return "running";
  return "muted";
}

export function verificationTone(status) {
  const value = String(status || "").toUpperCase();
  if (value === "PASSED") return "ok";
  if (value === "FAILED") return "danger";
  if (value === "NOT_OBSERVED" || value === "INCONCLUSIVE") return "warn";
  return "muted";
}

/** maximumDuration chega como ISO-8601 (PT2M) ou como segundos, conforme o codec do backend. */
export function formatMaximumDuration(value) {
  if (value == null || value === "") return "—";
  if (typeof value === "number") {
    return formatSeconds(value);
  }
  const text = String(value).trim();
  const iso = text.toUpperCase().match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?$/);
  if (iso) {
    const hours = Number(iso[1] || 0);
    const minutes = Number(iso[2] || 0);
    const seconds = Number(iso[3] || 0);
    return formatSeconds(hours * 3600 + minutes * 60 + seconds);
  }
  const numeric = Number(text);
  return Number.isFinite(numeric) ? formatSeconds(numeric) : text;
}

function formatSeconds(total) {
  const seconds = Math.round(total);
  if (!Number.isFinite(seconds) || seconds <= 0) return "—";
  if (seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes} min`;
  }
  if (seconds < 60) return `${seconds} s`;
  return `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

function formatWhen(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

function runbookRefOf(runbook) {
  return `${runbook.code}@${runbook.version}`;
}

function journeyStateFor(step, status) {
  const value = String(status || "").toUpperCase();
  const index = JOURNEY_STEPS.findIndex((candidate) => candidate.statuses.includes(value));
  const own = JOURNEY_STEPS.findIndex((candidate) => candidate.code === step.code);
  if (index < 0) return "pending";
  if (own < index) return "done";
  if (own === index) return index === JOURNEY_STEPS.length - 1 ? "done" : "current";
  return "pending";
}

const JOURNEY_STATE_LABELS = {
  done: "Concluído",
  current: "Em andamento",
  pending: "Pendente",
};

export default function FailureLab({ onOpenExecution }) {
  const [catalogStatus, setCatalogStatus] = useState("loading");
  const [catalog, setCatalog] = useState(null);
  const [catalogError, setCatalogError] = useState(null);
  const [selectedCode, setSelectedCode] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState(null);
  const [runError, setRunError] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [evidenceError, setEvidenceError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    setCatalogStatus("loading");
    listFailureLabScenarios({ signal: controller.signal })
      .then((data) => {
        const scenarios = Array.isArray(data) ? data : data?.scenarios || [];
        const runbooks = Array.isArray(data) ? [] : data?.runbooks || [];
        setCatalog({ ...(Array.isArray(data) ? {} : data), scenarios, runbooks });
        setCatalogError(null);
        setCatalogStatus(scenarios.length ? "ready" : "empty");
      })
      .catch((failure) => {
        if (failure.name === "AbortError") return;
        setCatalogError(failure);
        if (failure.status === 401 || failure.status === 403) {
          setCatalogStatus("unauthorized");
        } else if (failure.status === 404) {
          setCatalogStatus("disabled");
        } else {
          setCatalogStatus("error");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(
    () => () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    },
    [],
  );

  const scenarios = catalog?.scenarios || [];
  const selected = useMemo(
    () => scenarios.find((scenario) => scenario.code === selectedCode) || null,
    [scenarios, selectedCode],
  );
  const runbook = useMemo(() => {
    if (!selected) return null;
    const embedded = selected.runbook;
    if (embedded && typeof embedded === "object") return embedded;
    return (
      (catalog?.runbooks || []).find(
        (candidate) => runbookRefOf(candidate) === selected.runbookRef,
      ) || null
    );
  }, [catalog, selected]);

  const loadEvidence = useCallback((labRunId) => {
    getFailureLabEvidence(labRunId)
      .then((bundle) => {
        setEvidence(bundle);
        setEvidenceError(null);
      })
      .catch((failure) => {
        if (failure.name === "AbortError") return;
        setEvidence(null);
        setEvidenceError(failure);
      });
  }, []);

  const settle = useCallback(
    (nextRun) => {
      setRun(nextRun);
      if (EVIDENCE_RUN_STATUSES.has(String(nextRun?.status || "").toUpperCase())) {
        loadEvidence(nextRun.labRunId);
      }
    },
    [loadEvidence],
  );

  const poll = useCallback(
    (labRunId, attempt) => {
      if (attempt > MAX_POLL_ATTEMPTS) {
        setBusy(false);
        return;
      }
      pollRef.current = setTimeout(() => {
        getFailureLabRun(labRunId)
          .then((nextRun) => {
            settle(nextRun);
            if (isActiveRunStatus(nextRun?.status)) {
              poll(labRunId, attempt + 1);
            } else {
              setBusy(false);
            }
          })
          .catch((failure) => {
            if (failure.name === "AbortError") return;
            setRunError(failure);
            setBusy(false);
          });
      }, POLL_INTERVAL_MS);
    },
    [settle],
  );

  function selectScenario(code) {
    setSelectedCode((current) => (current === code ? null : code));
    setConfirmed(false);
    setRun(null);
    setRunError(null);
    setEvidence(null);
    setEvidenceError(null);
  }

  async function executeScenario() {
    if (!selected || !confirmed || busy) return;
    setBusy(true);
    setRunError(null);
    setEvidence(null);
    setEvidenceError(null);
    try {
      const started = await startFailureLabRun({
        scenarioCode: selected.code,
        scenarioVersion: selected.version,
        parameters: {},
      });
      settle(started);
      if (isActiveRunStatus(started?.status) && started?.labRunId) {
        poll(started.labRunId, 1);
      } else {
        setBusy(false);
      }
    } catch (failure) {
      setRunError(failure);
      setBusy(false);
    }
  }

  const runStatus = String(run?.status || "").toUpperCase();

  return (
    <section className="panel-card" aria-labelledby="failure-lab-title" data-testid="failure-lab">
      <div className="detail-head">
        <div>
          <h2 id="failure-lab-title">Failure Lab — Jornadas Operacionais Mock</h2>
          <p className="muted">
            Cenários controlados de falha declarados em catálogo versionado. O laboratório observa as
            fontes canônicas e emite veredito com evidência segura — não decide nada dentro da
            Engine.
          </p>
        </div>
        <span className="pill mock-badge">DEMONSTRAÇÃO MOCK</span>
      </div>

      <div className="banner warn" role="status" data-testid="failure-lab-boundary-banner">
        AMBIENTE DE DEMONSTRAÇÃO · MOCK_ONLY · FALHAS SIMULADAS · SEM CONEXÃO COM LEGADOS REAIS
      </div>

      {catalogStatus === "loading" && <p role="status">Carregando catálogo de cenários…</p>}

      {catalogStatus === "disabled" && (
        <p className="muted" role="status">
          Capability desabilitada ou console indisponível (spider.failure-lab.enabled /
          spider.failure-lab.http.enabled). Nenhum cenário é simulado no cliente.
        </p>
      )}

      {catalogStatus === "unauthorized" && (
        <p className="error" role="alert">
          Credencial sem permissão para o Failure Lab. Solicite a autorização de leitura de cenários
          controlados.
        </p>
      )}

      {catalogStatus === "empty" && (
        <p className="muted" role="status">
          Catálogo publicado sem cenários. Nada é executado enquanto o catálogo estiver vazio.
        </p>
      )}

      {catalogStatus === "error" && (
        <p className="error" role="alert">
          Catálogo indisponível: {catalogError?.message}
        </p>
      )}

      {catalogStatus === "ready" && (
        <>
          <h3>Cenários controlados ({scenarios.length})</h3>
          <ul className="scenario-grid" aria-label="Cenários do Failure Lab">
            {scenarios.map((scenario) => {
              const active = scenario.code === selectedCode;
              return (
                <li key={scenario.code} data-testid={`failure-lab-scenario-${scenario.code}`}>
                  <span className="pill">
                    {CATEGORY_LABELS[scenario.category] || scenario.category}
                  </span>
                  <h3>{scenario.title}</h3>
                  <p className="muted">{scenario.functionalDescription}</p>
                  <dl className="kv-grid">
                    <div>
                      <dt>Duração máxima</dt>
                      <dd>{formatMaximumDuration(scenario.maximumDuration)}</dd>
                    </div>
                    <div>
                      <dt>Versão</dt>
                      <dd>{scenario.version}</dd>
                    </div>
                    <div>
                      <dt>Runbook</dt>
                      <dd className="mono">{scenario.runbookRef}</dd>
                    </div>
                  </dl>
                  <button
                    type="button"
                    className={active ? "cta" : "ghost"}
                    data-testid={`failure-lab-select-${scenario.code}`}
                    aria-pressed={active}
                    onClick={() => selectScenario(scenario.code)}
                  >
                    {active ? "Cenário selecionado" : "Selecionar cenário"}
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {selected && (
        <div className="panel-card" data-testid="failure-lab-selection">
          <h3>{selected.title}</h3>
          <p className="muted">
            {selected.code}@{selected.version} · limite de {selected.maximumExecutions} execução(ões)
            controlada(s)
          </p>

          {selected.preconditions?.length > 0 && (
            <>
              <h4>Pré-condições</h4>
              <ul className="check-list">
                {selected.preconditions.map((precondition) => (
                  <li key={precondition}>{precondition}</li>
                ))}
              </ul>
            </>
          )}

          {selected.expectedObservations?.length > 0 && (
            <>
              <h4>Observações esperadas</h4>
              <ul className="check-list">
                {selected.expectedObservations.map((observation) => (
                  <li key={observation.code}>
                    <span className="pill">
                      {observation.required ? "Obrigatória" : "Complementar"}
                    </span>{" "}
                    {observation.description || observation.code}
                  </li>
                ))}
              </ul>
            </>
          )}

          <div className="banner warn" role="status" data-testid="failure-lab-confirmation">
            {CONFIRMATION_TEXT}
          </div>
          <label className="check-confirm">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />{" "}
            Li e confirmo o limite Mock deste cenário.
          </label>
          <p>
            <button
              type="button"
              className="cta"
              disabled={!confirmed || busy}
              onClick={executeScenario}
            >
              Executar cenário
            </button>
          </p>
          {!confirmed && (
            <p className="muted">Confirme o limite Mock para liberar a execução controlada.</p>
          )}
          {runError && (
            <p className="error" role="alert">
              {runError.status === 404
                ? "Failure Lab indisponível ou não autorizado — nenhum cenário foi executado."
                : runError.message || "Falha ao iniciar o cenário controlado."}
            </p>
          )}
        </div>
      )}

      {run && (
        <div className="panel-card" data-testid="failure-lab-run">
          <div className="detail-head">
            <h3>Execução controlada</h3>
            <span
              className={`status-chip state-${runStatusTone(runStatus)}`}
              data-testid="failure-lab-run-status"
              aria-live="polite"
            >
              {RUN_STATUS_LABELS[runStatus] || runStatus} ({runStatus})
            </span>
          </div>

          <dl className="kv-grid">
            <div>
              <dt>Identificador</dt>
              <dd className="mono">{run.labRunId}</dd>
            </div>
            <div>
              <dt>Cenário</dt>
              <dd>
                {run.scenarioCode}@{run.scenarioVersion}
              </dd>
            </div>
            <div>
              <dt>Boundary</dt>
              <dd>{run.boundary}</dd>
            </div>
            <div>
              <dt>Solicitado em</dt>
              <dd>{formatWhen(run.requestedAt)}</dd>
            </div>
            <div>
              <dt>Concluído em</dt>
              <dd>{formatWhen(run.completedAt)}</dd>
            </div>
          </dl>

          <h4>Jornada</h4>
          <ol className="journey-map" aria-label="Jornada da execução controlada">
            {JOURNEY_STEPS.map((step, index) => {
              const state = journeyStateFor(step, runStatus);
              return (
                <li
                  key={step.code}
                  className="journey-step"
                  data-testid={`failure-lab-journey-${step.code}`}
                >
                  <span className="journey-order">{index + 1}</span>
                  <span>
                    <strong>{step.label}</strong>{" "}
                    <span className="pill">{JOURNEY_STATE_LABELS[state]}</span>
                  </span>
                </li>
              );
            })}
          </ol>

          {run.failureMessage && (
            <p className="error" role="alert">
              Motivo seguro: {run.failureMessage}
            </p>
          )}
          {run.evidenceSummary && <p className="muted">Resumo: {run.evidenceSummary}</p>}

          <h4>Verificações</h4>
          {(run.verificationResults || []).length === 0 ? (
            <p className="muted">
              Nenhuma verificação registrada até agora. Ausência de evidência não é tratada como
              sucesso.
            </p>
          ) : (
            <ul className="check-list" aria-label="Resultados de verificação">
              {run.verificationResults.map((result) => (
                <li
                  key={result.observationCode}
                  data-testid={`failure-lab-verification-${result.observationCode}`}
                >
                  <span className={`pill state-${verificationTone(result.status)}`}>
                    {VERIFICATION_STATUS_LABELS[result.status] || result.status}
                  </span>{" "}
                  <strong>{result.observationCode}</strong>
                  <p className="muted">
                    Esperado: {result.expected || "—"} · Observado: {result.observed || "—"}
                  </p>
                  {result.explanation ? <p>{result.explanation}</p> : null}
                </li>
              ))}
            </ul>
          )}

          <h4>Execuções geradas</h4>
          {(run.executionRefs || []).length === 0 ? (
            <p className="muted">Este cenário não submete execução à Engine.</p>
          ) : (
            <ul className="check-list" aria-label="Execuções geradas">
              {run.executionRefs.map((executionId) => (
                <li key={executionId}>
                  <button
                    type="button"
                    className="linkish"
                    onClick={() => onOpenExecution?.(executionId)}
                  >
                    Abrir execução {executionId}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {runbook && (
        <div className="panel-card" data-testid="failure-lab-runbook">
          <h3>Runbook operacional provisório</h3>
          <p className="muted mono">{selected?.runbookRef}</p>
          <h4>{runbook.title}</h4>
          {runbook.purpose ? <p>{runbook.purpose}</p> : null}
          <RunbookList title="Sintomas" items={runbook.symptoms} />
          <RunbookList title="Verificações" items={runbook.checks} />
          <RunbookList title="Evidência esperada" items={runbook.expectedEvidence} />
          <RunbookList title="Ações seguras" items={runbook.safeActions} />
          <RunbookList title="Condições de parada" items={runbook.stopConditions} />
          {runbook.escalationGuidance ? (
            <p>
              <strong>Escalonamento:</strong> {runbook.escalationGuidance}
            </p>
          ) : null}
          {runbook.limitations ? <p className="muted">{runbook.limitations}</p> : null}
        </div>
      )}

      {(evidence || evidenceError) && (
        <div className="panel-card" data-testid="failure-lab-evidence">
          <h3>Evidência segura</h3>
          {evidenceError && (
            <p className="muted" role="status">
              {evidenceError.status === 404
                ? "Evidência indisponível ou não autorizada para esta execução controlada."
                : evidenceError.message}
            </p>
          )}
          {evidence && (
            <>
              <dl className="kv-grid">
                <div>
                  <dt>Digest (SHA-256)</dt>
                  <dd className="mono wrap">{evidence.digest}</dd>
                </div>
                <div>
                  <dt>Completude</dt>
                  <dd>
                    {COMPLETENESS_LABELS[evidence.completenessStatus] ||
                      evidence.completenessStatus}
                  </dd>
                </div>
                <div>
                  <dt>Redação</dt>
                  <dd>{evidence.redactionStatus === "APPLIED" ? "Aplicada" : evidence.redactionStatus}</dd>
                </div>
                <div>
                  <dt>Gerada em</dt>
                  <dd>{formatWhen(evidence.generatedAt)}</dd>
                </div>
              </dl>
              <h4>Resumo das verificações</h4>
              <ul className="check-list" aria-label="Resumo de verificações da evidência">
                {(evidence.verificationResults || []).map((result) => (
                  <li key={result.observationCode}>
                    <span className={`pill state-${verificationTone(result.status)}`}>
                      {VERIFICATION_STATUS_LABELS[result.status] || result.status}
                    </span>{" "}
                    {result.observationCode}
                  </li>
                ))}
              </ul>
              <p className="muted">
                A evidência cobre apenas o resumo estável da execução controlada — sem payload, sem
                credencial e sem conteúdo de negócio.
              </p>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function RunbookList({ title, items }) {
  if (!items?.length) return null;
  return (
    <>
      <h5>{title}</h5>
      <ul className="check-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </>
  );
}
