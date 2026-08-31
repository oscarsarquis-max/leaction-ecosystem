-- Registro de ocorrência + junção/continuação manual (paliativo do split/cascata).
-- Não recalcula agenda. Só registra o que aconteceu e links pontuais.

BEGIN;

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS ocorrencia_tipo VARCHAR(32);

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS ocorrencia_nota TEXT NOT NULL DEFAULT '';

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS ocorrencia_resolucao VARCHAR(32);

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS juncao_destino_id INTEGER
        REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE SET NULL;

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS continuacao_origem_id INTEGER
        REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE SET NULL;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_ocorrencia_tipo;
ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_ocorrencia_tipo
    CHECK (
        ocorrencia_tipo IS NULL
        OR ocorrencia_tipo IN (
            'concluida',
            'interrompida',
            'substituicao',
            'trabalho_monitorado'
        )
    );

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_ocorrencia_resolucao;
ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_ocorrencia_resolucao
    CHECK (
        ocorrencia_resolucao IS NULL
        OR ocorrencia_resolucao IN (
            'aguardando_continuacao',
            'concluida_via_juncao',
            'agendada_continuacao'
        )
    );

CREATE INDEX IF NOT EXISTS idx_inove_agenda_aguardando_continuacao
    ON public.inove_agenda_eventos (id_clie, turma, disciplina_id)
    WHERE ocorrencia_resolucao = 'aguardando_continuacao';

COMMENT ON COLUMN public.inove_agenda_eventos.ocorrencia_tipo IS
    'Registro honesto do fechamento: concluida | interrompida | substituicao | trabalho_monitorado.';
COMMENT ON COLUMN public.inove_agenda_eventos.ocorrencia_resolucao IS
    'Só para interrompida: aguardando_continuacao | concluida_via_juncao | agendada_continuacao.';

COMMIT;
