-- Senha do LeActioner (ActionHub). Execute em bases já existentes:
--   psql "$DATABASE_URL" -f shared/database/patch_users_password.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
