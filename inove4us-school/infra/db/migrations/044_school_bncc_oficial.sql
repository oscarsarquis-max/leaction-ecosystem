-- BNCC oficial importada (espelho da fonte bncc-dev/bncc-dados) + temas canônicos
-- para o seletor do Dia a Dia. Não altera school_disciplinas.ementa.

BEGIN;

CREATE TABLE IF NOT EXISTS public.bncc_habilidades_oficial (
    codigo                   TEXT PRIMARY KEY,
    etapa                    VARCHAR(20) NOT NULL,
    componente_id            TEXT,
    componente_nome          TEXT,
    area_id                  TEXT,
    area_nome                TEXT,
    anos                     INTEGER[],
    unidade_tematica         TEXT,
    objetos_conhecimento     TEXT,
    texto                    TEXT NOT NULL,
    vigencia_status          VARCHAR(40),
    fonte_documento          TEXT,
    fonte_arquivo            TEXT,
    fonte_proveniencia       TEXT,
    fonte_localizador        TEXT,
    fonte_localizador_pdf    TEXT,
    fonte_url                TEXT,
    dataset_versao           TEXT NOT NULL DEFAULT 'dados-2026.07.1',
    payload_json             JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bncc_oficial_etapa
    ON public.bncc_habilidades_oficial (etapa);
CREATE INDEX IF NOT EXISTS idx_bncc_oficial_componente
    ON public.bncc_habilidades_oficial (componente_id);
CREATE INDEX IF NOT EXISTS idx_bncc_oficial_anos
    ON public.bncc_habilidades_oficial USING GIN (anos);

COMMENT ON TABLE public.bncc_habilidades_oficial IS
  'Espelho só-leitura da BNCC importada (bncc-dev/bncc-dados). Nunca editar à mão; reimportar.';
COMMENT ON COLUMN public.bncc_habilidades_oficial.texto IS
  'Enunciado oficial da habilidade/objetivo, copiado do dataset — sem paráfrase.';
COMMENT ON COLUMN public.bncc_habilidades_oficial.fonte_proveniencia IS
  'Proveniência do registro no dataset (planilha MEC / PDF homologado).';

CREATE TABLE IF NOT EXISTS public.school_bncc_temas_canonico (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disciplina_nome      TEXT NOT NULL,
    disciplina_id        UUID
        REFERENCES public.school_disciplinas (id) ON DELETE SET NULL,
    curso_id             UUID
        REFERENCES public.school_cursos (id) ON DELETE SET NULL,
    curso_ano            TEXT NOT NULL,
    etapa                VARCHAR(8) NOT NULL,
    tema                 TEXT NOT NULL,
    habilidade_codigo    TEXT NOT NULL
        REFERENCES public.bncc_habilidades_oficial (codigo) ON DELETE RESTRICT,
    origem               VARCHAR(40) NOT NULL DEFAULT 'bncc_importado',
    status               VARCHAR(32) NOT NULL DEFAULT 'pendente_revisao',
    agrupamento_fonte    VARCHAR(40) NOT NULL DEFAULT 'unidade_tematica',
    gerado_em            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aprovado_em          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_bncc_tema_disc_ano_hab
        UNIQUE (disciplina_nome, curso_ano, habilidade_codigo),
    CONSTRAINT ck_school_bncc_tema_status
        CHECK (status IN ('pendente_revisao', 'aprovado', 'rejeitado')),
    CONSTRAINT ck_school_bncc_tema_origem
        CHECK (origem = 'bncc_importado')
);

CREATE INDEX IF NOT EXISTS idx_school_bncc_temas_status
    ON public.school_bncc_temas_canonico (status);
CREATE INDEX IF NOT EXISTS idx_school_bncc_temas_disc_ano
    ON public.school_bncc_temas_canonico (disciplina_nome, curso_ano);

COMMENT ON TABLE public.school_bncc_temas_canonico IS
  'Recorte curado disciplina×ano → tema prático + habilidade oficial. Camada nova; ementa da escola permanece.';
COMMENT ON COLUMN public.school_bncc_temas_canonico.tema IS
  'Rótulo didático extraído de campos oficiais do import (objeto único ou unidade temática), revisável.';
COMMENT ON COLUMN public.school_bncc_temas_canonico.habilidade_codigo IS
  'FK lógica/física para bncc_habilidades_oficial.codigo — texto oficial nunca é duplicado aqui.';
COMMENT ON COLUMN public.school_bncc_temas_canonico.status IS
  'pendente_revisao = gerado, não serve o seletor; aprovado = catálogo do Dia a Dia.';

COMMIT;
