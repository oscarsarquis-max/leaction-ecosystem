import { useEffect, useMemo, useRef, useState } from 'react';
import { getExecutionDetail, getExecutionContext, isTerminalState } from './api';
import { DEFINITIONS, FIELD_LABELS } from './monitorDefinitions';
import { formatWhen } from './components';
import ExecutionJourney from './ExecutionJourney';
import {
  humanLog, originLabel, kindLabel, buildMonitorFlow, defaultFlowSelection,
  FLOW_STATUS, classifyMonitorStatus,
} from './monitorProjection';

function Fields({value}) {
  const entries = Object.entries(value || {}).filter(([,v]) => v != null && typeof v !== 'object');
  return entries.length ? <dl className="workspace-fields">{entries.map(([key,v]) => <div key={key}><dt>{FIELD_LABELS[key] || key}</dt><dd>{String(v)}</dd></div>)}</dl> : null;
}

function statusOf(state) {
  return FLOW_STATUS[classifyMonitorStatus(state)] || FLOW_STATUS.unknown;
}

function journeySummary(transaction, detail) {
  return {
    executionId: transaction.id,
    state: transaction.state,
    routeRef: transaction.routeRef,
    operationRef: transaction.operationRef,
    startedAt: transaction.startedAt,
    completedAt: transaction.completedAt,
    durationMs: transaction.durationMs,
    correlationRef: transaction.correlationId,
    ...(detail?.summary || {}),
  };
}

