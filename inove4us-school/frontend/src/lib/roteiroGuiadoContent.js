/** Texto do Roteiro Guiado — espelha roteiro-guiado-inove4us.pdf (build_roteiro.py). */

export const TIPOS_ROTEIRO = [
  { id: 'homologacao', label: 'Homologação' },
  { id: 'treinamento', label: 'Treinamento' },
]

export const PASSOS_NUMERADOS = [
  'A.1',
  'A.2',
  'A.3',
  'A.4',
  'A.5',
  'A.6',
  'B.7',
  'B.8',
  'B.9',
  'C.10',
  'C.11',
]

export const OPCOES_CHECKPOINT = ['Sim', 'Mais ou menos', 'Não']
export const OPCOES_IMPACTO = ['Impede', 'Incomoda', 'Só estética']

export const BLOCOS = [
  {
    id: 'A',
    titulo: 'A · Escola — a Torre de Controle',
    cor: '#1f6f4a',
    intro:
      'Você no papel de coordenação pedagógica. É aqui que a escola organiza tudo antes da aula acontecer.',
    passos: [
      {
        id: 'A.1',
        titulo: '1. Entrar',
        itens: [
          'Acesse o link da Escola e faça login com os dados que você recebeu.',
          'Veja o menu disponível — os itens que aparecem dependem do seu perfil de acesso.',
        ],
      },
      {
        id: 'A.2',
        titulo: '2. Secretaria Acadêmica',
        itens: [
          'Abra **Secretaria Acadêmica** no menu.',
          'Veja a Unidade já cadastrada (endereço, dados básicos da escola).',
          'Veja o período letivo em andamento.',
          'Clique em um curso e veja as turmas e disciplinas dele aparecerem.',
          'Veja os alunos cadastrados em uma turma.',
          '*(Opcional)* Baixe o modelo de planilha e importe uma lista de alunos em uma turma.',
          'Dê uma olhada na aba **Situação por período** — ela mostra uma fotografia de agora, não um histórico completo.',
        ],
      },
      {
        id: 'A.3',
        titulo: '3. Minha Equipe',
        itens: [
          'Abra **Minha Equipe**.',
          'Convide um(a) professor(a) usando um e-mail (pode ser um segundo e-mail seu, só para testar).',
          'Copie o **link de convite** que aparece na tela — o convite ainda não manda e-mail automático neste momento, o link já sai pronto pra você compartilhar.',
          'Guarde esse link — você vai usar no Bloco B.',
        ],
      },
      {
        id: 'A.4',
        titulo: '4. Alocar o professor',
        itens: [
          'Ainda na Secretaria, aloque o(a) professor(a) convidado(a) em uma turma e disciplina.',
          '*(Opcional)* Publique um aviso simples para essa turma.',
        ],
      },
      {
        id: 'A.5',
        titulo: '5. Editor Pedagógico',
        itens: [
          'Abra o **Editor Pedagógico**.',
          'Veja o catálogo de metodologias — deve haver várias, cada uma com passos/conteúdo.',
          'Dê uma olhada na parte de inclusão (PEI) — não precisa preencher tudo agora, só conhecer.',
          'Guarde a ideia: aqui é onde a escola define *como* o professor deve ensinar.',
        ],
      },
      {
        id: 'A.6',
        titulo: '6. Radar Pedagógico',
        itens: [
          'Abra a tela inicial (**Radar Pedagógico**) — pode estar vazia agora, isso é normal (ainda não houve aula).',
          'Explore como funcionam o gráfico, as listas e a agenda.',
        ],
      },
    ],
    checkpoint: {
      id: 'A.checkpoint',
      pergunta: 'Ficou claro o que a escola organiza antes da aula existir?',
    },
  },
  {
    id: 'B',
    titulo: 'B · Professor — a Mesa de Trabalho',
    cor: '#8a5a2b',
    intro: 'Agora troque de chapéu: você no papel do(a) professor(a) convidado(a).',
    passos: [
      {
        id: 'B.7',
        titulo: '7. Aceitar o convite',
        itens: [
          'Abra o link de convite que você copiou no passo 3.',
          'Faça login ou crie uma conta com esse e-mail.',
          'Confirme o vínculo com a escola, se for pedido.',
          'Você deve cair na **Mesa do Inovador**.',
        ],
      },
      {
        id: 'B.8',
        titulo: '8. Preparar a aula',
        itens: [
          'Veja se aparece um cartão da turma/aula que foi alocada pra você.',
          'Abra o roteiro da aula — ele já vem pronto, em formato de texto.',
          'Se houver algum aviso fixado no cartão, note.',
          '*(Opcional)* Se um PEI foi ativado no Bloco A, confira se o nome do aluno aparece certo no cartão. Se não aparecer na hora, pode ser só demora de sincronização, não necessariamente um erro — anote e continue.',
        ],
      },
      {
        id: 'B.9',
        titulo: '9. Dar a aula',
        itens: [
          'Entre na execução da aula/desafio.',
          'Mova os cartões pelo quadro — isso já gera o registro da aula automaticamente.',
          'Feche a aula preenchendo o Diário de Bordo.',
          '*(Opcional)* Envie uma sugestão de melhoria no fechamento.',
        ],
      },
    ],
    checkpoint: {
      id: 'B.checkpoint',
      pergunta: 'Isso tira burocracia do seu dia, ou ainda parece um formulário a mais?',
    },
  },
  {
    id: 'C',
    titulo: 'C · De volta à Escola — a Ponte',
    cor: '#4a3a7a',
    intro:
      'Volte para o link da Escola (pode ser a mesma aba ou outra) e veja o que chegou do outro lado.',
    passos: [
      {
        id: 'C.10',
        titulo: '10. Radar, de novo',
        itens: [
          'Veja se a aula que você deu no Bloco B aparece aqui, refletida.',
          'Abra o mesmo cartão que apareceu para o(a) professor(a).',
          'Se você enviou uma sugestão no passo 9, veja se ela aparece para revisão.',
          'Se você publicou um aviso no passo 4, confirme que ele chegou para a turma certa.',
        ],
      },
      {
        id: 'C.11',
        titulo: '11. Minha Equipe — acompanhamento',
        itens: [
          'Abra o(a) professor(a) em **Minha Equipe**.',
          'Veja a linha do tempo: convite → aceite → aula dada.',
        ],
      },
    ],
    checkpoint: {
      id: 'C.checkpoint',
      pergunta:
        'A escola consegue ver o que aconteceu na sala sem precisar perguntar pro professor?',
    },
  },
]

