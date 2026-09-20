import { useEffect, useState } from 'react';
import { extractCanonicalExecutionId, getSimulationReadiness, submitMockScenario, submitMockSignal } from './api';
import { MOCK_SCENARIOS, buildCanonicalRequest, buildWaitSignal, newIdempotencyKey, newTraceparent } from './scenarios';
import { SEGSENSE_URL, SPIDERBANK_URL } from './urls';

const SATELLITES = [
  {
    id: 'segsense',
    category: 'EXPERIENCE SATELLITE DE SEGURO',
    product: 'SegSense',
    description: 'Inicie uma jornada de seguro no produto, com processamento pela Spider e execução no provider mock.',
    flow: ['SegSense', 'Spider', 'Provider de seguro', 'Monitor'],
    action: 'Abrir SegSense',
    url: SEGSENSE_URL,
  },
  {
    id: 'spiderbank',
    category: 'EXPERIENCE SATELLITE DE CRÉDITO',
    product: 'SpiderBank',
    description: 'Inicie uma jornada de crédito no produto, com processamento pela Spider e execução no provider mock.',
    flow: ['SpiderBank', 'Spider', 'Provider de crédito', 'Monitor'],
    action: 'Abrir SpiderBank',
    url: SPIDERBANK_URL,
  },
];

function satelliteState(id, readiness, readinessError) {
  if (readinessError) return { available: false, missing: 'Indisponível neste ambiente.' };
  const item = readiness?.satellites?.find(entry => entry.id === id);
  if (!readiness) return { available: false, missing: 'Verificando disponibilidade…', checking: true };
  if (!item) return { available: false, missing: 'Verificação de disponibilidade ausente neste ambiente.' };
  const missing = Array.isArray(item.missing) ? item.missing.filter(Boolean) : [];
  return { available: item.available === true && missing.length === 0, missing: missing[0] || '', url: item.url };
}

