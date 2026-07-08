/**
 * Textos dos grupos da Biblioteca de Metodologias Inov-ativas (Andrea Filatro).
 * Usados na prévia em /resultado — sem revelar metodologia específica antes do roteiro.
 */
export const GRUPOS_METODOLOGIA = {
  'Metodologias (Cri)ativas': {
    titulo: 'Metodologias (Cri)ativas',
    descricao:
      'Priorizam a expressão, a experimentação e a produção autoral dos estudantes. ' +
      'Incentivam criação, prototipagem e narrativas que transformam ideias em aprendizagem significativa.',
  },
  'Metodologias Ágeis': {
    titulo: 'Metodologias Ágeis',
    descricao:
      'Organizam o trabalho em ciclos curtos, com colaboração, feedback frequente e adaptação. ' +
      'São úteis quando é preciso envolver a turma de forma dinâmica e ajustar o percurso em tempo real.',
  },
  'Metodologias Imersivas': {
    titulo: 'Metodologias Imersivas',
    descricao:
      'Colocam os estudantes em situações vividas, simuladas ou experienciais. ' +
      'Ampliam engajamento ao aproximar o conteúdo de contextos reais, jogos, dramatizações ou ambientes digitais.',
  },
  'Metodologias Analíticas': {
    titulo: 'Metodologias Analíticas',
    descricao:
      'Estruturam a investigação, a argumentação e a resolução de problemas. ' +
      'Fortalecem o pensamento crítico ao guiar análises, hipóteses, evidências e tomada de decisão.',
  },
}

/** Normaliza nomes de grupo vindos do banco para as chaves acima. */
export function resolverGrupoPreview(nomeGrupo) {
  if (!nomeGrupo) return null
  const norm = nomeGrupo
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()

  if (norm.includes('cri') && norm.includes('ativa')) return GRUPOS_METODOLOGIA['Metodologias (Cri)ativas']
  if (norm.includes('agil')) return GRUPOS_METODOLOGIA['Metodologias Ágeis']
  if (norm.includes('imers')) return GRUPOS_METODOLOGIA['Metodologias Imersivas']
  if (norm.includes('analit')) return GRUPOS_METODOLOGIA['Metodologias Analíticas']
  return null
}
