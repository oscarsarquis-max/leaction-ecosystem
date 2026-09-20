import { COMPONENTS } from './components.js';
import { PROTOCOLS } from './protocols.js';
import { TABLES } from './schema.js';
import { ENVIRONMENT } from './environment.js';
import { ARCHITECTURE_LANES, ARCHITECTURE_EDGES } from './architecture.js';

function push(list, item) {
  const terms = [...new Set((item.terms || []).map((t) => String(t).toLowerCase()).filter(Boolean))];
  list.push({ ...item, terms, haystack: `${item.title} ${item.subtitle || ''} ${terms.join(' ')}`.toLowerCase() });
}

export function buildSearchIndex() {
  const items = [];

  ARCHITECTURE_LANES.forEach((lane) => {
    push(items, {
      id: `arch-lane-${lane.id}`,
      category: 'Arquitetura',
      section: 'architecture',
      itemId: lane.nodes[0],
      title: lane.title,
      subtitle: 'Faixa do diagrama',
      terms: [lane.title, lane.id, ...lane.nodes],
    });
  });
  ARCHITECTURE_EDGES.forEach((edge) => {
    push(items, {
      id: `arch-edge-${edge.id}`,
      category: 'Arquitetura',
      section: 'architecture',
      itemId: edge.from,
      protocolId: edge.protocol,
      edgeId: edge.id,
      title: edge.label,
      subtitle: `${edge.from} → ${edge.to}`,
      terms: [edge.label, edge.kind, edge.protocol, edge.from, edge.to],
    });
  });

  COMPONENTS.forEach((component) => {
    push(items, {
      id: `comp-${component.id}`,
      category: 'Componentes',
      section: 'components',
      itemId: component.id,
      title: component.name,
      subtitle: component.type,
      terms: [
        component.name,
        component.id,
        component.type,
        component.responsibility,
        ...(component.aliases || []),
        ...(component.contracts || []),
        ...(component.methods || []).flatMap((m) => [m.signature, m.purpose]),
      ],
    });
    (component.methods || []).forEach((method, index) => {
      push(items, {
        id: `meth-${component.id}-${index}`,
        category: 'Componentes',
        section: 'components',
        itemId: component.id,
        title: method.signature,
        subtitle: `${component.name} · método`,
        terms: [method.signature, method.purpose, method.type, component.name],
      });
    });
  });

  PROTOCOLS.forEach((protocol) => {
    push(items, {
      id: `prot-${protocol.id}`,
      category: 'Protocolos',
      section: 'protocols',
      itemId: protocol.id,
      title: protocol.name,
      subtitle: protocol.category,
      terms: [protocol.name, protocol.id, protocol.category, protocol.purpose, protocol.media, ...(protocol.aliases || [])],
    });
  });

  TABLES.forEach((table) => {
    push(items, {
      id: `tbl-${table.id}`,
      category: 'PostgreSQL',
      section: 'schema',
      itemId: table.id,
      title: table.id,
      subtitle: table.purpose,
      terms: [table.id, table.purpose, table.migration, ...(table.columns || []).map((c) => c.name), ...(table.jsonb || []), ...(table.jsonText || [])],
    });
  });

  const deps = [...ENVIRONMENT.backend, ...ENVIRONMENT.frontend, ...ENVIRONMENT.infra];
  deps.forEach((dep) => {
    push(items, {
      id: `env-${dep.id}`,
      category: 'Ambiente',
      section: 'environment',
      itemId: dep.id,
      title: dep.name,
      subtitle: `req ${dep.required} · obs ${dep.observed}`,
      terms: [dep.name, dep.id, dep.required, dep.observed, dep.source, dep.role],
    });
  });
  ENVIRONMENT.profiles.forEach((profile) => {
    push(items, {
      id: `profile-${profile.id}`,
      category: 'Ambiente',
      section: 'environment',
      itemId: profile.id,
      title: profile.name,
      subtitle: 'perfil',
      terms: [profile.name, profile.id, profile.summary],
    });
  });

  return items;
}

export const SEARCH_INDEX = buildSearchIndex();

export function searchDocumentation(query, index = SEARCH_INDEX) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return [];
  const tokens = q.split(/\s+/);
  return index.filter((item) => tokens.every((token) => item.haystack.includes(token)));
}
