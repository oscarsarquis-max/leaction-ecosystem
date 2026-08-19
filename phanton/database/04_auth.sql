-- Auth aditivo Phanton (users + ownership de shadows experimentais)
-- Idempotente.

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'restricted_tester')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- Ownership de shadows (Simulação Mativas / forks) — nullable = legado / admin local
ALTER TABLE crystal_shadow_runs
    ADD COLUMN IF NOT EXISTS owned_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_crystal_shadow_runs_owner
    ON crystal_shadow_runs (owned_by_user_id);
