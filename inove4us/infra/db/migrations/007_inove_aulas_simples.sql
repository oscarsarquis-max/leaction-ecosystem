-- DRAFT / PENDING APPLY — não executar em produção até validação financeira (Penny Test).
-- Vetor "Dia a Dia": aula rápida (~50 min), fora do fluxo de Sprints/projetos.
--
-- Aplicar depois com:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/007_inove_aulas_simples.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_aulas_simples (
    id                    BIGSERIAL PRIMARY KEY,
    id_clie               INTEGER NOT NULL
                            REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    data_planejada        DATE NOT NULL,
    turma_nome            VARCHAR(120),
    tema_aula             VARCHAR(255) NOT NULL,
    objetivo_aprendizagem TEXT NOT NULL DEFAULT '',

    -- Estrutura ágil simplificada (aula de 50 min)
    acolhida              TEXT NOT NULL DEFAULT '',
    conteudo_essencial    TEXT NOT NULL DEFAULT '',
    -- Ref. desacoplada à biblioteca MAtivas (nome/chave) ou slug local — sem FK cross-app
    dinamica_ativa_id     VARCHAR(160),
    dinamica_ativa_fonte  VARCHAR(32) NOT NULL DEFAULT 'mativas'
                            CHECK (dinamica_ativa_fonte IN ('mativas', 'inove_local', 'livre')),
    fechamento_checkout   TEXT NOT NULL DEFAULT '',

    -- Vínculo opcional com a agenda executiva (tipo aula_dia)
    id_evento_agenda      INTEGER,
    kanban_state          JSONB,

    status                VARCHAR(32) NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft', 'planejado', 'realizado')),

    created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_clie_data
    ON public.inove_aulas_simples (id_clie, data_planejada DESC);

CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_status
    ON public.inove_aulas_simples (status, data_planejada DESC);

CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_dinamica
    ON public.inove_aulas_simples (dinamica_ativa_id)
    WHERE dinamica_ativa_id IS NOT NULL;

COMMENT ON TABLE public.inove_aulas_simples IS
  'Vetor Dia a Dia — planejamento de aula simples (~50 min); não substitui ctdi_sprn.';
COMMENT ON COLUMN public.inove_aulas_simples.dinamica_ativa_id IS
  'Referência textual à metodologia (ex.: chave normalizada MAtivas). Sem FK cross-app.';
COMMENT ON COLUMN public.inove_aulas_simples.fechamento_checkout IS
  'Checkout / verificação final da aula.';

COMMIT;
