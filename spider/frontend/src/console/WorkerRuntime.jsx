import { useCallback, useEffect, useMemo, useState } from "react";
import { drainWorker, getWorkerRuntime } from "./api";

const DRAIN_CONFIRMATION_TEXT =
  "A drenagem é simulada no ambiente local-demo: marca o worker como DRAINING e para de aceitar novos claims. " +
  "Não interrompe o ciclo em curso, não remove leases e não atinge nenhuma infraestrutura real.";

const RUNTIME_STATUS_LABELS = {
  DISABLED: "Desabilitado",
  HEALTHY: "Saudável",
  DEGRADED: "Degradado",
  DRAINING: "Em drenagem",
  STOPPED: "Parado",
  UNKNOWN: "Indeterminado",
};

const WORKER_STATUS_LABELS = {
  STARTING: "Iniciando",
  IDLE: "Ocioso",
  RUNNING: "Processando",
  DRAINING: "Drenando",
  STOPPED: "Parado",
  FAILED: "Falho",
  STALE: "Sem heartbeat",
};

const BACKLOG_STATUS_LABELS = {
  EMPTY: "Vazio",
  NORMAL: "Normal",
  ACCUMULATING: "Acumulando",
  STALE: "Envelhecido",
  UNKNOWN: "Indeterminado",
};

const SCHEDULE_OUTCOME_LABELS = {
  SUCCESS: "Sucesso",
  PARTIAL: "Parcial",
  FAILED: "Falhou",
  SKIPPED: "Ignorado",
  FENCED_OUT: "Bloqueado por fencing",
};

const WORKER_TYPE_LABELS = {
  SIGNAL_APPLICATION: "Aplicação de sinal",
  WAIT_EXPIRY: "Expiração de espera",
  CALLBACK_DELIVERY: "Entrega de callback",
  CALLBACK_RECONCILIATION: "Reconciliação de callback",
  CALLBACK_RECOVERY: "Recuperação de callback",
  SIGNAL_APPLICATION_RECOVERY: "Recuperação de sinal",
  PROTECTED_ENVELOPE_MAINTENANCE: "Manutenção de envelope protegido",
};

const DRAINABLE_STATUSES = new Set(["RUNNING", "IDLE"]);

export function canDrainWorker(worker) {
  const status = String(worker?.status || "").toUpperCase();
  return DRAINABLE_STATUSES.has(status) && !worker?.drainRequestedAt;
}

export function runtimeStatusTone(status) {
  const value = String(status || "").toUpperCase();
  if (value === "HEALTHY") return "ok";
  if (value === "DEGRADED" || value === "DRAINING") return "warn";
  if (value === "STOPPED") return "danger";
  return "muted";
}

export function workerStatusTone(status) {
  const value = String(status || "").toUpperCase();
  if (value === "RUNNING" || value === "IDLE") return "ok";
  if (value === "STARTING") return "running";
  if (value === "DRAINING" || value === "STALE") return "warn";
  if (value === "FAILED" || value === "STOPPED") return "danger";
  return "muted";
}

export function backlogStatusTone(status) {
  const value = String(status || "").toUpperCase();
  if (value === "EMPTY" || value === "NORMAL") return "ok";
  if (value === "ACCUMULATING" || value === "STALE") return "warn";
  return "muted";
}

export function formatAgeMs(value) {
  if (value == null || value === "") return "—";
  const total = Number(value);
  if (!Number.isFinite(total)) return "—";
  const ms = Math.max(0, Math.round(total));
  if (ms < 1000) return `${ms} ms`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    const rest = seconds % 60;
    return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  return restMinutes ? `${hours} h ${restMinutes} min` : `${hours} h`;
}

/** interval chega como ISO-8601 (PT10S) ou como segundos, conforme o codec do backend. */
export function formatInterval(value) {
  if (value == null || value === "") return "—";
  if (typeof value === "number") return formatAgeMs(value * 1000);
  const iso = String(value)
    .trim()
    .toUpperCase()
    .match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?$/);
  if (iso) {
    const hours = Number(iso[1] || 0);
    const minutes = Number(iso[2] || 0);
    const seconds = Number(iso[3] || 0);
    return formatAgeMs((hours * 3600 + minutes * 60 + seconds) * 1000);
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? formatAgeMs(numeric * 1000) : String(value);
}

export function heartbeatAgeMs(worker, referenceIso) {
  if (!worker?.lastHeartbeatAt) return null;
  const beat = Date.parse(worker.lastHeartbeatAt);
  const reference = referenceIso ? Date.parse(referenceIso) : Date.now();
  if (Number.isNaN(beat) || Number.isNaN(reference)) return null;
  return reference - beat;
}

