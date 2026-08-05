import { useState } from "react";

const TABS = [
  { id: "A", label: "A · Originador" },
  { id: "B", label: "B · Traduzido → Legado" },
  { id: "C", label: "C · Resposta Legado" },
  { id: "D", label: "D · JWT emitido" },
];

/**
 * @param {{
 *  originatorPayload: unknown,
 *  translatedPayload: unknown,
 *  legacyResponse: unknown,
 *  jwtToken: string|null
 * }} props
 */
export function PayloadInspector({
  originatorPayload,
  translatedPayload,
  legacyResponse,
  jwtToken,
}) {
  const [tab, setTab] = useState("A");

  const content = {
    A: originatorPayload,
    B: translatedPayload,
    C: legacyResponse,
    D: jwtToken ? { stateTransitionToken: jwtToken } : null,
  }[tab];

  return (
    <section className="obs-card" aria-label="Inspeção de envelopes">
      <header className="obs-card__head">
        <div>
          <p className="obs-kicker">Envelopes</p>
          <h2>Inspeção de payloads</h2>
        </div>
      </header>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? "tabs__btn is-active" : "tabs__btn"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <pre className="code-block" role="tabpanel">
        {content == null
          ? "// aguardando disparo da jornada…"
          : typeof content === "string"
            ? content
            : JSON.stringify(content, null, 2)}
      </pre>
    </section>
  );
}
