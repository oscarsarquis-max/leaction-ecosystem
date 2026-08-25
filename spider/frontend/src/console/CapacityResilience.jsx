import { useCallback, useEffect, useMemo, useState } from "react";
import { getCapacityDecisions, getCapacitySnapshot } from "./api";

export const BOUNDARY_BANNER_TEXT =
  "DEMONSTRAÇÃO · INFRAESTRUTURA SIMULADA · INTEGRAÇÕES MOCK · SEM CAPACIDADE PRODUTIVA AFERIDA";

/** Acima desta idade a leitura deixa de ser tratada como atual. */
export const STALE_AFTER_MS = 60_000;

const DECISION_PAGE_SIZE = 50;

const MODE_LABELS = {
  DISABLED: "Desabilitado",
  MONITOR_ONLY: "Somente observação",
  ENFORCED: "Aplicando limites",
};

const MODE_NOTES = {
  DISABLED:
    "Governo de capacidade desligado: nada é admitido, adiado ou descartado por política nesta leitura.",
  MONITOR_ONLY:
    "Observação apenas: as decisões registram o desfecho que teria sido aplicado, sem recusar trabalho.",
  ENFORCED:
    "Limites aplicados: a admissão pode adiar, recusar ou descartar trabalho conforme a política declarada.",
};

const PRESSURE_LABELS = {
  NORMAL: "Normal",
  ELEVATED: "Elevada",
  HIGH: "Alta",
  CRITICAL: "Crítica",
  UNKNOWN: "Indeterminada",
};

const CIRCUIT_LABELS = {
  CLOSED: "Fechado",
  OPEN: "Aberto",
  HALF_OPEN: "Meio aberto",
};

const RESULT_LABELS = {
  ADMITTED: "Admitido",
  DELAYED: "Adiado",
  REJECTED_QUOTA: "Recusado por cota",
  REJECTED_CAPACITY: "Recusado por capacidade",
  REJECTED_CIRCUIT_OPEN: "Recusado por disjuntor aberto",
  SHED: "Descartado",
};

const SHED_REASON_LABELS = {
  BACKLOG_HARD_LIMIT: "Limite rígido de fila",
  CONCURRENCY_EXHAUSTED: "Concorrência esgotada",
  QUOTA_EXHAUSTED: "Cota esgotada",
  CIRCUIT_OPEN: "Disjuntor aberto",
};

const SCOPE_TYPE_LABELS = {
  GLOBAL: "Global",
  SERVICE_CLASS: "Classe de serviço",
  WORKER_TYPE: "Tipo de worker",
  SCHEDULE: "Agendamento",
  ADAPTER_BINDING: "Vínculo de adapter",
};

const NO_LIMIT_TEXT = "sem limite";

export function capacityModeLabel(mode) {
  const value = String(mode || "").toUpperCase();
  return MODE_LABELS[value] || value || "—";
}

export function capacityModeTone(mode) {
  const value = String(mode || "").toUpperCase();
  if (value === "ENFORCED") return "ok";
  if (value === "MONITOR_ONLY") return "warn";
  return "muted";
}

export function pressureLevelTone(level) {
  const value = String(level || "").toUpperCase();
  if (value === "NORMAL") return "ok";
  if (value === "ELEVATED" || value === "HIGH") return "warn";
  if (value === "CRITICAL") return "danger";
  return "muted";
}

export function circuitPhaseTone(phase) {
  const value = String(phase || "").toUpperCase();
  if (value === "CLOSED") return "ok";
  if (value === "HALF_OPEN") return "warn";
  if (value === "OPEN") return "danger";
  return "muted";
}

export function admissionResultTone(result) {
  const value = String(result || "").toUpperCase();
  if (value === "ADMITTED") return "ok";
  if (value === "DELAYED") return "warn";
  if (value.startsWith("REJECTED") || value === "SHED") return "danger";
  return "muted";
}

/** Rótulo textual sempre acompanhado do código: a situação nunca depende só da cor. */
export function statusText(labels, value) {
  const code = String(value || "").toUpperCase();
  if (!code) return "—";
  return `${labels[code] || code} (${code})`;
}

