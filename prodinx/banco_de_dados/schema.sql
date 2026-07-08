-- Schema Prodinx — catálogo mestre + histórico de medições
CREATE TABLE IF NOT EXISTS indicadores (
    id SERIAL PRIMARY KEY,
    cod_indicador VARCHAR(10) NOT NULL,
    nome_indicador VARCHAR(150) NOT NULL,
    nome_grupo VARCHAR(50) NOT NULL,
    dimensao VARCHAR(50),
    nivel_avaliacao VARCHAR(30),
    formula_original TEXT,
    formula_normalizada VARCHAR(255),
    parametros_configuraveis JSONB,
    subpapeis_aplicaveis TEXT[],
    CONSTRAINT uq_indicadores_cod_grupo UNIQUE (cod_indicador, nome_grupo)
);

CREATE INDEX IF NOT EXISTS ix_indicadores_cod_indicador ON indicadores (cod_indicador);
CREATE INDEX IF NOT EXISTS ix_indicadores_nome_grupo ON indicadores (nome_grupo);

CREATE TABLE IF NOT EXISTS descricao_indicador (
    id SERIAL PRIMARY KEY,
    cod_indicador VARCHAR(10) NOT NULL UNIQUE,
    subpapel VARCHAR(50),
    normalizacao VARCHAR(100),
    explicacao TEXT,
    importancia TEXT
);

CREATE INDEX IF NOT EXISTS ix_descricao_indicador_cod_indicador ON descricao_indicador (cod_indicador);

CREATE TABLE IF NOT EXISTS colaboradores (
    id_colaborador SERIAL PRIMARY KEY,
    matricula VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(150) NOT NULL,
    funcao VARCHAR(100),
    codsetor VARCHAR(20),
    papel VARCHAR(50),
    subpapel VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS ix_colaboradores_matricula ON colaboradores (matricula);

CREATE TABLE IF NOT EXISTS medicoes (
    id SERIAL PRIMARY KEY,
    indicador_id INTEGER REFERENCES indicadores(id) ON DELETE CASCADE,
    id_colaborador INTEGER REFERENCES colaboradores(id_colaborador) ON DELETE SET NULL,
    nome_arquivo VARCHAR(100),
    payload JSONB NOT NULL,
    data_importacao TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_referencia DATE,
    status_import VARCHAR(20) NOT NULL,
    detalhe_status TEXT
);

CREATE INDEX IF NOT EXISTS ix_medicoes_indicador_id ON medicoes (indicador_id);
CREATE INDEX IF NOT EXISTS ix_medicoes_id_colaborador ON medicoes (id_colaborador);
CREATE INDEX IF NOT EXISTS ix_medicoes_status_import ON medicoes (status_import);
CREATE INDEX IF NOT EXISTS ix_medicoes_data_importacao ON medicoes (data_importacao);
CREATE INDEX IF NOT EXISTS ix_medicoes_data_referencia ON medicoes (data_referencia);

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

CREATE INDEX IF NOT EXISTS ix_configuracao_pesos_papel ON configuracao_pesos (papel);
CREATE INDEX IF NOT EXISTS ix_configuracao_pesos_subpapel ON configuracao_pesos (subpapel);
