BEGIN;

DROP INDEX IF EXISTS public.idx_inove_agenda_planejamento_escola;

ALTER TABLE public.inove_importacoes_lote
    DROP CONSTRAINT IF EXISTS chk_inove_importacoes_lote_canal;

ALTER TABLE public.inove_importacoes_lote
    DROP COLUMN IF EXISTS canal;

ALTER TABLE public.inove_aulas_simples
    DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_origem;

ALTER TABLE public.inove_aulas_simples
    ADD CONSTRAINT chk_inove_aulas_simples_origem
        CHECK (origem IN ('manual', 'wizard_ia', 'importacao'));

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;

ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN (
            'manual',
            'wizard_ia',
            'importacao',
            'comunicado_escola',
            'alocacao_escola'
        ));

COMMIT;
