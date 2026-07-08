const PESOS_PADRAO_SEED = {
  peso_ind: 0.4,
  peso_eq: 0.6,
  peso_satisfacao: 0.25,
  peso_performance: 0.25,
  peso_atividade: 0.2,
  peso_comunicacao: 0.2,
  peso_eficiencia: 0.1,
};

const CONFIGURACOES_PADRAO = [
  { papel: "Técnica", subpapel: "Dev" },
  { papel: "Técnica", subpapel: "Tester" },
  { papel: "Técnica", subpapel: "Arquiteto" },
  { papel: "Gestão Técnica", subpapel: "PO" },
  { papel: "Gestão Técnica", subpapel: "Scrum Master" },
  { papel: "Gestão Técnica", subpapel: "Gerente" },
];

async function ensurePapeisIapsSchema(pool) {
  await pool.query(`
    ALTER TABLE colaboradores
        ADD COLUMN IF NOT EXISTS papel VARCHAR(50),
        ADD COLUMN IF NOT EXISTS subpapel VARCHAR(50);

    ALTER TABLE indicadores
        ADD COLUMN IF NOT EXISTS subpapeis_aplicaveis TEXT[];

    UPDATE indicadores
    SET subpapeis_aplicaveis = ARRAY['Dev', 'Tester', 'PO', 'Scrum Master']::TEXT[]
    WHERE cod_indicador = 'P007'
      AND (subpapeis_aplicaveis IS NULL OR cardinality(subpapeis_aplicaveis) = 0);
  `);
}

