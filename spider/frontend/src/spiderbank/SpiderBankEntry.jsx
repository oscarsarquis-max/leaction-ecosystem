import { useEffect, useMemo, useState } from "react";
import { getSpiderBankEntry, opaqueContextIdFromLocation, understandObjective } from "./api.js";
import { arrivalNarrative, directArrivalNarrative } from "./arrivalCopy.js";
import ProofDrawer from "./ProofDrawer.jsx";
import UnderstandingDrawer from "./UnderstandingDrawer.jsx";

const SCENARIO_A =
  "Perdi parte da safra, tenho compromissos vencendo e preciso de recursos para preparar o próximo plantio.";

export default function SpiderBankEntry() {
  const ctx = useMemo(() => opaqueContextIdFromLocation(window.location.search), []);
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [understandingOpen, setUnderstandingOpen] = useState(false);
  const [objective, setObjective] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [understanding, setUnderstanding] = useState(null);

  useEffect(() => {
    document.documentElement.dataset.surface = "spiderbank";
    return () => {
      delete document.documentElement.dataset.surface;
    };
  }, []);

  useEffect(() => {
    if (!ctx) {
      setPayload(null);
      setError(null);
      return undefined;
    }
    const controller = new AbortController();
    getSpiderBankEntry(ctx, { signal: controller.signal })
      .then((data) => {
        setPayload(data);
        setError(null);
      })
      .catch((err) => {
        if (err.name !== "AbortError") setError(err);
      });
    return () => controller.abort();
  }, [ctx]);

  const page = payload?.page || {};
  const click = payload?.click || {};
  const direct = !ctx;
  const narrative = direct
    ? directArrivalNarrative()
    : arrivalNarrative(page, payload?.partnerPublicName || "CampoAberto");
  const showContextStory = Boolean(payload) || direct;
  const human = understanding?.human;
  const technical = understanding?.technical;
  const status = understanding?.status;
  const understood = Boolean(understanding) && status !== "FAILED";
  const needAmount = status === "NEED_AMOUNT";
  const pathReady = status === "UNDERSTOOD" && human?.path;

  async function onDeclareObjective(event) {
    event.preventDefault();
    if (!objective.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await understandObjective({
        contextId: ctx,
        objective: objective.trim(),
      });
      setUnderstanding(result);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function onContinueAmount(event) {
    event.preventDefault();
    if (!amount.trim() || busy || !technical?.decisionId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await understandObjective({
        contextId: ctx,
        objective: objective.trim(),
        amount: amount.trim(),
        decisionId: technical.decisionId,
      });
      setUnderstanding(result);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sb-root" data-testid="spiderbank-entry">
      <header className="sb-nav">
        <p className="sb-wordmark">SPIDERBANK</p>
        <p className="sb-nav-role">Banco Contextual</p>
      </header>

      <section className="sb-fold" data-testid="spiderbank-hero">
        <div className="sb-fold-copy">
          <p className="sb-eyebrow">Banco Contextual</p>
          <h1>
            Um banco que
            <br />
            <em>entende primeiro.</em>
          </h1>
          <p className="sb-fold-lead">
            O SpiderBank considera o seu momento, a sua necessidade e o seu objetivo antes de
            determinar o melhor caminho para ajudá-lo.
          </p>
          <p className="sb-fold-quiet">
            Antes de oferecer um produto, queremos compreender o seu momento e o que você precisa
            resolver.
          </p>
        </div>
        {direct || payload ? (
          <aside className="sb-fold-aside" data-testid="fold-moment">
            <p className="sb-aside-kicker">Seu momento</p>
            <p className="sb-aside-title">{narrative.human}</p>
            {narrative.partnerName ? (
              <p className="sb-aside-origin">Origem: {narrative.partnerName}</p>
            ) : (
              <p className="sb-aside-origin">Conte-nos o que precisa resolver.</p>
            )}
          </aside>
        ) : null}
      </section>

      {showContextStory ? (
        <main className="sb-story" data-testid="story-path">
          <article className="sb-chapter" data-testid="origin-context">
            <p className="sb-num">01</p>
            <div>
              <p className="sb-eyebrow">Seu momento</p>
              <h2>
                {direct
                  ? "Você chegou diretamente ao SpiderBank."
                  : "Nós já temos algum contexto sobre a situação em que você chegou."}
              </h2>
              <p className="sb-chapter-lead" data-testid="arrival-lead">
                {narrative.lead}
              </p>
              <p className="visually-hidden" data-testid="arrival-banner">
                {narrative.banner}
              </p>
              {direct ? (
                <p className="sb-human" data-testid="direct-entry">
                  Conte-nos o que precisa resolver.
                </p>
              ) : (
                <>
                  <dl className="sb-quiet">
                    <div>
                      <dt>Origem</dt>
                      <dd data-testid="origin-name">{narrative.partnerName}</dd>
                    </div>
                    <div>
                      <dt>Conteúdo</dt>
                      <dd data-testid="origin-title">{narrative.content}</dd>
                    </div>
                    <div>
                      <dt>Neste instante</dt>
                      <dd data-testid="context-status">{narrative.status}</dd>
                    </div>
                  </dl>
                  <p className="sb-principle" data-testid="context-is-not-intent">
                    Conhecer o contexto não significa presumir o que você deseja. Seu objetivo sempre vem
                    de você.
                  </p>
                  <button type="button" className="sb-text-link" data-testid="open-provenance" onClick={() => setOpen(true)}>
                    Como identificamos este contexto?
                  </button>
                </>
              )}
            </div>
          </article>

          <article className="sb-chapter sb-chapter-objective" data-testid="objective-block">
            <p className="sb-num">02</p>
            <div>
              <p className="sb-eyebrow">Seu objetivo</p>
              <h2>
                O que você precisa
                <br />
                resolver agora?
              </h2>
              <p className="sb-chapter-lead">
                Conte o que está acontecendo. Não precisa saber o nome de um produto financeiro.
              </p>
              <p className="sb-human">Agora queremos ouvir você.</p>
              <form onSubmit={onDeclareObjective}>
                <label className="visually-hidden" htmlFor="client-objective">
                  O que você precisa resolver agora?
                </label>
                <textarea
                  id="client-objective"
                  data-testid="objective-input"
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  placeholder={`Ex.: ${SCENARIO_A}`}
                />
                <button
                  className="sb-cta"
                  type="submit"
                  data-testid="understand-objective"
                  disabled={!objective.trim() || busy}
                >
                  Entender meu objetivo
                </button>
              </form>
              {understood ? (
                <div className="sb-understood" data-testid="understanding-block">
                  <p className="sb-eyebrow">{human?.headline}</p>
                  <p className="sb-human" data-testid="understanding-copy">
                    {human?.understanding}
                  </p>
                  {human?.cropFailureNoted ? (
                    <p className="sb-crop-note" data-testid="crop-failure-human">
                      Este entendimento considera o conteúdo da reportagem sobre quebra de safra.
                    </p>
                  ) : (
                    <p className="visually-hidden" data-testid="crop-failure-absent">
                      CROP_FAILURE ausente
                    </p>
                  )}
                  <p className="sb-policy-human" data-testid="policy-human">
                    {human?.policy}
                  </p>
                  <button
                    type="button"
                    className="sb-text-link"
                    data-testid="open-understanding"
                    onClick={() => setUnderstandingOpen(true)}
                  >
                    Como o Spider entendeu?
                  </button>
                </div>
              ) : null}
              {needAmount ? (
                <form className="sb-amount" onSubmit={onContinueAmount} data-testid="missing-amount">
                  <p className="sb-human">{human?.missing?.question || "De quanto você precisa?"}</p>
                  <label className="visually-hidden" htmlFor="needed-amount">
                    De quanto você precisa?
                  </label>
                  <input
                    id="needed-amount"
                    data-testid="amount-input"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    inputMode="decimal"
                    placeholder="Informe o valor"
                    autoComplete="off"
                  />
                  <button
                    className="sb-cta"
                    type="submit"
                    data-testid="continue-with-amount"
                    disabled={!amount.trim() || busy}
                  >
                    Continuar
                  </button>
                </form>
              ) : null}
            </div>
          </article>

          <article className="sb-chapter" data-testid="path-block">
            <p className="sb-num">03</p>
            <div>
              <p className="sb-eyebrow">Seu caminho</p>
              <h2>
                {pathReady
                  ? human.path.title
                  : "O Spider poderá determinar o que precisa acontecer para ajudá-lo."}
              </h2>
              {pathReady ? (
                <>
                  <ol className="sb-path" data-testid="human-path">
                    {human.path.steps.map((step) => (
                      <li key={step.capabilityId} data-testid={`path-step-${step.capabilityId}`}>
                        <strong>{step.name}</strong>
                        <span>{step.state}</span>
                      </li>
                    ))}
                  </ol>
                  <p className="sb-honest" data-testid="path-honest">
                    {human.path.honest}
                  </p>
                </>
              ) : (
                <p className="sb-chapter-lead">
                  Produto, prazo e condições só aparecem depois — como consequência do seu objetivo, não
                  como ponto de partida.
                </p>
              )}
            </div>
          </article>
        </main>
      ) : null}

      <section className="sb-principles" data-testid="how-it-works">
        <h2>Um banco contextual funciona diferente</h2>
        <div className="sb-principle-row">
          <article>
            <p className="sb-num">Contexto</p>
            <p>Entendemos o momento em que você chegou.</p>
          </article>
          <article>
            <p className="sb-num">Objetivo</p>
            <p>Você nos conta o que precisa resolver.</p>
          </article>
          <article>
            <p className="sb-num">Caminho</p>
            <p>O Spider determina o que precisa acontecer.</p>
          </article>
        </div>
      </section>

      <p className="sb-demo-foot">Demonstração</p>

      {error ? (
        <p className="sb-error" data-testid="spiderbank-error">
          {error.message}
        </p>
      ) : null}

      <span data-testid="journey-contexto" className="visually-hidden">
        {payload || direct ? "concluído" : "ainda não"}
      </span>
      <span data-testid="journey-objetivo" className={objective.trim() && understood ? "is-done visually-hidden" : "visually-hidden"}>
        {objective.trim() && understood ? "concluído" : "ainda não"}
      </span>
      <span data-testid="journey-caminho" className={pathReady ? "is-done visually-hidden" : "visually-hidden"}>
        {pathReady ? "concluído" : "ainda não"}
      </span>
      <span data-testid="journey-entendimento" className={understood ? "is-done visually-hidden" : "visually-hidden"}>
        {understood ? "concluído" : "ainda não"}
      </span>

      <ProofDrawer
        open={open}
        onClose={() => setOpen(false)}
        payload={payload}
        click={click}
        page={page}
        ctx={ctx}
      />
      <UnderstandingDrawer
        open={understandingOpen}
        onClose={() => setUnderstandingOpen(false)}
        understanding={understanding}
      />
    </div>
  );
}
