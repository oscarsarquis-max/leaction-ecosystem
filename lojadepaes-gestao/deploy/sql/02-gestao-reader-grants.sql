-- GESTAO-002 — GRANTs do gestao_reader no banco "lojadepaes".
-- Só GRANT SELECT. Sem ALTER DEFAULT PRIVILEGES, sem pg_read_all_data, sem schema inteiro.
-- Sem colunas pessoais: nada de customer_*, delivery_*, customer_note, access_token_hash,
-- identity_subject_id, crm_id_sessao, submit_idempotency_key, fidelity_*.
-- Rodar como superusuário, conectado ao banco "lojadepaes".

\set ON_ERROR_STOP on

GRANT USAGE ON SCHEMA public TO gestao_reader;

-- orders: apenas colunas não pessoais
GRANT SELECT (
  id, public_reference, status, fulfillment_modality, production_batch_id,
  production_local_date, requested_date, proposed_production_date,
  holds_capacity, order_kind, currency,
  subtotal_cents, delivery_fee_cents, discount_cents, total_cents,
  confirmed_at, cancelled_at, production_started_at, ready_at,
  completed_at, fulfilled_at, delivery_confirmed_at, created_at, updated_at
) ON orders TO gestao_reader;

-- payment_records: sem pix_*, mp_payment_id, external_*, idempotency_key
GRANT SELECT (
  id, order_id, financial_status, expected_cents, amount_paid_cents,
  amount_refunded_cents, currency, confirmed_at
) ON payment_records TO gestao_reader;

-- schedule_closures: sem internal_reason, public_notice, created_by, updated_by
GRANT SELECT (
  id, start_date, end_date, first_eligible_date, pause_intake, cancelled_at
) ON schedule_closures TO gestao_reader;

-- managerial_exclusions: só o identificador do pedido (subject_id) e o que o qualifica.
-- Sem reason, author_ref, reverse_reason nem reversed_by.
GRANT SELECT (subject_type, subject_id, reversed_at) ON managerial_exclusions TO gestao_reader;

-- Tabelas sem dado pessoal: SELECT inteiro
GRANT SELECT ON TABLE
  order_items, order_item_ingredients,
  products, product_variants, product_ingredients,
  dough_types, ingredients, bread_shapes, recipe_bases,
  schedule_settings, schedule_week_overrides, schedule_date_overrides,
  schedule_eligible_bases,
  production_batches, production_batch_dough_limits,
  alembic_version
TO gestao_reader;
