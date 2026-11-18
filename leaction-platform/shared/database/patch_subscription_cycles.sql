-- Ciclos de assinatura do catálogo (pagamento confirmado ≠ autorização).
-- Execute: psql $DATABASE_URL -f patch_subscription_cycles.sql

CREATE TABLE IF NOT EXISTS subscription_cycles (
  payment_id TEXT PRIMARY KEY,
  preapproval_id TEXT,
  order_id UUID,
  kind TEXT NOT NULL,
  granted BOOLEAN NOT NULL DEFAULT FALSE,
  payload_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscription_cycles_preapproval
  ON subscription_cycles (preapproval_id);
