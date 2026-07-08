-- Assinaturas recorrentes Mercado Pago (preapproval)
-- Execute: psql $DATABASE_URL -f patch_subscriptions.sql

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    mp_preapproval_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    amount NUMERIC(10, 2) NOT NULL DEFAULT 99.00,
    currency_id TEXT NOT NULL DEFAULT 'BRL',
    frequency INTEGER NOT NULL DEFAULT 1,
    frequency_type TEXT NOT NULL DEFAULT 'months',
    reason TEXT,
    payer_email TEXT NOT NULL,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_order_id ON subscriptions(order_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_mp_id ON subscriptions(mp_preapproval_id);
