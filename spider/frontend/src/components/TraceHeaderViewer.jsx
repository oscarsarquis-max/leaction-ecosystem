import { extractTraceId } from "../lib/trace";

/**
 * @param {{
 *  traceparent: string|null,
 *  seenAt: { originator?: boolean, spider?: boolean, legado?: boolean, jwt?: boolean }
 * }} props
 */
export function TraceHeaderViewer({ traceparent, seenAt = {} }) {
  const traceId = extractTraceId(traceparent);

  return (
    <section className="obs-card" aria-label="Rastreabilidade W3C">
      <header className="obs-card__head">
        <div>
          <p className="obs-kicker">W3C Trace Context</p>
          <h2>Inspetor de traceparent</h2>
        </div>
      </header>

      <div className="trace-box">
        <code className="trace-box__value">
          {traceparent || "00-……………………trace-id……………………-……parent……-01"}
        </code>
      </div>

      {traceId ? (
        <p className="muted-line">
          Trace ID estável na jornada: <strong className="mono">{traceId}</strong>
        </p>
      ) : (
        <p className="muted-line">O mesmo ID deve navegar Originador → Spider → Legado → JWT.</p>
      )}

      <ul className="hop-list">
        <li className={seenAt.originator ? "is-on" : ""}>
          <span>Originador :8081</span>
          <em>{seenAt.originator ? "injetado" : "—"}</em>
        </li>
        <li className={seenAt.spider ? "is-on" : ""}>
          <span>SPIDER :8080</span>
          <em>{seenAt.spider ? "propagado" : "—"}</em>
        </li>
        <li className={seenAt.legado ? "is-on" : ""}>
          <span>Legado :8082</span>
          <em>{seenAt.legado ? "recebido" : "—"}</em>
        </li>
        <li className={seenAt.jwt ? "is-on" : ""}>
          <span>Claim JWT</span>
          <em>{seenAt.jwt ? "embutido" : "—"}</em>
        </li>
      </ul>
    </section>
  );
}
