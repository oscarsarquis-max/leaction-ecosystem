window.UX001 = {
  papeis: {
    gestor: { nome: "Proprietário / gestor", gestao: true, escrever: true, operar: false },
    tecnico: { nome: "Responsável técnico", gestao: false, escrever: true, operar: false },
    formulador: { nome: "Formulador", gestao: false, escrever: true, operar: false },
    revisor: { nome: "Revisor regulatório", gestao: false, escrever: false, operar: false },
    padeiro: { nome: "Padeiro / operador", gestao: false, escrever: false, operar: true },
    leitor: { nome: "Somente leitura", gestao: false, escrever: false, operar: false },
  },
  menus: {
    producao: ["Quadro", "Planejamento", "Ordens", "Rastreabilidade"],
    receitas: ["Minhas receitas", "Biblioteca e referências", "Fichas técnicas", "Testes e aprovações", "Propostas assistidas"],
    componentes: ["Ingredientes", "Preparações e bases", "Fornecedores e itens", "Unidades e conversões", "Nutrientes", "Alergênicos", "Fontes técnicas"],
    conformidade: ["Biblioteca normativa", "Avaliações", "Pendências e evidências"],
    gestao: ["Organização", "Estabelecimentos", "Pessoas e acessos", "Papéis e permissões"],
  },
  ordens: [
    { codigo: "OP-2026-0001", produto: "Pão tradicional", estado: "Em execução", acao: "Conferir pesagem", bloqueio: true },
    { codigo: "OP-2026-0002", produto: "Ciabatta", estado: "Liberada", acao: "Abrir pesagem", bloqueio: false },
    { codigo: "OP-2026-0003", produto: "Baguete", estado: "Agendada", acao: "Aguardando turno", bloqueio: false },
  ],
  ingredientes: [
    { nome: "Farinha de trigo tipo 1", estado: "completo", pendencia: "nenhuma", versao: "v4 aprovada" },
    { nome: "Fermento fresco", estado: "nutricao", pendencia: "dados nutricionais pendentes", versao: "v2 rascunho" },
    { nome: "Açúcar mascavo", estado: "fonte", pendencia: "fonte técnica pendente", versao: "v1 em revisão" },
  ],
  badgesProibidos: [
    "ranking individual de padeiros",
    "prêmio só por velocidade",
    "incentivo a omitir ocorrência",
    "badge de conformidade sem avaliação",
  ],
};
