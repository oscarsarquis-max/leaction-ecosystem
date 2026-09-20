import { useEffect, useMemo, useRef, useState } from 'react';
import TransactionWorkspace from './TransactionWorkspace';
import MonitorDocumentation from './MonitorDocumentation';
import './monitor-workspace.css';
import SimulationPanel from './SimulationPanel';
import { getMonitorEvents, listExecutions, getExecutionOperationalEvents } from './api';
import { MOCK_SCENARIOS } from './scenarios';
import { formatWhen, shortId } from './components';
import { projectTransactions, projectTransaction, originLabel, kindLabel, classifyMonitorStatus, FLOW_STATUS, isTerminalMonitorState, takeLatestArrivals, STREAM_WINDOW } from './monitorProjection';
import './monitor.css';
import './monitor-light.css';

const NAV = [['transactions', 'Monitor'], ['simulate', 'Simulação'], ['documentation', 'Documentação']];
const STREAM_MS = 4000;

function statusTone(status) {
  return FLOW_STATUS[classifyMonitorStatus(status)]?.tone || 'neutral';
}

function transactionLabel(t) {
  if (t.objective) return t.objective;
  const route = String(t.operationRef || t.routeRef || '').split('@')[0];
  const scenario = MOCK_SCENARIOS.find(s => s.id === route);
  if (scenario) return scenario.label;
  if (route) return route.replaceAll('_', ' ');
  return t.kind === 'SATELLITE' ? 'Interação de satélite' : 'Execução canônica';
}

function matchesQuery(t, query) {
  if (!query) return true;
  return [t.id, t.origin, t.objective, t.correlationId, t.state, t.routeRef, t.operationRef, kindLabel(t.kind), transactionLabel(t)]
    .some(v => String(v || '').toLowerCase().includes(query));
}

function TransactionLine({t, selected, onOpen, role = 'button'}) {
  return <button type="button" role={role} className="monitor-transaction" aria-pressed={selected === t.id} aria-selected={role === 'option' ? selected === t.id : undefined}
    data-live={!isTerminalMonitorState(t.state) || undefined} onClick={() => onOpen(t.id)}>
    {t.origin ? <span className="monitor-origin" data-known="true">[{originLabel(t.origin)}]</span> : null}
    <strong>{transactionLabel(t)}</strong>
    <span className="monitor-state" data-tone={statusTone(t.state)}>{t.state}</span>
    <span className="muted">{formatWhen(t.lastActivityAt || t.startedAt)}</span>
    <small title={t.id}>{shortId(t.id)}</small>
  </button>;
}

