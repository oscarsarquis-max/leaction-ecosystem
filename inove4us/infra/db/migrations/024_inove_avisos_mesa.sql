-- inove4us B2C — avisos da Mesa fixados pelo School (por instituição).
-- Fail-safe: listagem exige instituicao_b2b_id do professor E do aviso.
-- Numeração: 024.

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_avisos_mesa (
    id                          UUID PRIMARY KEY,
    instituicao_b2b_id          UUID,
    texto                       TEXT NOT NULL,
    disciplina_nome             TEXT,
    turma_nome                  TEXT,
    disciplina_id               UUID,
    turma_id                    UUID,
    ativo                       BOOLEAN NOT NULL DEFAULT TRUE,
    synced_at                   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_avisos_mesa_ativos
    ON public.inove_avisos_mesa (ativo, synced_at DESC)
    WHERE ativo = TRUE;

CREATE INDEX IF NOT EXISTS idx_inove_avisos_mesa_inst_ativos
    ON public.inove_avisos_mesa (instituicao_b2b_id, synced_at DESC)
    WHERE ativo = TRUE AND instituicao_b2b_id IS NOT NULL;

COMMENT ON TABLE public.inove_avisos_mesa IS
  'Avisos pinados pelo School (AVISO_MESA_PINNED). Escopo = instituicao_b2b_id.';
COMMENT ON COLUMN public.inove_avisos_mesa.instituicao_b2b_id IS
  'UUID da instituição School. NULL = órfão; listagem NÃO exibe (fail-safe fechado).';

COMMIT;
