BEGIN;

DROP INDEX IF EXISTS public.idx_school_planejamento_substitui;

ALTER TABLE public.school_planejamento_escolar
    DROP COLUMN IF EXISTS substitui_item_id;

ALTER TABLE public.school_planejamento_escolar
    DROP COLUMN IF EXISTS substituicao;

COMMIT;
