import { useMemo, useState } from "react";
import { ExecutionTimeline } from "./components/ExecutionTimeline";
import { PayloadInspector } from "./components/PayloadInspector";
import { TraceHeaderViewer } from "./components/TraceHeaderViewer";
import { JwtInspector } from "./components/JwtInspector";
import { generateTraceparent } from "./lib/trace";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function buildTranslated(originator, traceparent) {
  return {
    productId: originator.productId,
    transactionId: originator.transactionId,
    traceparent,
    payload: originator.payload,
    channel: "spider-orchestrator",
  };
}

export default function App() {
  const [status, setStatus] = useState("idle");
  const [activeStep, setActiveStep] = useState(0);
  const [traceparent, setTraceparent] = useState(null);
  const [originatorPayload, setOriginatorPayload] = useState(null);
  const [translatedPayload, setTranslatedPayload] = useState(null);
  const [legacyResponse, setLegacyResponse] = useState(null);
  const [jwtToken, setJwtToken] = useState(null);
  const [latencyMs, setLatencyMs] = useState(null);
  const [error, setError] = useState(null);
  const [problem, setProblem] = useState(null);
  const [hops, setHops] = useState({});

  const busy = status === "running";

  const seenAt = useMemo(
    () => ({
      originator: Boolean(hops.originator),
      spider: Boolean(hops.spider),
      legado: Boolean(hops.legado),
      jwt: Boolean(hops.jwt),
    }),
    [hops],
  );

  async function runFullJourney() {
    setError(null);
    setProblem(null);
    setStatus("running");
    setActiveStep(1);
    setLegacyResponse(null);
    setJwtToken(null);
    setLatencyMs(null);
    setHops({});

    const tp = generateTraceparent();
    const tx = `tx-${Date.now()}`;
    const originator = {
      productId: "CONTA_DIGITAL_ONBOARDING",
      transactionId: tx,
      payload: {
        canal: "console-observabilidade",
        clienteRef: "CLI-OBS-001",
        intent: "onboarding",
      },
    };

    setTraceparent(tp);
    setOriginatorPayload(originator);
    setHops((h) => ({ ...h, originator: true }));
    await sleep(450);

    setActiveStep(2);
    setHops((h) => ({ ...h, spider: true }));
    await sleep(400);

    setActiveStep(3);
    const translated = buildTranslated(originator, tp);
    setTranslatedPayload(translated);
    await sleep(450);

    setActiveStep(4);
    try {
      const res = await fetch("/v1/products/orchestrate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/problem+json, application/json",
          traceparent: tp,
          Authorization: "Bearer demo-console-token",
        },
        body: JSON.stringify(originator),
      });

      const body = await res.json();
      setProblem(body);

      const responseTp = body.traceparent || tp;
      setTraceparent(responseTp);
      setHops((h) => ({ ...h, legado: true }));

      setActiveStep(5);
      setLatencyMs(body.latencyMs ?? null);
      setLegacyResponse(
        body.legacyBody != null
          ? body.legacyBody
          : body.legacyHttpStatus != null
            ? {
                httpStatus: body.legacyHttpStatus,
                status_tecnico: body.status_tecnico,
                detail: body.detail,
                title: body.title,
              }
            : body,
      );
      await sleep(350);

      setActiveStep(6);
      const token = body.stateTransitionToken || null;
      setJwtToken(token);
      if (token) setHops((h) => ({ ...h, jwt: true }));

      // Melhor esforço: confirma callback no originador
      try {
        const cb = await fetch("/originador/api/callbacks");
        if (cb.ok) {
          const list = await cb.json();
          const hit = Array.isArray(list)
            ? list.find((c) => c?.body?.transactionId === tx)
            : null;
          if (hit?.body?.stateTransitionToken) {
            setJwtToken(hit.body.stateTransitionToken);
            setHops((h) => ({ ...h, jwt: true }));
          }
        }
      } catch {
        /* originador pode estar offline; JWT já veio do Spider */
      }

      if (!res.ok && res.status >= 500) {
        setStatus("error");
        setError(body.detail || `Falha HTTP ${res.status}`);
        return;
      }

      setStatus("done");
      setActiveStep(6);
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="obs-shell">
      <header className="obs-top">
        <div>
          <p className="obs-brand">SPIDER · Console de Observabilidade</p>
          <h1>Jornada de orquestração reativa</h1>
          <p className="obs-sub">
            Visualize a mensagem viajando:{" "}
            <strong>service-originador :8081</strong> ──►{" "}
            <strong>SPIDER :8080</strong> ──►{" "}
            <strong>service-legado-financeiro :8082</strong>
          </p>
        </div>
        <button
          type="button"
          className="cta"
          disabled={busy}
          onClick={() => void runFullJourney()}
          data-testid="dispatch-journey"
        >
          {busy ? "Jornada em andamento…" : "Disparar Jornada de Teste Completa"}
        </button>
      </header>

      {error ? (
        <div className="banner-error" role="alert">
          {error}
        </div>
      ) : null}

      <div className="obs-grid">
        <ExecutionTimeline
          activeStep={activeStep}
          status={status}
          latencyMs={latencyMs}
        />

        <div className="obs-stack">
          <TraceHeaderViewer traceparent={traceparent} seenAt={seenAt} />
          <JwtInspector token={jwtToken} />
        </div>
      </div>

      <PayloadInspector
        originatorPayload={originatorPayload}
        translatedPayload={translatedPayload}
        legacyResponse={legacyResponse}
        jwtToken={jwtToken}
      />

      {problem ? (
        <section className="obs-card">
          <header className="obs-card__head">
            <div>
              <p className="obs-kicker">RFC 7807</p>
              <h2>Problem Detail (resposta síncrona do SPIDER)</h2>
            </div>
          </header>
          <pre className="code-block">{JSON.stringify(problem, null, 2)}</pre>
        </section>
      ) : null}
    </div>
  );
}
