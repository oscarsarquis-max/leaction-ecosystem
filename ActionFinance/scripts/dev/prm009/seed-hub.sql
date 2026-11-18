CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    external_resource_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    product_id UUID REFERENCES products(id),
    gateway_reference TEXT UNIQUE,
    gateway_ref TEXT UNIQUE,
    payment_url TEXT,
    external_resource_id TEXT,
    status TEXT DEFAULT 'PENDING',
    payment_status TEXT,
    paid_at TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (id, email, full_name)
VALUES ('10000000-0000-4000-8000-000000000001', 'prm009.teste@example.test', 'Cliente de teste PRM009')
ON CONFLICT (id) DO NOTHING;

INSERT INTO products (id, sku, name, type, external_resource_id)
VALUES ('10000000-0000-4000-8000-000000000002', 'PRM009_TEST', 'Produto de teste PRM009', 'TEST_ORDER', 'test')
ON CONFLICT (id) DO NOTHING;

-- 26 cobranças homolog-padaria + 2 de outra empresa. Todas rotuladas teste.
-- 001 e 002: valor cobrado vs pago; 003 ausente; 005/006 mesmo timestamp.
INSERT INTO orders (id, user_id, product_id, gateway_reference, gateway_ref, external_resource_id, status, created_at, updated_at)
VALUES
('20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-001', 'hub:homolog-padaria:001',
 '{"app_id":"homolog-padaria","sandbox":true,"test_order":true,"amount_cents":12550,"currency":"BRL"}',
 'PAID', '2026-01-01 10:00:00+00', '2026-01-01 10:00:01+00'),
('20000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-002', 'hub:homolog-padaria:002',
 '{"app_id":"homolog-padaria","sandbox":true,"test_order":true,"amount_cents":15000,"paid_amount_cents":14000,"currency":"BRL"}',
 'PAID', '2026-01-01 10:00:00+00', '2026-01-01 10:00:02+00'),
('20000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-003', 'hub:homolog-padaria:003',
 '{"app_id":"homolog-padaria","sandbox":true,"test_order":true"}',
 'PENDING', '2026-01-01 10:00:00+00', '2026-01-01 10:00:03+00'),
('20000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-004', 'hub:homolog-padaria:004',
 '{"app_id":"homolog-padaria","sandbox":true,"test_order":true,"valor_negociado":99.90}',
 'PAID', '2026-01-01 10:00:00+00', '2026-01-01 10:00:04+00'),
('20000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-005', 'hub:homolog-padaria:005',
 '{"app_id":"homolog-padaria","sandbox":true,"test_order":true,"amount_cents":8000,"currency":"BRL"}',
 'REFUNDED', '2026-01-01 12:00:00+00', '2026-01-01 12:00:00+00'),
('20000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-006', 'hub:homolog-padaria:006',
 '{"app_id":"homolog-padaria","sandbox":true,"test_order":true,"amount_cents":5000,"currency":"BRL"}',
 'PENDING', '2026-01-01 12:00:00+00', '2026-01-01 12:00:00+00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO orders (id, user_id, product_id, gateway_reference, gateway_ref, external_resource_id, status, created_at, updated_at)
SELECT
  ('20000000-0000-4000-8000-00000000' || lpad(n::text, 4, '0'))::uuid,
  '10000000-0000-4000-8000-000000000001',
  '10000000-0000-4000-8000-000000000002',
  'proc-' || lpad(n::text, 3, '0'),
  'hub:homolog-padaria:' || lpad(n::text, 3, '0'),
  json_build_object(
    'app_id', 'homolog-padaria',
    'sandbox', true,
    'test_order', true,
    'amount_cents', 1000 + n,
    'currency', 'BRL'
  )::text,
  CASE WHEN n = 26 THEN 'CANCELLED' ELSE 'PAID' END,
  timestamptz '2026-01-02 00:00:00+00' + (n || ' minutes')::interval,
  timestamptz '2026-01-02 00:00:00+00' + (n || ' minutes')::interval
FROM generate_series(7, 26) AS n
ON CONFLICT (id) DO NOTHING;

INSERT INTO orders (id, user_id, product_id, gateway_reference, gateway_ref, external_resource_id, status, created_at, updated_at)
VALUES
('30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-other-1', 'hub:outra-empresa:001',
 '{"app_id":"outra-empresa","sandbox":true,"test_order":true,"amount_cents":99999,"currency":"BRL"}',
 'PAID', '2026-01-01 09:00:00+00', '2026-01-01 09:00:00+00'),
('30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000002',
 'proc-other-2', 'hub:outra-empresa:002',
 '{"app_id":"outra-empresa","sandbox":true,"test_order":true,"amount_cents":88888,"currency":"BRL"}',
 'PAID', '2026-01-01 09:01:00+00', '2026-01-01 09:01:00+00')
ON CONFLICT (id) DO NOTHING;