export default function MonitorShell() {
  const [view, setView] = useState('transactions');
  const selectedPanel = useRef(null);
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState({events: [], summaries: [], errors: [], loading: true});
  const [selected, setSelected] = useState(null);
  useEffect(() => { if (view === 'transactions' && selectedPanel.current && window.matchMedia?.('(max-width: 800px)').matches) selectedPanel.current.scrollIntoView?.({block:'start',behavior:'smooth'}); }, [selected, view]);
  const [evidence, setEvidence] = useState(null);
  const [origin, setOrigin] = useState('ALL');
  const [search, setSearch] = useState('');
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState(null);
  const [submittedSummary, setSubmittedSummary] = useState(null);
  const picked = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function load(initial) {
      if (initial) setData(previous => ({...previous, loading: !previous.events.length && !previous.summaries.length, errors: []}));
      const [events, executions] = await Promise.allSettled([
        getMonitorEvents({signal: controller.signal}),
        listExecutions({limit: 100}, {}, {signal: controller.signal}),
      ]);
      if (controller.signal.aborted) return;
      const errors = [];
      if (events.status === 'rejected') errors.push('Eventos indisponíveis: ' + events.reason.message);
      if (executions.status === 'rejected') errors.push('Execuções indisponíveis: ' + executions.reason.message);
      if (events.status === 'fulfilled' && events.value.available === false) errors.push('O armazenamento de eventos não está disponível neste ambiente.');
      setData(previous => ({
        events: events.status === 'fulfilled' ? events.value?.items || [] : previous.events,
        summaries: executions.status === 'fulfilled' ? executions.value?.items || [] : previous.summaries,
        errors,
        loading: false,
        availableScenarios: events.status === 'fulfilled' ? events.value?.availableScenarios || previous.availableScenarios : previous.availableScenarios,
        truncated: events.status === 'fulfilled' ? events.value?.truncated : previous.truncated,
        from: events.status === 'fulfilled' ? events.value?.from : previous.from,
        to: events.status === 'fulfilled' ? events.value?.to : previous.to,
      }));
      if (!controller.signal.aborted && !paused) timer = setTimeout(() => load(false), STREAM_MS);
    }
    load(true);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [refresh, paused]);

  const transactions = useMemo(() => projectTransactions(data.events, data.summaries), [data.events, data.summaries]);
  const selectedRow = transactions.find(t => t.id === selected);
  const summary = data.summaries.find(s => s.executionId === selected) || (submittedSummary?.executionId === selected ? submittedSummary : undefined);
  const transaction = evidence?.id === selected && evidence.events
    ? projectTransaction(selected, evidence.events, summary) : selectedRow;

  useEffect(() => {
    if (!selected) return undefined;
    const controller = new AbortController();
    let timer;
    setEvidence(previous => previous?.id === selected && previous.events
      ? {...previous, loading: false}
      : {id: selected, loading: true});
    async function load() {
      try {
        const result = await getExecutionOperationalEvents(selected, {signal: controller.signal});
        if (!controller.signal.aborted) {
          setEvidence({id: selected, events: result.items || []});
          const terminal = (result.items || []).some(e => ['SATELLITE_RESPONSE_RETURNED','EXECUTION_SUCCEEDED','EXECUTION_FAILED','EXECUTION_REJECTED'].includes(e.eventType));
          if (!terminal) timer = setTimeout(load, 4000);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setEvidence(previous => previous?.id === selected && previous.events
            ? {id: selected, events: previous.events, error: error.message}
            : {id: selected, error: error.message});
        }
      }
    }
    load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [selected, refresh]);

  function open(id) {
    picked.current = true;
    if (id !== selected) { setSelected(id); setEvidence(null); }
  }
  function openFromSimulation({id, summary, message: nextMessage}) {
    if (summary) setSubmittedSummary(summary);
    open(id);
    setView('transactions');
    setRefresh(n => n + 1);
    setMessage(nextMessage);
  }
  const origins = [...new Set(transactions.map(t => t.origin).filter(Boolean))];
  const scoped = transactions.filter(t => origin === 'ALL' || (origin === 'UNKNOWN' ? !t.origin : t.origin === origin));
  const live = takeLatestArrivals(scoped, STREAM_WINDOW);
  const query = search.trim().toLowerCase();
  const matches = query ? scoped.filter(t => matchesQuery(t, query)) : [];
  useEffect(() => {
    if (picked.current || selected || !live.length) return;
    picked.current = true;
    setSelected(live[0].id);
  }, [live, selected]);

  return <div className="obs-shell monitor-shell" data-testid="spider-console">
    <header className="monitor-header"><div><p className="obs-brand">SPIDER · MONITOR</p><h1>Monitor de transações</h1></div>
      <span className="pill mock-badge">AMBIENTE MOCK</span></header>
    <nav className="monitor-nav" aria-label="Navegação do Monitor">{NAV.map(([id,label]) => <button key={id} type="button"
      aria-current={view === id ? 'page' : undefined} onClick={() => setView(id)}>{label}</button>)}</nav>
    {view === 'transactions' && message && <p role="status" className="banner">{message}</p>}
    {view === 'transactions' && <><div className="monitor-workspace-grid">
      <section className="panel-card transaction-list-panel" aria-label="Fluxo de transações">
        <div className="monitor-section-heading"><h2>Fluxo de transações</h2>
          <p className="transaction-live-status" role="status" data-live={paused ? 'paused' : 'live'}>
            {paused ? 'Pausado' : 'Ao vivo'} · {live.length} mais recente{live.length === 1 ? '' : 's'}{scoped.length > live.length ? ` · ${scoped.length} no recorte` : ''}{data.truncated ? ' · últimos 2.000 eventos' : ''}
          </p>
          <div className="transaction-live-actions">
            <button className="ghost" type="button" onClick={() => setPaused(value => !value)}>{paused ? 'Retomar' : 'Pausar'}</button>
            <button className="ghost" type="button" onClick={() => setRefresh(n => n + 1)} disabled={data.loading}>Atualizar</button>
          </div></div>
        <div className="monitor-filters">
          <div className="transaction-search">
            <label>Buscar no recorte
              <input role="combobox" aria-autocomplete="list" aria-expanded={Boolean(query)} aria-controls="transaction-search-results"
                value={search} onChange={e => setSearch(e.target.value)} placeholder="Objetivo, origem ou id"
                onKeyDown={e => { if (e.key === 'Enter' && matches[0]) open(matches[0].id); }} />
            </label>
            {query ? <div id="transaction-search-results" className="transaction-search-results" role="listbox">
              <p>{matches.length} correspondência{matches.length === 1 ? '' : 's'} no recorte</p>
              {matches.length === 0 ? <p>Nenhuma transação com esse critério.</p> : matches.map(t =>
                <TransactionLine key={t.id} t={t} selected={selected} onOpen={open} role="option" />)}
            </div> : null}
          </div>
          <label>Origem<select value={origin} onChange={e => setOrigin(e.target.value)}><option value="ALL">Todas</option>{origins.map(o => <option key={o} value={o}>{originLabel(o)}</option>)}<option value="UNKNOWN">Não registrada</option></select></label>
        </div>
        {data.loading && <p role="status">Consultando transações…</p>}
        {data.errors.map(error => <p role="alert" className="error" key={error}>{error}</p>)}
        {!data.loading && live.length === 0 && <p>Nenhuma transação neste recorte.</p>}
        <div className="monitor-transactions">{live.map(t => <TransactionLine key={t.id} t={t} selected={selected} onOpen={open} />)}</div>
      </section>
      {selected && evidence?.error && <p role="alert" className="panel-card workspace-read-error error">Falha ao consultar evidências: {evidence.error}</p>}
      {selected && evidence?.loading && !transaction && <p className="panel-card workspace-empty" role="status">Carregando…</p>}
      {transaction && <TransactionWorkspace key={selected} transaction={transaction} identityRef={selectedPanel} />}
      {!selected && <section className="panel-card workspace-empty" aria-label="Transação selecionada"><p>Selecione uma transação no fluxo.</p></section>}
      </div>
    </>}
    {view === 'documentation' && <MonitorDocumentation />}
    {view === 'simulate' && <SimulationPanel availableScenarios={data.availableScenarios} loadingScenarios={data.loading} onOpened={openFromSimulation} />}
  </div>;
}
