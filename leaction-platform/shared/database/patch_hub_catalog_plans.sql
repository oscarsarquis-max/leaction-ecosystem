-- Catálogo / vitrine de planos por app satélite (painel admin Action Hub).
-- Aplicar: psql "$DATABASE_URL" -f shared/database/patch_catalog_plans.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS catalog_plans (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id      TEXT NOT NULL REFERENCES app_registry(app_id),
    name        TEXT NOT NULL,
    type        TEXT NOT NULL
        CHECK (type IN ('plan', 'credit_pack', 'addon', 'seat')),
    sku         TEXT NOT NULL,
    price       NUMERIC(12, 2) NOT NULL DEFAULT 0,
    currency    TEXT NOT NULL DEFAULT 'BRL',
    features    JSONB NOT NULL DEFAULT '[]'::jsonb,
    meta_json   JSONB NOT NULL DEFAULT '{}'::jsonb,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_catalog_plans_app_sku UNIQUE (app_id, sku)
);

CREATE INDEX IF NOT EXISTS idx_catalog_plans_app_id
    ON catalog_plans (app_id);

CREATE INDEX IF NOT EXISTS idx_catalog_plans_active
    ON catalog_plans (active)
    WHERE active = TRUE;

COMMENT ON TABLE catalog_plans IS
    'Planos e pacotes de créditos da vitrine multi-app (gestão admin Hub).';
