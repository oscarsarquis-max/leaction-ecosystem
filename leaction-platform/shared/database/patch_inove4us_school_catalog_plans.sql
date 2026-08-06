-- Action Hub — catálogo comercial B2B inove4us-school (licenças de professor).
-- Idempotente.
--
-- Aplicar (DB local do Hub):
--   psql -h 127.0.0.1 -p 5434 -U admin -d leaction_hub -v ON_ERROR_STOP=1 \
--     -f shared/database/patch_inove4us_school_catalog_plans.sql
--
-- Pré-requisito: app_registry com app_id = 'inove4us-school'
--   (patch_inove4us_school_app_registry.sql)

BEGIN;

-- Garante o satélite (no-op se já existir)
INSERT INTO app_registry (
    app_id, name, webhook_url, webhook_secret, return_origins, active
)
VALUES (
    'inove4us-school',
    'Inove4us School (B2B)',
    'http://localhost:5012/api/webhooks/actionhub',
    'sk_test_school_webhook_secret_999',
    ARRAY['http://localhost:5175', 'http://127.0.0.1:5175']::TEXT[],
    TRUE
)
ON CONFLICT (app_id) DO UPDATE SET
    name = EXCLUDED.name,
    active = TRUE,
    return_origins = EXCLUDED.return_origins;

-- Escola Inicial — 50 licenças de professor
INSERT INTO catalog_plans (
    app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
    'inove4us-school',
    'Escola Inicial',
    'seat',
    'school-starter-50',
    297.00,
    'BRL',
    '[
      "50 licenças de professor",
      "Torre de Controle institucional",
      "Espelho pedagógico e curadoria",
      "Suporte padrão"
    ]'::jsonb,
    '{
      "licenses_granted": 50,
      "seats": 50,
      "display_order": 10,
      "recommended": false,
      "entitlements": {"licenses_granted": 50, "seats": 50},
      "direitos": {"licenses_granted": 50, "seats": 50}
    }'::jsonb,
    TRUE
)
ON CONFLICT (app_id, sku) DO UPDATE SET
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    features = EXCLUDED.features,
    meta_json = EXCLUDED.meta_json,
    active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- Escola Crescimento — 100 licenças de professor
INSERT INTO catalog_plans (
    app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
    'inove4us-school',
    'Escola Crescimento',
    'seat',
    'school-growth-100',
    497.00,
    'BRL',
    '[
      "100 licenças de professor",
      "Torre de Controle institucional",
      "Espelho pedagógico e curadoria",
      "Prioridade de suporte"
    ]'::jsonb,
    '{
      "licenses_granted": 100,
      "seats": 100,
      "display_order": 20,
      "recommended": true,
      "entitlements": {"licenses_granted": 100, "seats": 100},
      "direitos": {"licenses_granted": 100, "seats": 100}
    }'::jsonb,
    TRUE
)
ON CONFLICT (app_id, sku) DO UPDATE SET
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    features = EXCLUDED.features,
    meta_json = EXCLUDED.meta_json,
    active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Verificação:
-- SELECT sku, name, type, price, meta_json->>'licenses_granted' AS licenses
-- FROM catalog_plans
-- WHERE app_id = 'inove4us-school' AND active = TRUE
-- ORDER BY (meta_json->>'display_order')::int;
