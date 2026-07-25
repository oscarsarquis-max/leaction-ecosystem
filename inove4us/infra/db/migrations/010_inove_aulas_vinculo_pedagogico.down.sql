-- Rollback Etapa 3 — vínculo pedagógico em aula/evento
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/010_inove_aulas_vinculo_pedagogico.down.sql

BEGIN;

DROP INDEX IF EXISTS public.idx_inove_agenda_eventos_origem;
DROP INDEX IF EXISTS public.idx_inove_agenda_eventos_disciplina;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS origem;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS disciplina_id;

DROP INDEX IF EXISTS public.idx_inove_aulas_simples_origem;
DROP INDEX IF EXISTS public.idx_inove_aulas_simples_disciplina;

ALTER TABLE public.inove_aulas_simples
    DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_origem;
ALTER TABLE public.inove_aulas_simples
    DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_tipo_registro;
ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS origem;
ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS tipo_registro;
ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS disciplina_id;

COMMIT;
