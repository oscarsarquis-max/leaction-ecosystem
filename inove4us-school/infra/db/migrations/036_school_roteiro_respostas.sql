-- Roteiro Guiado digital — respostas por gestor/instituição/tipo.
-- IDs UUID (padrão School). passo_id até 40 chars: A.1 … C.11, *.checkpoint, feedback.*.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_roteiro_respostas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    gestor_id       UUID NOT NULL
        REFERENCES public.school_gestores (id) ON DELETE CASCADE,
    tipo            VARCHAR(20) NOT NULL DEFAULT 'homologacao',
    passo_id        VARCHAR(40) NOT NULL,
    concluido       BOOLEAN NOT NULL DEFAULT FALSE,
    observacao      TEXT,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_roteiro_respostas_escopo
        UNIQUE (instituicao_id, gestor_id, tipo, passo_id),
    CONSTRAINT chk_school_roteiro_tipo
        CHECK (tipo IN ('homologacao', 'treinamento'))
);

CREATE INDEX IF NOT EXISTS idx_school_roteiro_respostas_instituicao_tipo
    ON public.school_roteiro_respostas (instituicao_id, tipo, gestor_id);

CREATE INDEX IF NOT EXISTS idx_school_roteiro_respostas_gestor
    ON public.school_roteiro_respostas (gestor_id, tipo);

COMMENT ON TABLE public.school_roteiro_respostas IS
  'Respostas do Roteiro Guiado (homologação ou treinamento). Uma linha por passo.';
COMMENT ON COLUMN public.school_roteiro_respostas.tipo IS
  'homologacao | treinamento — mesmos passos, registros isolados.';
COMMENT ON COLUMN public.school_roteiro_respostas.passo_id IS
  'Ex.: A.1, B.7, C.11, A.checkpoint, feedback.entendi.';

COMMIT;
