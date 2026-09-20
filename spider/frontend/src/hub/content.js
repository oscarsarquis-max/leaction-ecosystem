export const NAV = [
  { href: "#proposicao", label: "Plataforma", id: "proposicao" },
  { href: "#como-funciona", label: "Como funciona", id: "como-funciona" },
  { href: "#capacidades", label: "Capacidades", id: "capacidades" },
  { href: "#experiencias", label: "Experiências", id: "experiencias" },
  { href: "#arquitetura", label: "Arquitetura", id: "arquitetura" },
];

export const BEFORE_FLOW = [
  { id: "user", label: "Usuário" },
  { id: "product", label: "Produto" },
  { id: "process", label: "Processo" },
  { id: "sys-a", label: "Sistema A" },
  { id: "sys-b", label: "Sistema B" },
];

export const AFTER_FLOW = [
  { id: "user", label: "Usuário" },
  { id: "objective", label: "Objetivo" },
  { id: "spider", label: "Spider" },
  { id: "caps", label: "Capacidades" },
  { id: "systems", label: "Sistemas" },
];

export const PROBLEMS = [
  {
    id: "experience",
    title: "Experiência fragmentada",
    body: "O usuário precisa conhecer produtos, filas e jargão interno para obter um resultado.",
    highlights: ["user", "product", "process"],
  },
  {
    id: "integration",
    title: "Integração fragmentada",
    body: "Cada jornada cria integrações ponto a ponto. O legado fica isolado.",
    highlights: ["sys-a", "sys-b"],
  },
  {
    id: "decision",
    title: "Decisão fragmentada",
    body: "Regras, contexto e execução ficam espalhados. Ninguém reconstitui o caminho.",
    highlights: ["process", "sys-a"],
  },
];

export const PIPELINE_STEPS = [
  {
    id: "objetivo",
    short: "Objetivo",
    zone: "input",
    modeLabel: "Entrada",
    happens: "A pessoa declara o que precisa resolver agora.",
    why: "Sem objetivo, o Spider não tem o que planejar.",
    who: "Usuário no satélite.",
    result: "Pedido humano, ainda sem sistema escolhido.",
  },
  {
    id: "entendimento",
    short: "Entendimento",
    zone: "probabilistic",
    modeLabel: "IA",
    iaLabel: "IA interpreta.",
    happens: "Linguagem e contexto viram uma representação estruturada.",
    why: "O pedido chega em linguagem natural; a execução precisa de significado.",
    who: "Context Intelligence / IA.",
    result: "Entendimento que alimenta o Intent Contract.",
  },
  {
    id: "intent",
    short: "Intent",
    zone: "boundary",
    modeLabel: "IA → DET",
    boundaryLabel: "IA interpreta | Spider decide",
    happens: "A necessidade fica acordada, limitada e verificável.",
    why: "É a fronteira entre interpretação e decisão operacional.",
    who: "Context Plane.",
    result: "Intent Contract.",
  },
  {
    id: "policy",
    short: "Policy",
    zone: "deterministic",
    modeLabel: "DET",
    happens: "Regras explícitas autorizam, restringem ou pedem mais dado.",
    why: "Nenhuma decisão segue sem política aplicável.",
    who: "Spider — governança.",
    result: "Autorização ou lacuna explícita.",
  },
  {
    id: "plano",
    short: "Plano",
    zone: "deterministic",
    modeLabel: "DET",
    decideLabel: "Spider decide.",
    happens: "O caminho materializado deixa de ser uma escolha livre.",
    why: "A execução precisa de um plano versionado e correlacionável.",
    who: "Spider — Execution Planning.",
    result: "Execution Plan determinístico.",
  },
  {
    id: "capacidades",
    short: "Capacidades",
    zone: "deterministic",
    modeLabel: "DET",
    happens: "O plano pede o que precisa ser feito, não qual sistema chamar.",
    why: "O trabalho empresarial permanece estável quando o sistema muda.",
    who: "Spider — Business Capabilities.",
    result: "Lista de capacidades necessárias.",
  },
  {
    id: "resolucao",
    short: "Resolução",
    zone: "deterministic",
    modeLabel: "DET",
    decideLabel: "Spider decide.",
    happens: "Cada capacidade encontra rota, adapter e sistema vigentes.",
    why: "O binding pode mudar; a capacidade permanece.",
    who: "Spider — Capability Resolution.",
    result: "Rotas e adapters resolvidos.",
  },
  {
    id: "execucao",
    short: "Execução",
    zone: "deterministic",
    modeLabel: "DET",
    happens: "O Data Plane realiza o plano com espera, retomada e rastreio.",
    why: "Operar o caminho sem improvisar no momento.",
    who: "Spider — execução governada.",
    result: "Eventos correlacionados.",
  },
  {
    id: "resultado",
    short: "Resultado",
    zone: "deterministic",
    modeLabel: "DET",
    happens: "O efeito volta ao satélite e permanece explicável.",
    why: "O cliente e o operador precisam ver o desfecho do objetivo.",
    who: "Satélite + Console.",
    result: "Desfecho correlacionado ao objetivo.",
  },
];

