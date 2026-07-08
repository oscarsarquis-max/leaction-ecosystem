-- Vitrine PanelDX — cache do gateway (GET /hub-api/v1/vitrine/paneldx)
-- Base alinhada ao gateway-api; colunas version/is_active do seed solicitado.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS paneldx_vitrine_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    version VARCHAR(50) DEFAULT 'v1',
    payload JSONB NOT NULL,
    planos_count INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'paneldx',
    is_active BOOLEAN DEFAULT TRUE,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE paneldx_vitrine_snapshots
    ADD COLUMN IF NOT EXISTS version VARCHAR(50) DEFAULT 'v1';

ALTER TABLE paneldx_vitrine_snapshots
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

ALTER TABLE paneldx_vitrine_snapshots
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_paneldx_vitrine_snapshots_received
    ON paneldx_vitrine_snapshots (received_at DESC);

INSERT INTO paneldx_vitrine_snapshots (sync_id, version, payload, planos_count, is_active, source)
SELECT
    uuid_generate_v4(),
    'v1',
    '{
      "plans": [
        {
          "sku": "PANEL_MATURIDADE",
          "name": "Diagnóstico de Maturidade DX",
          "price": 1.00,
          "currency": "BRL",
          "description": "Assessment completo com IA",
          "features": ["Relatório Executivo", "Análise de Gaps", "Plano de Ação"]
        }
      ],
      "planos": [
        {
          "id": 1,
          "nome": "Diagnóstico de Maturidade DX",
          "valor_mensal": 1.00,
          "periodicidade": "Único",
          "descricao_beneficios": ["Relatório Executivo", "Análise de Gaps", "Plano de Ação"],
          "ativo": true,
          "tipo_plano": "assessment",
          "sku": "PANEL_MATURIDADE"
        }
      ],
      "addons": []
    }'::jsonb,
    1,
    TRUE,
    'seed'
WHERE NOT EXISTS (SELECT 1 FROM paneldx_vitrine_snapshots LIMIT 1);
