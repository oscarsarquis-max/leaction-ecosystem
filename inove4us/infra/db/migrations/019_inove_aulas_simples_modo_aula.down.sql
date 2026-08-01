BEGIN;

ALTER TABLE public.inove_aulas_simples
    DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_status;

ALTER TABLE public.inove_aulas_simples
    ADD CONSTRAINT chk_inove_aulas_simples_status
    CHECK (status IN ('draft', 'planejado', 'realizado'));

ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS feedback_json;

ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS data_conclusao;

ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS data_inicio;

COMMIT;