export function pressureLevelText(level) {
  return statusText(PRESSURE_LABELS, level);
}

export function circuitPhaseText(phase) {
  return statusText(CIRCUIT_LABELS, phase);
}

export function admissionResultText(result) {
  return statusText(RESULT_LABELS, result);
}

export function scopeTypeLabel(scopeType) {
  const value = String(scopeType || "").toUpperCase();
  return SCOPE_TYPE_LABELS[value] || value || "—";
}

export function shedReasonText(reason) {
  if (!reason) return null;
  return statusText(SHED_REASON_LABELS, reason);
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

export function ageMs(isoValue, nowMs = Date.now()) {
  if (!isoValue) return null;
  const parsed = Date.parse(isoValue);
  if (Number.isNaN(parsed)) return null;
  return Math.max(0, nowMs - parsed);
}

/** Idade desconhecida não é lida como leitura fresca. */
export function freshnessText(isoValue, nowMs = Date.now(), staleAfterMs = STALE_AFTER_MS) {
  const age = ageMs(isoValue, nowMs);
  if (age == null) return "Sem marca de tempo";
  return age > staleAfterMs ? `${formatAgeMs(age)} (envelhecida)` : `${formatAgeMs(age)} atrás`;
}

export function formatWhen(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

export function formatLimit(value, { zeroMeansNoLimit = false } = {}) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  if (numeric < 0) return NO_LIMIT_TEXT;
  if (zeroMeansNoLimit && numeric === 0) return NO_LIMIT_TEXT;
  return String(numeric);
}

export function formatUsage(used, limit, options) {
  return `${Number(used ?? 0)} / ${formatLimit(limit, options)}`;
}

/**
 * Estado de exibição derivado da leitura. Uma leitura sem marca de tempo ou antiga vira `stale`
 * — o console nunca apresenta um retrato envelhecido como situação corrente.
 */
export function capacityViewState(snapshot, nowMs = Date.now(), staleAfterMs = STALE_AFTER_MS) {
  if (!snapshot) return "empty";
  if (String(snapshot.mode || "").toUpperCase() === "DISABLED") return "disabled";
  const hasContent =
    (snapshot.pressure || []).length > 0 ||
    (snapshot.policies || []).length > 0 ||
    (snapshot.bulkheads || []).length > 0 ||
    (snapshot.circuits || []).length > 0;
  if (!hasContent) return "empty";
  const age = ageMs(snapshot.calculatedAt, nowMs);
  if (age == null || age > staleAfterMs) return "stale";
  return "ready";
}

export function summarizePressure(pressure = []) {
  const counts = { NORMAL: 0, ELEVATED: 0, HIGH: 0, CRITICAL: 0, UNKNOWN: 0 };
  for (const item of pressure) {
    const level = String(item?.level || "UNKNOWN").toUpperCase();
    counts[level] = (counts[level] || 0) + 1;
  }
  const worst = ["CRITICAL", "HIGH", "ELEVATED", "UNKNOWN", "NORMAL"].find((level) => counts[level] > 0);
  return { counts, worst: worst || null, total: pressure.length };
}

/** O backend publica fases e contadores; a razão da transição só aparece quando o dado existe. */
export function circuitTransitionNote(circuit) {
  const explicit = circuit?.lastTransitionReason || circuit?.transitionReason;
  if (explicit) return String(explicit);
  const phase = String(circuit?.phase || "").toUpperCase();
  if (phase === "OPEN" && circuit?.openedAt) {
    return `Aberto em ${formatWhen(circuit.openedAt)} após ${circuit.failureCount ?? 0} falha(s)`;
  }
  if (phase === "HALF_OPEN") {
    return `Prova liberada${circuit?.probeAfter ? ` a partir de ${formatWhen(circuit.probeAfter)}` : ""}`;
  }
  return null;
}

function StatusChip({ tone, children, testId }) {
  return (
    <span className={`status-chip state-${tone}`} data-testid={testId}>
      {children}
    </span>
  );
}

function Disclosure({ id, title, subtitle, count, open, onToggle, children }) {
  const contentId = `capacity-section-${id}`;
  return (
    <section className="cap-section">
      <button
        type="button"
        className="cap-disclosure"
        aria-expanded={open}
        aria-controls={contentId}
        data-testid={`capacity-toggle-${id}`}
        onClick={onToggle}
      >
        <span className="cap-disclosure-mark" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
        <span>
          <strong>{title}</strong>
          {count == null ? null : <span className="muted"> ({count})</span>}
          {subtitle ? <span className="muted cap-disclosure-sub">{subtitle}</span> : null}
        </span>
      </button>
      <div id={contentId} data-testid={contentId} hidden={!open}>
        {children}
      </div>
    </section>
  );
}

export default function CapacityResilience() {
  const [status, setStatus] = useState("loading");
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [loadedAt, setLoadedAt] = useState(null);
  const [extraDecisions, setExtraDecisions] = useState(null);
  const [decisionsError, setDecisionsError] = useState(null);
  const [decisionsBusy, setDecisionsBusy] = useState(false);
  const [open, setOpen] = useState({
    pressure: true,
    resilience: false,
    shedding: false,
  });

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    setExtraDecisions(null);
    setDecisionsError(null);
    getCapacitySnapshot({ signal: controller.signal })
      .then((data) => {
        setSnapshot(data);
        setError(null);
        setLoadedAt(Date.now());
        setStatus(capacityViewState(data, Date.now()));
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

  const refresh = useCallback(() => setReloadToken((token) => token + 1), []);

  const toggle = useCallback(
    (id) => setOpen((current) => ({ ...current, [id]: !current[id] })),
    [],
  );

  const pressure = snapshot?.pressure || [];
  const bulkheads = snapshot?.bulkheads || [];
  const circuits = snapshot?.circuits || [];
  const policies = snapshot?.policies || [];
  const decisions = extraDecisions || snapshot?.recentDecisions || [];
  const mode = String(snapshot?.mode || "").toUpperCase();
  const reference = loadedAt || Date.now();
  const summary = useMemo(() => summarizePressure(pressure), [pressure]);
  const quotaScopes = useMemo(
    () => pressure.filter((item) => Number(item?.quotaLimit) > 0),
    [pressure],
  );
  const partialData = Boolean(snapshot) && snapshot?.dataQuality?.complete === false;
  const showContent = Boolean(snapshot) && status !== "disabled";

  async function loadMoreDecisions() {
    if (decisionsBusy) return;
    setDecisionsBusy(true);
    setDecisionsError(null);
    try {
      const data = await getCapacityDecisions(DECISION_PAGE_SIZE);
      setExtraDecisions(data?.decisions || []);
    } catch (failure) {
      setDecisionsError(
        failure.status === 404
          ? "Registro de decisões indisponível ou não autorizado nesta credencial."
          : failure.message || "Falha ao carregar as decisões de admissão.",
      );
    } finally {
      setDecisionsBusy(false);
    }
  }

  return (
    <section
      className="panel-card"
      aria-labelledby="capacity-title"
      data-testid="capacity-resilience"
    >
      <div className="detail-head">
        <div>
          <h2 id="capacity-title">Capacidade &amp; Resiliência</h2>
          <p className="muted">
            Leitura do governo de admissão: pressão por escopo, bulkheads, disjuntores e as decisões
            recentes de cota e descarte. O console observa a política publicada — não altera limite
            nenhum.
          </p>
        </div>
        <div className="detail-actions">
          <span className="pill mock-badge">DEMONSTRAÇÃO MOCK</span>
          <button type="button" className="ghost" onClick={refresh} data-testid="capacity-refresh">
            Atualizar
          </button>
        </div>
      </div>

      <div className="banner warn" role="status" data-testid="capacity-boundary-banner">
        {BOUNDARY_BANNER_TEXT}
      </div>

      {status === "loading" && <p role="status">Carregando o governo de capacidade…</p>}

      {status === "disabled" && (
        <p className="muted" role="status" data-testid="capacity-disabled">
          Capability desabilitada ou console indisponível (spider.capacity.enabled /
          spider.capacity.http.enabled). Nenhuma política, pressão ou decisão é simulada no cliente.
        </p>
      )}

      {status === "unauthorized" && (
        <p className="error" role="alert" data-testid="capacity-unauthorized">
          Credencial sem permissão para o governo de capacidade. Solicite a autorização de leitura de
          capacidade.
        </p>
      )}

      {status === "empty" && (
        <p className="muted" role="status" data-testid="capacity-empty">
          Módulo habilitado sem nenhum escopo publicado. Ausência de política observada não é lida
          como folga de capacidade.
        </p>
      )}

      {status === "error" && (
        <p className="error" role="alert" data-testid="capacity-error">
          Governo de capacidade indisponível: {error?.message}
        </p>
      )}

      {showContent && (
        <>
          <div
            className="stat-row"
            aria-label="Resumo executivo de capacidade"
            data-testid="capacity-executive"
          >
            <div>
              <span className="muted">Modo do governo</span>
              <strong className={`state-${capacityModeTone(mode)}`} data-testid="capacity-mode">
                {capacityModeLabel(mode)} ({mode || "—"})
              </strong>
            </div>
            <div>
              <span className="muted">Pressão mais alta observada</span>
              <strong
                className={`state-${pressureLevelTone(summary.worst)}`}
                data-testid="capacity-worst-pressure"
              >
                {summary.worst ? pressureLevelText(summary.worst) : "Sem escopo observado"}
              </strong>
            </div>
            <div>
              <span className="muted">Escopos observados</span>
              <strong data-testid="capacity-scope-count">{summary.total}</strong>
            </div>
            <div>
              <span className="muted">Disjuntores fora de fechado</span>
              <strong data-testid="capacity-open-circuits">
                {
                  circuits.filter((circuit) => String(circuit.phase || "").toUpperCase() !== "CLOSED")
                    .length
                }
              </strong>
            </div>
            <div>
              <span className="muted">Calculado em</span>
              <strong data-testid="capacity-calculated-at" title={snapshot.calculatedAt || ""}>
                {formatWhen(snapshot.calculatedAt)}
              </strong>
            </div>
          </div>

          <p className="muted" data-testid="capacity-mode-note">
            {MODE_NOTES[mode] || "Modo do governo não declarado nesta leitura."}
          </p>

          <p className="muted">
            Fronteira declarada: {snapshot.boundary || "—"} · integrações{" "}
            {snapshot.integrationBoundary || "—"} · políticas publicadas {policies.length}
          </p>

          <p className="muted" data-testid="capacity-summary-counts">
            Distribuição da pressão: Normal {summary.counts.NORMAL} · Elevada{" "}
            {summary.counts.ELEVATED} · Alta {summary.counts.HIGH} · Crítica {summary.counts.CRITICAL}{" "}
            · Indeterminada {summary.counts.UNKNOWN}.
          </p>

          {status === "stale" && (
            <p className="banner warn" role="status" data-testid="capacity-stale">
              Leitura envelhecida ({freshnessText(snapshot.calculatedAt, reference)}). Atualize antes
              de tratar estes números como a situação corrente.
            </p>
          )}

          {partialData && (
            <p className="muted" role="status" data-testid="capacity-partial">
              Leitura parcial. Fontes ausentes:{" "}
              {(snapshot.dataQuality?.missingSources || []).join(", ") || "não informadas"}.
              {(snapshot.dataQuality?.warnings || []).length
                ? ` Avisos: ${snapshot.dataQuality.warnings.join(" · ")}.`
                : ""}{" "}
              Contagem incompleta não é lida como capacidade disponível.
            </p>
          )}

          <Disclosure
            id="pressure"
            title="Pressão por escopo"
            subtitle="Ocupação, fila pendente, cota e frescor da observação"
            count={pressure.length}
            open={open.pressure}
            onToggle={() => toggle("pressure")}
          >
            {pressure.length === 0 ? (
              <p className="muted">Nenhum escopo com pressão publicada.</p>
            ) : (
              <div className="table-wrap">
                <table data-testid="capacity-pressure">
                  <caption className="sr-caption">
                    Pressão consolidada por escopo de capacidade
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Escopo</th>
                      <th scope="col">Situação</th>
                      <th scope="col">Ocupação</th>
                      <th scope="col">Fila pendente</th>
                      <th scope="col">Cota na janela</th>
                      <th scope="col">Disjuntor</th>
                      <th scope="col">Frescor</th>
                      <th scope="col">Observação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pressure.map((item) => (
                      <tr key={item.scopeKey} data-testid={`capacity-pressure-${item.scopeKey}`}>
                        <th scope="row">
                          <span className="mono">{item.scopeKey}</span>
                          <span className="muted cap-scope-meta">
                            {scopeTypeLabel(item.scopeType)} · política {item.policyRef || "—"}
                          </span>
                        </th>
                        <td>
                          <StatusChip tone={pressureLevelTone(item.level)}>
                            {pressureLevelText(item.level)}
                          </StatusChip>
                        </td>
                        <td>{formatUsage(item.occupied, item.capacity, { zeroMeansNoLimit: true })}</td>
                        <td>
                          {item.backlogCount ?? 0} · brando {formatLimit(item.softBacklogLimit)} ·
                          rígido {formatLimit(item.hardBacklogLimit)}
                        </td>
                        <td>{formatUsage(item.quotaUsed, item.quotaLimit, { zeroMeansNoLimit: true })}</td>
                        <td>
                          <StatusChip tone={circuitPhaseTone(item.circuitPhase)}>
                            {circuitPhaseText(item.circuitPhase)}
                          </StatusChip>
                        </td>
                        <td title={item.observedAt || ""}>
                          {freshnessText(item.observedAt, reference)}
                        </td>
                        <td className="muted">{item.explanation || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted">
              Ocupação e fila são contagens da leitura atual; “{NO_LIMIT_TEXT}” significa proteção
              desligada na política, não folga aferida.
            </p>
          </Disclosure>

          <Disclosure
            id="resilience"
            title="Bulkheads e disjuntores"
            subtitle="Isolamento por escopo e fase dos disjuntores"
            count={bulkheads.length + circuits.length}
            open={open.resilience}
            onToggle={() => toggle("resilience")}
          >
            <h4>Bulkheads ({bulkheads.length})</h4>
            {bulkheads.length === 0 ? (
              <p className="muted">
                Nenhum bulkhead registrado nesta leitura — o estado é em memória e recomeça vazio
                após reinício do processo.
              </p>
            ) : (
              <div className="table-wrap">
                <table data-testid="capacity-bulkheads">
                  <caption className="sr-caption">Estado observável dos bulkheads</caption>
                  <thead>
                    <tr>
                      <th scope="col">Escopo</th>
                      <th scope="col">Situação</th>
                      <th scope="col">Ocupação</th>
                      <th scope="col">Em espera</th>
                      <th scope="col">Atualizado em</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bulkheads.map((bulkhead) => {
                      const saturated =
                        Number(bulkhead.capacity) > 0 &&
                        Number(bulkhead.occupied) >= Number(bulkhead.capacity);
                      return (
                        <tr
                          key={bulkhead.scopeKey}
                          data-testid={`capacity-bulkhead-${bulkhead.scopeKey}`}
                        >
                          <th scope="row" className="mono">
                            {bulkhead.scopeKey}
                          </th>
                          <td>
                            <StatusChip tone={saturated ? "danger" : "ok"}>
                              {saturated ? "Saturado (SATURATED)" : "Com vaga (AVAILABLE)"}
                            </StatusChip>
                          </td>
                          <td>
                            {formatUsage(bulkhead.occupied, bulkhead.capacity, {
                              zeroMeansNoLimit: true,
                            })}
                          </td>
                          <td>{bulkhead.waiting ?? 0}</td>
                          <td title={bulkhead.updatedAt || ""}>{formatWhen(bulkhead.updatedAt)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <h4>Disjuntores ({circuits.length})</h4>
            {circuits.length === 0 ? (
              <p className="muted">
                Nenhum disjuntor registrado nesta leitura — ausência de registro não é lida como
                integração saudável.
              </p>
            ) : (
              <div className="table-wrap">
                <table data-testid="capacity-circuits">
                  <caption className="sr-caption">Fase observável dos disjuntores</caption>
                  <thead>
                    <tr>
                      <th scope="col">Escopo</th>
                      <th scope="col">Fase</th>
                      <th scope="col">Falhas</th>
                      <th scope="col">Sucessos</th>
                      <th scope="col">Provas em curso</th>
                      <th scope="col">Última transição</th>
                    </tr>
                  </thead>
                  <tbody>
                    {circuits.map((circuit) => {
                      const note = circuitTransitionNote(circuit);
                      return (
                        <tr
                          key={circuit.scopeKey}
                          data-testid={`capacity-circuit-${circuit.scopeKey}`}
                        >
                          <th scope="row" className="mono">
                            {circuit.scopeKey}
                          </th>
                          <td>
                            <StatusChip tone={circuitPhaseTone(circuit.phase)}>
                              {circuitPhaseText(circuit.phase)}
                            </StatusChip>
                          </td>
                          <td>{circuit.failureCount ?? 0}</td>
                          <td>{circuit.successCount ?? 0}</td>
                          <td>{circuit.probeInFlight ?? 0}</td>
                          <td className="muted" title={circuit.updatedAt || ""}>
                            {note || `Sem transição registrada · ${formatWhen(circuit.updatedAt)}`}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Disclosure>

          <Disclosure
            id="shedding"
            title="Cotas e descarte de carga"
            subtitle="Cotas por janela e decisões recentes de admissão"
            count={decisions.length}
            open={open.shedding}
            onToggle={() => toggle("shedding")}
          >
            <h4>Cotas por janela ({quotaScopes.length})</h4>
            {quotaScopes.length === 0 ? (
              <p className="muted">Nenhum escopo com cota declarada nesta leitura.</p>
            ) : (
              <ul className="cap-quota-list" data-testid="capacity-quotas">
                {quotaScopes.map((item) => (
                  <li key={item.scopeKey} data-testid={`capacity-quota-${item.scopeKey}`}>
                    <span className="mono">{item.scopeKey}</span>
                    <span>
                      consumo {formatUsage(item.quotaUsed, item.quotaLimit)} ·{" "}
                      {pressureLevelText(item.level)}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            <h4>Decisões recentes de admissão ({decisions.length})</h4>
            {decisions.length === 0 ? (
              <p className="muted">
                Nenhuma decisão registrada. O registro é em memória e recomeça vazio após reinício do
                processo.
              </p>
            ) : (
              <ul className="cap-decision-list" data-testid="capacity-decisions">
                {decisions.map((decision) => {
                  const shed = shedReasonText(decision.shedReason);
                  return (
                    <li
                      key={decision.decisionId}
                      data-testid={`capacity-decision-${decision.decisionId}`}
                    >
                      <div className="cap-decision-head">
                        <StatusChip tone={admissionResultTone(decision.result)}>
                          {admissionResultText(decision.result)}
                        </StatusChip>
                        {decision.monitorOnly ? (
                          <span className="pill">Somente observação</span>
                        ) : null}
                        <span className="muted">{formatWhen(decision.decidedAt)}</span>
                      </div>
                      <p className="muted cap-decision-meta">
                        Motivo <span className="mono">{decision.reasonCode || "—"}</span> · política{" "}
                        <span className="mono">{decision.policyRef || "—"}</span>
                        {decision.policyVersion ? ` (versão ${decision.policyVersion})` : ""} ·
                        escopo <span className="mono">{decision.scopeRef || "—"}</span> (
                        {scopeTypeLabel(decision.scopeType)})
                        {shed ? ` · descarte ${shed}` : ""}
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}

            <div className="detail-actions">
              <button
                type="button"
                className="ghost"
                onClick={loadMoreDecisions}
                disabled={decisionsBusy}
                data-testid="capacity-load-decisions"
              >
                {decisionsBusy ? "Carregando decisões…" : "Carregar decisões recentes"}
              </button>
            </div>
            {decisionsError && (
              <p className="error" role="alert" data-testid="capacity-decisions-error">
                {decisionsError}
              </p>
            )}
            <p className="muted">
              Sob observação o desfecho fica no motivo prefixado por MONITOR_ONLY_ e o trabalho segue
              adiante; nada é recusado.
            </p>
          </Disclosure>
        </>
      )}
    </section>
  );
}
