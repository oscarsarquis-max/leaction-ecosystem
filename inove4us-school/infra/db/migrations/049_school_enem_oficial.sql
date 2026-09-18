-- Matriz de Referência do ENEM (INEP) — catálogo só-leitura.
-- 120 habilidades das 4 áreas + 5 competências de Redação à parte.
-- Texto oficial; sem geração por IA. Prompt 147.

BEGIN;

CREATE TABLE IF NOT EXISTS public.enem_habilidades_oficial (
    codigo                 TEXT PRIMARY KEY,
    area_codigo            VARCHAR(8) NOT NULL,
    area_nome              TEXT NOT NULL,
    competencia_numero     INTEGER NOT NULL,
    competencia_texto      TEXT NOT NULL,
    habilidade_numero      INTEGER NOT NULL,
    texto                  TEXT NOT NULL,
    fonte_documento        TEXT,
    fonte_url              TEXT,
    fonte_proveniencia     TEXT,
    fonte_localizador      TEXT,
    dataset_versao         TEXT NOT NULL DEFAULT 'enem-oficial-2026.09.1',
    texto_hash             TEXT,
    payload_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_enem_oficial_area
        CHECK (area_codigo IN ('LC', 'MT', 'CN', 'CH')),
    CONSTRAINT ck_enem_oficial_hab
        CHECK (habilidade_numero BETWEEN 1 AND 30),
    CONSTRAINT uq_enem_oficial_area_hab
        UNIQUE (area_codigo, habilidade_numero)
);

CREATE INDEX IF NOT EXISTS idx_enem_oficial_area
    ON public.enem_habilidades_oficial (area_codigo, competencia_numero);

COMMENT ON TABLE public.enem_habilidades_oficial IS
  'Espelho só-leitura da Matriz de Referência do ENEM (PDF INEP). Nunca editar à mão; reimportar.';
COMMENT ON COLUMN public.enem_habilidades_oficial.texto IS
  'Enunciado oficial da habilidade, copiado do PDF do INEP — sem paráfrase.';
COMMENT ON COLUMN public.enem_habilidades_oficial.fonte_proveniencia IS
  'PDF oficial + SHA-256 + edital que aponta a matriz vigente.';

CREATE TABLE IF NOT EXISTS public.enem_redacao_competencias_oficial (
    codigo                 TEXT PRIMARY KEY,
    competencia_numero     INTEGER NOT NULL UNIQUE,
    texto                  TEXT NOT NULL,
    fonte_documento        TEXT,
    fonte_url              TEXT,
    fonte_proveniencia     TEXT,
    dataset_versao         TEXT NOT NULL DEFAULT 'enem-oficial-2026.09.1',
    texto_hash             TEXT,
    payload_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_enem_redacao_n
        CHECK (competencia_numero BETWEEN 1 AND 5)
);

COMMENT ON TABLE public.enem_redacao_competencias_oficial IS
  'Cinco competências oficiais da Redação do ENEM (cartilha INEP). Sem H1–H30.';

CREATE TABLE IF NOT EXISTS public.enem_eixos_cognitivos_oficial (
    sigla                  VARCHAR(8) PRIMARY KEY,
    romano                 VARCHAR(8) NOT NULL,
    nome                   TEXT NOT NULL,
    texto                  TEXT NOT NULL,
    fonte_documento        TEXT,
    fonte_url              TEXT,
    dataset_versao         TEXT NOT NULL DEFAULT 'enem-oficial-2026.09.1',
    texto_hash             TEXT,
    imported_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.enem_eixos_cognitivos_oficial IS
  'Cinco eixos cognitivos comuns às quatro áreas (PDF INEP).';

COMMIT;