export const BLOCO_D = {
  id: 'D',
  titulo: 'D · Se sobrar tempo (opcional)',
  cor: '#5b5551',
  itens: [
    'Importar uma lista de alunos por planilha, se não fez no Bloco A.',
    'Adicionar uma segunda metodologia no Editor Pedagógico.',
  ],
}

export const FEEDBACK = {
  intro:
    'Para cada parte que você testou (Secretaria · Equipe · Editor Pedagógico · Mesa do Professor · Radar), responda:',
  perguntas: [
    {
      id: 'feedback.entendi',
      pergunta: 'Entendi para que serve?',
      tipo: 'radio',
      opcoes: OPCOES_CHECKPOINT,
    },
    {
      id: 'feedback.travou',
      pergunta: 'Travei em algum clique? Qual?',
      tipo: 'texto',
    },
    {
      id: 'feedback.termo_estranho',
      pergunta: 'Alguma palavra ou termo estranho? Qual?',
      tipo: 'texto',
    },
    {
      id: 'feedback.falta_para_usar',
      pergunta: 'O que falta para eu usar isso na minha escola amanhã?',
      tipo: 'texto',
    },
    {
      id: 'feedback.impacto',
      pergunta: 'Isso te impediria de usar o sistema, incomoda um pouco, ou é só estética?',
      tipo: 'radio',
      opcoes: OPCOES_IMPACTO,
    },
  ],
  notas: {
    id: 'feedback.notas_livres',
    titulo: 'Anotações livres (o que travou, o que gostou, o que faltou)',
  },
}
