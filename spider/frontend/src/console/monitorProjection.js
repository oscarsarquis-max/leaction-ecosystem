export const PHASES = [
  ['origin', 'Origem', 'ENTRADA', ['SATELLITE_REQUEST_RECEIVED', 'SATELLITE_AUTHENTICATED']],
  ['context', 'Contexto', 'ENTRADA', ['SATELLITE_CONTEXT_ACCEPTED', 'CLICK_CONTEXT_CREATED', 'PAGE_CONTEXT_ACQUIRED']],
  ['objective', 'Objetivo / intenção', 'ENTRADA', ['SATELLITE_OBJECTIVE_ACCEPTED', 'OBJECTIVE_DECLARED']],
  ['interpretation', 'Interpretação', 'IA', ['AI_INTERPRETATION_REQUESTED', 'AI_INTERPRETATION_SUCCEEDED', 'AI_INTERPRETATION_REJECTED', 'AI_INTERPRETATION_FAILED']],
  ['intent', 'Intent Contract', 'DET', ['INTENT_CREATED', 'INTENT_VALIDATED']],
  ['policy', 'Policy / contrato', 'DET', ['SATELLITE_CONTRACT_VALIDATED', 'INTENT_VALIDATED', 'EXECUTION_REJECTED']],
  ['plan', 'Plano', 'DET', ['EXECUTION_PLAN_RESOLVED', 'EXECUTION_PLAN_REJECTED']],
  ['capabilities', 'Capacidades', 'DET', ['CAPABILITY_DISPATCHED', 'CAPABILITY_RESOLVED', 'CAPABILITY_UNAVAILABLE']],
  ['resolution', 'Resolução', 'DET', ['CAPABILITY_RESOLVED', 'ROUTE_RESOLVED']],
  ['execution', 'Execução', 'DET', ['EXECUTION_STARTED', 'OUTBOUND_REQUEST_STARTED', 'OUTBOUND_RESPONSE_RECEIVED', 'PROVIDER_RESULT_RECEIVED']],
  ['result', 'Resultado', 'DET', ['SATELLITE_DECISION_CREATED', 'SATELLITE_RESPONSE_RETURNED', 'EXECUTION_SUCCEEDED', 'EXECUTION_FAILED', 'EXECUTION_REJECTED', 'EXECUTION_TIMED_OUT', 'EXECUTION_COMPLETED']],
];

const byTime = (a, b) => String(a.occurredAt).localeCompare(String(b.occurredAt)) || String(a.eventId).localeCompare(String(b.eventId));
const last = (items) => items[items.length - 1];
export function projectTransaction(id, events = [], summary = {}) {
  const ordered = events.filter(e => e.executionId === id).slice().sort(byTime);
  const find = type => last(ordered.filter(e => e.eventType === type));
  const satellite = ordered.some(e => e.source === 'satellite-contract');
  const auth = find('SATELLITE_AUTHENTICATED');
  // A declared envelope identity is not an authenticated origin.
  const origin = auth?.metadata?.originSatellite || auth?.metadata?.satelliteId || auth?.metadata?.reasonCode
    || (!satellite && ordered.find(e => e.metadata?.originSatellite)?.metadata?.originSatellite)
    || (satellite ? null : 'canonical');
  const response = find('SATELLITE_RESPONSE_RETURNED');
  const objective = find('SATELLITE_OBJECTIVE_ACCEPTED')?.metadata?.reasonCode
    || find('OBJECTIVE_DECLARED')?.metadata?.intent || null;
  const aiAttempt = ordered.some(e => e.eventType?.startsWith('AI_INTERPRETATION_'));
  const noAi = ordered.some(e => e.metadata?.aiUsage === 'NOT_USED');
  const startedAt = summary.startedAt || ordered[0]?.occurredAt;
  const terminal = last(ordered.filter(e => ['EXECUTION_SUCCEEDED','EXECUTION_FAILED','EXECUTION_REJECTED'].includes(e.eventType)));
  const completedAt = summary.completedAt || response?.occurredAt || terminal?.occurredAt;
  const terminalState = terminal?.eventType?.replace('EXECUTION_', '');
  const durationMs = startedAt && completedAt ? Math.max(0, Date.parse(completedAt) - Date.parse(startedAt)) : summary.durationMs ?? null;
  const lastActivityAt = [summary.updatedAt, completedAt, ...ordered.map(e => e.occurredAt), startedAt].filter(Boolean).sort().at(-1) || null;
  const component = last(ordered.filter(e => e.metadata?.currentComponent))?.metadata?.currentComponent || null;
  return {
    id, kind: satellite ? 'SATELLITE' : 'CANONICAL', origin, objective,
    routeRef: summary.routeRef || null,
    operationRef: summary.operationRef || null,
    state: response?.metadata?.reasonCode || terminalState || summary.state || 'SEM_RESULTADO_REGISTRADO',
    result: terminal?.metadata?.technicalStatus || response?.metadata?.reasonCode || summary.technicalStatus || terminalState || null,
    correlationId: last(ordered)?.correlationId || summary.correlationId || null,
    startedAt, completedAt, lastActivityAt, durationMs, events: ordered,
    executor: last(ordered.filter(e => e.metadata?.executor))?.metadata?.executor || null,
    component,
    ai: aiAttempt ? 'REQUESTED' : noAi ? 'NOT_USED' : 'UNKNOWN',
    phases: PHASES.map(([key, label, mode, types]) => ({key, label, mode,
      events: ordered.filter(e => types.includes(e.eventType))})),
  };
}

