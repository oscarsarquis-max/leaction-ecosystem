BEGIN;

DROP INDEX IF EXISTS public.idx_inove_agenda_aguardando_continuacao;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_ocorrencia_tipo;
ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_ocorrencia_resolucao;

ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS continuacao_origem_id;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS juncao_destino_id;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS ocorrencia_resolucao;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS ocorrencia_nota;
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS ocorrencia_tipo;

COMMIT;
