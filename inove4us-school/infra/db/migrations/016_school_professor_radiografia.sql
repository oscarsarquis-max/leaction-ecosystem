-- inove4us School — radiografia do professor (Equipe).
-- Numeração: 016.
--
-- 1) Recursos concedidos ao vínculo (licença, material, metodologia liberada…).
-- 2) Avaliações de desempenho declaradas (nota atual + histórico).

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_professor_recursos (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_vinculo_id    UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE CASCADE,
    titulo                  TEXT NOT NULL,
    tipo                    TEXT NOT NULL DEFAULT 'outro'
        CHECK (tipo IN (
            'licenca',
            'metodologia',
            'material',
            'pei',
            'formacao',
            'outro'
        )),
    detalhe                 TEXT,
    concedido_em            DATE NOT NULL DEFAULT CURRENT_DATE,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_prof_recursos_vinculo
    ON public.school_professor_recursos (professor_vinculo_id)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_professor_recursos IS
  'Recursos que o professor recebeu da escola (licença, material, formação, etc.).';

CREATE TABLE IF NOT EXISTS public.school_professor_avaliacoes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_vinculo_id    UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE CASCADE,
    nota                    NUMERIC(4, 2) NOT NULL
        CHECK (nota >= 0 AND nota <= 10),
    referencia              TEXT NOT NULL,
    observacao              TEXT,
    declarado_por_gestor_id UUID
        REFERENCES public.school_gestores (id) ON DELETE SET NULL,
    declarado_em            DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_prof_avaliacao_ref
        UNIQUE (professor_vinculo_id, referencia)
);

CREATE INDEX IF NOT EXISTS idx_school_prof_avaliacoes_vinculo
    ON public.school_professor_avaliacoes (professor_vinculo_id, declarado_em DESC);

COMMENT ON TABLE public.school_professor_avaliacoes IS
  'Notas de desempenho declaradas pela escola (histórico). Integração B2C futura pode espelhar.';
COMMENT ON COLUMN public.school_professor_avaliacoes.referencia IS
  'Rótulo do ciclo (ex.: 2026-1, 2º bimestre 2026).';

COMMIT;
