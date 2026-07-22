-- =====================================================================
-- MAtivas - Script de inicialização do banco de dados (PostgreSQL)
-- Mesa de Inovação | Metodologias Inov(ativas) na Educação
-- ---------------------------------------------------------------------
-- Estrutura relacional que persiste a jornada do professor de ponta a
-- ponta: cadastro, desafio enviado, roteiro gerado e o rastreio das
-- interações com a IA.
--
-- Uso:
--   createdb MAtivas
--   psql -d MAtivas -f database/init.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- Tabela: professores
-- Cadastro do educador. O e-mail é a chave natural de identificação.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS professores (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(100),
    email               VARCHAR(100) UNIQUE NOT NULL,
    estado              CHAR(2),
    status_livro        VARCHAR(50),
    opt_in_ecossistema  BOOLEAN DEFAULT FALSE,
    data_cadastro       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela: desafios
-- Cada desafio pedagógico enviado por um professor, com as respostas
-- das perguntas complementares e a síntese gerada.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS desafios (
    id                   SERIAL PRIMARY KEY,
    professor_id         INT REFERENCES professores(id) ON DELETE CASCADE,
    conteudo_desafio     TEXT,
    opcoes_selecionadas  TEXT,
    nivel_ensino         VARCHAR(50),
    formato_aula         VARCHAR(50),
    qtd_participantes    INT,
    sintese              TEXT,
    data_envio           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela: roteiros
-- Roteiro de aulas gerado a partir de um desafio. Os passos são
-- armazenados como JSONB para flexibilidade de estrutura.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roteiros (
    id                       SERIAL PRIMARY KEY,
    desafio_id               INT REFERENCES desafios(id) ON DELETE CASCADE,
    metodologia_recomendada  VARCHAR(100),
    justificativa            TEXT,
    passos_json              JSONB,
    feedback_autora          TEXT,
    status                   VARCHAR(20) DEFAULT 'Pendente',
    data_geracao             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migração para bases já existentes (idempotente).
ALTER TABLE roteiros
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Pendente';

-- Justificativa (racional) da escolha da metodologia, gerada pela IA.
ALTER TABLE roteiros
    ADD COLUMN IF NOT EXISTS justificativa TEXT;

-- Controle de envio automático de e-mail (evita duplicatas).
ALTER TABLE roteiros
    ADD COLUMN IF NOT EXISTS email_automatico_enviado_em TIMESTAMP NULL;

-- Curtida do professor no roteiro gerado.
ALTER TABLE roteiros
    ADD COLUMN IF NOT EXISTS curtido_em TIMESTAMP NULL;

-- ---------------------------------------------------------------------
-- Tabela: historico_interacoes_ia
-- Rastreio detalhado das interações com a IA (prompts, respostas,
-- modelo e consumo de tokens) para auditoria e análise de custos.
-- ON DELETE SET NULL preserva o histórico mesmo se o professor for
-- removido.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historico_interacoes_ia (
    id               SERIAL PRIMARY KEY,
    professor_id     INT REFERENCES professores(id) ON DELETE SET NULL,
    tipo_acao        VARCHAR(50),
    prompt_sistema   TEXT,
    prompt_usuario   TEXT,
    resposta_ia      TEXT,
    modelo_ia        VARCHAR(50),
    tokens_prompt    INT DEFAULT 0,
    tokens_resposta  INT DEFAULT 0,
    data_registro    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Índices de apoio às consultas mais frequentes.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_professores_email          ON professores (email);
CREATE INDEX IF NOT EXISTS idx_desafios_professor_id      ON desafios (professor_id);
CREATE INDEX IF NOT EXISTS idx_roteiros_desafio_id        ON roteiros (desafio_id);
CREATE INDEX IF NOT EXISTS idx_roteiros_status            ON roteiros (status);
CREATE INDEX IF NOT EXISTS idx_historico_professor_id     ON historico_interacoes_ia (professor_id);

-- ---------------------------------------------------------------------
-- Tabela: admin_users (área administrativa)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL
);

-- ---------------------------------------------------------------------
-- Tabela: vocabulary_rules (regras de vocabulário gerenciáveis)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vocabulary_rules (
    id              SERIAL PRIMARY KEY,
    keyword         VARCHAR(100) NOT NULL UNIQUE,
    rule_type       VARCHAR(50) NOT NULL,
    replacement     VARCHAR(255),
    is_active       INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_vocabulary_rules_keyword   ON vocabulary_rules (keyword);
CREATE INDEX IF NOT EXISTS idx_vocabulary_rules_rule_type ON vocabulary_rules (rule_type);
CREATE INDEX IF NOT EXISTS idx_vocabulary_rules_active    ON vocabulary_rules (is_active);
