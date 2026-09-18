-- 153 hotfix: 047 deixou chk_school_comunicacoes_publico sem 'administradores'.
-- 052 só recriou school_comunicacoes_eventos_publico_alvo_check.

ALTER TABLE public.school_comunicacoes_eventos
    DROP CONSTRAINT IF EXISTS chk_school_comunicacoes_publico;

ALTER TABLE public.school_comunicacoes_eventos
    ADD CONSTRAINT chk_school_comunicacoes_publico
    CHECK (publico_alvo IN (
        'toda_instituicao', 'unidade', 'turma', 'professores',
        'disciplina', 'administradores'
    ));
