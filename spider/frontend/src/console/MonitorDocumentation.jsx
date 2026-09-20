import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ARCHITECTURE_BOUNDARIES,
  ARCHITECTURE_EDGES,
  ARCHITECTURE_LANES,
  ARCHITECTURE_LEGEND,
  COMPONENTS,
  DOCUMENTATION_SNAPSHOT,
  ENVIRONMENT,
  PROTOCOLS,
  SCHEMA_GROUPS,
  SCHEMA_NOTE,
  SCHEMA_RUNTIME,
  TABLES,
  searchDocumentation,
} from './documentation/index.js';
import './documentation.css';

const SECTIONS = [
  { id: 'architecture', label: 'Arquitetura' },
  { id: 'components', label: 'Componentes' },
  { id: 'protocols', label: 'Protocolos' },
  { id: 'schema', label: 'PostgreSQL' },
  { id: 'environment', label: 'Ambiente e versões' },
];

const byId = (list) => Object.fromEntries(list.map((item) => [item.id, item]));
const COMPONENT_MAP = byId(COMPONENTS);
const PROTOCOL_MAP = byId(PROTOCOLS);
const TABLE_MAP = byId(TABLES);

function Status({ status, extra }) {
  return <span className="doc-status" data-status={status}>{DOCUMENTATION_SNAPSHOT.statuses[status] || status}{extra ? ` · ${extra}` : ''}</span>;
}

function EvidenceList({ items = [] }) {
  if (!items.length) return <p>Nenhuma evidência de arquivo associada.</p>;
  return <ul className="doc-evidence">
    {items.map((item) => <li key={`${item.path}-${item.label}`}>
      <span>{item.label}</span>
      <code>{item.path}</code>
    </li>)}
  </ul>;
}

function Provenance() {
  return <p className="doc-provenance">{DOCUMENTATION_SNAPSHOT.source} · snapshot {DOCUMENTATION_SNAPSHOT.generatedAt}. {DOCUMENTATION_SNAPSHOT.note}</p>;
}

function openFromSearch(result, setSection, setters) {
  setSection(result.section);
  if (result.section === 'components') setters.component(result.itemId);
  if (result.section === 'protocols') setters.protocol(result.itemId);
  if (result.section === 'schema') setters.table(result.itemId);
  if (result.section === 'environment') setters.env(result.itemId);
  if (result.section === 'architecture') {
    setters.node(result.itemId);
    if (result.protocolId) setters.edge(result.edgeId || result.protocolId);
  }
}

