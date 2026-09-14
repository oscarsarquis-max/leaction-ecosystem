import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import SegSenseLogo from '../components/SegSenseLogo';
import RouteFocus from '../components/RouteFocus';
import { apiBaseUrl } from '../api/systemInfo';
import {
  isConfirmedPreProposal,
  isConfirmedSimulatedQuote,
  submitDemoProtectionJourney,
  type DemoJourneyItem,
  type DemoJourneyProjection,
} from '../api/demoProtectionJourney';
import { resolveDemoContextSource, type GovernedContextSource } from '../api/demoContextSources';
import { ApiClientError } from '../api/errors';
import '../demonstration/demonstration.css';
import './integrated-mvp.css';
import SimulationEvidencePanel from './SimulationEvidencePanel';
import { humanJourneyStatus } from './humanJourneyStatus';
import {
  FAMILY_SOURCE_PATH,
  FIRES_SOURCE_PATH,
  INCOME_SOURCE_PATH,
  INTENT_COMPARE,
  INTENT_EFFECTIVE,
  INTENT_HOME,
  INTENT_UNDERSTAND,
  REVOKED_SOURCE_PATH,
  centsToReais,
  classifyIntention,
  declaredThemeFromText,
  governedSourceUrl,
  humanElementLabel,
  humanIntentionLabel,
  humanThemeLabel,
  intentionInterpretation,
  reaisToCents,
  speechRecognitionCtor,
} from './demoJourneyInputs';

const WATERMARK =
  'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO';
const QUOTE_WATERMARK =
  'SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO';

const DISCARD_NOTE =
  'A tentativa anterior foi descartada. As entradas atuais ainda não foram enviadas.';

function isAbortError(caught: unknown): boolean {
  return (
    (caught instanceof DOMException && caught.name === 'AbortError') ||
    (caught instanceof Error && caught.name === 'AbortError')
  );
}

