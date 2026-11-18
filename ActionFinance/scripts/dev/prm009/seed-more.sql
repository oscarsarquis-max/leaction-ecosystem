INSERT INTO orders (id, user_id, product_id, gateway_reference, gateway_ref, external_resource_id, status, created_at, updated_at)
SELECT
  ('20000000-0000-4000-8000-00000001' || lpad(n::text, 4, '0'))::uuid,
  '10000000-0000-4000-8000-000000000001',
  '10000000-0000-4000-8000-000000000002',
  'proc-page-' || lpad(n::text, 3, '0'),
  'hub:homolog-padaria:p' || lpad(n::text, 3, '0'),
  json_build_object(
    'app_id', 'homolog-padaria',
    'sandbox', true,
    'test_order', true,
    'amount_cents', 2000 + n,
    'currency', 'BRL'
  )::text,
  'PAID',
  now() + (n || ' seconds')::interval,
  now() + (n || ' seconds')::interval
FROM generate_series(1, 30) AS n
ON CONFLICT (id) DO NOTHING;