export default function MonitorDocumentation() {
  const [section, setSection] = useState('architecture');
  const [query, setQuery] = useState('');
  const [componentId, setComponentId] = useState(COMPONENTS[0].id);
  const [protocolId, setProtocolId] = useState(PROTOCOLS[0].id);
  const [tableId, setTableId] = useState(TABLES[0].id);
  const [envId, setEnvId] = useState(ENVIRONMENT.backend[0].id);
  const [nodeId, setNodeId] = useState(null);
  const [edgeId, setEdgeId] = useState(null);
  const headingRef = useRef(null);
  const results = useMemo(() => searchDocumentation(query).slice(0, 12), [query]);

  useEffect(() => { headingRef.current?.focus(); }, [section]);

  const setters = { component: setComponentId, protocol: setProtocolId, table: setTableId, env: setEnvId, node: setNodeId, edge: setEdgeId };
  const goResult = (result) => {
    if (!result) return;
    openFromSearch(result, setSection, setters);
    setQuery('');
  };

  const component = COMPONENT_MAP[componentId] || COMPONENTS[0];
  const protocol = PROTOCOL_MAP[protocolId] || PROTOCOLS[0];
  const table = TABLE_MAP[tableId] || TABLES[0];

  return <section className="panel-card documentation-page" data-testid="documentation-page">
    <p className="obs-brand">REFERÊNCIA TÉCNICA</p>
    <h2>Documentação da Spider</h2>
    <p className="documentation-lede">Arquitetura, componentes, protocolos, dados e ambiente reunidos em uma única referência navegável.</p>
    <form className="doc-search" role="search" onSubmit={(e) => { e.preventDefault(); goResult(results[0]); }}>
      <label htmlFor="documentation-search">Buscar componente, protocolo, tabela ou versão</label>
      <input id="documentation-search" data-testid="documentation-search" value={query} onChange={(e) => setQuery(e.target.value)}
        placeholder="Buscar componente, protocolo, tabela ou versão"
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); goResult(results[0]); } }}
        aria-controls="documentation-search-results" aria-autocomplete="list" />
      {query && <ul id="documentation-search-results" className="doc-search-results" role="listbox" aria-label="Resultados da documentação">
        {results.length === 0 && <li><button type="button" disabled>Nenhum resultado</button></li>}
        {results.map((result, index) => <li key={result.id} role="option">
          <button type="button" aria-selected={index === 0} onClick={() => goResult(result)}>
            {result.title}<small>{result.category}{result.subtitle ? ` · ${result.subtitle}` : ''}</small>
          </button>
        </li>)}
      </ul>}
    </form>
    <div className="documentation-layout">
      <nav className="documentation-index" aria-label="Índice da documentação" data-sticky="true">
        {SECTIONS.map((item) => <button type="button" className="ghost" key={item.id} aria-current={section === item.id} onClick={() => setSection(item.id)}>{item.label}</button>)}
      </nav>
      <article className="documentation-content">
        <h3 ref={headingRef} tabIndex={-1} id="documentation-section-title">{SECTIONS.find((item) => item.id === section)?.label}</h3>
        {section === 'architecture' && <ArchitectureView nodeId={nodeId} edgeId={edgeId}
          onNode={(id) => { setNodeId(id); setComponentId(id); setSection('components'); }}
          onEdge={(edge) => { setEdgeId(edge.id); if (edge.protocol) { setProtocolId(edge.protocol); setSection('protocols'); } }} />}
        {section === 'components' && <ComponentView selected={component} onSelect={setComponentId} />}
        {section === 'protocols' && <ProtocolView selected={protocol} onSelect={setProtocolId} onComponent={(id) => { setComponentId(id); setSection('components'); }} />}
        {section === 'schema' && <SchemaView selected={table} onSelect={setTableId} />}
        {section === 'environment' && <EnvironmentView selectedId={envId} onSelect={setEnvId} />}
        <Provenance />
      </article>
    </div>
  </section>;
}

function ArchitectureView({ nodeId, edgeId, onNode, onEdge }) {
  return <div data-testid="architecture-diagram">
    <p>Somente componentes existentes no repositório. Clique no nó para o catálogo; na relação, para o protocolo.</p>
    <ul className="doc-legend">{ARCHITECTURE_LEGEND.map((item) => <li key={item.kind}><i data-kind={item.kind} />{item.label}</li>)}</ul>
    <p className="doc-boundaries">{ARCHITECTURE_BOUNDARIES.map((item) => <span key={item.id} data-kind={item.kind}>{item.label}</span>)}</p>
    <div className="arch-lanes arch-wide">
      {ARCHITECTURE_LANES.map((lane) => <section className="arch-lane" key={lane.id}>
        <h4>{lane.title}</h4>
        <div className="arch-nodes">
          {lane.nodes.map((id) => {
            const node = COMPONENT_MAP[id];
            return <button type="button" key={id} aria-pressed={nodeId === id} data-profile={node?.status === 'profile' || undefined} onClick={() => onNode(id)}>
              {node?.name || id}{node?.status === 'profile' ? ' · perfil' : ''}
            </button>;
          })}
        </div>
      </section>)}
    </div>
    <ol className="arch-edges">
      {ARCHITECTURE_EDGES.map((edge) => <li key={edge.id}>
        <button type="button" data-kind={edge.kind} aria-pressed={edgeId === edge.id} onClick={() => onEdge(edge)}>
          {COMPONENT_MAP[edge.from]?.name || edge.from} → {COMPONENT_MAP[edge.to]?.name || edge.to} · {edge.label}
        </button>
      </li>)}
    </ol>
    <details className="arch-alt">
      <summary>Alternativa textual do diagrama</summary>
      <ul>{ARCHITECTURE_EDGES.map((edge) => <li key={edge.id}>{edge.from} {edge.kind} {edge.to} ({edge.protocol}): {edge.label}</li>)}</ul>
    </details>
  </div>;
}

