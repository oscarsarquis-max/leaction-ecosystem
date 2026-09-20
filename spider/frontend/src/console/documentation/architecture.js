export const ARCHITECTURE_LANES = [
  {
    id: 'origins',
    title: 'Origens e entradas',
    nodes: ['canonical-http', 'satellite-http', 'signal-http', 'context-http', 'contextual-link'],
  },
  {
    id: 'contracts',
    title: 'Contratos e segurança',
    nodes: ['canonical-ingress-auth', 'satellite-registry', 'replay-guard'],
  },
  {
    id: 'context',
    title: 'Contexto e intenção',
    nodes: ['context-intelligence', 'context-ai'],
  },
  {
    id: 'catalog',
    title: 'Catálogo, capacidades, resolução e policies',
    nodes: ['capability-catalog', 'execution-plan-catalog'],
  },
  {
    id: 'engine',
    title: 'Execution Plan e Execution Engine',
    nodes: ['submit-canonical', 'canonical-engine'],
  },
  {
    id: 'workers',
    title: 'Workers e concorrência',
    nodes: ['worker-runtime', 'capacity-admission'],
  },
  {
    id: 'adapters',
    title: 'Portas, adapters e providers',
    nodes: ['provider-adapter', 'mock-universal-adapter'],
  },
  {
    id: 'async',
    title: 'Wait, signal, callbacks e outbox',
    nodes: ['wait-signal', 'callback-outbox', 'callback-reconciliation'],
  },
  {
    id: 'persistence',
    title: 'Persistência PostgreSQL',
    nodes: ['persistence-ports'],
  },
  {
    id: 'observe',
    title: 'Operational Events e Monitor',
    nodes: ['operational-events', 'monitor-query'],
  },
];

export const ARCHITECTURE_BOUNDARIES = [
  { id: 'spider', label: 'Spider (Control Plane)', kind: 'spider' },
  { id: 'satellites', label: 'Experience Satellites', kind: 'satellite' },
  { id: 'providers', label: 'Providers / sistemas externos', kind: 'external' },
  { id: 'infra', label: 'Infraestrutura de dados', kind: 'infra' },
];

export const ARCHITECTURE_EDGES = [
  { id: 'e-canonical-in', from: 'canonical-http', to: 'submit-canonical', kind: 'sync', protocol: 'canonical-http', label: 'POST /v1/canonical/executions' },
  { id: 'e-sat-in', from: 'satellite-http', to: 'satellite-registry', kind: 'sync', protocol: 'satellite-contract', label: 'SAT-003' },
  { id: 'e-sat-engine', from: 'satellite-registry', to: 'capability-catalog', kind: 'sync', protocol: 'internal-port', label: 'regras + catálogo' },
  { id: 'e-signal', from: 'signal-http', to: 'wait-signal', kind: 'signal', protocol: 'external-signal', label: 'POST /v1/canonical/signals' },
  { id: 'e-context', from: 'context-http', to: 'context-intelligence', kind: 'sync', protocol: 'context-http', label: 'interpretação / plano' },
  { id: 'e-ai', from: 'context-intelligence', to: 'context-ai', kind: 'sync', protocol: 'context-ai', label: 'provider opcional' },
  { id: 'e-submit', from: 'submit-canonical', to: 'canonical-engine', kind: 'sync', protocol: 'internal-port', label: 'engine' },
  { id: 'e-plan', from: 'execution-plan-catalog', to: 'canonical-engine', kind: 'sync', protocol: 'internal-port', label: 'plano' },
  { id: 'e-caps', from: 'capability-catalog', to: 'canonical-engine', kind: 'sync', protocol: 'internal-port', label: 'capabilities' },
  { id: 'e-adapter', from: 'canonical-engine', to: 'provider-adapter', kind: 'sync', protocol: 'provider-http', label: 'resolver + executar' },
  { id: 'e-mock', from: 'canonical-engine', to: 'mock-universal-adapter', kind: 'sync', protocol: 'mock-adapter', label: 'mock-universal' },
  { id: 'e-wait', from: 'canonical-engine', to: 'wait-signal', kind: 'signal', protocol: 'wait-inbox', label: 'WAITING_EXTERNAL' },
  { id: 'e-outbox', from: 'canonical-engine', to: 'callback-outbox', kind: 'callback', protocol: 'callback-outbox', label: 'outbox' },
  { id: 'e-recon', from: 'callback-outbox', to: 'callback-reconciliation', kind: 'callback', protocol: 'callback-reconciliation', label: 'reconciliação operacional' },
  { id: 'e-workers', from: 'worker-runtime', to: 'wait-signal', kind: 'event', protocol: 'worker-lease', label: 'SIGNAL / WAIT' },
  { id: 'e-workers-cb', from: 'worker-runtime', to: 'callback-outbox', kind: 'event', protocol: 'worker-lease', label: 'CALLBACK_DELIVERY' },
  { id: 'e-persist', from: 'canonical-engine', to: 'persistence-ports', kind: 'persist', protocol: 'jpa-jdbc', label: 'stores' },
  { id: 'e-events', from: 'canonical-engine', to: 'operational-events', kind: 'event', protocol: 'operational-events', label: 'emit' },
  { id: 'e-sat-events', from: 'satellite-registry', to: 'operational-events', kind: 'event', protocol: 'operational-events', label: 'satélite' },
  { id: 'e-monitor', from: 'operational-events', to: 'monitor-query', kind: 'monitor', protocol: 'monitor-http', label: 'read model' },
  { id: 'e-link', from: 'contextual-link', to: 'context-intelligence', kind: 'sync', protocol: 'contextual-link', label: '/go e entry legado' },
];

export const ARCHITECTURE_LEGEND = [
  { kind: 'sync', label: 'Chamada síncrona' },
  { kind: 'persist', label: 'Persistência' },
  { kind: 'event', label: 'Evento operacional / worker' },
  { kind: 'signal', label: 'Sinal / wait' },
  { kind: 'callback', label: 'Callback / outbox' },
  { kind: 'monitor', label: 'Leitura do Monitor' },
];
