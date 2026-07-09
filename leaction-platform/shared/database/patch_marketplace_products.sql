-- Catálogo persistido da vitrine ActionHub (match SQL por overlap de tags).
-- Ofertas live ML/Amazon continuam nas prateleiras genéricas; recomendações
-- contextuais usam esta tabela para performance e estabilidade.

BEGIN;

CREATE TABLE IF NOT EXISTS marketplace_products (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    price           NUMERIC(12, 2),
    currency        TEXT NOT NULL DEFAULT 'BRL',
    price_label     TEXT,
    image           TEXT,
    link            TEXT NOT NULL,
    vendor          TEXT NOT NULL DEFAULT 'catalog',
    category        TEXT,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketplace_products_tags_gin
    ON marketplace_products USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_marketplace_products_active
    ON marketplace_products (active)
    WHERE active = TRUE;

COMMENT ON TABLE marketplace_products IS
    'Catálogo curado da vitrine — tags persistidas para match SQL com sprints PanelDX.';

COMMENT ON COLUMN marketplace_products.tags IS
    'Tags alinhadas às sprints (formacao, equipamentos, software, …).';

COMMIT;
