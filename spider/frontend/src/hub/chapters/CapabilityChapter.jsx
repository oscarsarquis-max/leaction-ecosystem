import { useState } from "react";
import { JOURNEY_CAPABILITIES, RESOLUTION_PATH } from "../content.js";
import { EvidencePanel, SectionEyebrow, SectionHeading, StatusIndicator } from "../primitives.jsx";

export default function CapabilityChapter() {
  const [selectedId, setSelectedId] = useState(JOURNEY_CAPABILITIES[0].id);
  const selected = JOURNEY_CAPABILITIES.find((item) => item.id === selectedId) ?? JOURNEY_CAPABILITIES[0];

  return (
    <section className="sx-chapter" id="capacidades" data-testid="hub-capabilities">
      <div className="sx-container sx-grid">
        <div className="sx-span-5">
          <SectionEyebrow>05 — Capacidades</SectionEyebrow>
          <SectionHeading>
            O Spider não começa pelo sistema. Começa pelo que precisa ser feito.
          </SectionHeading>
          <p className="sx-copy">
            Intent, Execution Plan e Business Capabilities descrevem o trabalho empresarial. Só
            depois a resolução escolhe rota, adapter e sistema.
          </p>
          <p className="sx-intro">Os sistemas podem mudar. A capacidade empresarial permanece.</p>
          <p className="sx-label">Objetivo</p>
          <p className="sx-fact">Manter a produção</p>
          <p className="sx-label">Plano</p>
          <p className="sx-fact">Working capital — continuidade produtiva</p>
        </div>
        <div className="sx-span-7">
          <p className="sx-label">Exemplo de jornada</p>
          <div className="sx-cap-explorer" data-testid="capability-explorer">
            <div className="sx-cap-list" role="tablist" aria-label="Capacidades da jornada">
              {JOURNEY_CAPABILITIES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={selectedId === item.id}
                  className={`sx-cap-item${selectedId === item.id ? " is-on" : ""}`}
                  onClick={() => setSelectedId(item.id)}
                >
                  {item.name}
                </button>
              ))}
            </div>
            <EvidencePanel>
              <div data-testid="capability-panel">
                <StatusIndicator tone="prepared">{selected.status}</StatusIndicator>
                <h3>{selected.name}</h3>
                <p>
                  <b>O que é.</b> {selected.what}
                </p>
                <p>
                  <b>Por que é necessária.</b> {selected.why}
                </p>
                <p>
                  <b>Rota.</b> {selected.route}
                </p>
                <p>
                  <b>Executor.</b> {selected.executor}
                </p>
              </div>
            </EvidencePanel>
          </div>
          <div className="sx-resolve" aria-label="Resolução de capacidade">
            {RESOLUTION_PATH.map((node, index) => (
              <b key={node} className={index === RESOLUTION_PATH.length - 1 ? "is-on" : ""}>
                {node === "Sistema" ? selected.system : node}
              </b>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
