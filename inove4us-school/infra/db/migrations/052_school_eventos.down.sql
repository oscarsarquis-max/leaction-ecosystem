DELETE FROM public.school_eventos;
DROP TABLE IF EXISTS public.school_eventos;
ALTER TABLE public.school_comunicacoes_eventos DROP COLUMN IF EXISTS tipo_evento;
ALTER TABLE public.school_comunicacoes_eventos
    DROP CONSTRAINT IF EXISTS school_comunicacoes_eventos_publico_alvo_check;
ALTER TABLE public.school_comunicacoes_eventos
    ADD CONSTRAINT school_comunicacoes_eventos_publico_alvo_check
    CHECK (publico_alvo IN (
        'toda_instituicao', 'unidade', 'turma', 'professores', 'disciplina'
    ));
