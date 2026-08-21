import { useState } from "react";

export function shortId(id) {
  if (!id || id.length < 12) return id || "—";
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
}

export function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)} s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export function formatWhen(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function StateBadge({ state, technicalStatus }) {
  const label = state || "UNKNOWN";
  return (
    <span className={`state-badge state-${(label || "").toLowerCase()}`} title={technicalStatus || ""}>
      <span className="state-dot" aria-hidden="true" />
      <span>{label}</span>
      {technicalStatus ? <span className="state-tech"> · {technicalStatus}</span> : null}
    </span>
  );
}

export function JourneyMap({ plan, steps }) {
  const ordered = plan?.data?.orderedSteps || steps?.data?.map((s) => s.stepRef) || [];
  const byRef = Object.fromEntries((steps?.data || []).map((s) => [s.stepRef, s]));
  if (!plan?.available && !steps?.available) {
    return <p className="muted">Plano indisponível ({plan?.reasonCode || "N/A"}).</p>;
  }
  return (
    <ol className="journey-map" aria-label="Mapa do Execution Plan">
      {ordered.map((ref, idx) => {
        const step = byRef[ref];
        const state = step?.state || "PENDING";
        const asyncWait = state === "WAITING_EXTERNAL";
        return (
          <li
            key={ref}
            className={`journey-step journey-${state.toLowerCase()}${asyncWait ? " journey-async" : ""}`}
          >
            <div className="journey-order">{idx + 1}</div>
            <div>
              <strong>{ref}</strong>
              <div className="muted">
                {state}
                {step?.attemptCount != null ? ` · ${step.attemptCount} attempt(s)` : ""}
                {asyncWait ? " · espera assíncrona" : ""}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function TimelineView({ timeline, phaseFilter }) {
  if (!timeline?.available) {
    return <p className="muted">Timeline indisponível ({timeline?.reasonCode || "N/A"}).</p>;
  }
  const events = (timeline.data || []).filter((e) => !phaseFilter || e.phase === phaseFilter);
  if (!events.length) return <p className="muted">Nenhum evento persistido nesta janela.</p>;
  return (
    <ol className="timeline-list" tabIndex={0} aria-label="Timeline canônica">
      {events.map((e) => (
        <li key={e.eventId} className={`tl-item severity-${(e.severity || "INFO").toLowerCase()}`}>
          <div className="tl-meta">
            <time dateTime={e.occurredAt} title={e.occurredAt ? `${e.occurredAt} (UTC)` : undefined}>
              {formatWhen(e.occurredAt)}
            </time>
            <span className="pill">{e.phase}</span>
            <span className="pill muted">{e.source}</span>
          </div>
          <strong>{e.title}</strong>
          <div className="muted">
            {e.eventType}
            {e.stepRef ? ` · step ${e.stepRef}` : ""}
            {e.attemptNumber != null ? ` · attempt #${e.attemptNumber}` : ""}
            {e.durationMs != null ? ` · ${formatDuration(e.durationMs)}` : ""}
          </div>
          {e.safeDescription ? <p>{e.safeDescription}</p> : null}
        </li>
      ))}
    </ol>
  );
}

export function SecurityPosturePanel({ section }) {
  if (!section?.available) {
    return <p className="muted">Postura de segurança indisponível.</p>;
  }
  const d = section.data || {};
  return (
    <dl className="kv-grid" aria-label="Postura de segurança">
      {Object.entries(d).map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function InspectorTabs({ detail }) {
  const [tab, setTab] = useState("resumo");
  const tabs = [
    { id: "resumo", label: "Resumo seguro" },
    { id: "steps", label: "Steps & Attempts" },
    { id: "wait", label: "Wait & Signal" },
    { id: "callback", label: "Callback & Reconciliation" },
    { id: "gov", label: "Governança" },
    { id: "sec", label: "Segurança" },
    { id: "proj", label: "Projeções redigidas" },
  ];
  return (
    <div>
      <div className="tab-row" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? "tab active" : "tab"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="tab-panel" role="tabpanel">
        {tab === "resumo" && (
          <pre className="code-block">{JSON.stringify(detail.summary, null, 2)}</pre>
        )}
        {tab === "steps" && (
          <pre className="code-block">{JSON.stringify(detail.steps, null, 2)}</pre>
        )}
        {tab === "wait" && (
          <pre className="code-block">
            {JSON.stringify({ wait: detail.waitInfo, signal: detail.signal }, null, 2)}
          </pre>
        )}
        {tab === "callback" && (
          <pre className="code-block">
            {JSON.stringify(
              { callback: detail.callback, reconciliation: detail.reconciliation },
              null,
              2,
            )}
          </pre>
        )}
        {tab === "gov" && (
          <pre className="code-block">{JSON.stringify(detail.governance, null, 2)}</pre>
        )}
        {tab === "sec" && <SecurityPosturePanel section={detail.securityPosture} />}
        {tab === "proj" && (
          <pre className="code-block">
            {JSON.stringify(
              {
                request: detail.safeRequestProjection,
                result: detail.safeResultProjection,
              },
              null,
              2,
            )}
          </pre>
        )}
      </div>
    </div>
  );
}
