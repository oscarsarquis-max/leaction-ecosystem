-- 047: comunicados — público-alvo por disciplina (prompt 114)
-- Fan-out = professores com alocação ativa na disciplina (qualquer turma).

BEGIN;

ALTER TABLE public.school_comunicacoes_eventos
    ADD COLUMN IF NOT EXISTS disciplina_id UUID
        REFERENCES public.school_disciplinas (id) ON DELETE SET NULL;

ALTER TABLE public.school_comunicacoes_eventos
    DROP CONSTRAINT IF EXISTS chk_school_comunicacoes_publico;

ALTER TABLE public.school_comunicacoes_eventos
    ADD CONSTRAINT chk_school_comunicacoes_publico
        CHECK (publico_alvo IN (
            'toda_instituicao',
            'unidade',
            'turma',
            'professores',
            'disciplina'
        ));

CREATE INDEX IF NOT EXISTS idx_school_comunicacoes_disciplina
    ON public.school_comunicacoes_eventos (disciplina_id)
    WHERE disciplina_id IS NOT NULL;

COMMENT ON COLUMN public.school_comunicacoes_eventos.disciplina_id IS
  'Usado quando publico_alvo = disciplina. Fan-out: alocações ativas desta disciplina.';

COMMIT;
