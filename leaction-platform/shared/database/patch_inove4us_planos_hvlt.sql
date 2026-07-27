-- Planos inove4us — High-Volume / Low-Ticket (comunidade)
-- Starter (freemium no app) | Profissional R$24,90 | Mentor R$49,90 | Pack 3 R$14,90
-- meta_json em PT: nivel, creditos, assinatura (direitos)
-- Idempotente.

BEGIN;

-- Desativa catálogo anterior (smoke / penny test / pacotes legados)
UPDATE catalog_plans
SET active = FALSE, updated_at = CURRENT_TIMESTAMP
WHERE app_id = 'inove4us'
  AND sku IN (
    'INOVE4US_CREDITS_10',
    'INOVE4US_CREDITS_50',
    'INOVE4US_SUB_30',
    'GOLIVE_CREDITS_50_20260718083518'
  )
  OR (
    app_id = 'inove4us'
    AND (
      sku ILIKE 'SMOKE_%'
      OR sku ILIKE '%smoke%'
      OR sku ILIKE 'GOLIVE_%'
    )
  );

-- 1) Profissional mensal — sweet spot
INSERT INTO catalog_plans (
  app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
  'inove4us',
  'Profissional',
  'plan',
  'INOVE4US_PRO_M',
  24.90,
  'BRL',
  '[
    "Aulas simples ilimitadas no Dia a Dia",
    "Até 5 desafios ativos",
    "Agenda e mapa de planejamento",
    "Importação da sua planilha de aulas",
    "Menos de um real por dia"
  ]'::jsonb,
  '{
    "creditos": 5,
    "meses": 1,
    "periodicidade": "mensal",
    "ordem_exibicao": 20,
    "recomendado": true,
    "direitos": {
      "nivel": "profissional",
      "creditos": 5,
      "aulas_simples": -1,
      "desafios_ativos": 5,
      "assinatura": true
    }
  }'::jsonb,
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

-- 2) Mentor / GoLive mensal
INSERT INTO catalog_plans (
  app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
  'inove4us',
  'Mentor',
  'plan',
  'INOVE4US_MENTOR_M',
  49.90,
  'BRL',
  '[
    "Aulas simples ilimitadas",
    "Desafios ilimitados",
    "Ideal para coordenadores e uso intensivo",
    "Tudo do plano Profissional",
    "Atendimento com prioridade"
  ]'::jsonb,
  '{
    "creditos": 100,
    "meses": 1,
    "periodicidade": "mensal",
    "ordem_exibicao": 30,
    "recomendado": false,
    "direitos": {
      "nivel": "mentor",
      "creditos": 100,
      "aulas_simples": -1,
      "desafios_ativos": -1,
      "assinatura": true
    }
  }'::jsonb,
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

-- 3) Pacote avulso — 3 desafios (upsell freemium sem assinatura)
INSERT INTO catalog_plans (
  app_id, name, type, sku, price, currency, features, meta_json, active
)
VALUES (
  'inove4us',
  'Pacote 3 Desafios',
  'credit_pack',
  'INOVE4US_PACK_3',
  14.90,
  'BRL',
  '[
    "3 desafios extras",
    "Sem assinatura mensal",
    "Ideal para um projeto pontual",
    "Os desafios ficam disponíveis na sua conta"
  ]'::jsonb,
  '{
    "creditos": 3,
    "ordem_exibicao": 10,
    "recomendado": false,
    "direitos": {
      "creditos": 3
    }
  }'::jsonb,
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

-- Remove planos inativos (anuais e legado)
DELETE FROM catalog_plans
 WHERE app_id = 'inove4us'
   AND active = FALSE;

COMMIT;
