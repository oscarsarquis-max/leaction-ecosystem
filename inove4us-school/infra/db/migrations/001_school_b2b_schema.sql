-- inove4us School (B2B) — schema inicial isolado.
-- Prefixo obrigatório: school_*
-- Banco dedicado: inove4us_school (NÃO usar o DB do inove4us B2C).
-- Aplicar:
--   psql -h 127.0.0.1 -p 5434 -U admin -d inove4us_school -v ON_ERROR_STOP=1 \
--     -f infra/db/migrations/001_school_b2b_schema.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1) Instituições (escola / rede)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_instituicoes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    razao_social    VARCHAR(255) NOT NULL,
    cnpj            VARCHAR(18)  NOT NULL,
    dominio_email   VARCHAR(255),
    status          VARCHAR(32)  NOT NULL DEFAULT 'ativa',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_instituicoes_cnpj UNIQUE (cnpj),
    CONSTRAINT chk_school_instituicoes_status
        CHECK (status IN ('ativa', 'inativa', 'suspensa', 'trial'))
);

CREATE INDEX IF NOT EXISTS idx_school_instituicoes_status
    ON public.school_instituicoes (status);

CREATE INDEX IF NOT EXISTS idx_school_instituicoes_dominio
    ON public.school_instituicoes (dominio_email)
    WHERE dominio_email IS NOT NULL;

COMMENT ON TABLE public.school_instituicoes IS
  'Escolas/redes geridas pela Torre de Controle B2B (inove4us School).';

-- ---------------------------------------------------------------------------
-- 2) Gestores — login exclusivo desta aplicação (Diretor / Coordenador)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_gestores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    nome            VARCHAR(200) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    senha_hash      TEXT NOT NULL,
    cargo           VARCHAR(32) NOT NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_gestores_email UNIQUE (email),
    CONSTRAINT chk_school_gestores_cargo
        CHECK (cargo IN ('Diretor', 'Coordenador'))
);

CREATE INDEX IF NOT EXISTS idx_school_gestores_instituicao
    ON public.school_gestores (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_gestores_cargo
    ON public.school_gestores (instituicao_id, cargo);

COMMENT ON TABLE public.school_gestores IS
  'Usuários B2B (Diretor/Coordenador). Autenticação própria — não compartilha sessão com o app dos professores.';
COMMENT ON COLUMN public.school_gestores.senha_hash IS
  'Hash de senha (ex.: scrypt/bcrypt). Nunca armazenar senha em claro.';

-- ---------------------------------------------------------------------------
-- 3) Vínculo professor B2C ↔ instituição
--    professor_b2c_id é referência lógica ao universo do professor (inove4us B2C).
--    Sem FK cross-database: isolamento físico entre apps.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_professores_vinculo (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id    UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    professor_b2c_id  UUID NOT NULL,
    status_vinculo    VARCHAR(32) NOT NULL DEFAULT 'pendente',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_prof_vinculo_inst_prof
        UNIQUE (instituicao_id, professor_b2c_id),
    CONSTRAINT chk_school_prof_vinculo_status
        CHECK (status_vinculo IN ('pendente', 'ativo', 'suspenso', 'revogado'))
);

CREATE INDEX IF NOT EXISTS idx_school_prof_vinculo_instituicao
    ON public.school_professores_vinculo (instituicao_id, status_vinculo);

CREATE INDEX IF NOT EXISTS idx_school_prof_vinculo_professor
    ON public.school_professores_vinculo (professor_b2c_id);

COMMENT ON TABLE public.school_professores_vinculo IS
  'Ponte lógica School → professor B2C. Somente IDs e status; sem dados pedagógicos do B2C.';
COMMENT ON COLUMN public.school_professores_vinculo.professor_b2c_id IS
  'UUID de referência ao professor no ecossistema B2C. Sem FK — comunicação via API/contratos.';

-- ---------------------------------------------------------------------------
-- 4) Editor pedagógico — diretrizes da escola (repassáveis ao B2C)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_editor_pedagogico (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id       UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    metodologia_base     VARCHAR(64) NOT NULL DEFAULT 'PBL',
    diretriz_customizada TEXT,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_editor_instituicao
    ON public.school_editor_pedagogico (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_editor_active
    ON public.school_editor_pedagogico (instituicao_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE public.school_editor_pedagogico IS
  'Diretrizes pedagógicas da instituição. A School é fonte de verdade; o B2C consome via integração.';
COMMENT ON COLUMN public.school_editor_pedagogico.metodologia_base IS
  'Metodologia âncora (ex.: Método inove4us, Aprendizagem Baseada em Projetos).';

COMMIT;
