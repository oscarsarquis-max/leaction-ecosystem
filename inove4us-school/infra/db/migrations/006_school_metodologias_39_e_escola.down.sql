-- Reverte 006: remove colunas novas; não restaura seed parcial de 3 (use 004+seed manual se necessário).
BEGIN;

ALTER TABLE public.school_metodologia_config
    DROP COLUMN IF EXISTS passos_customizados;

DROP INDEX IF EXISTS idx_school_metodologias_catalogo_origem_inst;
DROP INDEX IF EXISTS idx_school_metodologias_catalogo_categoria;
DROP INDEX IF EXISTS uq_school_metodologias_catalogo_codigo;
DROP INDEX IF EXISTS uq_school_metodologias_catalogo_nome_padrao;
DROP INDEX IF EXISTS uq_school_metodologias_catalogo_nome_escola;

ALTER TABLE public.school_metodologias_catalogo
    DROP CONSTRAINT IF EXISTS chk_school_metodologias_catalogo_origem;

ALTER TABLE public.school_metodologias_catalogo
    DROP COLUMN IF EXISTS instituicao_origem_id,
    DROP COLUMN IF EXISTS origem,
    DROP COLUMN IF EXISTS categoria,
    DROP COLUMN IF EXISTS codigo;

-- Recria UNIQUE(nome) clássico se ainda não existir.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_school_metodologias_catalogo_nome'
    ) THEN
        ALTER TABLE public.school_metodologias_catalogo
            ADD CONSTRAINT uq_school_metodologias_catalogo_nome UNIQUE (nome);
    END IF;
END $$;

COMMIT;