export default function IntegratedMvpPage() {
  const [declaredContext, setDeclaredContext] = useState('');
  const [declaredIntention, setDeclaredIntention] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [resolved, setResolved] = useState<GovernedContextSource | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [contextChoice, setContextChoice] = useState<'source' | ''>('');
  const [dwellingType, setDwellingType] = useState('');
  const [insuredAmountReais, setInsuredAmountReais] = useState('');
  const [coverPeriodMonths, setCoverPeriodMonths] = useState('12');
  const [speechTarget, setSpeechTarget] = useState<'context' | 'intention' | null>(null);
  const [speechState, setSpeechState] = useState<'unsupported' | 'idle' | 'listening' | 'denied'>(
    () => (speechRecognitionCtor() ? 'idle' : 'unsupported'),
  );
  const [phase, setPhase] = useState<'form' | 'awaiting' | 'done'>('form');
  const [result, setResult] = useState<DemoJourneyProjection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [attemptSerial, setAttemptSerial] = useState(0);
  const [discardedNote, setDiscardedNote] = useState<string | null>(null);
  const [askQuoteFields, setAskQuoteFields] = useState(false);

  const sourceUrlRef = useRef('');
  const resolveGenRef = useRef(0);
  const resolveAbortRef = useRef<AbortController | null>(null);
  const submitAbortRef = useRef<AbortController | null>(null);
  const submitSerialRef = useRef(0);

  const speechCtor = speechRecognitionCtor();
  const declaredTheme = declaredThemeFromText(declaredContext);
  const classifiedIntention = classifyIntention(declaredIntention);
  const conflict =
    Boolean(resolved && declaredTheme && declaredTheme !== 'conflict' && declaredTheme !== resolved.elements?.theme);
  const familyUrl = governedSourceUrl(FAMILY_SOURCE_PATH);
  const incomeUrl = governedSourceUrl(INCOME_SOURCE_PATH);
  const firesUrl = governedSourceUrl(FIRES_SOURCE_PATH);
  const revokedUrl = governedSourceUrl(REVOKED_SOURCE_PATH);
  const missingCodes = result?.missingQuestions?.map((item) => item.code) ?? result?.missingContext ?? [];
  const showQuoteQuestions =
    askQuoteFields ||
    missingCodes.includes('dwelling_type') ||
    missingCodes.includes('insured_amount') ||
    missingCodes.includes('cover_period');

  function rotateKey(): string {
    const next = crypto.randomUUID();
    setIdempotencyKey(next);
    setAttemptSerial((value) => value + 1);
    return next;
  }

  function discardCompletedAttempt() {
    if (phase !== 'done') {
      return;
    }
    setResult(null);
    setError(null);
    setPhase('form');
    rotateKey();
    setDiscardedNote(DISCARD_NOTE);
  }

  function cancelInFlightAttempt() {
    submitAbortRef.current?.abort();
    submitSerialRef.current += 1;
    setResult(null);
    setError(null);
    setPhase('form');
    rotateKey();
    setDiscardedNote('A tentativa em curso foi cancelada. Nada desta solicitação permanece na jornada atual.');
  }

  async function resolveUrl(url: string) {
    const trimmed = url.trim();
    const gen = ++resolveGenRef.current;
    resolveAbortRef.current?.abort();
    const controller = new AbortController();
    resolveAbortRef.current = controller;
    if (!trimmed) {
      setResolved(null);
      setResolveError(null);
      return;
    }
    setResolveError(null);
    try {
      const source = await resolveDemoContextSource(apiBaseUrl(), trimmed, controller.signal);
      if (gen !== resolveGenRef.current || trimmed !== sourceUrlRef.current.trim()) {
        return;
      }
      setResolved(source);
    } catch (caught) {
      if (isAbortError(caught) || gen !== resolveGenRef.current || trimmed !== sourceUrlRef.current.trim()) {
        return;
      }
      setResolved(null);
      setResolveError(caught instanceof ApiClientError ? caught.message : 'O link não pôde ser resolvido.');
    }
  }

  function onSourceUrlChange(value: string) {
    setSourceUrl(value);
    sourceUrlRef.current = value;
    resolveGenRef.current += 1;
    resolveAbortRef.current?.abort();
    setResolved(null);
    setResolveError(null);
    discardCompletedAttempt();
  }

  function startDictation(target: 'context' | 'intention') {
    if (!speechCtor) {
      setSpeechState('unsupported');
      return;
    }
    const recognition = new speechCtor();
    recognition.lang = 'pt-BR';
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((resultItem) => resultItem[0]?.transcript ?? '')
        .join(' ')
        .trim();
      if (transcript) {
        if (target === 'context') {
          setDeclaredContext((current) => (current ? `${current} ${transcript}` : transcript));
        } else {
          setDeclaredIntention((current) => (current ? `${current} ${transcript}` : transcript));
        }
        discardCompletedAttempt();
      }
    };
    recognition.onerror = (event) => {
      setSpeechState(event.error === 'not-allowed' ? 'denied' : 'idle');
      setSpeechTarget(null);
    };
    recognition.onend = () => {
      setSpeechState((current) => (current === 'listening' ? 'idle' : current));
      setSpeechTarget(null);
    };
    try {
      recognition.start();
      setSpeechState('listening');
      setSpeechTarget(target);
    } catch {
      setSpeechState('denied');
      setSpeechTarget(null);
    }
  }

  async function submit(event: { preventDefault: () => void }) {
    event.preventDefault();
    if (!resolved && !declaredTheme) {
      setError('Descreva um contexto sintético (por exemplo, incêndios nas proximidades) ou use um link governado.');
      return;
    }
    if ((conflict || declaredTheme === 'conflict') && contextChoice !== 'source') {
      setError('Há conflito entre a fonte e o relato. Escolha usar a fonte governada ou complemente o texto.');
      return;
    }
    submitAbortRef.current?.abort();
    const controller = new AbortController();
    submitAbortRef.current = controller;
    const serial = ++submitSerialRef.current;
    setError(null);
    setResult(null);
    setDiscardedNote(null);
    setPhase('awaiting');
    setAttemptSerial((value) => value + 1);
    const objective = classifiedIntention;
    try {
      const projection = await submitDemoProtectionJourney(apiBaseUrl(), objective, idempotencyKey, {
        sourceUrl: sourceUrl.trim() || undefined,
        declaredContext: declaredContext.trim() || undefined,
        declaredIntention: declaredIntention.trim() || undefined,
        contextChoice: contextChoice || undefined,
        intentionConfirmed: true,
        dwellingType: dwellingType || undefined,
        insuredAmountCents: reaisToCents(insuredAmountReais),
        coverPeriodMonths: coverPeriodMonths || undefined,
      }, controller.signal);
      if (serial !== submitSerialRef.current) {
        return;
      }
      setResult(projection);
      setPhase('done');
      const missing = projection.missingQuestions?.map((item) => item.code) ?? projection.missingContext ?? [];
      if (
        missing.includes('dwelling_type') ||
        missing.includes('insured_amount') ||
        missing.includes('cover_period')
      ) {
        setAskQuoteFields(true);
      }
    } catch (caught) {
      if (isAbortError(caught) || serial !== submitSerialRef.current) {
        return;
      }
      setResult(null);
      setPhase('done');
      if (caught instanceof ApiClientError) {
        setError(caught.message);
        return;
      }
      setError('A jornada integrada está indisponível. A UI não inventa possibilidades nem prêmio.');
    }
  }

  function startNewAttempt() {
    submitAbortRef.current?.abort();
    submitSerialRef.current += 1;
    setResult(null);
    setError(null);
    setPhase('form');
    setDiscardedNote(null);
    rotateKey();
    setAskQuoteFields(false);
  }

  const possibilities = result && isConfirmedPreProposal(result) ? result.items ?? [] : [];
  const quote = result && isConfirmedSimulatedQuote(result) ? result.simulatedQuote : null;
  const showOutcome = phase === 'done';
  const waiting = phase === 'awaiting';
  const intentionLabel = result ? humanIntentionLabel(result.declaredObjective) : null;
  const submitLabel =
    classifiedIntention === INTENT_HOME
      ? 'Gerar cotação simulada'
      : classifiedIntention === INTENT_UNDERSTAND || classifiedIntention === INTENT_COMPARE
        ? 'Ver possibilidades ilustrativas'
        : 'Continuar';

  return (
    <div className="demo-page mvp-page">
      <RouteFocus />
      <a className="skip-link" href="#conteudo">
        Ir para o conteúdo
      </a>
      <header className="demo-banner mvp-watermark" role="banner">
        <p className="demo-disclaimer">{result?.watermark || WATERMARK}</p>
      </header>
      <header className="demo-top mvp-top">
        <Link to="/" aria-label="Voltar à apresentação">
          <SegSenseLogo surface="public" />
        </Link>
        <nav className="mvp-nav">
          <Link to="/">Voltar à apresentação</Link>
          {' · '}
          <Link to="/demonstracao/icatu">Cenário Icatu (não oficial, separado)</Link>
        </nav>
      </header>
      <main id="conteudo" className="demo-main mvp-journey" tabIndex={-1}>
        <section className="demo-card mvp-hero" aria-labelledby="mvp-title">
          <p className="demo-badge demo-badge--live">MVP integrado sintético</p>
          {phase === 'form' && !result ? (
            <p className="mvp-kind">Configuração local — ainda não houve envio nesta página.</p>
          ) : null}
          <h1 id="mvp-title">Contexto, o que você quer e simulação</h1>
          <p className="mvp-promise">
            Diga o que aconteceu e o que deseja. Dados sintéticos. Uma cotação aqui é só simulação; não é
            oferta Icatu nem contratação.
          </p>
        </section>

        {discardedNote ? (
          <p className="demo-card mvp-discard-note" role="status">
            {discardedNote}
          </p>
        ) : null}

        <form className="mvp-journey-form" onSubmit={(event) => { void submit(event); }}>
          <fieldset disabled={waiting}>
            <section className="demo-card mvp-block" aria-labelledby="source-title">
              <h2 id="source-title">1. Fonte ou relato</h2>
              <p>
                Use um exemplo sintético, sem dados pessoais, CPF, nome, endereço ou telefone. O SegSense
                não recebe nem grava arquivo de áudio. A transcrição, se houver, aparece neste campo para
                revisão. Sem microfone, use só o texto. O ditado só começa se você pedir.
              </p>
              <label htmlFor="declared-context">Descreva o contexto</label>
              <textarea
                id="declared-context"
                value={declaredContext}
                disabled={waiting}
                onChange={(event) => {
                  setDeclaredContext(event.target.value);
                  discardCompletedAttempt();
                }}
                rows={4}
                placeholder="Ex.: Houve incêndios nas proximidades."
              />
              <div className="mvp-dictation">
                <button
                  className="button-secondary"
                  type="button"
                  onClick={() => {
                    startDictation('context');
                  }}
                  disabled={speechState === 'unsupported' || speechState === 'listening'}
                >
                  {speechTarget === 'context' && speechState === 'listening' ? 'Ouvindo…' : 'Ditar contexto'}
                </button>
                {speechState === 'unsupported' ? (
                  <p>Reconhecimento de fala indisponível neste navegador. O texto permanece utilizável.</p>
                ) : null}
                {speechState === 'denied' ? (
                  <p>Permissão de microfone negada. Continue pelo texto.</p>
                ) : null}
              </div>
              <label htmlFor="source-url">Usar contexto de um link</label>
              <input
                id="source-url"
                value={sourceUrl}
                disabled={waiting}
                onChange={(event) => {
                  onSourceUrlChange(event.target.value);
                }}
                onBlur={() => {
                  void resolveUrl(sourceUrl);
                }}
                placeholder={firesUrl}
              />
              <p className="mvp-source-hints">
                Exemplos governados:
                <button
                  type="button"
                  className="mvp-linkish"
                  onClick={() => {
                    onSourceUrlChange(firesUrl);
                    void resolveUrl(firesUrl);
                  }}
                >
                  incêndios próximos
                </button>
                {' · '}
                <button
                  type="button"
                  className="mvp-linkish"
                  onClick={() => {
                    onSourceUrlChange(familyUrl);
                    void resolveUrl(familyUrl);
                  }}
                >
                  continuidade familiar
                </button>
                {' · '}
                <button
                  type="button"
                  className="mvp-linkish"
                  onClick={() => {
                    onSourceUrlChange(incomeUrl);
                    void resolveUrl(incomeUrl);
                  }}
                >
                  interrupção de renda
                </button>
                {' · '}
                <button
                  type="button"
                  className="mvp-linkish"
                  onClick={() => {
                    onSourceUrlChange(revokedUrl);
                    void resolveUrl(revokedUrl);
                  }}
                >
                  link revogado
                </button>
              </p>
              {resolveError ? <p role="alert">{resolveError}</p> : null}
            </section>

            <section className="demo-card mvp-block" aria-labelledby="elements-title">
              <h2 id="elements-title">2. Elementos extraídos ou declarados</h2>
              <ContextBoard
                resolved={resolved}
                declaredTheme={declaredTheme}
                declaredContext={declaredContext}
                conflict={conflict || declaredTheme === 'conflict'}
              />
              {(conflict || declaredTheme === 'conflict') ? (
                <label className="mvp-choice mvp-confirm">
                  <input
                    type="checkbox"
                    checked={contextChoice === 'source'}
                    onChange={(event) => {
                      setContextChoice(event.target.checked ? 'source' : '');
                      discardCompletedAttempt();
                    }}
                  />
                  Usar os elementos da fonte governada (o relato diferente não será sobrescrito em silêncio).
                </label>
              ) : null}
            </section>

            <section className="demo-card mvp-block" aria-labelledby="intent-title">
              <h2 id="intent-title">3. Sua intenção</h2>
              <p>
                Escreva com as suas palavras. O clique em um artigo não é intenção. Você pode corrigir o
                texto e a interpretação antes de continuar.
              </p>
              <label htmlFor="declared-intention">O que você quer fazer?</label>
              <textarea
                id="declared-intention"
                value={declaredIntention}
                disabled={waiting}
                onChange={(event) => {
                  const next = event.target.value;
                  setDeclaredIntention(next);
                  if (classifyIntention(next) !== INTENT_HOME) {
                    setAskQuoteFields(false);
                  }
                  discardCompletedAttempt();
                }}
                rows={3}
                placeholder="Ex.: Quero contratar um seguro residencial"
              />
              <div className="mvp-dictation">
                <button
                  className="button-secondary"
                  type="button"
                  onClick={() => {
                    startDictation('intention');
                  }}
                  disabled={speechState === 'unsupported' || speechState === 'listening'}
                >
                  {speechTarget === 'intention' && speechState === 'listening' ? 'Ouvindo…' : 'Ditar o que você quer'}
                </button>
              </div>
              {declaredIntention.trim() ? (
                <p role="status" className="mvp-interpretation">
                  {intentionInterpretation(classifiedIntention)}
                </p>
              ) : null}
              {classifiedIntention === INTENT_HOME ? (
                <p>
                  Vamos calcular uma simulação; contratar de verdade depende de seguradora e produto
                  autorizados.
                </p>
              ) : null}
              {classifiedIntention === INTENT_EFFECTIVE ? (
                <p role="status">
                  Um pedido de contratação efetiva, assinatura, pagamento ou emissão continua bloqueado.
                </p>
              ) : null}

              {showQuoteQuestions ? (
                <div className="mvp-quote-questions">
                  <h3>Perguntas para a simulação</h3>
                  <p>Valores hipotéticos. Não informe endereço, CPF, nome ou telefone.</p>
                  <label htmlFor="dwelling-type">Tipo de imóvel (hipotético)</label>
                  <select
                    id="dwelling-type"
                    value={dwellingType}
                    onChange={(event) => {
                      setDwellingType(event.target.value);
                      discardCompletedAttempt();
                    }}
                  >
                    <option value="">Escolha</option>
                    <option value="APARTMENT">Apartamento</option>
                    <option value="HOUSE">Casa</option>
                  </select>
                  <label htmlFor="insured-amount">Valor de proteção desejado (R$)</label>
                  <input
                    id="insured-amount"
                    inputMode="decimal"
                    value={insuredAmountReais}
                    onChange={(event) => {
                      setInsuredAmountReais(event.target.value);
                      discardCompletedAttempt();
                    }}
                    placeholder="300000"
                  />
                  <label htmlFor="cover-period">Período</label>
                  <select
                    id="cover-period"
                    value={coverPeriodMonths}
                    onChange={(event) => {
                      setCoverPeriodMonths(event.target.value);
                      discardCompletedAttempt();
                    }}
                  >
                    <option value="12">12 meses</option>
                  </select>
                </div>
              ) : null}

              {(result?.missingQuestions ?? [])
                .filter((item) => item.code === 'intention' || item.code === 'home_intention')
                .map((item) => (
                  <p key={item.code}>{item.prompt}</p>
                ))}

              <button className="button-primary" type="submit" disabled={waiting}>
                {submitLabel}
              </button>
              {phase === 'done' ? (
                <button className="button-secondary mvp-new-attempt" type="button" onClick={startNewAttempt}>
                  Nova tentativa (nova chave)
                </button>
              ) : null}
            </section>
          </fieldset>
          {waiting ? (
            <button className="button-secondary mvp-cancel-attempt" type="button" onClick={cancelInFlightAttempt}>
              Cancelar esta tentativa
            </button>
          ) : null}
        </form>

        {waiting ? (
          <p className="demo-card mvp-awaiting" aria-live="polite">
            Solicitação enviada; aguardando o resultado desta tentativa…
          </p>
        ) : null}
        {error ? (
          <p className="demo-card" role="alert">
            {error}
          </p>
        ) : null}

        {showOutcome && result ? (
          <section className="demo-card mvp-print-scenario" aria-labelledby="scenario-title">
            <h2 id="scenario-title">Cenário desta tentativa</h2>
            <p>
              {result.contextSourceTitle || 'Contexto sintético'}
              {intentionLabel ? ` · intenção: ${intentionLabel}` : ''}
            </p>
            {result.intentionInterpretation ? <p>{result.intentionInterpretation}</p> : null}
          </section>
        ) : null}

        {showOutcome && result && quote && isConfirmedSimulatedQuote(result) ? (
          <section className="demo-card mvp-block mvp-print-outcome mvp-quote" aria-labelledby="quote-title">
            <h2 id="quote-title">Cotação simulada</h2>
            <p className="mvp-premium">
              {quote.premiumAnnualCents != null ? centsToReais(quote.premiumAnnualCents) : ''}
            </p>
            <p>Prêmio anual simulado para {quote.coverPeriodMonths ?? 12} meses.</p>
            {quote.insuredAmountCents != null ? (
              <p>Capital declarado nesta simulação: {centsToReais(quote.insuredAmountCents)}.</p>
            ) : null}
            <p>
              O artigo sobre incêndios, se usado, é só o fato que disparou a conversa. Ele não prova risco do
              seu imóvel e não entra na conta.
            </p>
            <h3>Como este valor foi calculado</h3>
            <p>{quote.humanCalculation || 'O valor veio do cálculo desta execução no simulador demonstrativo.'}</p>
            {(quote.premises ?? []).map((premise) => (
              <p key={premise}>{premise}</p>
            ))}
            <p className="mvp-watermark">{result.watermark || QUOTE_WATERMARK}</p>
            <p>Isto não é apólice, proposta de seguradora nem oferta Icatu.</p>
          </section>
        ) : null}

        {showOutcome && result && !quote ? (
          <>
            <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="possibilities-title">
              <h2 id="possibilities-title">Possibilidades ilustrativas</h2>
              {possibilities.length > 0 ? (
                <PossibilityLists items={possibilities} />
              ) : (
                <p role="status">
                  {humanJourneyStatus(result.status)}.
                  {result.status === 'MISSING_CONTEXT'
                    ? ' Responda às perguntas acima e envie de novo.'
                    : ' Nenhuma possibilidade ilustrativa nesta tentativa.'}
                </p>
              )}
            </section>
            <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="why-title">
              <h2 id="why-title">Por que surgiram</h2>
              <p>{result.explanation}</p>
            </section>
            <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="broker-title">
              <h2 id="broker-title">O que ainda depende de corretora ou seguradora</h2>
              {(result.pendingForBroker ?? []).length > 0 ? (
                (result.pendingForBroker ?? []).map((pending) => (
                  <p key={pending}>{pending}</p>
                ))
              ) : (
                <p>Nenhuma pendência humana veio nesta resposta.</p>
              )}
              <p className="mvp-watermark">{result.watermark || WATERMARK}</p>
              <p>Isto não é contrato Icatu. A URL governada não prova a vida real.</p>
            </section>
          </>
        ) : null}

        {showOutcome ? (
          <details className="demo-card mvp-secondary mvp-technical-fold">
            <summary>Detalhes técnicos desta tentativa</summary>
            <SimulationEvidencePanel
              key={attemptSerial}
              projection={result}
              errorMessage={error}
              idempotencyKey={idempotencyKey}
              attemptSerial={attemptSerial}
            />
            {result ? <TechnicalIds projection={result} /> : null}
            <p>
              Fora desta demonstração: Intent Contract pleno, CTX-004, Data Plane, URL pública
              arbitrária, cotação e produtos de seguradora autorizada.
            </p>
          </details>
        ) : null}
      </main>
    </div>
  );
}

