-- inove4us B2C — overrides PEI do School (2 níveis: AEE base + individual).
-- Espelha a lógica de 025 (metodologia): upsert + versão maior vence.
-- Numeração: 026.

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_pei_overrides_base (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_b2b_id      UUID NOT NULL,
    condicao                TEXT NOT NULL,
    diretriz                TEXT NOT NULL DEFAULT '',
    versao                  BIGINT NOT NULL DEFAULT 0,
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aee_matriz_id_origem    UUID,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    synced_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_pei_overrides_base_inst_cond
        UNIQUE (instituicao_b2b_id, condicao)
);

CREATE INDEX IF NOT EXISTS idx_inove_pei_overrides_base_inst
    ON public.inove_pei_overrides_base (instituicao_b2b_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE public.inove_pei_overrides_base IS
  'PEI_OVERRIDE nível aee_base — diretriz da escola por condição (TEA, TDAH…).';

CREATE TABLE IF NOT EXISTS public.inove_pei_overrides_individual (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_b2b_id      UUID NOT NULL,
    aluno_id                UUID NOT NULL,
    aluno_nome              TEXT NOT NULL DEFAULT '',
    condicao                TEXT NOT NULL DEFAULT '',
    particularidades        TEXT NOT NULL DEFAULT '',
    versao                  BIGINT NOT NULL DEFAULT 0,
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pei_aluno_id_origem     UUID,
    aee_matriz_id_base      UUID,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    synced_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_pei_overrides_indiv_inst_aluno
        UNIQUE (instituicao_b2b_id, aluno_id)
);

CREATE INDEX IF NOT EXISTS idx_inove_pei_overrides_indiv_inst
    ON public.inove_pei_overrides_individual (instituicao_b2b_id)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_inove_pei_overrides_indiv_nome
    ON public.inove_pei_overrides_individual (
        instituicao_b2b_id,
        lower(trim(aluno_nome))
    )
    WHERE is_active = TRUE;

COMMENT ON TABLE public.inove_pei_overrides_individual IS
  'PEI_OVERRIDE nível individual — particularidades por aluno (UUID School + nome para match best-effort).';

COMMIT;