function ComponentView({ selected, onSelect }) {
  return <div className="doc-split" data-testid="component-catalog">
    <div className="doc-index-list" role="listbox" aria-label="Catálogo de componentes">
      {COMPONENTS.map((item) => <button type="button" className="ghost" key={item.id} role="option" aria-current={selected.id === item.id} onClick={() => onSelect(item.id)}>
        {item.name}
      </button>)}
    </div>
    <div className="doc-detail">
      <h3>{selected.name}</h3>
      <p><Status status={selected.status} extra={selected.profile} /> · {selected.type}</p>
      <dl className="doc-kv">
        <div><dt>Responsabilidade</dt><dd>{selected.responsibility}</dd></div>
        <div><dt>Não faz</dt><dd>{selected.not || '—'}</dd></div>
        <div><dt>Entradas</dt><dd>{(selected.inputs || []).join(', ') || '—'}</dd></div>
        <div><dt>Saídas</dt><dd>{(selected.outputs || []).join(', ') || '—'}</dd></div>
        <div><dt>Relacionados</dt><dd>{(selected.related || []).join(', ') || '—'}</dd></div>
        <div><dt>Contratos</dt><dd>{(selected.contracts || []).join(', ') || '—'}</dd></div>
        <div><dt>Persistência</dt><dd>{selected.persistence || '—'}</dd></div>
        <div><dt>Configuração</dt><dd>{(selected.config || []).join(', ') || '—'}</dd></div>
        <div><dt>Erros</dt><dd>{selected.errors || '—'}</dd></div>
        {selected.states && <div><dt>Estados</dt><dd>{selected.states}</dd></div>}
      </dl>
      <h4>Métodos e funções</h4>
      <ol className="doc-methods">
        {(selected.methods || []).map((method) => <li key={method.signature}>
          <h5>{method.signature}</h5>
          <dl className="doc-kv">
            <div><dt>Classe / tipo</dt><dd>{method.type}</dd></div>
            <div><dt>Finalidade</dt><dd>{method.purpose}</dd></div>
            <div><dt>Resultado</dt><dd>{method.result}</dd></div>
            <div><dt>Efeitos</dt><dd>{method.effects}</dd></div>
            <div><dt>Erros</dt><dd>{method.errors}</dd></div>
            <div><dt>Fonte</dt><dd><code>{method.source}</code></dd></div>
          </dl>
        </li>)}
      </ol>
      <h4>Evidências</h4>
      <EvidenceList items={selected.evidence} />
    </div>
  </div>;
}

function ProtocolView({ selected, onSelect, onComponent }) {
  return <div className="doc-split" data-testid="protocol-matrix">
    <div className="doc-index-list" role="listbox" aria-label="Protocolos">
      {PROTOCOLS.map((item) => <button type="button" className="ghost" key={item.id} role="option" aria-current={selected.id === item.id} onClick={() => onSelect(item.id)}>{item.name}</button>)}
    </div>
    <div className="doc-detail">
      <h3>{selected.name}</h3>
      <p><Status status={selected.status} extra={selected.profile} /> · {selected.category}</p>
      <dl className="doc-kv">
        <div><dt>Origem</dt><dd>{(selected.from || []).join(', ')}</dd></div>
        <div><dt>Destino</dt><dd>{(selected.to || []).map((id) => COMPONENT_MAP[id] ? <button type="button" className="ghost" key={id} onClick={() => onComponent(id)}>{COMPONENT_MAP[id].name}</button> : id)}</dd></div>
        <div><dt>Direção</dt><dd>{selected.direction}</dd></div>
        <div><dt>Finalidade</dt><dd>{selected.purpose}</dd></div>
        <div><dt>Formato</dt><dd>{selected.media}</dd></div>
        <div><dt>Autenticação</dt><dd>{selected.auth}</dd></div>
        <div><dt>Versionamento</dt><dd>{selected.version}</dd></div>
        <div><dt>Identidade / idempotência</dt><dd>{selected.identity}</dd></div>
        <div><dt>Timeout / retry</dt><dd>{selected.timeoutRetry}</dd></div>
        <div><dt>Falhas</dt><dd>{selected.failures}</dd></div>
      </dl>
      <h4>Evidências</h4>
      <EvidenceList items={selected.evidence} />
    </div>
  </div>;
}

