BEGIN;

DROP INDEX IF EXISTS public.idx_school_roteiro_respostas_sessao;
DROP INDEX IF EXISTS public.uq_school_roteiro_respostas_sem_sessao;
DROP INDEX IF EXISTS public.uq_school_roteiro_respostas_com_sessao;

ALTER TABLE public.school_roteiro_respostas
    DROP COLUMN IF EXISTS sessao_id;

-- Restaura unique legado (sem sessao_id).
ALTER TABLE public.school_roteiro_respostas
    DROP CONSTRAINT IF EXISTS uq_school_roteiro_respostas_escopo;

ALTER TABLE public.school_roteiro_respostas
    ADD CONSTRAINT uq_school_roteiro_respostas_escopo
        UNIQUE (instituicao_id, gestor_id, tipo, passo_id);

DROP TABLE IF EXISTS public.school_homologacao_eventos;
DROP TABLE IF EXISTS public.school_homologacao_sessoes;
DROP TABLE IF EXISTS public.school_homologadores;

COMMIT;
