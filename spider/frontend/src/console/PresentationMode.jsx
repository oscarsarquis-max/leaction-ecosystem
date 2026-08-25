import { useEffect, useState } from "react";
import {
  getPresentationReadiness,
  submitMockScenario,
} from "./api";
import {
  MOCK_SCENARIOS,
  buildCanonicalRequest,
  newIdempotencyKey,
  newTraceparent,
} from "./scenarios";

const CHAPTERS = [
  { id: 1, title: "Propósito universal", body: "Spider orquestra contexto canônico entre canais e adapters Mock nesta fase." },
  { id: 2, title: "Arquitetura", body: "Console é consumidor read-only do Data Plane (ARCH-013)." },
  { id: 3, title: "Estado da implementação", body: "015–018 VERIFIED no Grupo A (4/4); Failure Lab e SLOs provisórios permanecem MOCK_ONLY e OFF_BY_DEFAULT." },
  { id: 4, title: "Jornada ao vivo", body: "Submit canônico real → executionId → detalhe/polling." },
  { id: 5, title: "Plano / steps / retries / assíncrono", body: "Journey map e timeline vêm de dados persistidos." },
  {
    id: 6,
    title: "Failure Lab",
    body:
      "Jornada operacional Mock: cenário RETRY_THEN_SUCCESS (falha transitória e sucesso) → timeline da execução → leitura no Cockpit Operacional → evidência segura com digest e completude. Cenários vêm de catálogo versionado; ausência de observação nunca vira sucesso.",
  },
  { id: 7, title: "Segurança / governança", body: "DenyAll, redaction, posture REDACTED — sem JWT." },
  { id: 8, title: "Mock versus real", body: "Boundary ativa MOCK_ONLY. CORPORATE_SANDBOX (025) e REAL_PILOT (026) são planejados, não ativos." },
  {
    id: 9,
    title: "Roadmap",
    body:
      "Grupos oficiais: A Visibilidade (015–018) → B Runtime (019–021) → C Plataforma (022–024) → D Integração real (025–026). Fonte: docs/roadmap/SPIDER-ROADMAP-IMPLEMENTACAO-016-026.md + manifesto. Atual: 018 Failure Lab (VERIFIED); Grupo A 4/4 completo; 019 elegível (PLANNED, não iniciado).",
  },
];

const LIVE_IDS = new Set([
  "SUCCESS_MULTI_STEP",
  "RETRY_THEN_SUCCESS",
  "WAIT_SIGNAL_RESUME",
  "CALLBACK_RECONCILIATION",
]);

export default function PresentationMode({ onOpenExecution }) {
  const [chapter, setChapter] = useState(1);
  const [readiness, setReadiness] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    const c = new AbortController();
    getPresentationReadiness({ signal: c.signal })
      .then((r) => {
        setReadiness(r);
        setError(null);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e);
      });
    return () => c.abort();
  }, []);

  async function runLive(scenarioId) {
    if (!readiness?.ready) {
      setMsg({ ok: false, text: "Apresentação bloqueada: readiness not-ready. Veja o checklist." });
      return;
    }
    const scenario = MOCK_SCENARIOS.find((s) => s.id === scenarioId);
    if (!scenario) return;
    setBusy(true);
    setMsg(null);
    try {
      const idem = newIdempotencyKey(scenario.id);
      const tp = newTraceparent();
      const body = buildCanonicalRequest(scenario, { idempotencyKey: idem, traceparent: tp });
      const res = await submitMockScenario(body, { idempotencyKey: idem, traceparent: tp });
      const executionId = res.executionId || res.executionRef || res.id;
      setMsg({ ok: true, text: executionId ? `Jornada iniciada: ${executionId}` : "Submetido." });
      if (executionId && onOpenExecution) onOpenExecution(executionId);
    } catch (e) {
      setMsg({
        ok: false,
        text:
          e.status === 404
            ? "Submit canônico indisponível — sem fallback legado."
            : e.message || "Falha na jornada",
      });
    } finally {
      setBusy(false);
    }
  }

  const ch = CHAPTERS.find((c) => c.id === chapter);

  return (
    <section className="panel-card presentation-mode" aria-labelledby="pres-title">
      <div className="detail-head">
        <h2 id="pres-title">Modo Apresentação</h2>
        <span className="pill mock-badge">DEMONSTRAÇÃO MOCK</span>
      </div>
      {error && <p className="error">Readiness indisponível: {error.message}</p>}
      {readiness && (
        <div className="readiness-box" aria-live="polite">
          <p>
            Preflight:{" "}
            <strong>{readiness.ready ? "READY" : "NOT READY"}</strong> · boundary{" "}
            {readiness.boundary} · manifest {readiness.manifestStatus}
          </p>
          <ul className="check-list">
            {(readiness.checks || []).map((c) => (
              <li key={c.code} className={c.passed ? "ok" : "error"}>
                <span aria-hidden="true">{c.passed ? "✓" : "✗"}</span> {c.message}
              </li>
            ))}
          </ul>
          {!readiness.ready && (
            <p className="error" role="alert">
              Demonstração bloqueada até o checklist ficar verde. Não fingimos jornada.
            </p>
          )}
        </div>
      )}
      <nav className="chapter-nav" aria-label="Capítulos da apresentação">
        {CHAPTERS.map((c) => (
          <button
            key={c.id}
            type="button"
            className={chapter === c.id ? "nav-btn active" : "nav-btn"}
            onClick={() => setChapter(c.id)}
          >
            {c.id}. {c.title}
          </button>
        ))}
      </nav>
      <article>
        <h3>
          Capítulo {ch.id}: {ch.title}
        </h3>
        <p>{ch.body}</p>
      </article>
      {chapter === 4 && (
        <div className="scenario-grid-wrap">
          <h4>Jornada ao vivo (canônica)</h4>
          <ul className="scenario-grid">
            {MOCK_SCENARIOS.filter((s) => LIVE_IDS.has(s.id)).map((s) => (
              <li key={s.id}>
                <h3>{s.label}</h3>
                <p className="muted">{s.description}</p>
                <button
                  type="button"
                  className="cta"
                  disabled={busy || !readiness?.ready}
                  onClick={() => runLive(s.id)}
                >
                  Executar ao vivo
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {msg && <p className={msg.ok ? "ok" : "error"}>{msg.text}</p>}
    </section>
  );
}
