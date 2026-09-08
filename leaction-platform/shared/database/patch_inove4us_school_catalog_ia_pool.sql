-- Prompt 98: plano institucional inclui pool de IA por professor (50).
-- Idempotente. Aplicar no DB do Hub (catalog_plans).

BEGIN;

UPDATE catalog_plans
SET
  features = '[
    "50 licenças de professor",
    "50 créditos de IA por professor incluso na licença",
    "Torre de Controle institucional",
    "Espelho pedagógico e curadoria",
    "Suporte padrão"
  ]'::jsonb,
  meta_json = COALESCE(meta_json, '{}'::jsonb) || '{
    "ia_credits_per_teacher": 50,
    "entitlements": {"licenses_granted": 50, "seats": 50, "ia_credits_per_teacher": 50},
    "direitos": {"licenses_granted": 50, "seats": 50, "ia_credits_per_teacher": 50}
  }'::jsonb,
  updated_at = CURRENT_TIMESTAMP
WHERE app_id = 'inove4us-school'
  AND sku = 'school-starter-50';

UPDATE catalog_plans
SET
  features = '[
    "100 licenças de professor",
    "50 créditos de IA por professor incluso na licença",
    "Torre de Controle institucional",
    "Espelho pedagógico e curadoria",
    "Prioridade de suporte"
  ]'::jsonb,
  meta_json = COALESCE(meta_json, '{}'::jsonb) || '{
    "ia_credits_per_teacher": 50,
    "entitlements": {"licenses_granted": 100, "seats": 100, "ia_credits_per_teacher": 50},
    "direitos": {"licenses_granted": 100, "seats": 100, "ia_credits_per_teacher": 50}
  }'::jsonb,
  updated_at = CURRENT_TIMESTAMP
WHERE app_id = 'inove4us-school'
  AND sku = 'school-growth-100';

COMMIT;
