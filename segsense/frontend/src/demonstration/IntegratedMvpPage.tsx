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
import {
  capturePublicUrl,
  confirmPublicUrlCapture,
  parseCaptureElements,
  type UrlCaptureConfirmation,
  type UrlCaptureProjection,
} from '../api/demoUrlCapture';
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
  dwellingTypeLabel,
  publicQuoteExplanation,
  declaredThemeFromText,
  governedSourceUrl,
  humanCaptureFieldLabel,
  humanCaptureValueLabel,
  humanElementLabel,
  humanIntentionLabel,
  humanThemeLabel,
  intentionInterpretation,
  isPublicCaptureElement,
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
  const [capture, setCapture] = useState<UrlCaptureProjection | null>(null);
  const [captureBusy, setCaptureBusy] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<UrlCaptureConfirmation | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [declaredCorrection, setDeclaredCorrection] = useState('');
  const [keptElementKeys, setKeptElementKeys] = useState<string[]>([]);
  const [elementEdits, setElementEdits] = useState<Record<string, string>>({});
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
    setCapture(null);
    setCaptureError(null);
    setConfirmation(null);
    setDeclaredCorrection('');
    setKeptElementKeys([]);
    setElementEdits({});
    discardCompletedAttempt();
  }

  async function obtainContent() {
    const trimmed = sourceUrl.trim();
    if (!trimmed) {
      setCaptureError('Informe um endereço público e obtenha o conteúdo.');
      return;
    }
    setCaptureBusy(true);
    setCaptureError(null);
    setCapture(null);
    setConfirmation(null);
    setKeptElementKeys([]);
    setElementEdits({});
    setResolved(null);
    setResolveError(null);
    try {
      const projection = await capturePublicUrl(apiBaseUrl(), trimmed);
      setCapture(projection);
      const keys = parseCaptureElements(projection.extractedElementsJson)
        .filter((element) => isPublicCaptureElement(element.key))
        .map((element) => element.key);
      setKeptElementKeys(keys);
      if (projection.publicStatus !== 'AWAITING_REVIEW') {
        setCaptureError(projection.message);
      }
    } catch (caught) {
      setCapture(null);
      setKeptElementKeys([]);
      setCaptureError(
        caught instanceof ApiClientError ? caught.message : 'A captura não concluiu com conteúdo utilizável.',
      );
    } finally {
      setCaptureBusy(false);
    }
  }

  async function confirmExtracted() {
    if (!capture?.captureId || capture.publicStatus !== 'AWAITING_REVIEW') {
      setCaptureError('Obtenha o conteúdo da URL e revise o trecho antes de confirmar.');
      return;
    }
    setConfirmBusy(true);
    setCaptureError(null);
    try {
      const original = parseCaptureElements(capture.extractedElementsJson).filter((element) =>
        isPublicCaptureElement(element.key),
      );
      const corrections: Record<string, string> = {};
      for (const element of original) {
        const edited = elementEdits[element.key]?.trim();
        if (edited && keptElementKeys.includes(element.key) && edited !== element.value) {
          corrections[element.key] = edited;
        }
      }
      const confirmed = await confirmPublicUrlCapture(apiBaseUrl(), capture.captureId, {
        confirmedKeys: keptElementKeys,
        corrections,
        declaredNote: declaredCorrection.trim() || undefined,
      });
      setConfirmation(confirmed);
    } catch (caught) {
      setConfirmation(null);
      setCaptureError(caught instanceof ApiClientError ? caught.message : 'Não foi possível confirmar este contexto.');
    } finally {
      setConfirmBusy(false);
    }
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
    if (capture?.publicStatus === 'AWAITING_REVIEW' && !confirmation) {
      setError('Confirme o contexto extraído da URL antes de continuar.');
      return;
    }
    if (!resolved && !declaredTheme && !confirmation) {
      setError(
        'Descreva um contexto sintético, use um exemplo governado ou obtenha o conteúdo de uma URL pública.',
      );
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
        sourceUrl: confirmation ? undefined : resolved ? sourceUrl.trim() || undefined : undefined,
        declaredContext: declaredContext.trim() || undefined,
        declaredIntention: declaredIntention.trim() || undefined,
        contextChoice: contextChoice || undefined,
        intentionConfirmed: true,
        dwellingType: dwellingType || undefined,
        insuredAmountCents: reaisToCents(insuredAmountReais),
        coverPeriodMonths: coverPeriodMonths || undefined,
        captureId: confirmation?.captureId,
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
  const showIllustrativeOutcome = Boolean(result && !quote && isConfirmedPreProposal(result));
  const showStatusOutcome = Boolean(
    result && !quote && result.status !== 'MISSING_CONTEXT' && !isConfirmedPreProposal(result),
  );
  const quoteExplanation = quote ? publicQuoteExplanation(quote) : null;
  const dwellingLabel = quote ? dwellingTypeLabel(quote.dwellingType) : null;
  const showOutcome = phase === 'done';
  const waiting = phase === 'awaiting';
  const intentionLabel = result ? humanIntentionLabel(result.declaredObjective) : null;
  const extractedElements = parseCaptureElements(capture?.extractedElementsJson).filter((element) =>
    isPublicCaptureElement(element.key),
  );
  const cropPaths = result?.capabilityId === 'DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS';
  const submitLabel =
    confirmation
      ? 'Ver possibilidades para este contexto'
      : classifiedIntention === INTENT_HOME
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
              <label htmlFor="source-url">URL pública</label>
              <input
                id="source-url"
                value={sourceUrl}
                disabled={waiting || captureBusy}
                onChange={(event) => {
                  onSourceUrlChange(event.target.value);
                }}
                placeholder="https://…"
              />
              <p>
                <button
                  className="button-secondary"
                  type="button"
                  disabled={waiting || captureBusy || !sourceUrl.trim()}
                  onClick={() => {
                    void obtainContent();
                  }}
                >
                  {captureBusy ? 'Obtendo conteúdo…' : 'Obter conteúdo da URL'}
                </button>
              </p>
              {captureBusy ? <p role="status">Obtendo a página indicada.</p> : null}
              {captureError ? <p role="alert">{captureError}</p> : null}
              {capture && capture.publicStatus === 'AWAITING_REVIEW' ? (
                <div className="mvp-capture-review">
                  <h3>Revisar contexto extraído</h3>
                  <p>
                    <strong>Título:</strong> {capture.title || 'não detectado'}
                  </p>
                  <p>
                    <strong>Domínio:</strong> {capture.finalHost || 'não disponível'}
                  </p>
                  <p>
                    <strong>URL final:</strong> {capture.finalUrl}
                  </p>
                  <p>
                    <strong>Capturado em (UTC):</strong> {capture.capturedAt}
                  </p>
                  <p>
                    <strong>Texto da fonte:</strong> {capture.excerpt}
                  </p>
                  {capture.normalizedText && capture.normalizedText !== capture.excerpt ? (
                    <details>
                      <summary>Expandir texto extraído (inerte, limitado)</summary>
                      <p className="mvp-extracted-text">{capture.normalizedText}</p>
                    </details>
                  ) : null}
                  {extractedElements.length > 0 ? (
                    <ul className="mvp-element-cards">
                      {extractedElements.map((element) => {
                        const label = humanCaptureFieldLabel(element.key) || element.key;
                        const removed = !keptElementKeys.includes(element.key);
                        const edited = Boolean(elementEdits[element.key]?.trim() && elementEdits[element.key] !== element.value);
                        const displayedValue = elementEdits[element.key] ?? element.value;
                        return (
                          <li key={element.key} className="mvp-element-card">
                            <p>
                              <strong>{label}:</strong> {humanCaptureValueLabel(displayedValue)}
                            </p>
                            <p>
                              Origem:{' '}
                              {removed
                                ? 'Removido — não será enviado como fato da página'
                                : edited
                                  ? 'Declarado/corrigido pela pessoa'
                                  : 'Extraído da página'}
                            </p>
                            {element.evidence ? (
                              <p>
                                Trecho que sustenta este valor: {element.evidence}
                              </p>
                            ) : (
                              <p>Sem trecho da página para este valor.</p>
                            )}
                            <label htmlFor={`capture-edit-${element.key}`}>Corrigir {label.toLowerCase()}</label>
                            <input
                              id={`capture-edit-${element.key}`}
                              type="text"
                              value={displayedValue}
                              disabled={waiting || Boolean(confirmation) || removed}
                              onChange={(event) => {
                                setElementEdits((current) => ({ ...current, [element.key]: event.target.value }));
                              }}
                            />
                            <button
                              className="button-secondary"
                              type="button"
                              disabled={waiting || Boolean(confirmation)}
                              onClick={() => {
                                setKeptElementKeys((current) =>
                                  removed
                                    ? [...current, element.key]
                                    : current.filter((key) => key !== element.key),
                                );
                              }}
                            >
                              {removed ? `Restaurar ${label}` : `Remover ${label}`}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p>Nenhum elemento estruturado foi extraído deste texto. O que faltar pode ser declarado pela pessoa.</p>
                  )}
                  <label htmlFor="url-correction">Complemento ou correção declarada (não apaga o texto da página)</label>
                  <textarea
                    id="url-correction"
                    value={declaredCorrection}
                    disabled={waiting || Boolean(confirmation)}
                    onChange={(event) => {
                      setDeclaredCorrection(event.target.value);
                    }}
                    rows={2}
                    placeholder="Opcional. Isto vira declaração sua, distinta da extração."
                  />
                  <button
                    className="button-secondary"
                    type="button"
                    disabled={confirmBusy || Boolean(confirmation)}
                    onClick={() => {
                      void confirmExtracted();
                    }}
                  >
                    {confirmation ? 'Contexto confirmado' : confirmBusy ? 'Confirmando…' : 'Confirmar este contexto'}
                  </button>
                  {confirmation ? <p role="status">{confirmation.message}</p> : null}
                  <details>
                    <summary>Detalhes técnicos desta tentativa</summary>
                    <p>resultCode: {capture.technical?.resultCode}</p>
                    <p>HTTP: {capture.technical?.httpStatus}</p>
                    <p>MIME: {capture.technical?.contentType}</p>
                    <p>bytesSha256: {capture.technical?.bytesSha256}</p>
                    <p>textSha256: {capture.technical?.textSha256}</p>
                    <p>extrator: {capture.technical?.extractorVersion}</p>
                    <p>seleção principal: {capture.technical?.selectionStrategy}</p>
                  </details>
                </div>
              ) : null}
              <p className="mvp-source-hints">
                Exemplos governados (demonstrações nomeadas, não são captura de URL pública):
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

        {showOutcome && result && result.status !== 'MISSING_CONTEXT' ? (
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
            <h3>Dados usados nesta simulação</h3>
            {quote.insuredAmountCents != null ? (
              <p>Valor de proteção: {centsToReais(quote.insuredAmountCents)}.</p>
            ) : null}
            {dwellingLabel ? <p>Tipo de imóvel: {dwellingLabel}.</p> : null}
            {quote.coverPeriodMonths != null ? <p>Período: {quote.coverPeriodMonths} meses.</p> : null}
            <h3>Como este valor foi calculado</h3>
            <p>
              {quoteExplanation ||
                'O valor veio do cálculo desta execução no simulador demonstrativo, a partir dos dados desta tentativa.'}
            </p>
            <h3>Limites desta simulação</h3>
            <p>
              A regra é fictícia, inventada para demonstrar o software, e não está calibrada ao mercado.
            </p>
            {quote.nearbyFiresDidNotAdjustPremium ? (
              <p>Incêndios próximos na fonte editorial não alteraram o prêmio.</p>
            ) : null}
            <p>
              O resultado veio de um simulador independente nesta execução. Não é cotação emitida por
              seguradora, apólice, proposta nem oferta Icatu.
            </p>
            <p className="mvp-watermark">{result.watermark || QUOTE_WATERMARK}</p>
          </section>
        ) : null}

        {showOutcome && showIllustrativeOutcome && result ? (
          <>
            <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="possibilities-title">
              <h2 id="possibilities-title">
                {cropPaths ? 'Possibilidades demonstrativas (sem prêmio)' : 'Possibilidades ilustrativas'}
              </h2>
              <PossibilityLists items={possibilities} />
            </section>
            <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="why-title">
              <h2 id="why-title">Por que surgiram</h2>
              <p>{result.explanation}</p>
              <p className="mvp-watermark">{result.watermark || WATERMARK}</p>
              <p>
                {cropPaths
                  ? 'Isto não é produto, cobertura, prêmio nem Icatu. O texto capturado não prova que a pessoa é produtora ou sofreu a perda.'
                  : 'Isto não é contrato Icatu. A URL governada não prova a vida real.'}
              </p>
            </section>
            {(result.pendingForBroker ?? []).length > 0 ? (
              <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="broker-title">
                <h2 id="broker-title">
                  {cropPaths
                    ? 'Perguntas sobre informações agrícolas ainda não comprovadas'
                    : 'O que ainda depende de corretora ou seguradora'}
                </h2>
                {(result.pendingForBroker ?? []).map((pending) => (
                  <p key={pending}>{pending}</p>
                ))}
              </section>
            ) : null}
          </>
        ) : null}

        {showOutcome && showStatusOutcome && result ? (
          <section className="demo-card mvp-block mvp-print-outcome" aria-labelledby="status-title">
            <h2 id="status-title">{humanJourneyStatus(result.status)}</h2>
            {result.explanation ? <p>{result.explanation}</p> : null}
            <p className="mvp-watermark">{result.watermark || WATERMARK}</p>
          </section>
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
              Fora desta demonstração: Intent Contract pleno, CTX-004, Data Plane, crawling, execução de
              JavaScript remoto, cotação agrícola em reais e produtos de seguradora autorizada.
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
      {projection.simulatedQuote?.ratingRuleVersion ? (
        <div>
          <dt>Versão da regra demonstrativa</dt>
          <dd>{projection.simulatedQuote.ratingRuleVersion}</dd>
        </div>
      ) : null}
      {projection.simulatedQuote?.dwellingType ? (
        <div>
          <dt>Tipo de imóvel (código)</dt>
          <dd>{projection.simulatedQuote.dwellingType}</dd>
        </div>
      ) : null}
      {projection.simulatedQuote?.dwellingBps != null ? (
        <div>
          <dt>Fator demonstrativo (bps)</dt>
          <dd>{projection.simulatedQuote.dwellingBps}</dd>
        </div>
      ) : null}
      {projection.simulatedQuote?.insuredAmountCents != null ? (
        <div>
          <dt>Capital (centavos)</dt>
          <dd>{projection.simulatedQuote.insuredAmountCents}</dd>
        </div>
      ) : null}
      {projection.simulatedQuote?.premiumAnnualCents != null ? (
        <div>
          <dt>Prêmio anual (centavos)</dt>
          <dd>{projection.simulatedQuote.premiumAnnualCents}</dd>
        </div>
      ) : null}
      {projection.simulatedQuote?.humanCalculation ? (
        <div>
          <dt>Memória interna do cálculo</dt>
          <dd>{projection.simulatedQuote.humanCalculation}</dd>
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