export function projectTransactions(events = [], summaries = []) {
  const groups = new Map();
  for (const event of events) {
    if (!event.executionId || event.category === 'SYSTEM') continue;
    if (!groups.has(event.executionId)) groups.set(event.executionId, []);
    groups.get(event.executionId).push(event);
  }
  const summaryMap = new Map(summaries.map(s => [s.executionId, s]));
  for (const summary of summaries) if (!groups.has(summary.executionId)) groups.set(summary.executionId, []);
  return Array.from(groups, ([id, entries]) => projectTransaction(id, entries, summaryMap.get(id)))
    .sort((a, b) => String(arrivalAt(b)).localeCompare(String(arrivalAt(a))));
}

export const STREAM_WINDOW = 5;

function arrivalAt(transaction) {
  return transaction.lastActivityAt || transaction.startedAt || transaction.completedAt || '';
}

export function takeLatestArrivals(transactions = [], limit = STREAM_WINDOW) {
  return transactions.slice().sort((a, b) => String(arrivalAt(b)).localeCompare(String(arrivalAt(a)))).slice(0, limit);
}

export function originLabel(origin) {
  if (!origin) return 'ORIGEM NÃO REGISTRADA';
  if (origin === 'canonical') return 'ENTRADA CANÔNICA';
  return origin.toUpperCase();
}

export function humanLog(event, origin) {
  const component = event.metadata?.currentComponent || event.source || 'COMPONENTE NÃO REGISTRADO';
  return `[${originLabel(origin)}] [${component}] ${event.eventType} ${event.outcome || 'SEM RESULTADO'}`;
}

export const FLOW_STATUS = {
  completed: {tone: 'success', label: 'Concluído'},
  running: {tone: 'info', label: 'Em andamento'},
  waiting: {tone: 'warning', label: 'Aguardando'},
  failed: {tone: 'danger', label: 'Falha técnica'},
  rejected: {tone: 'danger', label: 'Rejeição'},
  planned: {tone: 'planned', label: 'Previsto'},
  unknown: {tone: 'neutral', label: 'Sem informação suficiente'},
};

const COMPLETED = new Set(['SUCCEEDED','SUCCESS','COMPLETED','READY','VERIFIED','PRE_PROPOSAL_AVAILABLE']);
const FAILED = new Set(['FAILED','FAILURE','TIMED_OUT','PROVIDER_UNAVAILABLE','EXECUTION_FAILED','EXECUTION_TIMED_OUT']);
const REJECTED = new Set(['REJECTED','EXECUTION_REJECTED','EXECUTION_PLAN_REJECTED']);
const WAITING = new Set(['WAITING','WAITING_EXTERNAL','MISSING_CONTEXT','AMBIGUOUS','PARTIALLY_SUCCEEDED','PARTIAL']);
const RUNNING = new Set(['RUNNING','RECEIVED','VALIDATED','PLANNED','RESOLVED','RETRYING','EXECUTION_STARTED']);
const TERMINAL = new Set(['SUCCEEDED','SUCCESS','COMPLETED','FAILED','FAILURE','REJECTED','TIMED_OUT','READY']);

export function classifyMonitorStatus(state) {
  const s = String(state || '').toUpperCase();
  if (!s || s === 'SEM_RESULTADO_REGISTRADO' || s === 'UNKNOWN' || s === 'PENDING') return 'unknown';
  if (COMPLETED.has(s) || s === 'EXECUTION_SUCCEEDED' || s.endsWith('_SUCCEEDED') || s.endsWith('_COMPLETED') || s.endsWith('_RETURNED')) return 'completed';
  if (FAILED.has(s) || s.includes('FAILED') || s.includes('TIMED_OUT')) return 'failed';
  if (REJECTED.has(s) || s.includes('REJECTED')) return 'rejected';
  if (WAITING.has(s) || s.includes('WAITING')) return 'waiting';
  if (RUNNING.has(s) || s.endsWith('_STARTED') || s.endsWith('_REQUESTED') || s.endsWith('_RECEIVED')) return 'running';
  if (s === 'SUCCESS') return 'completed';
  return 'unknown';
}