function SchemaView({ selected, onSelect }) {
  return <div data-testid="schema-diagram">
    <p>{SCHEMA_NOTE}</p>
    <p>Runtime: Docker {SCHEMA_RUNTIME.docker}. Flyway: {SCHEMA_RUNTIME.flyway} Default: {SCHEMA_RUNTIME.defaultApp} local-demo: {SCHEMA_RUNTIME.localDemo}</p>
    <div className="schema-groups" aria-label="Diagrama de tabelas">
      {SCHEMA_GROUPS.map((group) => <section className="schema-group" key={group.id}>
        <h4>{group.title}</h4>
        <ul>{group.tables.map((id) => <li key={id}><button type="button" aria-current={selected.id === id} onClick={() => onSelect(id)}>{id}</button></li>)}</ul>
      </section>)}
    </div>
    <div className="schema-list" aria-label="Lista hierárquica de tabelas">
      {SCHEMA_GROUPS.map((group) => <details key={group.id} open>
        <summary>{group.title}</summary>
        <ul>{group.tables.map((id) => <li key={id}><button type="button" className="ghost" aria-current={selected.id === id} onClick={() => onSelect(id)}>{id}</button></li>)}</ul>
      </details>)}
    </div>
    <div className="doc-detail">
      <h3>{selected.id}</h3>
      <p><Status status={selected.status || 'implemented'} /> · {selected.purpose}</p>
      <dl className="doc-kv">
        <div><dt>Migration de origem</dt><dd><code>{selected.migration}</code></dd></div>
        {selected.alteredBy && <div><dt>Alterações</dt><dd>{selected.alteredBy.map((path) => <code key={path}>{path}</code>)}</dd></div>}
        <div><dt>Chave primária</dt><dd>{selected.pk.join(', ')}</dd></div>
        <div><dt>Únicos</dt><dd>{(selected.unique || []).join(', ') || 'nenhum'}</dd></div>
        <div><dt>FK declaradas</dt><dd>{(selected.fk || []).join(', ') || 'nenhuma no SQL'}</dd></div>
        <div><dt>Índices</dt><dd>{(selected.indexes || []).join(', ') || '—'}</dd></div>
        <div><dt>JSON / JSONB</dt><dd>{[...(selected.jsonb || []), ...(selected.jsonText || [])].join(', ') || '—'}</dd></div>
        <div><dt>Cardinalidade</dt><dd>{selected.cardinality}</dd></div>
        <div><dt>Leitura</dt><dd>{(selected.readers || []).join(', ')}</dd></div>
        <div><dt>Escrita</dt><dd>{(selected.writers || []).join(', ')}</dd></div>
      </dl>
      <div className="doc-table-wrap">
        <table>
          <thead><tr><th>Coluna</th><th>Tipo</th></tr></thead>
          <tbody>{(selected.columns || []).map((col) => <tr key={col.name}><td>{col.name}</td><td>{col.type}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  </div>;
}

function EnvironmentView({ selectedId, onSelect }) {
  const rows = [...ENVIRONMENT.backend, ...ENVIRONMENT.frontend, ...ENVIRONMENT.infra];
  return <div data-testid="environment-versions">
    <p>{ENVIRONMENT.note}</p>
    <h4>Backend, frontend e dados</h4>
    <div className="doc-table-wrap">
      <table>
        <thead><tr><th>Item</th><th>Requerida</th><th>Observada</th><th>Fonte</th><th>Função</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id} data-selected={selectedId === row.id || undefined} onClick={() => onSelect(row.id)}>
          <td>{row.name}</td><td>{row.required}</td><td>{row.observed}</td><td><code>{row.source}</code></td><td>{row.role}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <h4>Portas</h4>
    <div className="doc-table-wrap">
      <table>
        <thead><tr><th>Porta</th><th>Serviço</th><th>Perfil</th><th>Fonte</th></tr></thead>
        <tbody>{ENVIRONMENT.ports.map((row) => <tr key={`${row.port}-${row.service}`}><td>{row.port}</td><td>{row.service}</td><td>{row.profile}</td><td>{row.source}</td></tr>)}</tbody>
      </table>
    </div>
    <h4>Variáveis (somente nomes)</h4>
    <div className="doc-table-wrap">
      <table>
        <thead><tr><th>Nome</th><th>Finalidade</th></tr></thead>
        <tbody>{ENVIRONMENT.variables.map((row) => <tr key={row.name}><td><code>{row.name}</code></td><td>{row.purpose}</td></tr>)}</tbody>
      </table>
    </div>
    <h4>Perfis</h4>
    {ENVIRONMENT.profiles.map((profile) => <section key={profile.id} id={profile.id}>
      <h5>{profile.name} <Status status={profile.status} /></h5>
      <p>{profile.summary}</p>
      <p><code>{profile.source}</code></p>
    </section>)}
    <h4>Scripts e limitações</h4>
    <ul>{ENVIRONMENT.scripts.map((item) => <li key={item.name}><code>{item.name}</code> — {item.purpose}</li>)}</ul>
    <ul>{ENVIRONMENT.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
  </div>;
}
