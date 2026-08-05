import { decodeJwt } from "../lib/jwt";

/**
 * @param {{ token: string|null }} props
 */
export function JwtInspector({ token }) {
  const decoded = decodeJwt(token);

  const status = decoded.payload?.status_tecnico;
  const issuer = decoded.payload?.iss ?? decoded.header?.iss;
  const ok = status === "SUCCESS" || status === "PAYMENT_CONFIRMED";

  return (
    <section className="obs-card jwt-card" aria-label="Decodificador JWT">
      <header className="obs-card__head">
        <div>
          <p className="obs-kicker">Transição de estado</p>
          <h2>JWT Inspector</h2>
        </div>
        {token ? (
          <span className={ok ? "badge badge--ok" : "badge badge--warn"}>
            status_tecnico: {status ?? "n/a"}
          </span>
        ) : null}
      </header>

      {!token ? (
        <p className="muted-line">Aguardando emissão do token assinado pelo SPIDER…</p>
      ) : (
        <>
          <p className="muted-line">
            Issuer esperado: <strong>leaction-spider</strong>
            {issuer ? (
              <>
                {" "}
                · observado: <strong className="mono">{issuer}</strong>
              </>
            ) : null}
          </p>

          <div className="jwt-grid">
            <article>
              <h3>Header</h3>
              <pre className="code-block code-block--sm">
                {JSON.stringify(decoded.header, null, 2)}
              </pre>
            </article>
            <article>
              <h3>Payload</h3>
              <pre className="code-block code-block--sm">
                {JSON.stringify(decoded.payload, null, 2)}
              </pre>
            </article>
            <article>
              <h3>Signature</h3>
              <pre className="code-block code-block--sm mono wrap">
                {decoded.signature || "—"}
              </pre>
            </article>
          </div>

          <div className={ok ? "auth-banner is-ok" : "auth-banner"}>
            {ok
              ? "Token autoriza mudança de estado do cliente no Originador."
              : "Token presente, mas status_tecnico não confirma SUCCESS/PAYMENT_CONFIRMED."}
          </div>
        </>
      )}
    </section>
  );
}
