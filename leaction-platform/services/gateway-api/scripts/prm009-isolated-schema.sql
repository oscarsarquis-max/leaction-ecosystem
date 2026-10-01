-- PRM_009 — schema isolado no Postgres já existente do Hub.
-- Não cria instância, ALB, Cognito nem recurso AWS.
-- Não executar até autorização de apply. Não versiona dados pessoais.
-- Consumidores de public.orders (fulfillment, MP webhook, outbox, admin/payments,
-- catalog-public, amount-checkout) não leem esta relação.

CREATE SCHEMA IF NOT EXISTS prm009_public_test;

CREATE TABLE IF NOT EXISTS prm009_public_test.orders (
    id uuid PRIMARY KEY,
    status text NOT NULL,
    gateway_ref text,
    gateway_reference text,
    external_resource_id text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

COMMENT ON SCHEMA prm009_public_test IS 'PRM_009 public-test receipts. Not public.orders.';
COMMENT ON TABLE prm009_public_test.orders IS 'Lookup-only rows. No webhook_url, user_id, product_id or fulfillment columns.';

INSERT INTO prm009_public_test.orders (
    id, status, gateway_ref, gateway_reference, external_resource_id, created_at, updated_at
) VALUES
    (
        '9c2e0a10-4f11-4b8a-9c2e-0a104f110101',
        'PAID',
        'hub:af-public-test-padaria:001',
        'prm009-synthetic-001',
        '{"app_id":"af-public-test-padaria","amount_cents":12550,"currency":"BRL"}',
        TIMESTAMPTZ '2026-10-01 15:00:00+00',
        TIMESTAMPTZ '2026-10-01 15:00:01+00'
    ),
    (
        '9c2e0a10-4f11-4b8a-9c2e-0a104f110102',
        'PENDING',
        'hub:af-public-test-padaria:002',
        'prm009-synthetic-002',
        '{"app_id":"af-public-test-padaria","amount_cents":8000,"currency":"BRL"}',
        TIMESTAMPTZ '2026-10-01 15:00:02+00',
        TIMESTAMPTZ '2026-10-01 15:00:03+00'
    ),
    (
        '9c2e0a10-4f11-4b8a-9c2e-0a104f110103',
        'REFUNDED',
        'hub:af-public-test-padaria:003',
        'prm009-synthetic-003',
        '{"app_id":"af-public-test-padaria","amount_cents":4100,"currency":"BRL"}',
        TIMESTAMPTZ '2026-10-01 15:00:04+00',
        TIMESTAMPTZ '2026-10-01 15:00:05+00'
    ),
    (
        '9c2e0a10-4f11-4b8a-9c2e-0a104f110104',
        'PAID',
        'hub:af-public-test-padaria:004',
        NULL,
        '{"app_id":"af-public-test-padaria"}',
        TIMESTAMPTZ '2026-10-01 15:00:06+00',
        TIMESTAMPTZ '2026-10-01 15:00:07+00'
    )
ON CONFLICT (id) DO NOTHING;
