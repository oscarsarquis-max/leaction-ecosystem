import { useEffect, useMemo, useRef, useState } from 'react';
import TransactionWorkspace from './TransactionWorkspace';
import MonitorDocumentation from './MonitorDocumentation';
import './monitor-workspace.css';
import SimulationPanel from './SimulationPanel';
import { getMonitorEvents, listExecutions, getExecutionOperationalEvents, listMonitorRecords, getMonitorRecord } from './api';
import { MOCK_SCENARIOS } from './scenarios';
import { formatWhen, shortId } from './components';
import { projectTransactions, projectTransaction, mergeMonitorCatalog, originLabel, kindLabel, classifyMonitorStatus, FLOW_STATUS, isTerminalMonitorState, takeLatestArrivals, pinSelectedArrival, STREAM_WINDOW } from './monitorProjection';
import { monitorEnvironmentBadge } from './monitorEnvironmentBadge';
import {
  classifyLiveFailure,
  isTerminalMonitorEventList,
  liveStreamLabel,
  liveStreamTone,
  monitorSelectionWanted,
  replaceMonitorSelectionSearch,
  safeMonitorReturnTo,
} from './monitorLiveQuery';
import { useLivePoll } from './useLivePoll';
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
  if (t.kind === 'PAYMENT' || t.recordKind === 'DISCOVERED_PAYMENT') return 'Pagamento descoberto no ActionHub Pay';
  if (t.kind === 'SYNC' || t.recordKind === 'SYNC_EXECUTION') return 'Sincronismo de recebimentos';
  return t.kind === 'SATELLITE' ? 'Interação de satélite' : 'Execução canônica';
}

