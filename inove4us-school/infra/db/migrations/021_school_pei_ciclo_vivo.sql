-- Ciclo Vivo do PEI: adaptações por metodologia × aluno + curadoria bottom-up.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_pei_metodologia_adaptacao (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id       UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    pei_aluno_id         UUID NOT NULL
        REFERENCES public.school_pei_individualizado (id) ON DELETE CASCADE,
    metodologia_nome     TEXT NOT NULL,
    passos_customizados  TEXT NOT NULL DEFAULT '',
    gerado_por_ia        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_pei_met_adapt_pei_met
        UNIQUE (pei_aluno_id, metodologia_nome)
);

CREATE INDEX IF NOT EXISTS idx_school_pei_met_adapt_inst
    ON public.school_pei_metodologia_adaptacao (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_pei_met_adapt_pei
    ON public.school_pei_metodologia_adaptacao (pei_aluno_id);

COMMENT ON TABLE public.school_pei_metodologia_adaptacao IS
  'Passos da metodologia customizados para o PEI de um aluno (Ciclo Vivo).';

CREATE TABLE IF NOT EXISTS public.school_curadoria_pei (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    pei_aluno_id            UUID
        REFERENCES public.school_pei_individualizado (id) ON DELETE SET NULL,
    metodologia_nome        TEXT NOT NULL DEFAULT '',
    sugestao_professor_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status_analise          VARCHAR(32) NOT NULL DEFAULT 'pendente'
        CHECK (status_analise IN (
            'pendente',
            'incorporado',
            'rejeitado',
            'rejeitada',
            'mantido_apenas_na_aula'
        )),
    plano_espelhado_id      UUID
        REFERENCES public.school_planos_aula_espelhados (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_curadoria_pei_inst_status
    ON public.school_curadoria_pei (instituicao_id, status_analise);

CREATE INDEX IF NOT EXISTS idx_school_curadoria_pei_aluno
    ON public.school_curadoria_pei (pei_aluno_id)
    WHERE pei_aluno_id IS NOT NULL;

COMMENT ON TABLE public.school_curadoria_pei IS
  'Sugestões da trincheira (professor) sobre execução do PEI na aula.';

COMMIT;
