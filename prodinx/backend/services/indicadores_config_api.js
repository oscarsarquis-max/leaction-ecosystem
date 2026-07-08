const MAX_FORMULA_NORMALIZADA = 255;

function criarErroHttp(statusCode, mensagem, detalhes = undefined) {
  const erro = new Error(mensagem);
  erro.statusCode = statusCode;
  if (detalhes !== undefined) {
    erro.detalhes = detalhes;
  }
  return erro;
}

function mapRowToIndicadorConfig(row) {
  return {
    id: row.id,
    cod_indicador: row.cod_indicador,
    nome_indicador: row.nome_indicador,
    nome_grupo: row.nome_grupo,
    dimensao: row.dimensao ?? null,
    nivel_avaliacao: row.nivel_avaliacao ?? null,
    formula_original: row.formula_original ?? null,
    formula_normalizada: row.formula_normalizada ?? null,
    parametros_configuraveis: row.parametros_configuraveis ?? null,
    subpapeis_aplicaveis: row.subpapeis_aplicaveis ?? null,
  };
}

function validarPayloadAtualizacao(payload) {
  if (payload === null || payload === undefined) {
    throw criarErroHttp(400, "Corpo da requisição é obrigatório");
  }

  if (typeof payload !== "object" || Array.isArray(payload)) {
    throw criarErroHttp(400, "Payload deve ser um objeto JSON válido");
  }

  const possuiFormula = Object.prototype.hasOwnProperty.call(
    payload,
    "formula_normalizada"
  );
  const possuiParametros = Object.prototype.hasOwnProperty.call(
    payload,
    "parametros_configuraveis"
  );

  if (!possuiFormula && !possuiParametros) {
    throw criarErroHttp(
      400,
      "Informe ao menos um campo para atualização: formula_normalizada ou parametros_configuraveis"
    );
  }

  const erros = [];

  if (possuiFormula) {
    const formula = payload.formula_normalizada;

    if (formula !== null && typeof formula !== "string") {
      erros.push("formula_normalizada deve ser string ou null");
    } else if (typeof formula === "string") {
      const formulaLimpa = formula.trim();
      if (!formulaLimpa) {
        erros.push("formula_normalizada não pode ser string vazia (use null para limpar)");
      } else if (formulaLimpa.length > MAX_FORMULA_NORMALIZADA) {
        erros.push(`formula_normalizada excede ${MAX_FORMULA_NORMALIZADA} caracteres`);
      }
    }
  }

  if (possuiParametros) {
    const parametros = payload.parametros_configuraveis;

    if (parametros !== null && (typeof parametros !== "object" || Array.isArray(parametros))) {
      erros.push("parametros_configuraveis deve ser um objeto JSON ou null");
    }
  }

  if (erros.length > 0) {
    throw criarErroHttp(400, "Payload malformado", erros);
  }

  return {
    formula_normalizada: possuiFormula ? payload.formula_normalizada : undefined,
    parametros_configuraveis: possuiParametros
      ? payload.parametros_configuraveis
      : undefined,
  };
}

async function listarIndicadoresConfig(pool) {
  const { rows } = await pool.query(
    `SELECT id, cod_indicador, nome_indicador, nome_grupo, dimensao, nivel_avaliacao,
            formula_original, formula_normalizada, parametros_configuraveis,
            subpapeis_aplicaveis
     FROM indicadores
     ORDER BY cod_indicador, nome_grupo`
  );

  return rows.map(mapRowToIndicadorConfig);
}

async function atualizarIndicadorConfig(pool, codIndicador, payload, nomeGrupo = null) {
  const dadosValidados = validarPayloadAtualizacao(payload);

  const { rows: existentes } = await pool.query(
    `SELECT id, cod_indicador, nome_grupo
     FROM indicadores
     WHERE cod_indicador = $1
       AND ($2::text IS NULL OR nome_grupo = $2)`,
    [codIndicador, nomeGrupo]
  );

  if (existentes.length === 0) {
    throw criarErroHttp(404, `Indicador '${codIndicador}' não encontrado`);
  }

  const campos = [];
  const valores = [];
  let indice = 1;

  if (dadosValidados.formula_normalizada !== undefined) {
    const formula =
      dadosValidados.formula_normalizada === null
        ? null
        : String(dadosValidados.formula_normalizada).trim();
    campos.push(`formula_normalizada = $${indice++}`);
    valores.push(formula);
  }

  if (dadosValidados.parametros_configuraveis !== undefined) {
    campos.push(`parametros_configuraveis = $${indice++}::jsonb`);
    valores.push(
      dadosValidados.parametros_configuraveis === null
        ? null
        : JSON.stringify(dadosValidados.parametros_configuraveis)
    );
  }

  valores.push(codIndicador);
  const filtroCod = `$${indice++}`;
  valores.push(nomeGrupo);
  const filtroGrupo = `$${indice}`;

  const { rows } = await pool.query(
    `UPDATE indicadores
     SET ${campos.join(", ")}
     WHERE cod_indicador = ${filtroCod}
       AND (${filtroGrupo}::text IS NULL OR nome_grupo = ${filtroGrupo})
     RETURNING id, cod_indicador, nome_indicador, nome_grupo, dimensao, nivel_avaliacao,
               formula_original, formula_normalizada, parametros_configuraveis,
               subpapeis_aplicaveis`,
    valores
  );

  return {
    cod_indicador: codIndicador,
    nome_grupo: nomeGrupo,
    atualizados: rows.length,
    indicadores: rows.map(mapRowToIndicadorConfig),
  };
}

module.exports = {
  MAX_FORMULA_NORMALIZADA,
  listarIndicadoresConfig,
  atualizarIndicadorConfig,
  validarPayloadAtualizacao,
};