function PossibilityLists({ items }: { items: DemoJourneyItem[] }) {
  const illustrative = items.filter((item) => item.kind !== 'JOURNEY_STEP');
  const nextSteps = items.filter((item) => item.kind === 'JOURNEY_STEP');
  return (
    <>
      {illustrative.length > 0 ? (
        <ul className="mvp-possibilities">
          {illustrative.map((item) => (
            <PossibilityItem key={item.code} item={item} />
          ))}
        </ul>
      ) : null}
      {nextSteps.length > 0 ? (
        <>
          <h3>Próximos passos</h3>
          <ul className="mvp-possibilities">
            {nextSteps.map((item) => (
              <PossibilityItem key={item.code} item={item} />
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}

function PossibilityItem({ item }: { item: DemoJourneyItem }) {
  const need = publicNeedLabel(item.needAddressed);
  return (
    <li>
      <h3>{item.title}</h3>
      <p>Ilustrativo — não é contrato Icatu nem oferta.</p>
      {need ? <p>Necessidade contextual: {need}</p> : null}
      {item.pertinence ? <p>{item.pertinence}</p> : null}
      {item.limits ? <p>{item.limits}</p> : null}
    </li>
  );
}

function publicNeedLabel(value: string | null | undefined): string | null {
  const mapped = humanElementLabel(value);
  if (mapped) {
    return mapped;
  }
  if (value && !/_/.test(value)) {
    return value;
  }
  return null;
}

function ContextBoard({
  resolved,
  declaredTheme,
  declaredContext,
  conflict,
}: {
  resolved: GovernedContextSource | null;
  declaredTheme: string | null;
  declaredContext: string;
  conflict: boolean;
}) {
  if (!resolved && !declaredTheme && !declaredContext) {
    return <p>Ainda não há elementos de contexto. Use o texto, o ditado ou um link governado.</p>;
  }
  return (
    <div className="mvp-board">
      <h3>Elementos do contexto</h3>
      {resolved ? <GovernedElements resolved={resolved} /> : null}
      {declaredTheme ? (
        <p>
          Relato mapeado no SegSense: tema {humanThemeLabel(declaredTheme) ?? 'do esquema limitado'}. O
          texto original não é enviado à Spider; o mapeamento é determinístico no SegSense, não uma
          interpretação da Spider.
        </p>
      ) : declaredContext ? (
        <p>Do relato: o texto não mapeia o esquema limitado desta demo.</p>
      ) : null}
      {conflict ? <p role="status">Conflito: fonte e relato apontam temas diferentes. Nada foi sobrescrito.</p> : null}
    </div>
  );
}

function GovernedElements({ resolved }: { resolved: GovernedContextSource }) {
  const themeLabel = humanThemeLabel(resolved.elements?.theme);
  const situationLabel = humanElementLabel(resolved.elements?.situation);
  return (
    <p>
      Fonte editorial governada: {resolved.title} · {resolved.sourceLabel} · {resolved.version}.
      {themeLabel ? ` Tema: ${themeLabel}.` : ''}
      {situationLabel ? ` Situação: ${situationLabel}.` : ''} Publicação da fonte rotulada à parte. O
      artigo integral não é copiado. A URL não prova a vida real nem o risco de um imóvel.
    </p>
  );
}

function TechnicalIds({ projection }: { projection: DemoJourneyProjection }) {
  const confirmed = isConfirmedPreProposal(projection) || isConfirmedSimulatedQuote(projection);
  return (
    <dl className="mvp-technical-ids">
      <div>
        <dt>Identificador SegSense</dt>
        <dd>{projection.id}</dd>
      </div>
      {projection.spiderDecisionId ? (
        <div>
          <dt>Decisão Spider</dt>
          <dd>{projection.spiderDecisionId}</dd>
        </div>
      ) : null}
      <div>
        <dt>Correlação</dt>
        <dd>{projection.correlationId}</dd>
      </div>
      {confirmed && projection.capabilityId ? (
        <div>
          <dt>Capability</dt>
          <dd>{projection.capabilityId}</dd>
        </div>
      ) : null}
      {confirmed && projection.providerRequestId ? (
        <div>
          <dt>Pedido ao provedor</dt>
          <dd>{projection.providerRequestId}</dd>
        </div>
      ) : null}
      {confirmed && projection.mockResultId ? (
        <div>
          <dt>Referência do simulador</dt>
          <dd>{projection.mockResultId}</dd>
        </div>
      ) : null}
      {projection.satelliteContractVersion ? (
        <div>
          <dt>Contrato</dt>
          <dd>
            {projection.satelliteId} · {projection.satelliteRole} · {projection.satelliteContractVersion}
          </dd>
        </div>
      ) : null}
    </dl>
  );
}