function formatWhen(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

function workerTypeLabel(workerType) {
  return WORKER_TYPE_LABELS[workerType] || workerType || "—";
}

export default function WorkerRuntime() {
  const [status, setStatus] = useState("loading");
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [drainCandidate, setDrainCandidate] = useState(null);
  const [drainBusy, setDrainBusy] = useState(false);
  const [drainMessage, setDrainMessage] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    getWorkerRuntime({ signal: controller.signal })
      .then((data) => {
        setSnapshot(data);
        setError(null);
        const runtimeStatus = String(data?.runtimeStatus || "").toUpperCase();
        if (runtimeStatus === "DISABLED") {
          setStatus("disabled");
        } else if (!(data?.workers || []).length) {
          setStatus("empty");
        } else {
          setStatus("ready");
        }
      })
      .catch((failure) => {
        if (failure.name === "AbortError") return;
        setSnapshot(null);
        setError(failure);
        if (failure.status === 401 || failure.status === 403) {
          setStatus("unauthorized");
        } else if (failure.status === 404) {
          setStatus("disabled");
        } else {
          setStatus("error");
        }
      });
    return () => controller.abort();
  }, [reloadToken]);

  const refresh = useCallback(() => {
    setDrainCandidate(null);
    setReloadToken((token) => token + 1);
  }, []);

  const workers = snapshot?.workers || [];
  const schedules = snapshot?.schedules || [];
  const backlogs = snapshot?.backlogs || [];
  const runtimeStatus = String(snapshot?.runtimeStatus || "").toUpperCase();

  const claimsByType = useMemo(() => {
    const map = {};
    for (const worker of workers) {
      map[worker.workerType] = (map[worker.workerType] || 0) + (worker.currentClaims || 0);
    }
    return map;
  }, [workers]);

  const partialData = Boolean(snapshot) && snapshot?.dataQuality?.complete === false;

  async function confirmDrain(workerId) {
    if (drainBusy) return;
    setDrainBusy(true);
    setDrainMessage(null);
    try {
      await drainWorker(workerId);
      setDrainMessage({
        ok: true,
        text: `Drenagem simulada solicitada para ${workerId}. O worker deixa de aceitar novos claims.`,
      });
      setDrainCandidate(null);
      setReloadToken((token) => token + 1);
    } catch (failure) {
      setDrainMessage({
        ok: false,
        text:
          failure.status === 404
            ? "Drenagem indisponível ou não autorizada — nenhum worker foi alterado."
            : failure.message || "Falha ao solicitar a drenagem simulada.",
      });
    } finally {
      setDrainBusy(false);
    }
  }

  return (
    <section className="panel-card" aria-labelledby="worker-runtime-title" data-testid="worker-runtime">
      <div className="detail-head">
        <div>
          <h2 id="worker-runtime-title">Runtime de Workers</h2>
          <p className="muted">
            Leitura do runtime durável: instâncias, agendamentos com lease e fencing, e backlog por
            tipo. O console observa o runtime — não decide nada dentro da Engine.
          </p>
        </div>
        <div className="detail-actions">
          <span className="pill mock-badge">DEMONSTRAÇÃO MOCK</span>
          <button type="button" className="ghost" onClick={refresh} data-testid="worker-runtime-refresh">
            Atualizar
          </button>
        </div>
      </div>

      <div className="banner warn" role="status" data-testid="worker-runtime-boundary-banner">
        <strong>INFRAESTRUTURA SIMULADA</strong>
        <br />
        INTEGRAÇÕES MOCK_ONLY
        <br />
        NÃO PRODUTIVO
      </div>

      {status === "loading" && <p role="status">Carregando runtime de workers…</p>}

      {status === "disabled" && (
        <p className="muted" role="status">
          Capability desabilitada ou console indisponível (spider.worker-runtime.enabled /
          spider.worker-runtime.http.enabled). Nenhum runtime é simulado no cliente.
        </p>
      )}

      {status === "unauthorized" && (
        <p className="error" role="alert">
          Credencial sem permissão para o runtime de workers. Solicite a autorização de leitura do
          runtime.
        </p>
      )}

      {status === "empty" && (
        <p className="muted" role="status">
          Runtime habilitado sem nenhuma instância registrada. Ausência de worker não é tratada como
          runtime saudável.
        </p>
      )}

      {status === "error" && (
        <p className="error" role="alert">
          Runtime de workers indisponível: {error?.message}
        </p>
      )}

      {snapshot && status !== "disabled" && (
        <>
          <div className="stat-row" aria-label="Resumo do runtime" data-testid="worker-runtime-summary">
            <div>
              <span className="muted">Condição do runtime</span>
              <strong
                className={`state-${runtimeStatusTone(runtimeStatus)}`}
                data-testid="worker-runtime-status"
              >
                {RUNTIME_STATUS_LABELS[runtimeStatus] || runtimeStatus || "—"} ({runtimeStatus || "—"})
              </strong>
            </div>
            <div>
              <span className="muted">Workers sem heartbeat</span>
              <strong data-testid="worker-runtime-stale-workers">{snapshot.staleWorkers ?? 0}</strong>
            </div>
            <div>
              <span className="muted">Leases expirados</span>
              <strong data-testid="worker-runtime-expired-leases">{snapshot.expiredLeases ?? 0}</strong>
            </div>
            <div>
              <span className="muted">Pendência mais antiga</span>
              <strong>{formatAgeMs(snapshot.oldestPendingAgeMs)}</strong>
            </div>
            <div>
              <span className="muted">Calculado em</span>
              <strong data-testid="worker-runtime-calculated-at">
                {formatWhen(snapshot.calculatedAt)}
              </strong>
            </div>
          </div>

          <p className="muted">
            Fronteira declarada: {snapshot.boundary || "—"} · integrações{" "}
            {snapshot.integrationBoundary || "—"}
          </p>

          {partialData && (
            <p className="muted" role="status" data-testid="worker-runtime-partial">
              Leitura parcial. Fontes ausentes:{" "}
              {(snapshot.dataQuality?.missingSources || []).join(", ") || "não informadas"}.
              {(snapshot.dataQuality?.warnings || []).length
                ? ` Avisos: ${snapshot.dataQuality.warnings.join(" · ")}.`
                : ""}{" "}
              Contagem incompleta não é tratada como runtime saudável.
            </p>
          )}

          {drainMessage && (
            <p
              className={drainMessage.ok ? "ok" : "error"}
              role={drainMessage.ok ? "status" : "alert"}
              data-testid="worker-runtime-drain-message"
            >
              {drainMessage.text}
            </p>
          )}

          <h3>Instâncias de worker ({workers.length})</h3>
          {workers.length === 0 ? (
            <p className="muted">Nenhuma instância registrada.</p>
          ) : (
            <div className="table-wrap">
              <table data-testid="worker-runtime-workers">
                <caption className="sr-caption">Instâncias de worker do runtime durável</caption>
                <thead>
                  <tr>
                    <th scope="col">Tipo</th>
                    <th scope="col">Situação</th>
                    <th scope="col">Heartbeat</th>
                    <th scope="col">Drenagem</th>
                    <th scope="col">Claims</th>
                    <th scope="col">Processados</th>
                    <th scope="col">Falhas</th>
                    <th scope="col">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {workers.map((worker) => {
                    const workerStatus = String(worker.status || "").toUpperCase();
                    const drainable = canDrainWorker(worker);
                    const confirming = drainCandidate === worker.workerId;
                    return (
                      <tr
                        key={worker.workerId}
                        data-testid={`worker-runtime-worker-${worker.workerId}`}
                      >
                        <th scope="row">
                          {workerTypeLabel(worker.workerType)}
                          <span className="muted mono wr-worker-id">{worker.workerId}</span>
                        </th>
                        <td>
                          <span className={`status-chip state-${workerStatusTone(workerStatus)}`}>
                            {WORKER_STATUS_LABELS[workerStatus] || workerStatus} ({workerStatus})
                          </span>
                        </td>
                        <td title={worker.lastHeartbeatAt || ""}>
                          {formatAgeMs(heartbeatAgeMs(worker, snapshot.calculatedAt))}
                        </td>
                        <td>
                          {worker.drainRequestedAt || workerStatus === "DRAINING"
                            ? `Solicitada ${formatWhen(worker.drainRequestedAt)}`
                            : "Não solicitada"}
                        </td>
                        <td>{worker.currentClaims ?? 0}</td>
                        <td>{worker.processedCount ?? 0}</td>
                        <td>{worker.failureCount ?? 0}</td>
                        <td>
                          {drainable ? (
                            confirming ? (
                              <span className="wr-drain-actions">
                                <button
                                  type="button"
                                  className="cta"
                                  disabled={drainBusy}
                                  data-testid={`worker-runtime-drain-confirm-${worker.workerId}`}
                                  onClick={() => confirmDrain(worker.workerId)}
                                >
                                  Confirmar drenagem simulada
                                </button>
                                <button
                                  type="button"
                                  className="ghost"
                                  disabled={drainBusy}
                                  onClick={() => setDrainCandidate(null)}
                                >
                                  Cancelar
                                </button>
                              </span>
                            ) : (
                              <button
                                type="button"
                                className="ghost"
                                data-testid={`worker-runtime-drain-${worker.workerId}`}
                                onClick={() => {
                                  setDrainMessage(null);
                                  setDrainCandidate(worker.workerId);
                                }}
                              >
                                Drenar
                              </button>
                            )
                          ) : (
                            <span className="muted">Indisponível</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {drainCandidate && (
            <div className="banner warn" role="status" data-testid="worker-runtime-drain-confirmation">
              {DRAIN_CONFIRMATION_TEXT}
            </div>
          )}

          <h3>Agendamentos duráveis ({schedules.length})</h3>
          {schedules.length === 0 ? (
            <p className="muted">Nenhum agendamento publicado.</p>
          ) : (
            <div className="table-wrap">
              <table data-testid="worker-runtime-schedules">
                <caption className="sr-caption">
                  Agendamentos duráveis com posse por lease e fencing monotônico
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Código</th>
                    <th scope="col">Intervalo</th>
                    <th scope="col">Próxima elegibilidade</th>
                    <th scope="col">Dono do lease</th>
                    <th scope="col">Lease até</th>
                    <th scope="col">Fencing token</th>
                    <th scope="col">Último resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {schedules.map((schedule) => {
                    const outcome = String(schedule.lastOutcome || "").toUpperCase();
                    return (
                      <tr
                        key={schedule.scheduleCode}
                        data-testid={`worker-runtime-schedule-${schedule.scheduleCode}`}
                      >
                        <th scope="row">
                          <span className="mono">{schedule.scheduleCode}</span>
                          <span className="muted wr-worker-id">
                            {workerTypeLabel(schedule.workerType)} ·{" "}
                            {schedule.enabled ? "Habilitado" : "Desabilitado"}
                          </span>
                        </th>
                        <td>{formatInterval(schedule.interval)}</td>
                        <td title={schedule.nextEligibleAt || ""}>
                          {formatWhen(schedule.nextEligibleAt)}
                        </td>
                        <td className="mono">{schedule.ownerWorkerId || "Sem dono"}</td>
                        <td>{formatWhen(schedule.leaseUntil)}</td>
                        <td className="mono">{schedule.fencingToken ?? 0}</td>
                        <td>
                          {outcome
                            ? `${SCHEDULE_OUTCOME_LABELS[outcome] || outcome} (${outcome})`
                            : "Sem ciclo concluído"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <h3>Backlog por tipo ({backlogs.length})</h3>
          {backlogs.length === 0 ? (
            <p className="muted">Nenhuma leitura de backlog disponível.</p>
          ) : (
            <div className="table-wrap">
              <table data-testid="worker-runtime-backlogs">
                <caption className="sr-caption">Backlog elegível por tipo de worker</caption>
                <thead>
                  <tr>
                    <th scope="col">Tipo</th>
                    <th scope="col">Situação</th>
                    <th scope="col">Elegíveis</th>
                    <th scope="col">Em claim</th>
                    <th scope="col">Mais antigo</th>
                    <th scope="col">Observação</th>
                  </tr>
                </thead>
                <tbody>
                  {backlogs.map((backlog) => {
                    const backlogStatus = String(backlog.status || "").toUpperCase();
                    return (
                      <tr
                        key={backlog.workerType}
                        data-testid={`worker-runtime-backlog-${backlog.workerType}`}
                      >
                        <th scope="row">{workerTypeLabel(backlog.workerType)}</th>
                        <td>
                          <span className={`status-chip state-${backlogStatusTone(backlogStatus)}`}>
                            {BACKLOG_STATUS_LABELS[backlogStatus] || backlogStatus} ({backlogStatus})
                          </span>
                        </td>
                        <td>{backlog.eligibleCount ?? 0}</td>
                        <td>{claimsByType[backlog.workerType] ?? 0}</td>
                        <td>{formatAgeMs(backlog.oldestEligibleAgeMs)}</td>
                        <td className="muted">
                          {backlog.approximate ? "Contagem aproximada. " : ""}
                          {backlog.explanation || "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <p className="muted">
            Contagem “em claim” é derivada dos claims ativos das instâncias do mesmo tipo nesta
            leitura — não é uma contagem persistida de backlog.
          </p>
        </>
      )}
    </section>
  );
}