export default function TransactionWorkspace({transaction: t, identityRef}) {
  const [choice, setChoice] = useState({txn: t.id, id: null});
  const [loaded, setLoaded] = useState({forId: t.id, loading: t.kind === 'CANONICAL'});
  const inspector = useRef(null);
  if (choice.txn !== t.id) setChoice({txn: t.id, id: null});

  useEffect(() => {
    const controller = new AbortController();
    let timer;
    let attempts = 0;
    setLoaded({forId: t.id, loading: t.kind === 'CANONICAL'});
    if (t.kind !== 'CANONICAL') return () => controller.abort();
    async function load() {
      const [detail, context] = await Promise.allSettled([
        getExecutionDetail(t.id, {signal: controller.signal}),
        getExecutionContext(t.id, {signal: controller.signal}),
      ]);
      if (controller.signal.aborted) return;
      setLoaded(previous => {
        const failed = detail.status === 'rejected';
        const keep = failed && previous.detail && previous.forId === t.id;
        return {
          forId: t.id,
          loading: false,
          detail: keep ? previous.detail : detail.value,
          context: context.status === 'fulfilled' ? context.value : (keep ? previous.context : undefined),
          error: (!keep && failed) ? detail.reason.message : null,
          refreshError: keep ? detail.reason.message : null,
          contextError: context.status === 'rejected' && context.reason?.status !== 404 ? context.reason.message : null,
        };
      });
      if (detail.value?.summary && !isTerminalState(detail.value.summary.state) && ++attempts < 60) timer = setTimeout(load, 4000);
    }
    load();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [t.id, t.kind]);

  const detail = loaded.forId === t.id ? loaded.detail : undefined;
  const plan = detail?.plan?.available ? detail.plan.data : null;
  const steps = detail?.steps?.available ? detail.steps.data || [] : [];
  const flow = useMemo(() => buildMonitorFlow(t, {plan, steps, detail}), [t, plan, steps, detail]);
  const selectedId = choice.txn === t.id && choice.id && flow.nodes.some(n => n.id === choice.id)
    ? choice.id
    : defaultFlowSelection(flow);

  const node = flow.nodes.find(n => n.id === selectedId) || null;
  const state = detail?.summary?.state || t.state;
  const events = node?.events || [];
  const records = node?.step || node?.record || (
    node?.definitionKey === 'plan' ? plan
      : node?.definitionKey === 'result' ? (detail?.safeResultProjection?.available ? detail.safeResultProjection.data : detail?.summary)
      : node?.definitionKey === 'policy' ? (detail?.governance?.available ? detail.governance.data : null)
      : node?.definitionKey === 'intent' ? loaded.context?.intentContract
      : null
  );
  const definition = DEFINITIONS[node?.definitionKey] || DEFINITIONS.execution;
  const nodeStatus = FLOW_STATUS[node?.status] || FLOW_STATUS.unknown;

  function choose(id) {
    setChoice({txn: t.id, id});
    if (window.matchMedia?.('(max-width: 1100px)').matches) inspector.current?.scrollIntoView?.({block:'nearest', behavior:'smooth'});
  }

  const alerts = <>
    {loaded.loading && t.kind === 'CANONICAL' && !detail && <p role="status">Consultando o plano…</p>}
    {loaded.error && <p role="alert" className="error">Não foi possível consultar o plano persistido: {loaded.error}</p>}
    {loaded.refreshError && <p role="alert" className="error">Falha ao atualizar. Os dados anteriores foram mantidos: {loaded.refreshError}</p>}
    {loaded.contextError && <p role="alert" className="error">{loaded.contextError}</p>}
  </>;

  if (t.kind === 'CANONICAL') {
    return <>
      <p className="workspace-sticky-context">
        <strong>{t.objective || kindLabel(t.kind)}</strong>
        <span>Transação selecionada</span>
      </p>
      <section ref={identityRef} className="panel-card workspace-stage workspace-journey" aria-label="Transação selecionada">
        {alerts}
        <ExecutionJourney
          compact
          heading="Transação selecionada"
          summary={journeySummary(t, detail)}
          timeline={detail?.timeline}
          steps={detail?.steps}
          waitInfo={detail?.waitInfo}
          callback={detail?.callback}
          operationalEvents={t.events}
          contextJourney={loaded.forId === t.id ? loaded.context?.contextJourney : undefined}
        />
      </section>
    </>;
  }

  return <>
    <p className="workspace-sticky-context">
      <strong>{t.objective || kindLabel(t.kind)}</strong>
      <span>{node ? node.title : 'Sem elemento selecionado'}</span>
    </p>
    <section ref={identityRef} className="panel-card workspace-stage" aria-label="Plano de execução">
      <header className="workspace-stage-head">
        <div>
          <h2>{flow.mode === 'plan' ? 'Plano de execução' : 'Percurso registrado'}</h2>
          <p className="workspace-stage-meta">
            <span>{kindLabel(t.kind)}{t.origin ? ` · ${originLabel(t.origin)}` : ''}</span>
            <span className="monitor-id" title={t.id}>{t.id}</span>
            {plan?.planId ? <span>{plan.planId}{plan.routeRef ? ` · ${plan.routeRef}` : ''}</span> : null}
          </p>
        </div>
        <span className="monitor-state" data-tone={statusOf(state).tone}>{state}</span>
      </header>
      {alerts}
      {flow.mode === 'empty' && !loaded.loading && <p>Não há percurso registrado para esta transação.</p>}
      <ol className="workspace-path">{flow.nodes.map((item, index) => {
        const status = FLOW_STATUS[item.status] || FLOW_STATUS.unknown;
        return <li key={item.id}>
          <button type="button" aria-pressed={selectedId === item.id} aria-current={item.current ? 'step' : undefined}
            aria-controls="stage-inspector" data-status={item.status} data-current={item.current}
            onClick={() => choose(item.id)}>
            <span className="workspace-number">{index + 1}</span>
            <span>
              <strong>{item.title}</strong>
              <small>
                <span className="flow-status" data-tone={status.tone}>{status.label}</span>
                {item.attemptCount != null ? ` · ${item.attemptCount} tentativa(s)` : ''}
                {item.step?.state ? ` · ${item.step.state}` : item.events.length ? ` · ${item.events.length} evento(s)` : ''}
              </small>
            </span>
            <span aria-hidden="true">›</span>
          </button>
        </li>;
      })}</ol>
    </section>
    <aside ref={inspector} id="stage-inspector" className="panel-card workspace-inspector" aria-label="Elemento selecionado" aria-live="polite">
      {node ? <>
        <h2>{node.title}</h2>
        <p className="flow-status" data-tone={nodeStatus.tone}>{nodeStatus.label}</p>
        <section><h3>Definição</h3><p>{definition[1]}</p></section>
        <section><h3>Evidências</h3>
          {records ? <Fields value={records}/> : null}
          {node.definitionKey === 'origin' && <Fields value={{'Satélite de origem': t.origin ? originLabel(t.origin) : null, 'Componente atual': events.at(-1)?.metadata?.currentComponent || events.at(-1)?.source, 'Executor': t.executor}}/>}
          {node.definitionKey === 'interpretation' && t.ai === 'NOT_USED' && <p>O serviço registrou explicitamente que não utilizou IA nesta transação.</p>}
          {!records && !events.length && node.status === 'planned' && <p>Etapa prevista pelo plano, ainda sem execução registrada.</p>}
          {!records && !events.length && node.status === 'unknown' && <p>Não há registro disponível que comprove este elemento nesta transação. Não é possível concluir que ele ocorreu, falhou ou foi omitido.</p>}
          {node.step?.attempts?.map(a => <div className="workspace-proof" key={a.attemptNumber}><strong>Tentativa {a.attemptNumber}</strong><Fields value={a}/></div>)}
          {events.map(e => <article className="workspace-proof" key={e.eventId}><strong>{e.eventType}</strong>
            <p>Resultado: {e.outcome || 'Não registrado'}{e.metadata?.reasonCode ? ` · ${e.metadata.reasonCode}` : ''}</p>
            <Fields value={e.metadata}/>
            <p className="muted monitor-id">{e.eventId} · {formatWhen(e.occurredAt)}</p>
            <details><summary>Registro técnico</summary><p className="monitor-log">{humanLog(e, t.origin)}</p><pre>{JSON.stringify(e,null,2)}</pre></details>
          </article>)}
          {records && <details className="workspace-proof"><summary>Registro técnico</summary><pre>{JSON.stringify(records,null,2)}</pre></details>}
          {!records && !events.length && node.status !== 'planned' && node.status !== 'unknown' && <p className="muted">Nenhuma evidência disponível neste recorte.</p>}
        </section>
      </> : <p className="muted">Selecione um elemento do plano para ver a definição e as evidências.</p>}
    </aside>
  </>;
}
