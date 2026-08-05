const STEPS = [
  {
    id: 1,
    title: "Início — Originador :8081",
    detail: "Emissão da requisição do produto e injeção do traceparent (W3C).",
  },
  {
    id: 2,
    title: "Segurança & Ingress — SPIDER :8080",
    detail: "Recepção no gateway, sanitização de payload e verificação de Bearer Token.",
  },
  {
    id: 3,
    title: "Resolução de Rota & Circuit Breaker",
    detail: "Busca da rota no PostgreSQL / fallback em memória e ativação Resilience4j.",
  },
  {
    id: 4,
    title: "Chamada Legada — Legado :8082",
    detail: "Tradução de payload pelo Engine e chamada WebClient não-bloqueante.",
  },
  {
    id: 5,
    title: "Retorno & Audit",
    detail: "Resposta do legado, audit async em tb_audit_trace e latência (ms).",
  },
  {
    id: 6,
    title: "Conclusão & JWT",
    detail: "Emissão do JWT (iss: leaction-spider) e webhook callback ao Originador.",
  },
];

/**
 * @param {{ activeStep: number, status: 'idle'|'running'|'done'|'error', latencyMs?: number|null }} props
 */
export function ExecutionTimeline({ activeStep = 0, status = "idle", latencyMs = null }) {
  return (
    <section className="obs-card timeline" aria-label="Linha do tempo da orquestração">
      <header className="obs-card__head">
        <div>
          <p className="obs-kicker">Fluxo da mensagem</p>
          <h2>Linha do tempo reativa</h2>
        </div>
        <div className="pipeline" aria-hidden="true">
          <span>8081</span>
          <span className="pipeline__arrow">──►</span>
          <span>SPIDER 8080</span>
          <span className="pipeline__arrow">──►</span>
          <span>8082</span>
        </div>
      </header>

      <ol className="stepper">
        {STEPS.map((step) => {
          const done = activeStep > step.id || (status === "done" && activeStep >= step.id);
          const current = activeStep === step.id && status === "running";
          const failed = status === "error" && activeStep === step.id;
          return (
            <li
              key={step.id}
              className={[
                "stepper__item",
                done ? "is-done" : "",
                current ? "is-current" : "",
                failed ? "is-failed" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div className="stepper__rail" aria-hidden="true">
                <span className="stepper__dot">{step.id}</span>
              </div>
              <div className="stepper__body">
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
                {step.id === 5 && latencyMs != null ? (
                  <p className="stepper__meta">Latência medida: {latencyMs} ms</p>
                ) : null}
                {current ? (
                  <span className="pulse" aria-live="polite">
                    Em trânsito…
                  </span>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
