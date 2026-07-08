const TOLERANCIA_SOMA = 0.01;

const PAPEIS_SUBPAPEIS = {
  Técnica: ["Dev", "Tester", "Arquiteto"],
  "Gestão Técnica": ["PO", "Scrum Master", "Gerente"],
};

const CAMPOS_DIMENSAO = [
  { chave: "peso_satisfacao", label: "Satisfação" },
  { chave: "peso_performance", label: "Performance" },
  { chave: "peso_atividade", label: "Atividade" },
  { chave: "peso_comunicacao", label: "Comunicação" },
  { chave: "peso_eficiencia", label: "Eficiência" },
];

function arredondarPeso(valor, casas = 4) {
  return Number(Number(valor).toFixed(casas));
}

function mapRowToResponse(row) {
  if (!row) {
    return null;
  }

  return {
    id: row.id,
    papel: row.papel,
    subpapel: row.subpapel,
    peso_ind: Number(row.peso_ind),
    peso_eq: Number(row.peso_eq),
    peso_satisfacao: Number(row.peso_satisfacao),
    peso_performance: Number(row.peso_performance),
    peso_atividade: Number(row.peso_atividade),
    peso_comunicacao: Number(row.peso_comunicacao),
    peso_eficiencia: Number(row.peso_eficiencia),
  };
}

function validarPayloadPesos(payload) {
  const erros = [];
  const pesoInd = Number(payload.peso_ind);
  const pesoEq = Number(payload.peso_eq);

  if (Number.isNaN(pesoInd) || pesoInd < 0 || pesoInd > 1) {
    erros.push("peso_ind deve estar entre 0 e 1");
  }

  if (Number.isNaN(pesoEq) || pesoEq < 0 || pesoEq > 1) {
    erros.push("peso_eq deve estar entre 0 e 1");
  }

  const somaNiveis = arredondarPeso(pesoInd + pesoEq);
  if (Math.abs(somaNiveis - 1) > TOLERANCIA_SOMA) {
    erros.push("A soma de Peso Individual e Peso Equipe deve ser 100%");
  }

  const somaDimensoes = CAMPOS_DIMENSAO.reduce(
    (total, campo) => total + Number(payload[campo.chave] || 0),
    0
  );

  if (Math.abs(arredondarPeso(somaDimensoes) - 1) > TOLERANCIA_SOMA) {
    erros.push("A soma dos pesos das dimensões SPACE deve ser 100%");
  }

  CAMPOS_DIMENSAO.forEach((campo) => {
    const valor = Number(payload[campo.chave]);
    if (Number.isNaN(valor) || valor < 0 || valor > 1) {
      erros.push(`${campo.label} deve estar entre 0% e 100%`);
    }
  });

  return erros;
}

async function listarOpcoesConfiguracaoPesos() {
  return {
    papeis: Object.keys(PAPEIS_SUBPAPEIS),
    subpapeis_por_papel: PAPEIS_SUBPAPEIS,
  };
}

async function buscarConfiguracaoPesosPorPapel(pool, papel, subpapel) {
  const { rows } = await pool.query(
    `SELECT id, papel, subpapel,
            peso_ind, peso_eq,
            peso_satisfacao, peso_performance, peso_atividade,
            peso_comunicacao, peso_eficiencia
     FROM configuracao_pesos
     WHERE papel = $1 AND subpapel = $2
     LIMIT 1`,
    [papel, subpapel]
  );

  return mapRowToResponse(rows[0] ?? null);
}

async function salvarConfiguracaoPesos(pool, payload) {
  const papel = String(payload.papel || "").trim();
  const subpapel = String(payload.subpapel || "").trim();

  if (!papel || !subpapel) {
    const erro = new Error("papel e subpapel são obrigatórios");
    erro.statusCode = 400;
    throw erro;
  }

  const subpapeisValidos = PAPEIS_SUBPAPEIS[papel];
  if (!subpapeisValidos || !subpapeisValidos.includes(subpapel)) {
    const erro = new Error("Combinação papel/subpapel inválida");
    erro.statusCode = 400;
    throw erro;
  }

  const dadosNormalizados = {
    peso_ind: arredondarPeso(payload.peso_ind),
    peso_eq: arredondarPeso(payload.peso_eq),
    peso_satisfacao: arredondarPeso(payload.peso_satisfacao),
    peso_performance: arredondarPeso(payload.peso_performance),
    peso_atividade: arredondarPeso(payload.peso_atividade),
    peso_comunicacao: arredondarPeso(payload.peso_comunicacao),
    peso_eficiencia: arredondarPeso(payload.peso_eficiencia),
  };

  const erros = validarPayloadPesos(dadosNormalizados);
  if (erros.length > 0) {
    const erro = new Error(erros.join("; "));
    erro.statusCode = 400;
    erro.detalhes = erros;
    throw erro;
  }

  const { rows } = await pool.query(
    `
    INSERT INTO configuracao_pesos (
      papel, subpapel,
      peso_ind, peso_eq,
      peso_satisfacao, peso_performance, peso_atividade,
      peso_comunicacao, peso_eficiencia
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (papel, subpapel)
    DO UPDATE SET
      peso_ind = EXCLUDED.peso_ind,
      peso_eq = EXCLUDED.peso_eq,
      peso_satisfacao = EXCLUDED.peso_satisfacao,
      peso_performance = EXCLUDED.peso_performance,
      peso_atividade = EXCLUDED.peso_atividade,
      peso_comunicacao = EXCLUDED.peso_comunicacao,
      peso_eficiencia = EXCLUDED.peso_eficiencia
    RETURNING id, papel, subpapel,
              peso_ind, peso_eq,
              peso_satisfacao, peso_performance, peso_atividade,
              peso_comunicacao, peso_eficiencia
    `,
    [
      papel,
      subpapel,
      dadosNormalizados.peso_ind,
      dadosNormalizados.peso_eq,
      dadosNormalizados.peso_satisfacao,
      dadosNormalizados.peso_performance,
      dadosNormalizados.peso_atividade,
      dadosNormalizados.peso_comunicacao,
      dadosNormalizados.peso_eficiencia,
    ]
  );

  return mapRowToResponse(rows[0]);
}

module.exports = {
  CAMPOS_DIMENSAO,
  PAPEIS_SUBPAPEIS,
  listarOpcoesConfiguracaoPesos,
  buscarConfiguracaoPesosPorPapel,
  salvarConfiguracaoPesos,
  validarPayloadPesos,
};