async function ensureConfiguracaoPesosSchema(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS configuracao_pesos (
        id SERIAL PRIMARY KEY,
        papel VARCHAR(50) NOT NULL,
        subpapel VARCHAR(50) NOT NULL,
        peso_ind NUMERIC(5, 4) NOT NULL DEFAULT 0.4,
        peso_eq NUMERIC(5, 4) NOT NULL DEFAULT 0.6,
        peso_satisfacao NUMERIC(5, 4) NOT NULL,
        peso_performance NUMERIC(5, 4) NOT NULL,
        peso_atividade NUMERIC(5, 4) NOT NULL,
        peso_comunicacao NUMERIC(5, 4) NOT NULL,
        peso_eficiencia NUMERIC(5, 4) NOT NULL,
        CONSTRAINT uq_configuracao_pesos_papel_subpapel UNIQUE (papel, subpapel)
    );

    CREATE INDEX IF NOT EXISTS ix_configuracao_pesos_papel
        ON configuracao_pesos (papel);
    CREATE INDEX IF NOT EXISTS ix_configuracao_pesos_subpapel
        ON configuracao_pesos (subpapel);
  `);

  for (const item of CONFIGURACOES_PADRAO) {
    await pool.query(
      `
      INSERT INTO configuracao_pesos (
        papel, subpapel,
        peso_ind, peso_eq,
        peso_satisfacao, peso_performance, peso_atividade,
        peso_comunicacao, peso_eficiencia
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      ON CONFLICT (papel, subpapel) DO NOTHING
      `,
      [
        item.papel,
        item.subpapel,
        PESOS_PADRAO_SEED.peso_ind,
        PESOS_PADRAO_SEED.peso_eq,
        PESOS_PADRAO_SEED.peso_satisfacao,
        PESOS_PADRAO_SEED.peso_performance,
        PESOS_PADRAO_SEED.peso_atividade,
        PESOS_PADRAO_SEED.peso_comunicacao,
        PESOS_PADRAO_SEED.peso_eficiencia,
      ]
    );
  }
}

const {
  CATALOGO_TECNICA_COMPLETO,
  FORMULAS_INDICADORES_PADRAO,
} = require("./services/indicadores_formulas_padrao");

async function ensureIndicadoresMotorRegrasSchema(pool) {
  await pool.query(`
    ALTER TABLE indicadores
        ADD COLUMN IF NOT EXISTS formula_normalizada VARCHAR(255),
        ADD COLUMN IF NOT EXISTS parametros_configuraveis JSONB;
  `);
}

async function upsertCatalogoTecnica(pool) {
  for (const item of CATALOGO_TECNICA_COMPLETO) {
    const subpapeis = item.subpapeis_aplicaveis ?? null;

    await pool.query(
      `
      INSERT INTO indicadores (
        cod_indicador,
        nome_indicador,
        nome_grupo,
        dimensao,
        nivel_avaliacao,
        formula_normalizada,
        parametros_configuraveis,
        subpapeis_aplicaveis
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::text[])
      ON CONFLICT (cod_indicador, nome_grupo)
      DO UPDATE SET
        nome_indicador = EXCLUDED.nome_indicador,
        dimensao = EXCLUDED.dimensao,
        nivel_avaliacao = EXCLUDED.nivel_avaliacao,
        formula_normalizada = EXCLUDED.formula_normalizada,
        parametros_configuraveis = EXCLUDED.parametros_configuraveis,
        subpapeis_aplicaveis = COALESCE(
          EXCLUDED.subpapeis_aplicaveis,
          indicadores.subpapeis_aplicaveis
        )
      `,
      [
        item.cod_indicador,
        item.nome_indicador,
        item.nome_grupo,
        item.dimensao,
        item.nivel_avaliacao,
        item.formula_normalizada,
        JSON.stringify(item.parametros_configuraveis || {}),
        subpapeis,
      ]
    );
  }
}

async function seedFormulasIndicadoresPadrao(pool) {
  for (const item of FORMULAS_INDICADORES_PADRAO) {
    await pool.query(
      `
      UPDATE indicadores
      SET formula_normalizada = $1,
          parametros_configuraveis = $2::jsonb
      WHERE cod_indicador = $3
        AND ($4::text IS NULL OR nome_grupo = $4)
      `,
      [
        item.formula_normalizada,
        JSON.stringify(item.parametros_configuraveis || {}),
        item.cod_indicador,
        item.nome_grupo ?? null,
      ]
    );
  }
}

async function corrigirPayloadSeedApdP007(pool) {
  await pool.query(`
    UPDATE medicoes m
    SET payload = jsonb_set(
          jsonb_set(
            COALESCE(m.payload, '{}'::jsonb),
            '{resumo,ie}',
            '3'::jsonb,
            true
          ),
          '{resumo,ir}',
          '1'::jsonb,
          true
        )
    FROM indicadores i
    WHERE m.indicador_id = i.id
      AND i.cod_indicador = 'P007'
      AND m.nome_arquivo LIKE 'seed_apd_%'
  `);
}

async function atualizarCodsetorColaboradoresApd(pool) {
  await pool.query(`
    UPDATE colaboradores
    SET codsetor = 'APD'
    WHERE matricula IN ('F178992', 'F178841', 'F170046', 'F179117')
      AND (codsetor IS NULL OR codsetor <> 'APD')
  `);
}

async function corrigirMedicoesSeedApdAtividade(pool) {
  await pool.query(`
    UPDATE medicoes m
    SET payload = jsonb_set(
          jsonb_set(
            COALESCE(m.payload, '{}'::jsonb),
            '{resumo,score}',
            '0.4'::jsonb,
            true
          ),
          '{resumo,score_percentual}',
          '40'::jsonb,
          true
        )
    FROM indicadores i
    WHERE m.indicador_id = i.id
      AND i.cod_indicador = 'A002'
      AND m.nome_arquivo LIKE 'seed_apd_%';

    UPDATE medicoes m
    SET payload = jsonb_set(
          jsonb_set(
            COALESCE(m.payload, '{}'::jsonb),
            '{resumo,score}',
            '0.5'::jsonb,
            true
          ),
          '{resumo,score_percentual}',
          '50'::jsonb,
          true
        )
    FROM indicadores i
    WHERE m.indicador_id = i.id
      AND i.cod_indicador = 'A009'
      AND m.nome_arquivo LIKE 'seed_apd_%';
  `);
}

async function ensureAnalisesInteligentesSchema(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS analises_inteligentes (
        id SERIAL PRIMARY KEY,
        id_colaborador INTEGER NOT NULL
            REFERENCES colaboradores(id_colaborador) ON DELETE CASCADE,
        hash_contexto VARCHAR(64) NOT NULL,
        resultado JSONB NOT NULL,
        modelo VARCHAR(120),
        provider VARCHAR(50),
        gerado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_analises_inteligentes_colaborador UNIQUE (id_colaborador)
    );

    CREATE INDEX IF NOT EXISTS ix_analises_inteligentes_colaborador
        ON analises_inteligentes (id_colaborador);
  `);
}

async function ensureDatabaseSchema(pool) {
  await ensurePapeisIapsSchema(pool);
  await ensureConfiguracaoPesosSchema(pool);
  await ensureIndicadoresMotorRegrasSchema(pool);
  await ensureAnalisesInteligentesSchema(pool);
  await upsertCatalogoTecnica(pool);
  await seedFormulasIndicadoresPadrao(pool);
  await corrigirPayloadSeedApdP007(pool);
  await atualizarCodsetorColaboradoresApd(pool);
  await corrigirMedicoesSeedApdAtividade(pool);
}

module.exports = {
  ensurePapeisIapsSchema,
  ensureConfiguracaoPesosSchema,
  ensureIndicadoresMotorRegrasSchema,
  seedFormulasIndicadoresPadrao,
  upsertCatalogoTecnica,
  corrigirPayloadSeedApdP007,
  corrigirMedicoesSeedApdAtividade,
  atualizarCodsetorColaboradoresApd,
  ensureAnalisesInteligentesSchema,
  ensureDatabaseSchema,
};
