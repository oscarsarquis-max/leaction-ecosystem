-- P1-Pay: recebedores (seller OAuth + cobranças). Aditivo. Sem orders / webhook_outbox.
-- psql "$DATABASE_URL" -f shared/database/patch_seller_payments.sql

CREATE TABLE IF NOT EXISTS seller_accounts (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  app_id text NOT NULL,
  seller_ref text NOT NULL,
  mp_user_id bigint,
  mp_nickname text,
  access_token_enc text NOT NULL,
  refresh_token_enc text NOT NULL,
  public_key text NOT NULL,
  expires_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('connected', 'revoked', 'error')),
  last_error text,
  connected_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (app_id, seller_ref)
);

CREATE TABLE IF NOT EXISTS seller_charges (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  app_id text NOT NULL,
  seller_ref text NOT NULL,
  seller_account_id uuid NOT NULL REFERENCES seller_accounts (id),
  idempotency_key text NOT NULL,
  external_reference text NOT NULL,
  description text NOT NULL,
  payer_email text NOT NULL,
  amount_cents integer NOT NULL CHECK (amount_cents > 0),
  currency text NOT NULL DEFAULT 'BRL',
  method text CHECK (method IS NULL OR method IN ('pix', 'card')),
  mp_payment_id text,
  status text NOT NULL CHECK (
    status IN ('PENDING', 'PAID', 'REJECTED', 'CANCELLED', 'EXPIRED', 'REFUNDED')
  ),
  mp_status text,
  mp_status_detail text,
  pix_qr_code text,
  pix_qr_code_base64 text,
  pix_ticket_url text,
  pix_expires_at timestamptz,
  paid_amount_cents integer,
  refunded_amount_cents integer,
  paid_at timestamptz,
  return_to text,
  last_observed_at timestamptz,
  mismatch_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (app_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_seller_charges_mp_payment_id
  ON seller_charges (mp_payment_id)
  WHERE mp_payment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_seller_charges_account
  ON seller_charges (seller_account_id);