export const JOURNEY_CAPABILITIES = [
  {
    id: "identify",
    name: "Identificar cliente",
    what: "Reconhecer quem está na jornada a partir do contexto permitido.",
    why: "Sem identidade, as demais capacidades não têm sujeito.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Adapter de cadastro (exemplo)",
    system: "Cadastro",
  },
  {
    id: "profile",
    name: "Conhecer perfil",
    what: "Compor o que já se sabe do cliente sem inventar dado.",
    why: "O plano precisa de perfil para não oferecer caminho cego.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Adapter de perfil (exemplo)",
    system: "Cadastro / perfil",
  },
  {
    id: "registry",
    name: "Verificar cadastro",
    what: "Confirmar se o cadastro permite seguir.",
    why: "Lacuna de cadastro é bloqueio explícito, não surpresa no fim.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Adapter de cadastro (exemplo)",
    system: "Cadastro",
  },
  {
    id: "commitments",
    name: "Analisar compromissos",
    what: "Ler obrigações visíveis sem decidir crédito.",
    why: "Continuidade produtiva depende do que já vence.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Adapter financeiro (exemplo)",
    system: "Legado financeiro",
  },
  {
    id: "options",
    name: "Encontrar alternativas",
    what: "Levantar caminhos empresariais compatíveis com o Intent.",
    why: "O Spider oferece opções; não escolhe o produto no lugar do cliente.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Capability resolver (exemplo)",
    system: "Catálogo de capacidades",
  },
  {
    id: "simulate",
    name: "Simular",
    what: "Projetar o efeito do caminho ainda sem executar.",
    why: "O cliente precisa ver consequência antes do commit.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Adapter de simulação (exemplo)",
    system: "Motor de simulação",
  },
  {
    id: "present",
    name: "Apresentar opções",
    what: "Devolver as alternativas ao satélite em linguagem de negócio.",
    why: "A decisão final permanece com o cliente.",
    status: "Exemplo de jornada",
    route: "Ilustrativo — não é catálogo operacional",
    executor: "Satélite SpiderBank (exemplo)",
    system: "SpiderBank",
  },
];

export const RESOLUTION_PATH = ["Capability", "Resolver", "Route", "Adapter", "Sistema"];

export const SYSTEM_PORTS = ["API", "SOAP", "MQ", "FILE", "DB", "LEGACY"];

