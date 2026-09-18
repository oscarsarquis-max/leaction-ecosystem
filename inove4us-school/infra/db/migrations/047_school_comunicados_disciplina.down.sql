BEGIN;

DROP INDEX IF EXISTS public.idx_school_comunicacoes_disciplina;

ALTER TABLE public.school_comunicacoes_eventos
    DROP CONSTRAINT IF EXISTS chk_school_comunicacoes_publico;

ALTER TABLE public.school_comunicacoes_eventos
    ADD CONSTRAINT chk_school_comunicacoes_publico
        CHECK (publico_alvo IN (
            'toda_instituicao',
            'unidade',
            'turma',
            'professores'
        ));

ALTER TABLE public.school_comunicacoes_eventos
    DROP COLUMN IF EXISTS disciplina_id;

COMMIT;
