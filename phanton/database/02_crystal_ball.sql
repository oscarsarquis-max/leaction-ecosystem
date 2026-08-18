-- Crystal Ball — tabelas isoladas (nunca escreve em pipeline_runs / phase_executions)
CREATE TABLE IF NOT EXISTS crystal_shadow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_run_id UUID NOT NULL REFERENCES pipeline_runs (id) ON DELETE CASCADE,
    fork_phase_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'forked',
    spec JSONB NOT NULL,
    edited_phase_id VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    predicted_quality_score INTEGER,
    final_prompt_excerpt TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS crystal_shadow_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shadow_run_id UUID NOT NULL REFERENCES crystal_shadow_runs (id) ON DELETE CASCADE,
    phase_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'copied',
    origin VARCHAR NOT NULL DEFAULT 'copied',
    artifact_data JSONB,
    quality_score INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crystal_shadow_runs_source
    ON crystal_shadow_runs (source_run_id);

CREATE INDEX IF NOT EXISTS idx_crystal_shadow_phases_shadow
    ON crystal_shadow_phases (shadow_run_id, phase_id);

CREATE TABLE IF NOT EXISTS crystal_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_run_id UUID REFERENCES pipeline_runs (id) ON DELETE SET NULL,
    shadow_run_id UUID REFERENCES crystal_shadow_runs (id) ON DELETE SET NULL,
    kind VARCHAR NOT NULL,
    predicted_quality_score INTEGER,
    actual_quality_score INTEGER,
    prediction_error INTEGER,
    preview_text TEXT,
    confidence VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    calibrated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crystal_predictions_source
    ON crystal_predictions (source_run_id);

COMMENT ON TABLE crystal_shadow_runs IS
    'Crystal Ball — shadow runs de what-if; isolados dos runs oficiais.';
COMMENT ON TABLE crystal_shadow_phases IS
    'Artefatos copiados ou recalculados em modo simulação.';
COMMENT ON TABLE crystal_predictions IS
    'Calibração previsão vs quality_score real (só relatório Crystal Ball).';
