-- Modo Aula (Dia a Dia): status em execução + timestamps de início/conclusão + feedback.
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/019_inove_aulas_simples_modo_aula.sql

BEGIN;

ALTER TABLE public.inove_aulas_simples
    DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_status;

ALTER TABLE public.inove_aulas_simples
    ADD CONSTRAINT chk_inove_aulas_simples_status
    CHECK (status IN ('draft', 'planejado', 'em_execucao', 'realizado'));

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS data_inicio TIMESTAMPTZ;

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS data_conclusao TIMESTAMPTZ;

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS feedback_json JSONB;

COMMENT ON COLUMN public.inove_aulas_simples.data_inicio IS
  'Timestamp do clique em Iniciar Aula (Modo Aula).';
COMMENT ON COLUMN public.inove_aulas_simples.data_conclusao IS
  'Timestamp do clique em Encerrar Aula — independente do horário planejado.';
COMMENT ON COLUMN public.inove_aulas_simples.feedback_json IS
  'Retroalimentação pós-aula (metodologia, engajamento, estrutura, observações).';

COMMIT;
