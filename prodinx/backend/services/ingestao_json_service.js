const crypto = require("crypto");
const { isSemInformacao, sanitizeJsonValue } = require("../utils/json_sanitizer");

/** Limite da coluna colaboradores.matricula (schema atual). */
const MATRICULA_MAX_LEN = 20;

/**
 * Mapeamento indicador → chaves de origem no JSON por pessoa.
 * `aliases` espelham variáveis esperadas pelas fórmulas mathjs quando o nome
 * no JSON diverge (ex.: tb→bt, i3s→bp).
 */
const INDICADOR_PAYLOAD_MAP = {
  P007: { keys: ["ir", "ie"] },
  P003: {
    keys: ["tb", "tr", "horas_bloqueado", "ainda_bloqueado"],
    aliases: { bt: "tb" },
  },
  A004: { keys: ["mi", "dv"] },
  E008: { keys: ["mcy", "dpcy"] },
  E006: { keys: ["tec", "ctt"] },
  E002: {
    keys: ["ta", "ltt"],
    aliases: { lt: "ltt" },
  },
  A001: {
    keys: ["ca", "i3s"],
    aliases: { bp: "i3s" },
  },
  A002: { keys: ["fd", "fp"] },
  A005: {
    keys: ["spb", "spa"],
    aliases: { spr: "spb", spi: "spa" },
  },
  A006: {
    keys: ["md", "mp"],
    aliases: { mt: "md" },
  },
  A009: { keys: ["sta", "sdp"] },
  A010: { keys: ["btes", "bprod"] },
  C001: {
    keys: ["t0", "tq"],
    aliases: { it: "t0" },
  },
  C002: { keys: ["dr", "i3us"] },
  C008: { keys: ["wdr", "ics"] },
  P001: {
    keys: ["bv_ir", "bv_rs", "bv_eo", "bv_rc"],
    aliases: {
      ir: "bv_ir",
      rs: "bv_rs",
      eo: "bv_eo",
      rc: "bv_rc",
    },
  },
  P004: { keys: ["pe", "pp"] },
  P005: {
    keys: ["cmpp", "cmpt"],
    aliases: { zmpt: "cmpt" },
  },
  // Campos auxiliares presentes no Snapshot (quando houver indicador no catálogo)
  E001: { keys: ["mwi", "mwi_n_itens", "mwi_min_dias", "mwi_max_dias"] },
};

function criarErroHttp(statusCode, message, detalhes) {
  const error = new Error(message);
  error.statusCode = statusCode;
  if (detalhes !== undefined) {
    error.detalhes = detalhes;
  }
  return error;
}

function extrairLocalPartEmail(email) {
  if (typeof email !== "string") {
    return null;
  }
  const local = email.trim().split("@")[0];
  if (!local) {
    return null;
  }
  return local
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9._-]/g, ".")
    .toLowerCase();
}

function matriculaArtificialFromEmail(email) {
  if (email === null || email === undefined) {
    return null;
  }

  const emailStr = String(email).trim();
  if (!emailStr || isSemInformacao(emailStr) || !emailStr.includes("@")) {
    return null;
  }

  const localPart = extrairLocalPartEmail(emailStr);
  if (!localPart || isSemInformacao(localPart)) {
    return null;
  }

  const candidata = `EXT-${localPart}`;
  if (candidata.length <= MATRICULA_MAX_LEN) {
    return candidata;
  }

  // varchar(20): mantém prefixo legível + hash curto para unicidade
  const hash = crypto.createHash("sha1").update(localPart).digest("hex").slice(0, 4);
  const maxLocal = MATRICULA_MAX_LEN - "EXT-".length - 1 - hash.length;
  return `EXT-${localPart.slice(0, Math.max(1, maxLocal))}-${hash}`;
}

function resolverMatricula(pessoa) {
  const matriculaBruta = pessoa?.matricula;
  if (
    matriculaBruta !== null &&
    matriculaBruta !== undefined &&
    String(matriculaBruta).trim() !== "" &&
    !isSemInformacao(String(matriculaBruta))
  ) {
    const matricula = String(matriculaBruta).trim();
    if (matricula.length > MATRICULA_MAX_LEN) {
      throw criarErroHttp(
        400,
        `matricula excede ${MATRICULA_MAX_LEN} caracteres`,
        { matricula }
      );
    }
    return matricula;
  }

  return matriculaArtificialFromEmail(pessoa?.responsavel_email);
}

