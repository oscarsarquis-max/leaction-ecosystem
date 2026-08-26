export type Intent = {
  code: string;
  label: string;
  to: string;
  permission: string;
  precondition: string;
};

export const INTENTS: Intent[] = [
  { code: "ingrediente.criar", label: "Cadastrar ingrediente", to: "/componentes/ingredientes/novo", permission: "ingredient.create", precondition: "Permissão de criação." },
  { code: "receita.criar", label: "Criar receita", to: "/receitas/novo", permission: "recipe.create", precondition: "Permissão de criação." },
  { code: "receita.adaptar", label: "Adaptar receita", to: "/receitas/assistente/adaptar", permission: "recipe.ai.propose", precondition: "Proposta assistiva, revisão humana." },
  { code: "plano.abrir", label: "Planejar produção", to: "/planejamento", permission: "production.plan.read", precondition: "Organização ativa." },
  { code: "ordem.executar", label: "Executar ordem", to: "/producao", permission: "production.board.read", precondition: "Ordem liberada no quadro." },
  { code: "lote.consultar", label: "Consultar lote", to: "/componentes/lotes", permission: "inventory.read", precondition: "Leitura de estoque." },
  { code: "recebimento.registrar", label: "Registrar recebimento", to: "/gestao/compras/recebimentos", permission: "procurement.receive", precondition: "Pedido emitido." },
  { code: "custo.calcular", label: "Calcular custo", to: "/gestao/custos", permission: "costing.read", precondition: "Política de custeio." },
  { code: "preco.simular", label: "Simular preço", to: "/gestao/custos/simulacoes", permission: "pricing.simulation.manage", precondition: "Cálculo existente." },
  { code: "rotulo.revisar", label: "Revisar rótulo", to: "/conformidade/rotulos", permission: "labeling.read", precondition: "Dossiê ou candidato." },
  { code: "relatorio.abrir", label: "Abrir relatório", to: "/gestao/relatorios", permission: "reporting.dashboard.read", precondition: "Permissão do relatório." },
];
