-- Terceiro artefato canônico: AEE (condição) × metodologia (catálogo).
-- Numerado 043: em produção 040/041/042 já existem (aviso docente, PEI período, curadoria PEI).
-- Somente leitura dos originais. Servir no Editor só quando status = aprovado.
-- A tabela também é criada em runtime por ensure_canonico_schema() se a migration ainda não rodou.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_aee_metodologias_canonico (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condicao_categoria   VARCHAR(80) NOT NULL,
    metodologia_codigo   VARCHAR(120) NOT NULL,
    metodologia_nome     VARCHAR(255) NOT NULL,
    passos_adaptados     TEXT NOT NULL,
    status               VARCHAR(32) NOT NULL DEFAULT 'pendente_revisao',
    origem               VARCHAR(80) NOT NULL DEFAULT 'ia_lote',
    gerado_em            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aprovado_em          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_aee_met_canonico_cond_cod
        UNIQUE (condicao_categoria, metodologia_codigo),
    CONSTRAINT ck_school_aee_met_canonico_status
        CHECK (status IN ('pendente_revisao', 'aprovado', 'rejeitado'))
);

CREATE INDEX IF NOT EXISTS idx_school_aee_met_canonico_cond
    ON public.school_aee_metodologias_canonico (condicao_categoria);

CREATE INDEX IF NOT EXISTS idx_school_aee_met_canonico_status
    ON public.school_aee_metodologias_canonico (status);

COMMENT ON TABLE public.school_aee_metodologias_canonico IS
  'Card modificado condição × metodologia. Catálogo das 39 e school_aee_matrizes permanecem intactos.';
COMMENT ON COLUMN public.school_aee_metodologias_canonico.passos_adaptados IS
  'Passos da metodologia reescritos in-place com a diretriz da condição.';
COMMENT ON COLUMN public.school_aee_metodologias_canonico.status IS
  'pendente_revisao = gerado, ainda não herda no Editor; aprovado = canônico servido.';

COMMIT;
