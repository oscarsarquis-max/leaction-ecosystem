import { useState } from "react";
import { EXPLAIN_TRAIL, GOVERNANCE_DIMS } from "../content.js";
import { ExpandableDetail, SectionEyebrow, SectionHeading, StatusIndicator } from "../primitives.jsx";

const SPINE = ["Objetivo", "Policy", "Plan", "Capabilities", "Execution", "Result"];

export default function GovernanceChapter() {
  const [dimId, setDimId] = useState("resilience");
  const [explain, setExplain] = useState(false);
  const dim = GOVERNANCE_DIMS.find((item) => item.id === dimId) ?? GOVERNANCE_DIMS[2];

  return (
    <section className="sx-chapter" id="governanca" data-testid="hub-governance">
      <div className="sx-container sx-grid">
        <div className="sx-span-4">
          <SectionEyebrow>08 — Governança e explicabilidade</SectionEyebrow>
          <SectionHeading>Governado por construção.</SectionHeading>
          <p className="sx-intro">
            A governança envolve a execução inteira. Selecione uma dimensão.
          </p>
          <div className="sx-fragment-nav sx-fragment-nav-col" role="tablist" aria-label="Dimensões">
            {GOVERNANCE_DIMS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={dimId === item.id}
                className={`sx-chip-btn${dimId === item.id ? " is-on" : ""}`}
                onClick={() => setDimId(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="sx-span-8">
          <div className="sx-gov-wrap">
            <ol className="sx-spine">
              {SPINE.map((item) => (
                <li key={item}>
                  <b>✓</b> {item}
                </li>
              ))}
            </ol>
            <aside className="sx-gov-panel" data-testid="governance-panel">
              <h3>{dim.label}</h3>
              <p>{dim.body}</p>
              <ul>
                {dim.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </aside>
          </div>
          <ExpandableDetail
            open={explain}
            onToggle={() => setExplain((value) => !value)}
            label="Ver o que o Spider consegue explicar"
            testId="explain-toggle"
          >
            <ol className="sx-explain-list">
              {EXPLAIN_TRAIL.map((item) => (
                <li key={item.id}>
                  <strong>{item.label}</strong>
                  <span>{item.example}</span>
                </li>
              ))}
            </ol>
            <p className="sx-footnote">Exemplo ancorado em DEMO-002 / CTX-003A — não é telemetria ao vivo.</p>
          </ExpandableDetail>
          <aside className="sx-evidence">
            <StatusIndicator tone="prepared">Arquitetura preparada</StatusIndicator>
            <p className="sx-label">Trusted Evidence</p>
            <p className="sx-attestation">Execução → Evidência → Attestation</p>
            <p>
              A arquitetura prevê atestação criptográfica de decisões relevantes, inclusive por
              ledger distribuído quando o modelo de confiança justificar. Não implementado.
            </p>
          </aside>
        </div>
      </div>
    </section>
  );
}
