-- Phanton — schema do orquestrador (pipeline multi-modelo)
-- Aplicado no primeiro boot do volume Docker e via apply-schema.ps1 em bases já existentes.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec JSONB NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    project_key VARCHAR,
    project_name VARCHAR,
    version VARCHAR DEFAULT '1.0',
    acceptance_status VARCHAR NOT NULL DEFAULT 'open',
    accepted_at TIMESTAMP,
    parent_run_id UUID,
    retorno_markdown TEXT,
    lineage_kind VARCHAR
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

-- Migração idempotente (volumes já existentes)
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS project_key VARCHAR;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS project_name VARCHAR;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS version VARCHAR DEFAULT '1.0';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS acceptance_status VARCHAR;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMP;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS parent_run_id UUID;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS retorno_markdown TEXT;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS lineage_kind VARCHAR;

UPDATE pipeline_runs
SET acceptance_status = 'open'
WHERE acceptance_status IS NULL;

DO $$
BEGIN
    ALTER TABLE pipeline_runs
        ALTER COLUMN acceptance_status SET DEFAULT 'open';
EXCEPTION
    WHEN others THEN NULL;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_parent_run_id_fkey'
    ) THEN
        ALTER TABLE pipeline_runs
            ADD CONSTRAINT pipeline_runs_parent_run_id_fkey
            FOREIGN KEY (parent_run_id) REFERENCES pipeline_runs (id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Histórico / listagem de runs
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON pipeline_runs (status);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created_at
    ON pipeline_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_updated_at
    ON pipeline_runs (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_project_key
    ON pipeline_runs (project_key);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_project_version
    ON pipeline_runs (project_key, version);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_acceptance
    ON pipeline_runs (acceptance_status);

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
COMMENT ON COLUMN pipeline_runs.project_key IS
    'Slug estável do projeto (derivado do name na aceitação / start).';
COMMENT ON COLUMN pipeline_runs.acceptance_status IS
    'open | accepted — após accepted o resultado é imutável.';
COMMENT ON COLUMN pipeline_runs.parent_run_id IS
    'Run aceito de origem quando este run é substituto (retorno/evolução).';
COMMENT ON COLUMN pipeline_runs.lineage_kind IS
    'retorno | evolucao — origem do pipeline substituto.';
COMMENT ON TABLE phase_executions IS
    'Resultado de cada fase (artifact_data JSONB) — recuperável após aprovação.';
COMMENT ON COLUMN phase_executions.artifact_data IS
    'Artefato da fase (metodologia, pesquisa, síntese ou entrega HTML/Markdown).';
COMMENT ON COLUMN phase_executions.task_token IS
    'Token de aprovação humana enquanto status = AWAITING_APPROVAL.';

CREATE TABLE IF NOT EXISTS phanton_improvement_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_run_id UUID REFERENCES pipeline_runs (id) ON DELETE SET NULL,
    substitute_run_id UUID REFERENCES pipeline_runs (id) ON DELETE SET NULL,
    title VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    items JSONB,
    raw_section TEXT,
    status VARCHAR NOT NULL DEFAULT 'pending',
    source VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_phanton_improvements_status
    ON phanton_improvement_proposals (status);

CREATE INDEX IF NOT EXISTS idx_phanton_improvements_source_run
    ON phanton_improvement_proposals (source_run_id);

COMMENT ON TABLE phanton_improvement_proposals IS
    'Melhorias propostas no Phanton a partir de retorno; decisão explícita aceitar/rejeitar.';
