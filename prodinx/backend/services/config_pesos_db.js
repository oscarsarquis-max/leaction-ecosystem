const { DIMENSOES_PADRAO, normalizarPapel } = require("../config_pesos");

const ALIAS_SUBPAPEL = {
  SM: "Scrum Master",
};

const PESOS_PADRAO_DIMENSOES = { ...DIMENSOES_PADRAO };

const PESOS_PADRAO_NIVEIS = {
  Individual: 0.4,
  Equipe: 0.6,
};

function normalizarSubpapel(subpapel) {
  if (!subpapel) {
    return null;
  }

  const valor = String(subpapel).trim();
  return ALIAS_SUBPAPEL[valor] || valor;
}

function mapRowToPesosConfig(row) {
  if (!row) {
    return null;
  }

  return {
    id: row.id,
    papel: row.papel,
    subpapel: row.subpapel,
    pesos_niveis: {
      Individual: Number(row.peso_ind),
      Equipe: Number(row.peso_eq),
    },
    pesos_dimensoes: {
      Satisfação: Number(row.peso_satisfacao),
      Performance: Number(row.peso_performance),
      Atividade: Number(row.peso_atividade),
      Comunicação: Number(row.peso_comunicacao),
      Eficiência: Number(row.peso_eficiencia),
    },
  };
}

function criarPesosConfigPadrao(papel, subpapel) {
  return {
    id: null,
    papel: normalizarPapel(papel) || "Técnica",
    subpapel: normalizarSubpapel(subpapel),
    pesos_niveis: { ...PESOS_PADRAO_NIVEIS },
    pesos_dimensoes: { ...PESOS_PADRAO_DIMENSOES },
  };
}

async function buscarConfiguracaoPesos(pool, papel, subpapel) {
  const papelNormalizado = normalizarPapel(papel) || "Técnica";
  const subpapelNormalizado = normalizarSubpapel(subpapel);

  if (subpapelNormalizado) {
    const { rows } = await pool.query(
      `SELECT id, papel, subpapel,
              peso_ind, peso_eq,
              peso_satisfacao, peso_performance, peso_atividade,
              peso_comunicacao, peso_eficiencia
       FROM configuracao_pesos
       WHERE papel = $1 AND subpapel = $2
       LIMIT 1`,
      [papelNormalizado, subpapelNormalizado]
    );

    if (rows[0]) {
      return mapRowToPesosConfig(rows[0]);
    }
  }

  const { rows: rowsPapel } = await pool.query(
    `SELECT id, papel, subpapel,
            peso_ind, peso_eq,
            peso_satisfacao, peso_performance, peso_atividade,
            peso_comunicacao, peso_eficiencia
     FROM configuracao_pesos
     WHERE papel = $1
     ORDER BY id
     LIMIT 1`,
    [papelNormalizado]
  );

  if (rowsPapel[0]) {
    return mapRowToPesosConfig(rowsPapel[0]);
  }

  return criarPesosConfigPadrao(papelNormalizado, subpapelNormalizado);
}

function resolverPesosDimensoesComConfig(pesosConfig) {
  return pesosConfig?.pesos_dimensoes || PESOS_PADRAO_DIMENSOES;
}

function resolverPesosNiveisComConfig(pesosConfig) {
  return pesosConfig?.pesos_niveis || PESOS_PADRAO_NIVEIS;
}

module.exports = {
  ALIAS_SUBPAPEL,
  normalizarSubpapel,
  mapRowToPesosConfig,
  criarPesosConfigPadrao,
  buscarConfiguracaoPesos,
  resolverPesosDimensoesComConfig,
  resolverPesosNiveisComConfig,
};
