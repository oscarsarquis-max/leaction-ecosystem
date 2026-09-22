/** Definição canônica das 8 etapas do Fluxo produtivo (CURSOR-028-B). */

export type FlowStepId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export type FlowSituation =
  | "Não iniciado"
  | "Em andamento"
  | "Requer atenção"
  | "Pronto"
  | "Não se aplica"
  | "Sem acesso";

export type FlowLink = {
  to: string;
  label: string;
  /** Permissão mínima para exibir o link. */
  permission?: string;
  /** Alternativas (ex.: fiscal + compras legado). Basta uma. */
  permissionAnyOf?: string[];
};

export type FlowStepDef = {
  id: FlowStepId;
  title: string;
  objective: string;
  /** Permissões: basta uma para “acesso”. Custos usam regra especial. */
  accessAnyOf: string[];
  /** Se true, etapa some por completo sem permissão (não aparece nem desabilitada). */
  hideWithoutAccess: boolean;
  /** Ressalva de escopo da etapa, quando parte da capacidade ainda está por vir. */
  structureNote?: string;
  primary?: FlowLink;
  secondary: FlowLink[];
  /** Prefixos de rota que ativam esta etapa na trilha. */
  pathMatchers: (path: string) => boolean;
};

export const FLOW_STEPS: FlowStepDef[] = [
  {
    id: 1,
    title: "Compras e entradas",
    objective:
      "Abastecer a operação: registrar a mercadoria que chega por documento fiscal, conferir e só então atualizar o estoque.",
    accessAnyOf: ["fiscal.document.read", "procurement.read", "procurement.receive", "supplier.read"],
    hideWithoutAccess: false,
    primary: { to: "/gestao/compras/entradas", label: "Registrar entrada" },
    secondary: [
      {
        to: "/gestao/compras/entradas/nova?origem=xml",
        label: "Importar XML",
        permissionAnyOf: ["fiscal.document.capture", "procurement.receive", "procurement.order.manage"],
      },
      {
        to: "/gestao/compras/entradas?situacao=aguardando-correspondencia",
        label: "Itens sem correspondência",
        permissionAnyOf: ["fiscal.document.match", "procurement.receive"],
      },
      {
        to: "/gestao/compras/entradas?situacao=aguardando-conferencia",
        label: "Documentos aguardando conferência",
        permissionAnyOf: ["fiscal.document.check", "procurement.receive"],
      },
      {
        to: "/gestao/compras/entradas?situacao=parcial",
        label: "Recebimentos parciais",
        permission: "procurement.receive",
      },
      {
        to: "/gestao/compras/entradas?situacao=divergencia",
        label: "Divergências",
        permissionAnyOf: ["fiscal.document.read", "procurement.read"],
      },
      {
        to: "/gestao/compras/entradas?situacao=historico",
        label: "Histórico",
        permissionAnyOf: ["fiscal.document.read", "procurement.read"],
      },
    ],
    pathMatchers: (path) =>
      path.startsWith("/gestao/compras/entradas")
      || path.startsWith("/gestao/compras")
      || path.startsWith("/componentes/fornecedores"),
  },
  {
    id: 2,
    title: "Ingredientes e estoque",
    objective: "Manter o cadastro de ingredientes e acompanhar lotes, posição e movimentações.",
    accessAnyOf: ["ingredient.read", "inventory.read"],
    hideWithoutAccess: false,
    primary: { to: "/componentes/ingredientes", label: "Abrir ingredientes", permission: "ingredient.read" },
    secondary: [
      { to: "/componentes/estoque", label: "Estoque", permission: "inventory.read" },
      { to: "/componentes/lotes", label: "Lotes e validade", permission: "inventory.read" },
      { to: "/componentes/estoque/posicao", label: "Posição", permission: "inventory.read" },
    ],
    pathMatchers: (path) =>
      path.startsWith("/componentes/ingredientes")
      || path.startsWith("/componentes/estoque")
      || path.startsWith("/componentes/lotes")
      || path.startsWith("/componentes/catalogos"),
  },
  {
    id: 3,
    title: "Produtos",
    objective: "Cadastrar a identidade comercial e operacional do que se vende, estoca ou produz.",
    accessAnyOf: ["product.read"],
    hideWithoutAccess: false,
    primary: { to: "/produtos", label: "Abrir produtos", permission: "product.read" },
    secondary: [
      { to: "/produtos/novo", label: "Novo produto", permission: "product.create" },
      { to: "/produtos/familias", label: "Famílias", permission: "product.read" },
    ],
    pathMatchers: (path) => path.startsWith("/produtos"),
  },
  {
    id: 4,
    title: "Receitas",
    objective: "Definir e versionar como a produção transforma ingredientes e preparos.",
    accessAnyOf: ["recipe.read"],
    hideWithoutAccess: false,
    primary: { to: "/receitas", label: "Abrir receitas", permission: "recipe.read" },
    secondary: [
      { to: "/receitas/assistente", label: "Assistente de receitas", permission: "recipe.read" },
    ],
    pathMatchers: (path) => path.startsWith("/receitas"),
  },
  {
    id: 5,
    title: "Planejamento e ordens",
    objective: "Organizar a demanda do turno, planos e ordens de produção.",
    accessAnyOf: ["production.board.read", "production.plan.read", "production.order.read"],
    hideWithoutAccess: false,
    primary: { to: "/ordens", label: "Abrir ordens", permission: "production.order.read" },
    secondary: [
      { to: "/planejamento", label: "Planejamento", permission: "production.plan.read" },
      { to: "/producao", label: "Quadro de produção", permission: "production.board.read" },
    ],
    pathMatchers: (path) =>
      path === "/producao"
      || path.startsWith("/planejamento")
      || (path.startsWith("/ordens") && !path.includes("/fichas"))
      || path.startsWith("/rastreabilidade"),
  },
  {
    id: 6,
    title: "Preparo e execução",
    objective: "Executar no chão de fábrica: pesar, consumir, conferir e concluir a ordem.",
    accessAnyOf: ["production.order.read", "production.board.read"],
    hideWithoutAccess: false,
    primary: { to: "/ordens", label: "Escolher ordem para executar", permission: "production.order.read" },
    secondary: [
      { to: "/producao", label: "Quadro do turno", permission: "production.board.read" },
    ],
    pathMatchers: (path) => path.includes("/executar") || /\/ordens\/[^/]+\/fichas\//.test(path),
  },
  {
    id: 7,
    title: "Produto acabado e rotulagem",
    objective: "Conferir conformidade e rotulagem do que foi produzido.",
    accessAnyOf: ["labeling.read"],
    hideWithoutAccess: false,
    structureNote:
      "A rotulagem já existe. O estoque de produto acabado ainda não tem depósito próprio (previsto em 028-C/G).",
    primary: { to: "/conformidade", label: "Abrir conformidade", permission: "labeling.read" },
    secondary: [
      { to: "/conformidade/dossies", label: "Dossiês", permission: "labeling.read" },
      { to: "/conformidade/rotulos", label: "Rótulos candidatos", permission: "labeling.read" },
    ],
    pathMatchers: (path) => path.startsWith("/conformidade"),
  },
  {
    id: 8,
    title: "Custos e preços",
    objective: "Acompanhar custeio, formação de preço e indicadores gerenciais.",
    accessAnyOf: ["costing.read", "pricing.review", "pricing.simulation.manage"],
    hideWithoutAccess: true,
    primary: { to: "/gestao/custos", label: "Abrir custos e preços", permission: "costing.read" },
    secondary: [
      { to: "/gestao/custos/precos", label: "Preços e histórico", permission: "pricing.review" },
      { to: "/gestao/custos/calculadora", label: "Calculadora", permission: "pricing.simulation.manage" },
    ],
    pathMatchers: (path) => path.startsWith("/gestao/custos"),
  },
];

export function stepById(id: FlowStepId): FlowStepDef {
  const found = FLOW_STEPS.find((step) => step.id === id);
  if (!found) throw new Error(`Etapa inválida: ${id}`);
  return found;
}

export function matchFlowStep(pathname: string): FlowStepId | null {
  // Execução antes de ordens genéricas / quadro.
  for (const step of [...FLOW_STEPS].sort((a, b) => {
    if (a.id === 6) return -1;
    if (b.id === 6) return 1;
    return 0;
  })) {
    if (step.pathMatchers(pathname)) return step.id;
  }
  return null;
}

export function withFlowReturn(to: string, step: FlowStepId): string {
  const url = new URL(to, "http://panne.local");
  url.searchParams.set("from", "fluxo");
  url.searchParams.set("step", String(step));
  return `${url.pathname}${url.search}`;
}

export function flowHref(step: FlowStepId): string {
  return `/fluxo?etapa=${step}`;
}