function resolverNomeColaborador(pessoa, matricula) {
  const nome = pessoa?.responsavel ?? pessoa?.nome;
  if (typeof nome === "string" && nome.trim() && !isSemInformacao(nome)) {
    return nome.trim().slice(0, 150);
  }
  return String(matricula).slice(0, 150);
}

function extrairPayloadIndicador(pessoaSanitizada, codIndicador) {
  const mapa = INDICADOR_PAYLOAD_MAP[codIndicador];
  if (!mapa) {
    return null;
  }

  const payload = {};

  for (const chave of mapa.keys) {
    if (Object.prototype.hasOwnProperty.call(pessoaSanitizada, chave)) {
      payload[chave] = pessoaSanitizada[chave];
    } else {
      payload[chave] = null;
    }
  }

  if (mapa.aliases) {
    for (const [alias, origem] of Object.entries(mapa.aliases)) {
      payload[alias] = Object.prototype.hasOwnProperty.call(payload, origem)
        ? payload[origem]
        : pessoaSanitizada[origem] ?? null;
    }
  }

  return payload;
}

function payloadTemDadosUteis(payload) {
  if (!payload || typeof payload !== "object") {
    return false;
  }

  return Object.values(payload).some(
    (valor) => valor !== null && valor !== undefined
  );
}

function extrairDataReferencia(documento) {
  const fim = documento?.periodo?.fim;
  if (typeof fim === "string" && fim.trim()) {
    return fim.trim().slice(0, 10);
  }
  throw criarErroHttp(
    400,
    "periodo.fim é obrigatório no JSON para data_referencia"
  );
}

function extrairPessoas(documento) {
  if (!documento || typeof documento !== "object" || Array.isArray(documento)) {
    throw criarErroHttp(400, "Corpo deve ser um objeto JSON com array pessoas");
  }

  if (!Array.isArray(documento.pessoas)) {
    throw criarErroHttp(400, "JSON inválido: campo pessoas[] é obrigatório");
  }

  return documento.pessoas;
}

async function carregarMapaIndicadores(client) {
  const { rows } = await client.query(`
    SELECT DISTINCT ON (cod_indicador)
      id,
      cod_indicador
    FROM indicadores
    ORDER BY
      cod_indicador,
      CASE WHEN nome_grupo = 'Técnica' THEN 0 ELSE 1 END,
      id
  `);

  const mapa = new Map();
  for (const row of rows) {
    mapa.set(String(row.cod_indicador).toUpperCase(), row.id);
  }
  return mapa;
}

async function upsertColaborador(client, pessoa) {
  const matricula = resolverMatricula(pessoa);
  const nome = resolverNomeColaborador(pessoa, matricula);

  const { rows } = await client.query(
    `
      INSERT INTO colaboradores (matricula, nome)
      VALUES ($1, $2)
      ON CONFLICT (matricula) DO UPDATE
        SET nome = EXCLUDED.nome
      RETURNING id_colaborador
    `,
    [matricula, nome]
  );

  return {
    id_colaborador: rows[0].id_colaborador,
    matricula,
    nome,
  };
}

async function inserirMedicao(client, {
  indicadorId,
  idColaborador,
  dataReferencia,
  payload,
  nomeArquivo,
}) {
  await client.query(
    `
      INSERT INTO medicoes (
        indicador_id,
        id_colaborador,
        nome_arquivo,
        payload,
        data_importacao,
        data_referencia,
        status_import,
        detalhe_status
      )
      VALUES ($1, $2, $3, $4::jsonb, NOW(), $5::date, 'SUCESSO', NULL)
    `,
    [
      indicadorId,
      idColaborador,
      nomeArquivo,
      JSON.stringify(payload),
      dataReferencia,
    ]
  );
}

