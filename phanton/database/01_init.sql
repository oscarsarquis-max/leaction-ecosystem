-- Phanton — schema do orquestrador (pipeline multi-modelo)
-- Aplicado no primeiro boot do volume Docker e via apply-schema.ps1 em bases já existentes.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec JSONB NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS phase_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs (id) ON DELETE CASCADE,
    phase_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    artifact_data JSONB,
    approver TEXT,
    comments TEXT,
    task_token VARCHAR
);

-- Histórico / listagem de runs
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON pipeline_runs (status);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created_at
    ON pipeline_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_updated_at
    ON pipeline_runs (updated_at DESC);

-- Fases por run + recuperação de artefatos
CREATE INDEX IF NOT EXISTS idx_phase_executions_run_id
    ON phase_executions (run_id);

CREATE INDEX IF NOT EXISTS idx_phase_executions_run_phase
    ON phase_executions (run_id, phase_id);

CREATE INDEX IF NOT EXISTS idx_phase_executions_status
    ON phase_executions (status);

CREATE INDEX IF NOT EXISTS idx_phase_executions_task_token
    ON phase_executions (task_token)
    WHERE task_token IS NOT NULL;

COMMENT ON TABLE pipeline_runs IS
    'Runs do orquestrador Phanton (spec JSON + status). Histórico em GET /api/pipeline.';
COMMENT ON TABLE phase_executions IS
    'Resultado de cada fase (artifact_data JSONB) — recuperável após aprovação.';
COMMENT ON COLUMN phase_executions.artifact_data IS
    'Artefato da fase (metodologia, pesquisa, síntese ou entrega HTML/Markdown).';
COMMENT ON COLUMN phase_executions.task_token IS
    'Token de aprovação humana enquanto status = AWAITING_APPROVAL.';
