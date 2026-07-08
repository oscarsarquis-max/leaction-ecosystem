const DIMENSOES_PADRAO = {
  Satisfação: 0.25,
  Performance: 0.25,
  Atividade: 0.2,
  Comunicação: 0.2,
  Eficiência: 0.1,
};

export const CONFIG_PESOS_IAPS = {
  pesos_niveis: {
    Individual: 0.4,
    Equipe: 0.6,
  },
  pesos_dimensoes: {
    Técnica: { ...DIMENSOES_PADRAO },
    "Gestão Técnica": { ...DIMENSOES_PADRAO },
    "Gerência Técnica": { ...DIMENSOES_PADRAO },
    "Gestão Geral": { ...DIMENSOES_PADRAO },
  },
  pesos_dimensoes_subpapel: {},
  pesos_niveis_subpapel: {},
};

export const MAPA_GRUPO_PARA_PAPEL = {
  Técnica: "Técnica",
  "Gerência Técnica": "Gestão Técnica",
  "Gestão Geral": "Gestão Geral",
};

export function normalizarPapel(papel) {
  if (!papel) {
    return null;
  }

  const valor = String(papel).trim();
  if (CONFIG_PESOS_IAPS.pesos_dimensoes[valor]) {
    return valor;
  }

  return MAPA_GRUPO_PARA_PAPEL[valor] || valor;
}

export function mapNomeGrupoParaPapel(nomeGrupo) {
  if (!nomeGrupo) {
    return null;
  }

  return normalizarPapel(MAPA_GRUPO_PARA_PAPEL[nomeGrupo] || nomeGrupo);
}

export function resolverPesosNiveis(papel, subpapel) {
  if (subpapel && CONFIG_PESOS_IAPS.pesos_niveis_subpapel[subpapel]) {
    return CONFIG_PESOS_IAPS.pesos_niveis_subpapel[subpapel];
  }

  return CONFIG_PESOS_IAPS.pesos_niveis;
}

export function resolverPesosDimensoes(papel, subpapel) {
  const papelNormalizado = normalizarPapel(papel);

  if (subpapel && CONFIG_PESOS_IAPS.pesos_dimensoes_subpapel[subpapel]) {
    return CONFIG_PESOS_IAPS.pesos_dimensoes_subpapel[subpapel];
  }

  if (papelNormalizado && CONFIG_PESOS_IAPS.pesos_dimensoes[papelNormalizado]) {
    return CONFIG_PESOS_IAPS.pesos_dimensoes[papelNormalizado];
  }

  return DIMENSOES_PADRAO;
}

export function indicadorAplicaAoSubpapel(subpapeisAplicaveis, subpapel) {
  if (!Array.isArray(subpapeisAplicaveis) || subpapeisAplicaveis.length === 0) {
    return true;
  }

  if (!subpapel) {
    return true;
  }

  return subpapeisAplicaveis.includes(subpapel);
}
