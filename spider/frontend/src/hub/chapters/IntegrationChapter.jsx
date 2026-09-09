import { useState } from "react";
import { INTEGRATION_MODES, SYSTEM_PORTS } from "../content.js";
import { SectionEyebrow, SectionHeading } from "../primitives.jsx";

export default function IntegrationChapter() {
  const [modeId, setModeId] = useState("legacy");
  const mode = INTEGRATION_MODES.find((item) => item.id === modeId) ?? INTEGRATION_MODES[2];

  return (
    <section className="sx-chapter" id="integracao" data-testid="hub-integration">
      <div className="sx-container">
        <SectionEyebrow>06 — Integração</SectionEyebrow>
        <SectionHeading>Integração sem ruptura.</SectionHeading>
        <p className="sx-intro">
          O Spider não exige que todo o ambiente seja modernizado para começar. O contrato
          completo de satélite permanece o norte arquitetural, ainda em preparação.
        </p>
        <div className="sx-integrate-map">
          <div>
            <p className="sx-label">Sistemas</p>
            <ul className="sx-port-list">
              {SYSTEM_PORTS.map((port) => (
                <li key={port}>{port}</li>
              ))}
            </ul>
          </div>
          <div className="sx-path-col" data-testid="integration-path">
            {mode.inbound.map((node, index) => (
              <span key={`in-${node}`}>
                <b>{node}</b>
                {index < mode.inbound.length - 1 ? <span className="sx-down">↓</span> : null}
              </span>
            ))}
          </div>
          <div className="sx-path-col">
            {mode.outbound.map((node, index) => (
              <span key={`out-${node}`}>
                <b>{node}</b>
                {index < mode.outbound.length - 1 ? <span className="sx-down">↓</span> : null}
              </span>
            ))}
          </div>
        </div>
        <div className="sx-fragment-nav" role="tablist" aria-label="Modo de integração">
          {INTEGRATION_MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={modeId === item.id}
              className={`sx-chip-btn${modeId === item.id ? " is-on" : ""}`}
              onClick={() => setModeId(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="sx-copy">{mode.note}</p>
      </div>
    </section>
  );
}