export default function SimulationPanel({ availableScenarios, loadingScenarios, onOpened }) {
  const [readiness, setReadiness] = useState(null);
  const [readinessError, setReadinessError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [status, setStatus] = useState(null);
  const [pendingWait, setPendingWait] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    getSimulationReadiness({ signal: controller.signal })
      .then(result => { setReadiness(result); setReadinessError(null); })
      .catch(error => { if (error.name !== 'AbortError') setReadinessError(error.message); });
    return () => controller.abort();
  }, []);

  async function run(scenario) {
    setBusyId(scenario.id);
    setStatus({ id: scenario.id, kind: 'starting', text: 'Iniciando…' });
    const idempotencyKey = newIdempotencyKey(scenario.id);
    const traceparent = newTraceparent();
    const body = buildCanonicalRequest(scenario, { idempotencyKey, traceparent });
    try {
      const result = await submitMockScenario(body, { idempotencyKey, traceparent });
      const id = extractCanonicalExecutionId(result);
      if (!id) throw new Error('O servidor recebeu o pedido, mas não retornou a identidade da execução.');
      if (scenario.twoPhase) {
        setPendingWait({ id, correlationId: body.trace.correlationId });
        setStatus({ id: scenario.id, kind: 'waiting', text: 'Execução em espera. Envie o sinal para retomar.' });
        return;
      }
      setPendingWait(null);
      onOpened({
        id,
        summary: { ...result.execution, technicalStatus: result.outcome?.technicalStatus, executionId: id, correlationId: body.trace.correlationId, startedAt: body.execution.requestedAt },
        message: 'Execução registrada. Acompanhe o resultado no Monitor.',
      });
    } catch (error) {
      const recovered = extractCanonicalExecutionId(error.body);
      if (recovered) {
        setPendingWait(null);
        onOpened({
          id: recovered,
          summary: { ...error.body?.execution, technicalStatus: error.body?.outcome?.technicalStatus, executionId: recovered, correlationId: error.body?.trace?.correlationId || body.trace.correlationId },
          message: 'Transação registrada com rejeição ou falha.',
        });
      } else {
        setStatus({ id: scenario.id, kind: 'failed', text: 'Falha ao iniciar neste ambiente.' });
      }
    } finally {
      setBusyId(null);
    }
  }

  async function resumeWait() {
    if (!pendingWait) return;
    setBusyId('WAIT_SIGNAL_RESUME');
    setStatus({ id: 'WAIT_SIGNAL_RESUME', kind: 'starting', text: 'Enviando sinal…' });
    try {
      await submitMockSignal(buildWaitSignal(pendingWait.id, { correlationId: pendingWait.correlationId }));
      const id = pendingWait.id;
      setPendingWait(null);
      onOpened({ id, summary: { executionId: id, correlationId: pendingWait.correlationId }, message: 'Sinal enviado. Acompanhe a retomada no Monitor.' });
    } catch {
      setStatus({ id: 'WAIT_SIGNAL_RESUME', kind: 'failed', text: 'Falha ao enviar o sinal. A execução continua em espera.' });
    } finally {
      setBusyId(null);
    }
  }

  return <section className="panel-card simulation-panel" data-testid="simulation-panel">
    <header className="simulation-header">
      <p className="obs-brand">DEMONSTRAÇÃO</p>
      <h2>Iniciar uma simulação</h2>
      <p>Escolha uma jornada completa por um satélite ou execute diretamente um cenário da entrada canônica.</p>
      <p className="simulation-rule">Toda execução registrada aparece no Monitor</p>
    </header>

    <section className="simulation-section">
      <p className="obs-brand">JORNADAS COMPLETAS</p>
      <h3>Experience Satellites</h3>
      <p>Comece no produto e acompanhe o resultado na Spider.</p>
      {readinessError && <p className="simulation-status" data-kind="failed">Falha ao verificar os satélites neste ambiente.</p>}
      <div className="satellite-simulation">
        {SATELLITES.map(satellite => {
          const state = satelliteState(satellite.id, readiness, readinessError);
          const href = state.url || satellite.url;
          return <article key={satellite.id} className="satellite-card" data-testid={`satellite-card-${satellite.id}`} data-available={state.available || undefined}>
            <p className="obs-brand">{satellite.category}</p>
            <p className="satellite-availability" data-available={state.available || undefined}>{state.checking ? 'Verificando' : state.available ? 'Disponível' : 'Indisponível'}</p>
            <h3>{satellite.product}</h3>
            <p>{satellite.description}</p>
            <ol className="satellite-flow">{satellite.flow.map(step => <li key={step}>{step}</li>)}</ol>
            {state.available
              ? <a className="cta" href={href} target="_blank" rel="noreferrer">{satellite.action}</a>
              : <button type="button" className="cta" disabled>{satellite.action}</button>}
            <p className="muted">{state.available ? 'Aparece pela origem registrada' : state.missing}</p>
          </article>;
        })}
      </div>
    </section>

    <section className="simulation-section">
      <p className="obs-brand">ENTRADA CANÔNICA</p>
      <h3>Cenários controlados da Spider</h3>
      <p>Execute o comportamento que deseja demonstrar.</p>
      <ol className="scenario-lines">
        {MOCK_SCENARIOS.map((scenario, index) => {
          const available = availableScenarios?.includes(scenario.id);
          const busy = busyId === scenario.id;
          const waiting = pendingWait && scenario.twoPhase;
          const contextual = status?.id === scenario.id ? status : null;
          return <li key={scenario.id} className="scenario-line" data-testid={`scenario-${scenario.id}`}>
            <span className="scenario-number">{index + 1}</span>
            <div>
              <strong>{scenario.label}</strong>
              <p>{scenario.description}</p>
              {contextual && <p className="simulation-status" data-kind={contextual.kind} role="status">{contextual.text}</p>}
              {waiting && !busy && <button type="button" className="cta" onClick={resumeWait}>Enviar sinal</button>}
            </div>
            <button type="button" className="cta" aria-label={`Executar ${scenario.label}`}
              disabled={!available || busy || Boolean(waiting)}
              onClick={() => run(scenario)}>{busy && contextual?.kind === 'starting' ? 'Iniciando…' : 'Executar'}</button>
            {!available && <p className="muted">{loadingScenarios ? 'Verificando disponibilidade…' : 'Indisponível neste ambiente.'}</p>}
          </li>;
        })}
      </ol>
    </section>
  </section>;
}