export function isTerminalMonitorState(state) {
  return TERMINAL.has(String(state || '').toUpperCase());
}

export function kindLabel(kind) {
  return kind === 'SATELLITE' ? 'Interação' : 'Execução';
}

function lastEventSignal(events) {
  const item = last(events || []);
  if (!item) return null;
  return item.outcome || item.metadata?.reasonCode || item.eventType;
}

function markCurrent(nodes, transactionState) {
  if (!nodes.length) return nodes;
  const terminal = isTerminalMonitorState(transactionState);
  const active = [...nodes].reverse().find(n => n.status === 'running' || n.status === 'waiting');
  const lastKnown = [...nodes].reverse().find(n => ['completed','failed','rejected'].includes(n.status));
  const target = (!terminal && active) || lastKnown || nodes[nodes.length - 1];
  return nodes.map(n => ({...n, current: n.id === target.id}));
}

function observedNode(phase, events, extras = {}) {
  return {
    id: extras.id || phase.key,
    kind: extras.kind || 'observed',
    definitionKey: extras.definitionKey || phase.key,
    title: extras.title || phase.label,
    status: extras.status || (events.length ? classifyMonitorStatus(lastEventSignal(events)) : 'unknown'),
    events,
    step: extras.step || null,
    record: extras.record || null,
    current: false,
    attemptCount: extras.attemptCount,
  };
}

export function buildMonitorFlow(transaction, extras = {}) {
  const {plan, steps = [], detail} = extras;
  const events = transaction?.events || [];
  const orderedSteps = plan?.orderedSteps || [];

  if (orderedSteps.length) {
    const attached = new Set();
    const nodes = orderedSteps.map(id => {
      const entry = steps.find(s => s.stepRef === id);
      const stepEvents = events.filter(e => e.metadata?.stepRef === id);
      stepEvents.forEach(e => attached.add(e.eventId));
      let status = 'planned';
      if (entry) status = classifyMonitorStatus(entry.state);
      else if (stepEvents.length) status = classifyMonitorStatus(lastEventSignal(stepEvents));
      return {
        id,
        kind: 'step',
        definitionKey: 'execution',
        title: id,
        status,
        events: stepEvents,
        step: entry || null,
        record: entry || null,
        current: false,
        attemptCount: entry?.attemptCount,
      };
    });
    for (const [key, label, , types] of PHASES) {
      if (key !== 'origin' && key !== 'result') continue;
      const extraEvents = events.filter(e => types.includes(e.eventType) && !e.metadata?.stepRef && !attached.has(e.eventId));
      if (!extraEvents.length) continue;
      extraEvents.forEach(e => attached.add(e.eventId));
      const node = observedNode({key, label}, extraEvents);
      if (key === 'origin') nodes.unshift(node);
      else nodes.push(node);
    }
    return {mode: 'plan', nodes: markCurrent(nodes, detail?.summary?.state || transaction.state), plan};
  }

  const used = new Set();
  const nodes = [];
  for (const [key, label, , types] of PHASES) {
    const phaseEvents = events.filter(e => types.includes(e.eventType));
    if (!phaseEvents.length) continue;
    phaseEvents.forEach(e => used.add(e.eventId));
    nodes.push(observedNode({key, label}, phaseEvents));
  }
  const leftovers = events.filter(e => !used.has(e.eventId) && e.category !== 'SYSTEM');
  const leftoverGroups = new Map();
  for (const event of leftovers) {
    const type = event.eventType || 'EVENTO';
    if (!leftoverGroups.has(type)) leftoverGroups.set(type, []);
    leftoverGroups.get(type).push(event);
  }
  for (const [type, group] of leftoverGroups) {
    nodes.push(observedNode({key: `event:${type}`, label: type}, group, {definitionKey: 'execution'}));
  }
  if (!nodes.length && detail?.summary) {
    nodes.push(observedNode({key: 'result', label: 'Resultado'}, events, {
      status: classifyMonitorStatus(detail.summary.state || transaction.state),
      record: detail.summary,
    }));
  }
  return {mode: nodes.length ? 'observed' : 'empty', nodes: markCurrent(nodes, detail?.summary?.state || transaction.state), plan: null};
}

export function defaultFlowSelection(flow) {
  if (!flow?.nodes?.length) return null;
  return flow.nodes.find(n => n.current)?.id || flow.nodes[flow.nodes.length - 1].id;
}
