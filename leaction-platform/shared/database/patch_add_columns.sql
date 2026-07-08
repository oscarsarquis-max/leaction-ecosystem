-- Execute manualmente em bases já criadas antes desta alteração (ex.: psql -f patch_add_columns.sql).
ALTER TABLE users ADD COLUMN IF NOT EXISTS document_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS company TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS state TEXT;

ALTER TABLE orders ADD COLUMN IF NOT EXISTS external_resource_id TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_url TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway_ref TEXT;