export const INTEGRATION_MODES = [
  {
    id: "modern",
    label: "Moderno",
    systemSide: [
      { id: "system", label: "Aplicação / Satélite", kind: "technology", anchor: "system" },
      { id: "bff", label: "Satellite BFF", kind: "integration" },
      { id: "contract", label: "Satellite Contract", kind: "integration" },
    ],
    spiderSide: [
      { id: "capability", label: "Business Capability", kind: "business", detail: "capability", anchor: "capability" },
      { id: "resolver", label: "Capability Resolver", kind: "integration", detail: "resolver" },
      { id: "route", label: "Route", kind: "integration" },
      { id: "adapter", label: "Contract / Adapter", kind: "integration" },
      { id: "executor", label: "Executor moderno", kind: "technology", anchor: "executor" },
    ],
    insight:
      "Aderência por contrato. Quando o sistema pode evoluir, ele adota diretamente a arquitetura de referência do Spider.",
    insightLead: "Aderência por contrato.",
    insightBody:
      "Quando o sistema pode evoluir, ele adota diretamente a arquitetura de referência do Spider.",
    systemChange: "maior",
    boundaryComplexity: "mínima",
    benefit: "alta",
    meta: [
      { label: "Mudança no sistema", value: "maior" },
      { label: "Camada compensatória", value: "mínima" },
      { label: "Aderência ao modelo ideal", value: "alta" },
    ],
  },
  {
    id: "limited",
    label: "Baixa modificabilidade",
    systemSide: [
      { id: "system", label: "Sistema existente", kind: "technology", anchor: "system" },
      { id: "facade", label: "Integration Facade", kind: "integration" },
      { id: "adapter", label: "Adapter", kind: "integration" },
    ],
    spiderSide: [
      { id: "capability", label: "Business Capability", kind: "business", detail: "capability", anchor: "capability" },
      { id: "resolver", label: "Capability Resolver", kind: "integration", detail: "resolver" },
      { id: "route", label: "Route", kind: "integration" },
      { id: "adapter", label: "Adapter / Facade", kind: "integration" },
      { id: "executor", label: "Sistema limitado", kind: "technology", anchor: "executor" },
    ],
    insight:
      "A fachada absorve a limitação. O sistema muda pouco; protocolo, transformação e compatibilidade permanecem fora da semântica do Spider.",
    insightLead: "A fachada absorve a limitação.",
    insightBody:
      "O sistema muda pouco; protocolo, transformação e compatibilidade permanecem fora da semântica do Spider.",
    systemChange: "baixa",
    boundaryComplexity: "média",
    benefit: "alta",
    meta: [
      { label: "Mudança no sistema", value: "baixa" },
      { label: "Camada compensatória", value: "média" },
      { label: "Preservação do investimento", value: "alta" },
    ],
  },
  {
    id: "legacy",
    label: "Legado",
    systemSide: [
      { id: "system", label: "Legado", kind: "technology", anchor: "system" },
      { id: "protocol", label: "Protocolo existente", kind: "integration" },
      { id: "bridge", label: "Legacy Bridge", kind: "integration" },
      { id: "adapter", label: "Legacy Adapter", kind: "integration" },
    ],
    spiderSide: [
      { id: "capability", label: "Business Capability", kind: "business", detail: "capability", anchor: "capability" },
      { id: "resolver", label: "Capability Resolver", kind: "integration", detail: "resolver" },
      { id: "route", label: "Route", kind: "integration" },
      { id: "adapter", label: "Legacy Adapter / Bridge", kind: "integration" },
      { id: "protocol", label: "Protocolo existente", kind: "integration" },
      { id: "executor", label: "Legado", kind: "technology", anchor: "executor" },
    ],
    insight:
      "O legado não precisa conhecer o Spider. A plataforma se aproxima do protocolo existente sem degradar seu modelo arquitetural.",
    insightLead: "O legado não precisa conhecer o Spider.",
    insightBody:
      "A plataforma se aproxima do protocolo existente sem degradar seu modelo arquitetural.",
    systemChange: "mínima/nula",
    boundaryComplexity: "maior",
    benefit: "reduzido",
    meta: [
      { label: "Mudança no legado", value: "mínima/nula" },
      { label: "Complexidade da fronteira", value: "maior" },
      { label: "Risco de intervenção no legado", value: "reduzido" },
    ],
  },
];

export const INTEGRATION_CRITERIA = [
  { id: "data", label: "Dados", text: "Quais informações precisam atravessar a fronteira?" },
  { id: "purpose", label: "Finalidade", text: "O executor precisa realmente desses dados?" },
  { id: "security", label: "Segurança", text: "Como a fronteira protege identidade e mutação?" },
  { id: "compliance", label: "Compliance", text: "A execução é elegível sob as políticas aplicáveis?" },
  { id: "criticality", label: "Criticidade", text: "Qual o impacto se esse executor falhar?" },
  { id: "cost", label: "Custo", text: "Qual o TCO dessa capability neste executor?" },
];

export const GOVERNANCE_DIMS = [
  {
    id: "policy",
    label: "Policy",
    body: "Toda decisão passa por regras explícitas. Sem política aplicável, o caminho não segue.",
    items: ["Autorizar", "Restringir", "Pedir dado", "Registrar decisão"],
  },
  {
    id: "security",
    label: "Security",
    body: "Identidade, autorização e mutation safety acompanham o plano — não ficam no fim como verniz.",
    items: ["Identidade", "Autorização", "Mutation safety", "Fronteira de canal"],
  },
  {
    id: "resilience",
    label: "Resilience",
    body: "A execução sobrevive ao tempo real sem improvisar o caminho.",
    items: ["Retry", "Timeout", "Wait/Resume", "Capacity", "Backpressure", "Circuit"],
  },
  {
    id: "observability",
    label: "Observability",
    body: "O que aconteceu permanece correlacionável: objetivo, plano, capacidades e execução.",
    items: ["Trace", "Eventos", "Auditoria", "Correlação"],
  },
];

