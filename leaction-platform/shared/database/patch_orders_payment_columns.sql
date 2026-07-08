-- Colunas de pagamento alinhadas ao init.sql / payment-fulfillment
ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_reference TEXT;
