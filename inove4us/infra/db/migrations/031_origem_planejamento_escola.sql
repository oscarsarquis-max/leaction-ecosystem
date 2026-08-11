-- inove4us B2C — origem planejamento_escola (push Secretaria → agenda).
-- Numeração: 031.
-- Reaproveita inove_importacoes_lote com canal arquivo|escola.

BEGIN;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;

ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN (
            'manual',
            'wizard_ia',
            'importacao',
            'comunicado_escola',
            'alocacao_escola',
            'planejamento_escola'
        ));

ALTER TABLE public.inove_aulas_simples
    DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_origem;

ALTER TABLE public.inove_aulas_simples
    ADD CONSTRAINT chk_inove_aulas_simples_origem
        CHECK (origem IN (
            'manual',
            'wizard_ia',
            'importacao',
            'planejamento_escola'
        ));

ALTER TABLE public.inove_importacoes_lote
    ADD COLUMN IF NOT EXISTS canal VARCHAR(32) NOT NULL DEFAULT 'arquivo';

ALTER TABLE public.inove_importacoes_lote
    DROP CONSTRAINT IF EXISTS chk_inove_importacoes_lote_canal;

ALTER TABLE public.inove_importacoes_lote
    ADD CONSTRAINT chk_inove_importacoes_lote_canal
        CHECK (canal IN ('arquivo', 'escola'));

CREATE INDEX IF NOT EXISTS idx_inove_agenda_planejamento_escola
    ON public.inove_agenda_eventos (id_clie, origem)
    WHERE origem = 'planejamento_escola';

COMMENT ON COLUMN public.inove_agenda_eventos.origem IS
  'manual | wizard_ia | importacao | comunicado_escola | alocacao_escola | planejamento_escola';
COMMENT ON COLUMN public.inove_importacoes_lote.canal IS
  'arquivo = upload do professor; escola = push S2S da Secretaria (planejamento).';

COMMIT;
