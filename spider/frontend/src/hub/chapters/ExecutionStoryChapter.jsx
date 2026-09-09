import { useState } from "react";
import { PIPELINE_STEPS } from "../content.js";
import { Callout, EvidencePanel, SectionEyebrow, SectionHeading } from "../primitives.jsx";

export default function ExecutionStoryChapter() {
  const [selectedId, setSelectedId] = useState("entendimento");
  const selected = PIPELINE_STEPS.find((item) => item.id === selectedId) ?? PIPELINE_STEPS[1];

  return (
    <section className="sx-chapter" id="como-funciona" data-testid="hub-how">
      <div className="sx-container">
        <SectionEyebrow>04 — Como funciona</SectionEyebrow>
        <SectionHeading>Uma frase vira execução por um encadeamento governado.</SectionHeading>
        <p className="sx-intro">
          Selecione uma etapa. O Spider não improvisa o caminho depois de compreender o pedido.
        </p>
        <div className="sx-pipeline" role="tablist" aria-label="Pipeline de execução" data-testid="hub-flow">
          {PIPELINE_STEPS.map((step) => (
            <button
              key={step.id}
              type="button"
              role="tab"
              aria-selected={selectedId === step.id}
              className={`sx-pipe-step sx-zone-${step.zone}${selectedId === step.id ? " is-on" : ""}`}
              onClick={() => setSelectedId(step.id)}
            >
              {step.short}
            </button>
          ))}
        </div>
        <div className="sx-boundary" data-testid="hub-boundary">
          <div>
            <p className="sx-label">Probabilístico</p>
            <p>IA interpreta linguagem e contexto.</p>
          </div>
          <p className="sx-boundary-mark">Intent Contract</p>
          <div>
            <p className="sx-label">Determinístico</p>
            <p>Policy, plano, capacidades e rotas.</p>
          </div>
        </div>
        <EvidencePanel label="O que acontece">
          <div className="sx-pipe-detail" data-testid="pipeline-detail">
            <h3>{selected.short}</h3>
            <p>
              <b>O que acontece.</b> {selected.happens}
            </p>
            <p>
              <b>Por que existe.</b> {selected.why}
            </p>
            <p>
              <b>Quem decide.</b> {selected.who}
            </p>
            <p>
              <b>Qual é o resultado.</b> {selected.result}
            </p>
          </div>
        </EvidencePanel>
        <Callout testId="hub-ai-principle">
          <h3>{selected.iaLabel || selected.decideLabel || "IA interpreta. Spider decide."}</h3>
          <p>
            A IA transforma linguagem e contexto em uma representação estruturada. A partir daí,
            planejamento, políticas, capacidades e resolução permanecem governados.
          </p>
        </Callout>
      </div>
    </section>
  );
}
