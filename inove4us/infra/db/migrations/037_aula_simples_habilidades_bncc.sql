-- Dia a Dia: códigos BNCC da aula como lista (prompt 95).
-- tema_aula VARCHAR(255) permanece título humano; não é mais a fonte da verdade.
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/037_aula_simples_habilidades_bncc.sql

BEGIN;

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS habilidades_bncc JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.inove_aulas_simples.habilidades_bncc IS
  'Códigos BNCC desta aula, em ordem de seleção. Lista JSON; independente do tema_aula VARCHAR(255).';

COMMIT;
