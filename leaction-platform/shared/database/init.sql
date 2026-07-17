-- Extensão para gerar IDs únicos (UUID)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. TABELA DE UTILIZADORES CENTRALIZADA
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT, -- scrypt$salt$hash — login ActionHub
    document_id TEXT,
    phone TEXT,
    company TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    moodle_user_id INTEGER, -- ID do aluno no Moodle (preenchido após a primeira matrícula)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABELA DE PRODUTOS (Cursos vs Assessments)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku TEXT UNIQUE NOT NULL, -- Código identificador (ex: CURSO_GESTAO_01)
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'MOODLE_COURSE' ou 'PANELDX_ASSESSMENT'
    external_resource_id TEXT NOT NULL -- ID do Curso no Moodle ou ID do Modelo no PanelDX
);

-- 3. TABELA DE VENDAS / TRANSAÇÕES
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    product_id UUID REFERENCES products(id),
    gateway_reference TEXT UNIQUE, -- ID da transação no Asaas/Stripe
    gateway_ref TEXT UNIQUE, -- Referência interna hub:client:order
    payment_url TEXT, -- Callback webhook do originador (PanelDX)
    external_resource_id TEXT, -- id_matu PanelDX ou recurso externo do pedido
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'PAID', 'REFUNDED'
    payment_status TEXT,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. ASSINATURAS RECORRENTES (Mercado Pago preapproval)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    mp_preapproval_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    amount NUMERIC(10, 2) NOT NULL DEFAULT 99.00,
    currency_id TEXT NOT NULL DEFAULT 'BRL',
    frequency INTEGER NOT NULL DEFAULT 1,
    frequency_type TEXT NOT NULL DEFAULT 'months',
    reason TEXT,
    payer_email TEXT NOT NULL,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserindo um Curso da Academy (Moodle)
INSERT INTO products (sku, name, type, external_resource_id) 
VALUES ('CURSO_LIDERANCA', 'Liderança Eficaz Academy', 'MOODLE_COURSE', '2');

-- Inserindo um Assessment do Sistema (PanelDX)
INSERT INTO products (sku, name, type, external_resource_id) 
VALUES ('PANEL_MATURIDADE', 'Diagnóstico de Maturidade DX', 'PANELDX_ASSESSMENT', 'DX_MOD_101');

-- 5. SERVIÇO DE CONTRATOS (Fase 1) — ver também patch_contracts_service.sql
CREATE TABLE IF NOT EXISTS app_registry (
    app_id          TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    webhook_url     TEXT,
    webhook_secret  TEXT,
    return_origins  TEXT[] NOT NULL DEFAULT '{}',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contracts (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id           TEXT NOT NULL REFERENCES app_registry(app_id),
    subject_type     TEXT NOT NULL,
    subject_id       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN (
            'draft', 'pending_payment', 'active', 'past_due', 'canceled', 'expired'
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

CREATE TABLE IF NOT EXISTS entitlement_snapshots (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id        TEXT NOT NULL REFERENCES app_registry(app_id),
    subject_id    TEXT NOT NULL,
    payload_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_until   TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_entitlement_snapshots_app_subject UNIQUE (app_id, subject_id)
);

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

-- webhook_url local do inove4us; em PRODUÇÃO usar env (APP_WEBHOOK_URL_INOVE4US) / admin.
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

-- 6. CATÁLOGO / VITRINE multi-app (painel admin) — ver patch_hub_catalog_plans.sql
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