-- Cache do conteúdo sugerido do Dia a Dia (prompt 86).
-- Chave: tema (habilidade BNCC ou tópico de ementa) × nível da turma.
-- Compartilhado entre professores. Sem metodologia e sem AEE na chave.
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/036_inove_roteiro_conteudo_cache.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_roteiro_conteudo_cache (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key           VARCHAR(64) NOT NULL,
    fonte               VARCHAR(16) NOT NULL,
    habilidade_codigo   VARCHAR(32),
    tema                TEXT NOT NULL,
    disciplina_nome     VARCHAR(160),
    nivel_turma         VARCHAR(64) NOT NULL,
    conteudo_json       JSONB NOT NULL,
    texto_montado       TEXT NOT NULL,
    created_by          INTEGER
        REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_roteiro_conteudo_cache_key UNIQUE (cache_key),
    CONSTRAINT ck_inove_roteiro_conteudo_fonte
        CHECK (fonte IN ('bncc', 'ementa'))
);

CREATE INDEX IF NOT EXISTS idx_inove_roteiro_conteudo_nivel
    ON public.inove_roteiro_conteudo_cache (nivel_turma, fonte);

COMMENT ON TABLE public.inove_roteiro_conteudo_cache IS
  'Conteúdo sugerido da disciplina, gerado 1× por tema×nível. Metodologia/AEE não entram na chave.';

COMMIT;
