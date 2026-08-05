-- Apply on existing volumes (init.sql runs only on first boot)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tb_product_routes (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_code    varchar(100) NOT NULL,
  name            varchar(200) NOT NULL,
  description     varchar(1000) NOT NULL DEFAULT '',
  enabled         boolean NOT NULL DEFAULT true,
  definition_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  version         integer NOT NULL DEFAULT 1,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_tb_product_routes_code_version UNIQUE (product_code, version)
);

CREATE INDEX IF NOT EXISTS ix_tb_product_routes_code
  ON tb_product_routes (product_code)
  WHERE enabled;

CREATE TABLE IF NOT EXISTS tb_audit_trace (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id    uuid NOT NULL,
  product_code      varchar(100) NOT NULL,
  idempotency_key   varchar(200),
  status            varchar(40) NOT NULL DEFAULT 'started',
  started_at        timestamptz NOT NULL DEFAULT now(),
  finished_at       timestamptz,
  error_summary     varchar(2000),
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_tb_audit_trace_correlation
  ON tb_audit_trace (correlation_id);

CREATE INDEX IF NOT EXISTS ix_tb_audit_trace_started
  ON tb_audit_trace (started_at DESC);

INSERT INTO tb_product_routes (product_code, name, description, definition_json)
SELECT
  'CONTA_DIGITAL_ONBOARDING',
  'Onboarding Conta Digital',
  'Cadastro + análise de crédito (mock local)',
  '{"steps":[{"name":"consultar_cadastro","system":"cadastro","mode":"sync"},{"name":"analisar_credito","system":"credito","mode":"sync"}]}'::jsonb
WHERE NOT EXISTS (
  SELECT 1 FROM tb_product_routes
  WHERE product_code = 'CONTA_DIGITAL_ONBOARDING' AND version = 1
);
