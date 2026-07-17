-- Serviço de Contratos (Fase 1) — Action Hub
-- Apps satélites, contratos, itens, snapshots de entitlement e outbox de webhooks.
--
-- Aplicar em bases existentes:
--   psql "$DATABASE_URL" -f shared/database/patch_contracts_service.sql
--   (ou via scripts/deploy/remote-db-migrate.sh — inclui patch_*.sql)
--
-- Requer: uuid-ossp, tabelas users/orders/subscriptions (init + patches anteriores).

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Registro de aplicativos satélites (PanelDX, inove4us, …)
CREATE TABLE IF NOT EXISTS app_registry (
    app_id          TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    webhook_url     TEXT,
    webhook_secret  TEXT,
    return_origins  TEXT[] NOT NULL DEFAULT '{}',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Contratos comerciais (fonte da verdade no Hub)
CREATE TABLE IF NOT EXISTS contracts (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id           TEXT NOT NULL REFERENCES app_registry(app_id),
    subject_type     TEXT NOT NULL,
    subject_id       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN (
            'draft',
            'pending_payment',
            'active',
            'past_due',
            'canceled',
            'expired'
        )),
    started_at       TIMESTAMP,
    ends_at          TIMESTAMP,
    canceled_at      TIMESTAMP,
    order_id         UUID REFERENCES orders(id) ON DELETE SET NULL,
    subscription_id  UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    external_ref     TEXT,
    meta_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contracts_app_subject
    ON contracts (app_id, subject_type, subject_id);

CREATE INDEX IF NOT EXISTS idx_contracts_status
    ON contracts (status);

CREATE INDEX IF NOT EXISTS idx_contracts_order_id
    ON contracts (order_id);

CREATE INDEX IF NOT EXISTS idx_contracts_subscription_id
    ON contracts (subscription_id);

-- 3. Itens do contrato (plano, addon, pacote de créditos, seats)
CREATE TABLE IF NOT EXISTS contract_items (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id   UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    item_type     TEXT NOT NULL
        CHECK (item_type IN ('plan', 'addon', 'credit_pack', 'seat')),
    sku           TEXT NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_label    TEXT,
    meta_json     JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_contract_items_contract_id
    ON contract_items (contract_id);

CREATE INDEX IF NOT EXISTS idx_contract_items_sku
    ON contract_items (sku);

-- 4. Projeção cacheável de direitos (consulta rápida pelas apps)
CREATE TABLE IF NOT EXISTS entitlement_snapshots (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id        TEXT NOT NULL REFERENCES app_registry(app_id),
    subject_id    TEXT NOT NULL,
    payload_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_until   TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_entitlement_snapshots_app_subject UNIQUE (app_id, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_entitlement_snapshots_valid_until
    ON entitlement_snapshots (valid_until);

-- 5. Outbox de webhooks (entrega confiável / idempotente para apps)
CREATE TABLE IF NOT EXISTS webhook_outbox (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id            TEXT NOT NULL REFERENCES app_registry(app_id),
    event_type        TEXT NOT NULL,
    payload_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key   TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'delivered', 'failed')),
    attempts          INTEGER NOT NULL DEFAULT 0,
    next_retry_at     TIMESTAMP,
    last_error        TEXT,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_webhook_outbox_idempotency UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_webhook_outbox_dispatch
    ON webhook_outbox (status, next_retry_at)
    WHERE status IN ('pending', 'failed');

CREATE INDEX IF NOT EXISTS idx_webhook_outbox_app_id
    ON webhook_outbox (app_id);

-- Seeds mínimos (apps conhecidas; secret via generate-app-secrets.js)
-- webhook_url local do inove4us: em PRODUÇÃO sobrescrever via env
--   (ex.: APP_WEBHOOK_URL_INOVE4US / painel admin) — não versionar URL de prod no seed.
INSERT INTO app_registry (app_id, name, webhook_url, webhook_secret, return_origins, active)
VALUES
    (
        'paneldx',
        'PanelDX',
        NULL,
        NULL,
        ARRAY['https://paneldx.com.br', 'http://localhost:3000']::TEXT[],
        TRUE
    ),
    (
        'inove4us',
        'inove4us',
        'http://localhost:5000/api/webhooks/actionhub',
        NULL,
        ARRAY['https://inove4us.com.br', 'http://localhost:5174']::TEXT[],
        TRUE
    )
ON CONFLICT (app_id) DO NOTHING;
