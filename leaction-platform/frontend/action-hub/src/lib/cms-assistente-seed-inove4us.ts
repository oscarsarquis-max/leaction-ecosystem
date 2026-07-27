/**
 * Seed canônico da árvore Nina (inove4us).
 * Espelha scripts/seed-cms-assistente-chat-inove4us.js — não hardcodar números freemium.
 */
export type AssistenteTreeOption = {
  label: string;
  next?: string;
  href?: string;
  action?: string;
};

export type AssistenteTreeNode = {
  message: string;
  options: AssistenteTreeOption[];
};

export type AssistenteTree = {
  avatar_name: string;
  avatar_tagline: string;
  avatar_candidates?: string[];
  root_id: string;
  nodes: Record<string, AssistenteTreeNode>;
};

export const ASSISTENTE_SEED_INOVE4US: AssistenteTree = {
  avatar_name: 'Nina',
  avatar_tagline: 'Guia do inovador',
  avatar_candidates: ['Nina'],
  root_id: 'inicio',
  nodes: {
    inicio: {
      message:
        'Olá! Sou a Nina, sua guia no inove4us. ' +
        'Escolha um tema abaixo — ou deixe uma sugestão no campo acima.',
      options: [
        { label: 'Aulas do Dia a Dia (rápido)', next: 'dia_a_dia' },
        { label: 'Desafios e Projetos', next: 'desafios' },
        { label: 'Como usar o Kanban', next: 'kanban' },
        { label: 'Planos, pagamentos e conta', next: 'planos' },
      ],
    },
    dia_a_dia: {
      message:
        'O Dia a Dia é o ciclo rápido (~50 min) para planejar e executar ' +
        'uma aula. Você preenche as 4 estações e move o trabalho no Kanban ' +
        '(Para Fazer → Fazendo → Pronto).',
      options: [
        { label: 'O que são as 4 estações?', next: 'dia_estacoes' },
        { label: 'Como escolher a atividade em campo?', next: 'dia_dinamica' },
        { label: 'Abrir o Dia a Dia', next: 'dia_a_dia', href: '/dia-a-dia' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    dia_estacoes: {
      message:
        'As 4 estações do ciclo são:\n' +
        '1 · Alinhamento (abertura)\n' +
        '2 · Entrega do dia\n' +
        '3 · Atividade em campo (dinâmica ativa)\n' +
        '4 · Retro do ciclo (fechamento)\n\n' +
        'Isso aparece exatamente assim na tela de planejar aula.',
      options: [
        { label: 'Como escolher a atividade em campo?', next: 'dia_dinamica' },
        {
          label: 'Ir para nova aula',
          next: 'dia_estacoes',
          href: '/dia-a-dia/nova',
        },
        { label: 'Voltar ao Dia a Dia', next: 'dia_a_dia' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    dia_dinamica: {
      message:
        'Na estação 3 · Atividade em campo você pode escolher uma dinâmica ' +
        'sugerida do catálogo ou descrever a sua. A sugestão é um atalho — ' +
        'não substitui o seu julgamento pedagógico.',
      options: [
        {
          label: 'Abrir nova aula',
          next: 'dia_dinamica',
          href: '/dia-a-dia/nova',
        },
        { label: 'Voltar ao Dia a Dia', next: 'dia_a_dia' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    desafios: {
      message:
        'Em Desafios você descreve a dor real da turma; a inove4us estrutura ' +
        'causas e caminhos metodológicos e gera um plano EduScrum com Kanban. ' +
        'Cada geração bem-sucedida consome 1 crédito de desafio.',
      options: [
        { label: 'Como escrever um bom desafio?', next: 'desafio_escrever' },
        { label: 'A geração consome crédito?', next: 'desafio_credito' },
        { label: 'Abrir Desafio', next: 'desafios', href: '/desafio' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    desafio_escrever: {
      message:
        'Seja específico: turma, tema e a dor real (o que trava a aprendizagem). ' +
        'Cite nomes concretos (projeto, prazo, hipóteses dos alunos). ' +
        'Evite só dizer “a turma está dispersa” — quanto mais contexto, ' +
        'melhor a hipótese e o plano.',
      options: [
        { label: 'Ir para Desafio', next: 'desafio_escrever', href: '/desafio' },
        { label: 'Voltar a Desafios', next: 'desafios' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    desafio_credito: {
      message:
        'Sim. Cada estruturação com IA consome 1 crédito de desafio. ' +
        'No plano gratuito você começa com {{FREEMIUM_DESAFIOS}} desafio (crédito de IA). ' +
        'Aulas do Dia a Dia usam outro limite (aulas/mês), não esse crédito.',
      options: [
        { label: 'Ver planos e créditos', next: 'planos' },
        { label: 'Voltar a Desafios', next: 'desafios' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    kanban: {
      message:
        'O Kanban acompanha a execução da aula ou do plano EduScrum. ' +
        'As colunas são: Para Fazer → Fazendo → Pronto. ' +
        'Ao mover um card, você registra uma observação curta do que mudou.',
      options: [
        { label: 'Como mover os cards?', next: 'kanban_mover' },
        { label: 'Onde vejo o Kanban?', next: 'kanban_onde' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    kanban_mover: {
      message:
        'Clique no card e escolha a coluna de destino (Para Fazer, Fazendo ou Pronto). ' +
        'É pedido um registro breve do que foi feito — isso alimenta o histórico ' +
        'da aula. Não usamos o termo “Sprint” aqui: o ciclo é a própria aula ' +
        'ou a continuidade/reinício no EduScrum.',
      options: [
        {
          label: 'Abrir Mesa (agenda e mapa)',
          next: 'kanban_mover',
          href: '/mesa-do-inovador',
        },
        { label: 'Voltar ao Kanban', next: 'kanban' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    kanban_onde: {
      message:
        'No Dia a Dia, o Kanban fica ao lado do planejamento do ciclo. ' +
        'Nos Desafios, depois de gerar o plano EduScrum, o quadro aparece ' +
        'na etapa de execução da aula registrada na agenda.',
      options: [
        { label: 'Ir ao Dia a Dia', next: 'kanban_onde', href: '/dia-a-dia' },
        { label: 'Ir a Desafios', next: 'kanban_onde', href: '/desafio' },
        { label: 'Voltar ao Kanban', next: 'kanban' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos: {
      message:
        'No plano gratuito: até {{FREEMIUM_AULAS}} aulas do Dia a Dia por mês e ' +
        '{{FREEMIUM_DESAFIOS}} desafio ativo (crédito de IA). ' +
        'Para mais liberdade, veja Profissional, Mentor ou pacotes avulsos.',
      options: [
        { label: 'Limites do plano grátis', next: 'planos_limites' },
        { label: 'Como assinar / comprar créditos?', next: 'planos_assinar' },
        { label: 'Renovação e cancelamento', next: 'planos_cancelar' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos_limites: {
      message:
        'Gratuito: {{FREEMIUM_AULAS}} aulas do Dia a Dia / mês e ' +
        '{{FREEMIUM_DESAFIOS}} crédito de desafio. ' +
        'Quando o crédito acaba, a estruturação com IA fica bloqueada até ' +
        'você escolher um plano ou pacote.',
      options: [
        { label: 'Como assinar?', next: 'planos_assinar' },
        { label: 'Voltar a Planos', next: 'planos' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos_assinar: {
      message:
        'Use o botão Ver planos (no topo ou quando os créditos acabam). ' +
        'Você escolhe o plano no Action Hub e paga com Mercado Pago ' +
        '(cartão e demais meios disponíveis no checkout). ' +
        'Profissional R$ 24,90 · Mentor R$ 49,90 · pacote avulso de 3 desafios.',
      options: [
        {
          label: 'Abrir planos (upgrade)',
          next: 'planos_assinar',
          action: 'open_upgrade',
        },
        { label: 'Voltar a Planos', next: 'planos' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos_cancelar: {
      message:
        'Assinaturas e cobranças ficam no Action Hub / Mercado Pago. ' +
        'Para alterar ou cancelar, use o fluxo de planos/conta do Hub ' +
        'ou o suporte indicado na página de pagamento. ' +
        'Pacotes avulsos de créditos não renovam automaticamente.',
      options: [
        { label: 'Voltar a Planos', next: 'planos' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
  },
};

export function cloneAssistenteSeedInove4us(): AssistenteTree {
  return JSON.parse(JSON.stringify(ASSISTENTE_SEED_INOVE4US)) as AssistenteTree;
}
