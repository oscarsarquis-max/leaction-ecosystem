-- Integração operacional inove4us no Action Hub:
-- 1) webhook local na porta correta do Flask (5010)
-- 2) planos de crédito/assinatura canônicos no Construtor de Planos
-- Idempotente.

BEGIN;

-- Webhook S2S → inove4us (produção; override local via APP_WEBHOOK_URL_INOVE4US)
UPDATE app_registry
SET
  webhook_url = 'https://inove4us.com.br/api/webhooks/actionhub',
  return_origins = ARRAY[
    'https://inove4us.com.br',
    'http://localhost:5174'
  ]::TEXT[],
  active = TRUE,
  name = 'inove4us'
WHERE app_id = 'inove4us';

-- Desativa SKUs de smoke / legado de teste
UPDATE catalog_plans
SET active = FALSE, updated_at = CURRENT_TIMESTAMP
WHERE app_id = 'inove4us'
  AND (
    sku ILIKE 'SMOKE_%'
    OR sku ILIKE '%smoke%'
  );

-- Pacote de créditos (compra avulsa) — 10 desafios
INSERT INTO catalog_plans (
  app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
  'inove4us',
  'Pacote 10 desafios',
  'credit_pack',
  'INOVE4US_CREDITS_10',
  1.00,
  'BRL',
  '["10 créditos de IA", "Estruturação de desafios", "Elaboração de planos"]'::jsonb,
  '{"credits": 10, "entitlements": {"credits": 10}}'::jsonb,
  TRUE
)
ON CONFLICT (app_id, sku) DO UPDATE
SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  price = EXCLUDED.price,
  features = EXCLUDED.features,
  meta_json = EXCLUDED.meta_json,
  active = TRUE,
  updated_at = CURRENT_TIMESTAMP;

-- Pacote Go Live — 50 desafios
INSERT INTO catalog_plans (
  app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
  'inove4us',
  'Pacote GoLive 50',
  'credit_pack',
  'INOVE4US_CREDITS_50',
  3.00,
  'BRL',
  '["50 créditos de IA", "Uso intensivo na Mesa do Inovador", "Prioridade de suporte"]'::jsonb,
  '{"credits": 50, "entitlements": {"credits": 50}}'::jsonb,
  TRUE
)
ON CONFLICT (app_id, sku) DO UPDATE
SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  price = EXCLUDED.price,
  features = EXCLUDED.features,
  meta_json = EXCLUDED.meta_json,
  active = TRUE,
  updated_at = CURRENT_TIMESTAMP;

-- Assinatura mensal (recorrente) — 30 créditos/mês
INSERT INTO catalog_plans (
  app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
  'inove4us',
  'Assinatura Mensal 30',
  'plan',
  'INOVE4US_SUB_30',
  2.00,
  'BRL',
  '["30 créditos de IA por mês", "Renovação automática", "Ideal para uso contínuo"]'::jsonb,
  '{"credits": 30, "entitlements": {"credits": 30, "subscription": true}}'::jsonb,
  TRUE
)
ON CONFLICT (app_id, sku) DO UPDATE
SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  price = EXCLUDED.price,
  features = EXCLUDED.features,
  meta_json = EXCLUDED.meta_json,
  active = TRUE,
  updated_at = CURRENT_TIMESTAMP;

-- Mantém GoLive legado ativo mapeado (billing alias golive-50)
UPDATE catalog_plans
SET
  active = TRUE,
  meta_json = COALESCE(meta_json, '{}'::jsonb) || '{"credits": 50, "entitlements": {"credits": 50}}'::jsonb,
  updated_at = CURRENT_TIMESTAMP
WHERE app_id = 'inove4us'
  AND sku = 'GOLIVE_CREDITS_50_20260718083518';

COMMIT;
