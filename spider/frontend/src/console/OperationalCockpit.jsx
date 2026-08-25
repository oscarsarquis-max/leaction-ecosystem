import { useEffect, useMemo, useState } from "react";
import { getOperationalHealth } from "./api";

const WINDOWS = ["PT15M", "PT1H", "PT24H", "P7D"];

const SLI_TITLES = {
  EXECUTION_TECHNICAL_RELIABILITY: "Confiabilidade técnica",
  EXECUTION_LATENCY_P95_MS: "Latência técnica (p95)",
  ASYNC_WAIT_AGED: "Esperas assíncronas envelhecidas",
  CALLBACK_CONFIRMATION_RATIO: "Entrega de callback",
  SIGNAL_ACCEPTANCE_RATIO: "Aceitação de sinais",
  TELEMETRY_COVERAGE: "Cobertura da telemetria",
};

function formatValue(sli) {
  if (sli.value == null) return "—";
  if (sli.unit === "ratio") return `${(sli.value * 100).toFixed(1)}%`;
  if (sli.unit === "ms") return `${Math.round(sli.value)} ms`;
  return String(sli.value);
}

function formatTarget(slo) {
  if (slo?.targetValue == null) return null;
  if (slo.sliCode?.includes("LATENCY")) return `${Math.round(slo.targetValue)} ms`;
  if (slo.targetValue <= 1) return `${(slo.targetValue * 100).toFixed(1)}%`;
  return String(slo.targetValue);
}

function statusTone(status) {
  const s = (status || "").toUpperCase();
  if (s === "HEALTHY" || s === "MET" || s === "AVAILABLE" || s === "OK") return "ok";
  if (s === "DEGRADED" || s === "AT_RISK") return "warn";
  if (s === "UNHEALTHY" || s === "MISSED" || s === "EXHAUSTED") return "danger";
  return "muted";
}

export default function OperationalCockpit() {
  const [window, setWindow] = useState("PT24H");
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    const controller = new AbortController();
    setSnapshot(null);
    setError(null);
    setStatus("loading");
    getOperationalHealth(window, { signal: controller.signal })
      .then((data) => {
        setSnapshot(data);
        setStatus("ok");
      })
      .catch((failure) => {
        if (failure.name === "AbortError") return;
        setError(failure);
        setStatus(
          failure.consoleUnavailable || failure.status === 404 ? "disabled" : "error",
        );
      });
    return () => controller.abort();
  }, [window]);

  const sloBySli = useMemo(() => {
    const map = {};
    for (const slo of snapshot?.sloEvaluations || []) {
      map[slo.sliCode] = slo;
    }
    return map;
  }, [snapshot]);

  return (
    <section className="panel-card" aria-labelledby="health-title" data-testid="operational-cockpit">
      <div className="detail-head">
        <div>
          <h2 id="health-title">Cockpit Operacional</h2>
          <p className="muted">
            Saúde, SLIs e SLOs provisórios calculados a partir de stores e Operational Events reais.
            Não controla a Engine.
          </p>
        </div>
        <label>
          Janela
          <select
            aria-label="Janela de avaliação"
            value={window}
            onChange={(event) => setWindow(event.target.value)}
          >
            {WINDOWS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="banner warn" role="status" data-testid="health-boundary-banner">
        AMBIENTE DE DEMONSTRAÇÃO · MOCK_ONLY · SLOs PROVISÓRIOS — NÃO CONTRATUAIS
      </div>

      {status === "loading" && <p role="status">Calculando saúde operacional…</p>}
      {status === "disabled" && (
        <p className="muted" role="status">
          Capability desabilitada ou console indisponível (spider.operational-health / spider.console).
        </p>
      )}
      {error && status === "error" && (
        <p className="error" role="alert">
          Saúde operacional indisponível: {error.message}
        </p>
      )}

      {snapshot && (
        <>
          <div className="stat-row" aria-label="Resumo de saúde">
            <div>
              <span className="muted">Condição observada</span>
              <strong className={`state-${statusTone(snapshot.overallStatus)}`}>
                {snapshot.overallStatus}
              </strong>
            </div>
            <div>
              <span className="muted">Janela</span>
              <strong>{snapshot.window?.duration || window}</strong>
            </div>
            <div>
              <span className="muted">Calculado em</span>
              <strong>
                {snapshot.generatedAt
                  ? new Date(snapshot.generatedAt).toLocaleString()
                  : "—"}
              </strong>
            </div>
            <div>
              <span className="muted">Qualidade dos dados</span>
              <strong>
                {snapshot.dataQuality?.complete ? "Suficiente" : "Parcial / insuficiente"}
              </strong>
            </div>
          </div>

          <h3>Indicadores (SLI)</h3>
          <ul className="scenario-grid" aria-label="SLIs operacionais">
            {(snapshot.slis || []).map((sli) => {
              const slo = sloBySli[sli.code];
              const title = SLI_TITLES[sli.code] || sli.code;
              return (
                <li key={sli.code} data-testid={`sli-card-${sli.code}`}>
                  <span className={`pill state-${statusTone(sli.status)}`}>{sli.status}</span>
                  <h3>{title}</h3>
                  <strong>{formatValue(sli)}</strong>
                  {slo?.targetValue != null ? (
                    <p className="muted">
                      Objetivo provisório Mock: {formatTarget(slo)} · {slo.status}
                    </p>
                  ) : null}
                  <p className="muted">Amostra: {sli.sampleSize}</p>
                  {sli.explanation ? <p>{sli.explanation}</p> : null}
                </li>
              );
            })}
          </ul>

          {(snapshot.errorBudgets || []).length > 0 && (
            <>
              <h3>Tolerância técnica provisória (error budget)</h3>
              <ul className="scenario-grid" aria-label="Error budgets">
                {snapshot.errorBudgets.map((budget) => (
                  <li key={budget.objectiveCode || budget.sliCode || JSON.stringify(budget)}>
                    <span className={`pill state-${statusTone(budget.status)}`}>
                      {budget.status}
                    </span>
                    <h3>{budget.objectiveCode || "Orçamento"}</h3>
                    <p className="muted">
                      Consumo:{" "}
                      {budget.consumedRatio == null
                        ? "—"
                        : `${(budget.consumedRatio * 100).toFixed(1)}%`}
                      {budget.remainingRatio != null
                        ? ` · restante ${(budget.remainingRatio * 100).toFixed(1)}%`
                        : ""}
                    </p>
                    {budget.explanation ? <p>{budget.explanation}</p> : null}
                  </li>
                ))}
              </ul>
            </>
          )}

          {!snapshot.dataQuality?.complete && (
            <p className="muted" role="status">
              Dados parciais. Fontes ausentes:{" "}
              {(snapshot.dataQuality?.missingSources || []).join(", ") || "não informadas"}.
              Ausência de amostra não é tratada como saudável.
            </p>
          )}
        </>
      )}
    </section>
  );
}
