-- Rollback Etapa 4 — importações
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/011_inove_importacoes_lote.down.sql

BEGIN;

DROP INDEX IF EXISTS public.idx_inove_agenda_importacao_origem;
DROP INDEX IF EXISTS public.uq_inove_aulas_simples_id_externo_clie;
DROP INDEX IF EXISTS public.uq_inove_agenda_id_externo_clie;

ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS id_externo_importacao;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS id_externo_importacao;

DROP TABLE IF EXISTS public.inove_importacoes_lote;

COMMIT;
