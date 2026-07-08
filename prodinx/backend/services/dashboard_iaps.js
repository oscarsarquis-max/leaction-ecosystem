const { calcularIapsColaborador } = require("./iaps_calculator");
const { buscarConfiguracaoPesos } = require("./config_pesos_db");

async function buscarColaboradorPorId(pool, idColaborador) {
  if (!idColaborador) {
    return null;
  }

  const { rows } = await pool.query(
    `SELECT id_colaborador, matricula, nome, funcao, codsetor, papel, subpapel
     FROM colaboradores
     WHERE id_colaborador = $1`,
    [idColaborador]
  );

  return rows[0] ?? null;
}

async function resolverIdColaboradorFiltro(pool, filtros) {
  if (filtros.idColaborador) {
    return filtros.idColaborador;
  }

  if (filtros.nivel !== "colaborador" || !filtros.colaboradorBusca) {
    return null;
  }

  const termo = filtros.colaboradorBusca.trim();
  const { rows } = await pool.query(
    `SELECT id_colaborador
     FROM colaboradores
     WHERE matricula = $1
        OR LOWER(nome) = LOWER($1)
        OR matricula ILIKE '%' || $1 || '%'
        OR nome ILIKE '%' || $1 || '%'
     LIMIT 2`,
    [termo]
  );

  if (rows.length === 1) {
    return rows[0].id_colaborador;
  }

  return null;
}

async function calcularIapsColaboradorComPesos(pool, metricas, colaboradorDb) {
  const contextoPesos = colaboradorDb
    ? { papel: colaboradorDb.papel, subpapel: colaboradorDb.subpapel }
    : { papel: null, subpapel: null };

  const pesosConfig = await buscarConfiguracaoPesos(
    pool,
    contextoPesos.papel,
    contextoPesos.subpapel
  );

  return calcularIapsColaborador(metricas, colaboradorDb, pesosConfig);
}

module.exports = {
  buscarColaboradorPorId,
  resolverIdColaboradorFiltro,
  calcularIapsColaborador,
  calcularIapsColaboradorComPesos,
};