export const EXPLAIN_TRAIL = [
  { id: "objetivo", label: "Objetivo", example: "Manter a produção após quebra de safra — declarado pelo cliente." },
  { id: "entendimento", label: "Entendimento", example: "Necessidade de continuidade financeira, com CROP_FAILURE só quando o contexto e o objetivo sustentam." },
  { id: "policy", label: "Policy", example: "A política contextual permite continuar ou pede o valor que não existia no link." },
  { id: "plano", label: "Plano", example: "Execution Plan versionado; working capital pode ser parcial." },
  { id: "capabilities", label: "Capabilities", example: "Capacidades necessárias vs disponíveis, sem inventar executor." },
  { id: "routes", label: "Routes", example: "Rotas resolvidas a partir da capacidade, não do texto livre." },
  { id: "execucao", label: "Execução", example: "Eventos e espera/retomada no Console, quando houver execução." },
  { id: "resultado", label: "Resultado", example: "Desfecho correlacionado ao objetivo no satélite e na prova técnica." },
];

export const ARCH_STATUS = [
  {
    id: "done",
    label: "Implementado",
    tone: "done",
    items: "Context Intelligence, Intent Contract, Execution Planning, Business Capabilities, Capability Resolution, Contextual Link.",
  },
  {
    id: "prepared",
    label: "Preparado / documentado",
    tone: "prepared",
    items: "Satellite Architecture (contrato de satélite) e atestação verificável de decisões.",
  },
  {
    id: "future",
    label: "Futuro",
    tone: "future",
    items: "Trusted Evidence com ledger distribuído, somente se o modelo de confiança justificar.",
  },
];

export const ARCH_LAYERS = [
  { id: "channels", title: "Fontes e canais", body: "Originam contexto e objetivos — páginas, satélites, interações.", status: "done" },
  { id: "link", title: "Contextual Link", body: "Canal iniciador ultraleve. O parceiro publica somente /go.", status: "done" },
  { id: "intel", title: "Context Intelligence", body: "Interpreta linguagem e contexto. Não escolhe rota.", status: "done" },
  { id: "intent", title: "Intent Contract", body: "Fronteira entre compreensão e execução governada.", status: "done" },
  { id: "plan", title: "Execution Plan", body: "Caminho determinístico, versionado e correlacionável.", status: "done" },
  { id: "caps", title: "Business Capabilities", body: "O que precisa ser feito, independente do sistema.", status: "done" },
  { id: "resolve", title: "Capability Resolution", body: "Capability → rota → adapter → sistema.", status: "done" },
  { id: "sat", title: "Satellites", body: "SpiderBank é satélite de referência. Contrato completo: preparado.", status: "prepared" },
  { id: "evidence", title: "Trusted Evidence", body: "Atestação criptográfica. Não implementado.", status: "future" },
];

export const EXPERIENCE_WALK = [
  { id: "origin", label: "Origem", body: "Reportagem CampoAberto — página externa, independente do banco." },
  { id: "link", label: "Link", body: "Somente GET /go. Sem intent, campanha ou contexto no endereço." },
  { id: "context", label: "Contexto", body: "ClickContext e PageContext existem depois do clique." },
  { id: "objective", label: "Objetivo", body: "O cliente declara o que precisa. O contexto não escolhe por ele." },
  { id: "plan", label: "Plano", body: "A partir do Intent, o Spider decide o caminho governado." },
];

export const INFOGRAPHIC_SRC = "/spider-contextual-platform-overview.png";
export const INFOGRAPHIC_ALT =
  "Visão da Plataforma Contextual Spider: contexto, inteligência, governança, capacidades, integração, sistemas e resultados.";

export const CAMPOABERTO_PREVIEW = "/experience/campoaberto-preview.png";
export const SPIDERBANK_PREVIEW = "/experience/spiderbank-preview.png";