/**
 * Pipeline ETL: sanitiza → upsert colaboradores → fatia por indicador → insert médicoes.
 * Toda a importação roda em uma única transação.
 *
 * Identidade (matrícula/e-mail) usa o registro bruto — a higienização transforma
 * 'Sem informação' em null e isso é necessário para gerar EXT-*.
 */
async function processarIngestaoJson(pool, documentoBruto, opcoes = {}) {
  const pessoasBrutas = extrairPessoas(documentoBruto);
  const documentoMeta = sanitizeJsonValue({
    periodo: documentoBruto?.periodo,
    base: documentoBruto?.base,
    origem: documentoBruto?.origem,
  });
  const dataReferencia = extrairDataReferencia({
    periodo: documentoBruto?.periodo ?? documentoMeta.periodo,
  });
  const nomeArquivo =
    opcoes.nomeArquivo ||
    documentoMeta.base ||
    documentoMeta.origem ||
    documentoBruto?.base ||
    documentoBruto?.origem ||
    "ingestao_json";

  const client = await pool.connect();
  let colaboradoresProcessados = 0;
  let medicoesInseridas = 0;
  const indicadoresIgnorados = new Set();
  const colaboradoresIgnorados = [];
  const detalhes = [];

  try {
    await client.query("BEGIN");

    const mapaIndicadores = await carregarMapaIndicadores(client);
    const codigosMapeados = Object.keys(INDICADOR_PAYLOAD_MAP);

    for (const pessoaBruta of pessoasBrutas) {
      if (!pessoaBruta || typeof pessoaBruta !== "object") {
        continue;
      }

      const matriculaResolvida = resolverMatricula(pessoaBruta);
      if (!matriculaResolvida) {
        colaboradoresIgnorados.push({
          motivo: "sem_matricula_nem_email_valido",
          responsavel: pessoaBruta.responsavel ?? null,
          responsavel_email: pessoaBruta.responsavel_email ?? null,
          chave_agrupamento: pessoaBruta.chave_agrupamento ?? null,
        });
        continue;
      }

      const pessoaLimpa = sanitizeJsonValue(pessoaBruta);
      const colaborador = await upsertColaborador(client, pessoaBruta);

      colaboradoresProcessados += 1;
      let medicoesPessoa = 0;

      for (const codIndicador of codigosMapeados) {
        const indicadorId = mapaIndicadores.get(codIndicador);
        if (!indicadorId) {
          indicadoresIgnorados.add(codIndicador);
          continue;
        }

        const payload = extrairPayloadIndicador(pessoaLimpa, codIndicador);
        if (!payloadTemDadosUteis(payload)) {
          continue;
        }

        await inserirMedicao(client, {
          indicadorId,
          idColaborador: colaborador.id_colaborador,
          dataReferencia,
          payload,
          nomeArquivo,
        });

        medicoesInseridas += 1;
        medicoesPessoa += 1;
      }

      detalhes.push({
        id_colaborador: colaborador.id_colaborador,
        matricula: colaborador.matricula,
        medicoes: medicoesPessoa,
      });
    }

    await client.query("COMMIT");

    const mensagem = `${colaboradoresProcessados} colaboradores processados, ${medicoesInseridas} medições limpas inseridas`;

    const resultado = {
      mensagem,
      colaboradores_processados: colaboradoresProcessados,
      medicoes_inseridas: medicoesInseridas,
      colaboradores_ignorados: colaboradoresIgnorados.length,
      data_referencia: dataReferencia,
      nome_arquivo: nomeArquivo,
      indicadores_sem_catalogo: [...indicadoresIgnorados].sort(),
    };

    if (opcoes.verbose) {
      resultado.detalhes_ignorados = colaboradoresIgnorados;
      resultado.detalhes = detalhes;
    } else if (colaboradoresIgnorados.length > 0) {
      resultado.detalhes_ignorados = colaboradoresIgnorados;
    }

    return resultado;
  } catch (error) {
    try {
      await client.query("ROLLBACK");
    } catch (_rollbackError) {
      // ignora falha de rollback secundária
    }
    throw error;
  } finally {
    client.release();
  }
}

module.exports = {
  INDICADOR_PAYLOAD_MAP,
  processarIngestaoJson,
  extrairPayloadIndicador,
  resolverMatricula,
  payloadTemDadosUteis,
};