function matchesQuery(t, query) {
  if (!query) return true;
  return [t.id, t.origin, t.objective, t.correlationId, t.state, t.routeRef, t.operationRef, t.eventKey, kindLabel(t.kind), transactionLabel(t)]
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

function throwIfAuthFailure(results) {
  for (const result of results) {
    if (result.status !== 'rejected') continue;
    const kind = classifyLiveFailure(result.reason);
    if (kind === 'expired' || kind === 'denied') throw result.reason;
  }
}

export default function MonitorShell() {
  const [view, setView] = useState('transactions');
  const selectedPanel = useRef(null);
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState(null);
  useEffect(() => { if (view === 'transactions' && selectedPanel.current && window.matchMedia?.('(max-width: 800px)').matches) selectedPanel.current.scrollIntoView?.({block:'start',behavior:'smooth'}); }, [selected, view]);
  const [origin, setOrigin] = useState('ALL');
  const [search, setSearch] = useState(() => {
    if (typeof window === 'undefined') return '';
    return new URLSearchParams(window.location.search).get('q') || '';
  });
  const [searchHits, setSearchHits] = useState([]);
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState(null);
  const [submittedSummary, setSubmittedSummary] = useState(null);
  const userPicked = useRef(false);
  const lastStream = useRef({events: [], summaries: [], records: []});

  const stream = useLivePoll({
    enabled: view === 'transactions',
    paused,
    intervalMs: STREAM_MS,
    resetKey: 'monitor-stream',
    forceKey: refresh,
    run: async (signal) => {
      const [events, executions, records] = await Promise.allSettled([
        getMonitorEvents({signal}),
        listExecutions({limit: 100}, {}, {signal}),
        listMonitorRecords({limit: 100}, {signal}),
      ]);
      throwIfAuthFailure([events, executions, records]);
      const errors = [];
      if (events.status === 'rejected') errors.push('Eventos indisponíveis: ' + events.reason.message);
      if (executions.status === 'rejected') errors.push('Execuções indisponíveis: ' + executions.reason.message);
      if (records.status === 'rejected') errors.push('Projeção indisponível: ' + records.reason.message);
      if (events.status === 'fulfilled' && events.value.available === false) errors.push('O armazenamento de eventos não está disponível neste ambiente.');
      const next = {
        events: events.status === 'fulfilled' ? events.value?.items || [] : lastStream.current.events,
        summaries: executions.status === 'fulfilled' ? executions.value?.items || [] : lastStream.current.summaries,
        records: records.status === 'fulfilled' ? records.value?.items || [] : lastStream.current.records,
        errors,
        availableScenarios: events.status === 'fulfilled' ? events.value?.availableScenarios : lastStream.current.availableScenarios,
        truncated: events.status === 'fulfilled' ? events.value?.truncated : lastStream.current.truncated,
        from: events.status === 'fulfilled' ? events.value?.from : lastStream.current.from,
        to: events.status === 'fulfilled' ? events.value?.to : lastStream.current.to,
        partial: errors.length > 0,
      };
      lastStream.current = next;
      return next;
    },
  });

  const evidencePoll = useLivePoll({
    enabled: view === 'transactions' && Boolean(selected),
    paused,
    intervalMs: STREAM_MS,
    resetKey: selected || '',
    forceKey: refresh,
    run: async (signal) => {
      const record = (stream.value?.records || []).find(item => item.recordId === selected);
      const eventKey = record?.eventKey || selected;
      const [events, detail] = await Promise.allSettled([
        getExecutionOperationalEvents(eventKey, {signal}),
        record ? Promise.resolve({item: record}) : getMonitorRecord(selected, {signal}).catch(() => null),
      ]);
      throwIfAuthFailure([events]);
      if (events.status === 'rejected') throw events.reason;
      return {
        items: events.value?.items || [],
        record: detail.status === 'fulfilled' ? detail.value?.item || detail.value : record || null,
      };
    },
    isTerminal: (result) => isTerminalMonitorEventList(result?.items),
  });

  const data = useMemo(() => {
    if (stream.auth === 'denied') {
      return {events: [], summaries: [], errors: stream.error ? [stream.error.message] : [], loading: false};
    }
    const value = stream.value;
    const errors = [...(value?.errors || [])];
    if (stream.error && stream.auth !== 'denied' && !errors.includes(stream.error.message)) {
      errors.push(stream.error.message);
    }
    return {
      events: value?.events || [],
      summaries: value?.summaries || [],
      records: value?.records || [],
      errors,
      loading: stream.status === 'loading' && !value,
      availableScenarios: value?.availableScenarios,
      truncated: value?.truncated,
      from: value?.from,
      to: value?.to,
    };
  }, [stream]);

  const stale = Boolean(stream.stale || stream.value?.partial || evidencePoll.stale);
  const evidence = selected ? {
    id: selected,
    events: evidencePoll.auth === 'denied' ? undefined : evidencePoll.value?.items,
    error: evidencePoll.auth === 'denied' ? evidencePoll.error?.message
      : evidencePoll.error && classifyLiveFailure(evidencePoll.error) !== 'abort'
        ? evidencePoll.error.message
        : undefined,
    loading: evidencePoll.status === 'loading' && !evidencePoll.value,
    stale: evidencePoll.stale,
  } : null;

  const transactions = useMemo(
    () => mergeMonitorCatalog(projectTransactions(data.events, data.summaries), data.records),
    [data.events, data.summaries, data.records],
  );
  const selectedRow = transactions.find(t => t.id === selected || t.eventKey === selected)
    || (submittedSummary?.executionId === selected
      ? projectTransaction(selected, data.events.filter(event => event.executionId === selected), submittedSummary)
      : undefined);
  const summary = data.summaries.find(s => s.executionId === selected) || (submittedSummary?.executionId === selected ? submittedSummary : undefined);
  const transaction = evidence?.id === selected && evidence.events?.length
    ? projectTransaction(selected, evidence.events, summary) : selectedRow;

  function syncSelectionUrl(id) {
    if (typeof window === 'undefined' || !id) return;
    const nextSearch = replaceMonitorSelectionSearch(window.location.search, id);
    const next = `${window.location.pathname}${nextSearch}${window.location.hash || ''}`;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash || ''}`;
    if (next !== current) window.history.replaceState(null, '', next);
  }

  function open(id) {
    userPicked.current = true;
    syncSelectionUrl(id);
    if (id !== selected) { setSelected(id); }
  }
  function openFromSimulation({id, summary, message: nextMessage}) {
    if (summary) setSubmittedSummary(summary);
    open(id);
    setView('transactions');
    setRefresh(n => n + 1);
    setMessage(nextMessage);
  }
  const environmentBadge = monitorEnvironmentBadge({
    events: evidence?.id === selected ? evidence.events : data.events.filter(event => event.executionId === selected),
    transaction,
  });
  const origins = [...new Set(transactions.map(t => t.origin).filter(Boolean))];
  const scoped = transactions.filter(t => origin === 'ALL' || (origin === 'UNKNOWN' ? !t.origin : t.origin === origin));
  const latest = takeLatestArrivals(scoped, STREAM_WINDOW);
  const live = pinSelectedArrival(latest, selected, selectedRow ? [...scoped, selectedRow] : scoped, STREAM_WINDOW);
  const query = search.trim().toLowerCase();
  useEffect(() => {
    if (!query) {
      setSearchHits([]);
      return undefined;
    }
    let cancelled = false;
    listMonitorRecords({q: search.trim(), limit: 50})
      .then((body) => {
        if (!cancelled) setSearchHits(body?.items || []);
      })
      .catch(() => {
        if (!cancelled) setSearchHits([]);
      });
    return () => { cancelled = true; };
  }, [query, search]);
  const matches = query ? mergeMonitorCatalog(scoped.filter(t => matchesQuery(t, query)), searchHits) : [];
  useEffect(() => {
    if (typeof window === 'undefined') return;
    function onPop() {
      userPicked.current = false;
      const wanted = monitorSelectionWanted(window.location.search);
      if (wanted) setSelected(wanted);
    }
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  useEffect(() => {
    if (typeof window === 'undefined' || userPicked.current) return;
    const wanted = monitorSelectionWanted(window.location.search);
    if (!wanted) return;
    const match = transactions.find(t => t.id === wanted || t.correlationId === wanted);
    setSelected(match ? match.id : wanted);
  }, [transactions]);

  useEffect(() => {
    if (userPicked.current || selected || !live.length) return;
    if (typeof window !== 'undefined' && monitorSelectionWanted(window.location.search)) return;
    userPicked.current = true;
    setSelected(live[0].id);
  }, [live, selected]);

  const streamLabel = liveStreamLabel({
    paused,
    auth: stream.auth,
    stale,
    updatedAt: stream.updatedAt,
    formatWhen,
  });
  const returnTo = safeMonitorReturnTo();

  return <div className="obs-shell monitor-shell" data-testid="spider-console">
    <header className="monitor-header"><div><p className="obs-brand">SPIDER · MONITOR</p><h1>Monitor de transações</h1></div>
      <div className="monitor-header-actions">
        <span className="pill mock-badge" data-mock={environmentBadge.mock ? 'true' : 'false'}>{environmentBadge.label}</span>
        <a className="ghost" href="/logout">Sair</a>
      </div></header>
    <nav className="monitor-nav" aria-label="Navegação do Monitor">{NAV.map(([id,label]) => <button key={id} type="button"
      aria-current={view === id ? 'page' : undefined} onClick={() => setView(id)}>{label}</button>)}</nav>
    {view === 'transactions' && stream.auth === 'expired' && <p role="alert" className="banner">
      Sessão expirada. <a href={returnTo}>Entrar novamente</a> para continuar neste destino. A atualização automática foi interrompida.
    </p>}
    {view === 'transactions' && stream.auth === 'denied' && <p role="alert" className="banner">
      O acesso a este recorte foi recusado. O conteúdo anterior foi removido.
    </p>}
    {view === 'transactions' && message && <p role="status" className="banner">{message}</p>}
    {view === 'transactions' && <><div className="monitor-workspace-grid">
      <section className="panel-card transaction-list-panel" aria-label="Fluxo de transações">
        <div className="monitor-section-heading"><h2>Fluxo de transações</h2>
          <p className="transaction-live-status" role="status" data-live={liveStreamTone({paused, auth: stream.auth, stale})}>
            {streamLabel} · {live.length} mais recente{live.length === 1 ? '' : 's'}{scoped.length > live.length ? ` · ${scoped.length} no recorte` : ''}{data.truncated ? ' · últimos 2.000 eventos' : ''}
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
        {data.errors.length > 0 && stream.auth !== 'expired' && stream.auth !== 'denied' ? (
          <p>
            <button className="ghost" type="button" onClick={() => setRefresh(n => n + 1)} disabled={data.loading}>
              Tentar novamente
            </button>
          </p>
        ) : null}
        {!data.loading && live.length === 0 && data.errors.length === 0 && stream.auth !== 'denied' && <p>Nenhuma transação neste recorte.</p>}
        <div className="monitor-transactions">{live.map(t => <TransactionLine key={t.id} t={t} selected={selected} onOpen={open} />)}</div>
      </section>
      {selected && evidence?.loading && !transaction && <p className="panel-card workspace-empty" role="status">Carregando…</p>}
      {transaction && <TransactionWorkspace key={selected} transaction={transaction} identityRef={selectedPanel} paused={paused} relatedEventsError={evidence?.id === selected ? evidence.error : null} />}
      {selected && !evidence?.loading && !transaction && evidence?.error && (
        <section className="panel-card workspace-empty" aria-label="Transação selecionada">
          <p role="status">{evidence.error.includes('404') || evidence.error.includes('403') || evidence.error.includes('recusada')
            ? 'Esta execução não está disponível neste recorte. Pode ter expirado ou o acesso não é autorizado.'
            : evidence.error}</p>
        </section>
      )}
      {selected && !evidence?.loading && !transaction && !evidence?.error && (
        <section className="panel-card workspace-empty" aria-label="Transação selecionada">
          <p role="status">Esta execução não está na retenção atual da engine. Não é o mesmo que acesso negado a outra empresa.</p>
        </section>
      )}
      {!selected && <section className="panel-card workspace-empty" aria-label="Transação selecionada"><p>Selecione uma transação no fluxo.</p></section>}
      </div>
    </>}
    {view === 'documentation' && <MonitorDocumentation />}
    {view === 'simulate' && <SimulationPanel availableScenarios={data.availableScenarios} loadingScenarios={data.loading} onOpened={openFromSimulation} />}
  </div>;
}
