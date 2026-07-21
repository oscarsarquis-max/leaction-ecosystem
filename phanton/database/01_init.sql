-- Phanton — schema inicial do orquestrador
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

CREATE INDEX IF NOT EXISTS idx_phase_executions_run_id
    ON phase_executions (run_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON pipeline_runs (status);
