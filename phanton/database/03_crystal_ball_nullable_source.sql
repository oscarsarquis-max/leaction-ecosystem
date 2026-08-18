-- Crystal Ball: permitir shadow experimental sem run oficial
ALTER TABLE crystal_shadow_runs
    ALTER COLUMN source_run_id DROP NOT NULL;
