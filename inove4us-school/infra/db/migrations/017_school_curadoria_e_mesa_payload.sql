-- inove4us School — curadoria de metodologias + payload completo da mesa B2C.
-- Numeração: 017.

BEGIN;

-- Payload completo da Mesa (Dia a Dia / Desafio) para renderização read-only.
ALTER TABLE public.school_planos_aula_espelhados
    ADD COLUMN IF NOT EXISTS mesa_payload_json JSONB;

COMMENT ON COLUMN public.school_planos_aula_espelhados.mesa_payload_json IS
  'JSON completo da Mesa do professor (B2C). Fonte do MirroredLessonDesk (somente leitura).';

-- UPSERT estável por origem B2C (sem FK cross-DB).
CREATE UNIQUE INDEX IF NOT EXISTS uq_school_planos_origem_b2c
    ON public.school_planos_aula_espelhados (instituicao_id, origem_plano_b2c_id)
    WHERE origem_plano_b2c_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.school_curadoria_metodologias (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id        UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    metodologia_nome      TEXT NOT NULL,
    plano_espelhado_id    UUID
        REFERENCES public.school_planos_aula_espelhados (id) ON DELETE SET NULL,
    sugestao_professor_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status_analise        VARCHAR(32) NOT NULL DEFAULT 'pendente'
        CHECK (status_analise IN (
            'pendente', 'em_analise', 'incorporada', 'rejeitada'
        )),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_curadoria_instituicao
    ON public.school_curadoria_metodologias (instituicao_id, status_analise);

CREATE INDEX IF NOT EXISTS idx_school_curadoria_plano
    ON public.school_curadoria_metodologias (plano_espelhado_id)
    WHERE plano_espelhado_id IS NOT NULL;

COMMENT ON TABLE public.school_curadoria_metodologias IS
  'Fila de curadoria: adaptações do professor (has_teacher_adaptations) para o pedagogo analisar.';

COMMIT;
