import { COMPONENTS } from './components.js';
import { PROTOCOLS } from './protocols.js';
import { TABLES } from './schema.js';
import { ENVIRONMENT } from './environment.js';
import { ARCHITECTURE_LANES, ARCHITECTURE_EDGES } from './architecture.js';
import { SEARCH_INDEX } from './searchIndex.js';

const FORBIDDEN_IMPLEMENTED = [
  /composer de resposta/i,
  /agente conversacional/i,
  /reconciliation workbench/i,
];

function uniqueIds(items, label, errors) {
  const seen = new Set();
  items.forEach((item) => {
    if (!item.id) errors.push(`${label} sem id`);
    else if (seen.has(item.id)) errors.push(`${label} duplicado: ${item.id}`);
    else seen.add(item.id);
  });
  return seen;
}

export function collectEvidenceRefs() {
  const refs = [];
  const add = (owner, evidence = []) => {
    evidence.forEach((item) => {
      if (item?.path) refs.push({ owner, path: item.path, label: item.label || item.path });
    });
  };
  COMPONENTS.forEach((c) => {
    add(c.id, c.evidence);
    (c.methods || []).forEach((m) => {
      if (m.source) refs.push({ owner: `${c.id}:${m.signature}`, path: m.source, label: m.signature });
    });
  });
  PROTOCOLS.forEach((p) => add(p.id, p.evidence));
  TABLES.forEach((t) => {
    if (t.migration) refs.push({ owner: t.id, path: t.migration, label: 'migration' });
    (t.alteredBy || []).forEach((path) => refs.push({ owner: t.id, path, label: 'alter' }));
  });
  return refs;
}

export function validateDocumentationContent({
  components = COMPONENTS,
  protocols = PROTOCOLS,
  tables = TABLES,
  environment = ENVIRONMENT,
  lanes = ARCHITECTURE_LANES,
  edges = ARCHITECTURE_EDGES,
  searchIndex = SEARCH_INDEX,
} = {}) {
  const errors = [];
  const componentIds = uniqueIds(components, 'componente', errors);
  const protocolIds = uniqueIds(protocols, 'protocolo', errors);
  uniqueIds(tables, 'tabela', errors);

  lanes.forEach((lane) => {
    (lane.nodes || []).forEach((id) => {
      if (!componentIds.has(id)) errors.push(`nó de arquitetura sem componente: ${id}`);
    });
  });

  edges.forEach((edge) => {
    if (!edge.from || !edge.to) errors.push(`relação sem origem/destino: ${edge.id || '?'}`);
    if (edge.from && !componentIds.has(edge.from)) errors.push(`relação origem inexistente: ${edge.from}`);
    if (edge.to && !componentIds.has(edge.to)) errors.push(`relação destino inexistente: ${edge.to}`);
    if (edge.protocol && !protocolIds.has(edge.protocol)) errors.push(`relação sem protocolo: ${edge.id} → ${edge.protocol}`);
  });

  tables.forEach((table) => {
    if (!table.migration) errors.push(`tabela sem migration de origem: ${table.id}`);
  });

  const deps = [...environment.backend, ...environment.frontend, ...environment.infra];
  deps.forEach((dep) => {
    if (!dep.source || !dep.required) errors.push(`dependência sem fonte/versão: ${dep.id || dep.name}`);
  });

  const implementedText = [
    ...components.filter((c) => c.status === 'implemented').map((c) => `${c.name} ${c.responsibility}`),
    ...protocols.filter((p) => p.status === 'implemented').map((p) => `${p.name} ${p.purpose}`),
  ].join('\n');
  FORBIDDEN_IMPLEMENTED.forEach((re) => {
    if (re.test(implementedText)) errors.push(`termo indevido em item implementado: ${re}`);
  });

  if (!searchIndex.length) errors.push('índice de busca vazio');

  return { ok: errors.length === 0, errors };
}
