import { useEffect, useState } from 'react';
import {
  fetchCreditContext,
  formatCents,
  newCorrelationId,
  newIdempotencyKey,
  reaisToCents,
  startDemoSession,
  submitCreditJourney,
  type CreditContext,
  type CreditError,
  type CreditJourney,
  type DemoSession,
} from '../api/creditJourney';

const PERSONAS = [
  { id: 'ok', label: 'Cliente sintético elegível' },
  { id: 'pending-registration', label: 'Cadastro sintético pendente' },
  { id: 'no-profile', label: 'Perfil sintético ausente' },
  { id: 'ineligible', label: 'Sem alternativa sintética elegível' },
  { id: 'rejected', label: 'Recusa sintética' },
  { id: 'review', label: 'Pendência humana sintética' },
];

export function CreditJourneyPage() {
  const [context, setContext] = useState<CreditContext | null>(null);
  const [session, setSession] = useState<DemoSession | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [persona, setPersona] = useState('ok');
  const [confirmed, setConfirmed] = useState(false);
  const [amountReais, setAmountReais] = useState('10000,00');
  const [termMonths, setTermMonths] = useState('12');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CreditJourney | null>(null);
  const [error, setError] = useState<(Error & Partial<CreditError>) | null>(null);
  const [correlationId, setCorrelationId] = useState(newCorrelationId);
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey);

  useEffect(() => {
    Promise.all([fetchCreditContext(), startDemoSession(persona)])
      .then(([nextContext, nextSession]) => {
        setContext(nextContext);
        setSession(nextSession);
      })
      .catch((cause: unknown) => {
        setLoadError(cause instanceof Error ? cause.message : 'Falha ao carregar a sessão demonstrativa.');
      });
  }, [persona]);

  async function send() {
    setSubmitting(true);
    setError(null);
    try {
      const journey = await submitCreditJourney({
        objectiveConfirmed: confirmed,
        correlationId,
        idempotencyKey,
        sessionAssertion: session?.assertion,
        principalCents: reaisToCents(amountReais),
        termMonths: termMonths ? Number(termMonths) : undefined,
      });
      setResult(journey);
    } catch (cause) {
      setError(cause as Error & Partial<CreditError>);
    } finally {
      setSubmitting(false);
    }
  }

  function retryTransient() {
    void send();
  }

  function startOver() {
    setResult(null);
    setError(null);
    setConfirmed(false);
    setAmountReais('10000,00');
    setTermMonths('12');
    setCorrelationId(newCorrelationId());
    setIdempotencyKey(newIdempotencyKey());
  }

  const simulation = result?.options?.simulation;
  const products = result?.options?.eligibleProducts?.products ?? [];

  return (
    <main className="page" data-testid="credit-journey-page">
      <p className="banner" data-testid="demo-banner">
        Ambiente demonstrativo — dados sintéticos. Não é análise de crédito, oferta, aprovação nem contratação.
      </p>
      <header className="hero">
        <p className="kicker">SpiderBank</p>
        <h1>Avaliação demonstrativa de capital de giro</h1>
        <p>
          Esta experiência envia o contexto governado, a sessão demonstrativa e o objetivo confirmado à
          Spider. O resultado apresentado é o que a Spider devolver — inclusive impedimentos.
        </p>
      </header>

      {loadError ? <p className="error">{loadError}</p> : null}

      {session ? (
        <section className="card" data-testid="demo-session">
          <h2>{session.label}</h2>
          <p className="watermark">{session.warning}</p>
          <label className="field">
            Perfil sintético de teste
            <select
              value={persona}
              onChange={(event) => setPersona(event.target.value)}
              data-testid="demo-persona"
            >
              {PERSONAS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <p className="muted">
            Ambiente {session.environment}. Referência {session.subjectRef}. Não é KYC nem autenticação de cliente real.
          </p>
        </section>
      ) : null}

      {context ? (
        <section className="card" data-testid="credit-context">
          <h2>{context.title}</h2>
          <p>{context.summary}</p>
          <p>
            <strong>Origem:</strong> {context.originLabel}. {context.originDetail}
          </p>
          <p className="muted">{context.limits}</p>
          <details>
            <summary>Detalhes técnicos do contexto</summary>
            <dl>
              <dt>sourceId</dt>
              <dd>{context.sourceId}</dd>
              <dt>captureMethod</dt>
              <dd>{context.captureMethod}</dd>
              <dt>trustLevel</dt>
              <dd>{context.trustLevel}</dd>
            </dl>
          </details>
        </section>
      ) : null}

      <section className="card" data-testid="credit-objective">
        <h2>Objetivo e parâmetros declarados</h2>
        <p>
          Quero buscar capital de giro para esta situação demonstrativa. A Spider interpreta a
          declaração reconhecida; o SpiderBank não escolhe o plano, o provider nem a taxa.
        </p>
        <label className="field">
          Valor declarado
          <input
            inputMode="decimal"
            value={amountReais}
            onChange={(event) => setAmountReais(event.target.value)}
            data-testid="declared-amount"
          />
        </label>
        <label className="field">
          Prazo declarado (meses)
          <input
            inputMode="numeric"
            value={termMonths}
            onChange={(event) => setTermMonths(event.target.value)}
            data-testid="declared-term"
          />
        </label>
        <p className="muted">Valores informados pelo usuário. Não se tornam fatos de cadastro, renda ou risco.</p>
        <label className="confirm">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
            data-testid="confirm-objective"
          />
          Confirmo o objetivo de buscar capital de giro
        </label>
        <div className="actions">
          <button type="button" disabled={!confirmed || submitting} onClick={() => void send()} data-testid="submit-journey">
            {submitting ? 'Enviando…' : 'Pedir avaliação à Spider'}
          </button>
          <button type="button" className="secondary" onClick={startOver} data-testid="reset-journey">
            Recomeçar
          </button>
        </div>
      </section>

      {error ? (
        <section className="card error-card" data-testid="credit-error">
          <h2>Não foi possível concluir o envio</h2>
          <p>{error.message}</p>
          <p className="muted">Isso não é recusa de crédito.</p>
          {error.retryable ? (
            <button type="button" onClick={retryTransient} data-testid="retry-journey">
              Tentar novamente
            </button>
          ) : null}
        </section>
      ) : null}

      {result ? (
        <section className="card" data-testid="credit-result">
          <h2>{result.headline}</h2>
          <p>{result.explanation}</p>
          <p className="watermark">{result.watermark}</p>
          {result.missingContext.length > 0 ? (
            <p data-testid="missing-context">Complemento solicitado: {result.missingContext.join(', ')}</p>
          ) : null}
          {result.impediments.length > 0 ? (
            <ol className="impediments" data-testid="impediments">
              {result.impediments.map((item) => (
                <li key={`${item.sequence}-${item.capabilityId}`}>
                  <strong>{item.title}</strong>
                  <span>{item.reason}</span>
                </li>
              ))}
            </ol>
          ) : null}
          {simulation ? (
            <div className="simulation" data-testid="credit-simulation">
              <h3>Resultado demonstrativo</h3>
              <p data-testid="simulation-warning">
                {simulation.watermark ||
                  'Simulação ilustrativa — sem valor comercial. Não é oferta, aprovação ou contratação.'}
              </p>
              <dl>
                <dt>Necessidade</dt>
                <dd>Capital de giro confirmado</dd>
                <dt>Valor solicitado</dt>
                <dd>{formatCents(result.options?.principalCents)}</dd>
                <dt>Prazo solicitado</dt>
                <dd>{result.options?.termMonths} meses</dd>
                <dt>Total demonstrativo</dt>
                <dd>{formatCents(simulation.totalCents)}</dd>
                <dt>Juros de teste</dt>
                <dd>{formatCents(simulation.interestCents)}</dd>
              </dl>
              {simulation.installmentsCents?.length ? (
                <p data-testid="simulation-installments">
                  Parcelas sintéticas: {simulation.installmentsCents.map((item) => formatCents(item)).join(' · ')}
                </p>
              ) : null}
              {simulation.premises?.length ? (
                <ul data-testid="simulation-premises">
                  {simulation.premises.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              {products.length > 0 ? (
                <p data-testid="synthetic-alternative">
                  Alternativa sintética: {products[0].title}. Ofertável: não. Validade comercial: não.
                </p>
              ) : null}
              <p className="muted">
                Simulação concluída: {result.simulationComplete ? 'sim' : 'não'}. Análise de crédito: não.
                Decisão: {result.creditDecision}. Contratação e desembolso não são suportados.
              </p>
            </div>
          ) : (
            <p className="muted">Nenhum produto, taxa, limite ou proposta é fabricado nesta tela.</p>
          )}
          <details>
            <summary>Detalhes técnicos da resposta</summary>
            <dl>
              <dt>status</dt>
              <dd>{result.status}</dd>
              <dt>correlationId</dt>
              <dd>{result.correlationId}</dd>
              <dt>decisionId</dt>
              <dd>{result.decisionId}</dd>
              <dt>intent</dt>
              <dd>{result.technical?.intent ?? '—'}</dd>
              <dt>planId</dt>
              <dd>{result.technical?.planId ?? '—'}</dd>
            </dl>
          </details>
        </section>
      ) : null}
    </main>
  );
}
