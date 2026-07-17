-- Contexto de aula: turma, turno e modo (continuidade vs reinício)
ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS turma VARCHAR(120);

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS turno VARCHAR(32);

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS modo_execucao VARCHAR(32);

-- Mesmo dia OK se turma/turno forem diferentes; bloqueia duplicata exata
CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_agenda_aula_dia_turma_turno
    ON public.inove_agenda_eventos (
        id_clie,
        (data_evento::date),
        lower(trim(turma)),
        lower(trim(turno))
    )
    WHERE tipo = 'aula_eduscrum'
      AND turma IS NOT NULL
      AND trim(turma) <> ''
      AND turno IS NOT NULL
      AND trim(turno) <> '';
