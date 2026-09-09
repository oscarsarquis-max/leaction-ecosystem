import { useState } from "react";
import { AFTER_FLOW, BEFORE_FLOW, PROBLEMS } from "../content.js";
import { FlowNode, SectionEyebrow, SectionHeading } from "../primitives.jsx";

export default function ProblemChapter() {
  const [focus, setFocus] = useState(PROBLEMS[0].id);
  const selected = PROBLEMS.find((item) => item.id === focus) ?? PROBLEMS[0];

  return (
    <section className="sx-chapter" id="problema" data-testid="hub-problem">
      <div className="sx-container">
        <SectionEyebrow>02 — Problema</SectionEyebrow>
        <SectionHeading>
          Empresas não têm falta de sistemas. Têm dificuldade de fazê-los trabalhar juntos para um
          objetivo.
        </SectionHeading>
        <p className="sx-intro">
          O Spider introduz uma camada capaz de compreender o objetivo antes de decidir como
          executá-lo.
        </p>
        <div className="sx-compare" data-testid="hub-problem-compare">
          <div>
            <p className="sx-label">Antes do Spider</p>
            <ol className="sx-compare-flow">
              {BEFORE_FLOW.map((node, index) => (
                <li key={node.id}>
                  <FlowNode
                    active={selected.highlights.includes(node.id)}
                    dimmed={!selected.highlights.includes(node.id)}
                  >
                    {node.label}
                  </FlowNode>
                  {index < BEFORE_FLOW.length - 1 ? <span className="sx-down">↓</span> : null}
                </li>
              ))}
            </ol>
          </div>
          <p className="sx-compare-vs">versus</p>
          <div>
            <p className="sx-label">Com Spider</p>
            <ol className="sx-compare-flow">
              {AFTER_FLOW.map((node, index) => (
                <li key={node.id}>
                  <FlowNode active>{node.label}</FlowNode>
                  {index < AFTER_FLOW.length - 1 ? <span className="sx-down">↓</span> : null}
                </li>
              ))}
            </ol>
          </div>
        </div>
        <div className="sx-fragment-nav" role="tablist" aria-label="Onde a fragmentação aparece">
          {PROBLEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={focus === item.id}
              className={`sx-chip-btn${focus === item.id ? " is-on" : ""}`}
              onClick={() => setFocus(item.id)}
            >
              {item.title}
            </button>
          ))}
        </div>
        <p className="sx-copy">{selected.body}</p>
      </div>
    </section>
  );
}
