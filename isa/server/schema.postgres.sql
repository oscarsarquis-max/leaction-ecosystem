-- Alvo PostgreSQL da ISA, versão de esquema 3.
-- O processo de produção aplica estas tabelas em connect() e grava em ISA_DATABASE_URL.
-- Não abre isa.sqlite. Não foi aplicado no RDS. Banco próprio e papel próprio.
-- Não usar o database actionfinance nem a credencial do Finance.

CREATE TABLE schema_migration (
  version INTEGER PRIMARY KEY
);

CREATE TABLE availability (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  as_of TEXT NOT NULL,
  protected_cents INTEGER NOT NULL,
  source TEXT NOT NULL,
  convention TEXT NOT NULL,
  created_at TEXT NOT NULL,
  active INTEGER NOT NULL
);

CREATE TABLE balance_observation (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  as_of TEXT NOT NULL,
  kind TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE inflow (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  label TEXT NOT NULL,
  amount_cents INTEGER,
  due_on TEXT,
  state TEXT NOT NULL,
  recurrence TEXT,
  series_id TEXT,
  origin TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE commitment (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  label TEXT NOT NULL,
  total_cents INTEGER,
  remaining_cents INTEGER,
  due_on TEXT,
  original_due_on TEXT,
  essential INTEGER NOT NULL,
  priority TEXT,
  recurrence TEXT,
  series_id TEXT,
  origin TEXT NOT NULL,
  conditions_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE reserve (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  label TEXT NOT NULL,
  amount_cents INTEGER,
  usable_cents INTEGER,
  available_on TEXT,
  included_in_base INTEGER NOT NULL,
  kind_detail TEXT NOT NULL,
  restrictions TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE scenario (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  name TEXT NOT NULL,
  reference_on TEXT NOT NULL,
  premise_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  chosen INTEGER NOT NULL,
  note TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE batch (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  batch_key TEXT NOT NULL,
  origin TEXT NOT NULL,
  imported INTEGER NOT NULL,
  pending INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (owner_id, batch_key)
);

CREATE TABLE occurrence (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  batch_id TEXT NOT NULL,
  signature TEXT NOT NULL,
  state TEXT NOT NULL,
  movement_id TEXT,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE movement (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  occurrence_id TEXT UNIQUE,
  amount_cents INTEGER NOT NULL,
  direction TEXT NOT NULL,
  nature TEXT NOT NULL,
  booked_on TEXT NOT NULL,
  label TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE link_row (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  movement_id TEXT NOT NULL,
  commitment_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE draft (
  owner_id TEXT NOT NULL,
  key TEXT NOT NULL,
  body_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, key)
);

CREATE TABLE suggestion (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  purpose TEXT NOT NULL,
  origin TEXT NOT NULL,
  provider TEXT,
  model TEXT,
  prompt_version TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  premise_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  content TEXT NOT NULL,
  justification TEXT NOT NULL,
  status TEXT NOT NULL,
  revision_of TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE suggestion_event (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  suggestion_id TEXT NOT NULL,
  event TEXT NOT NULL,
  actor TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE stored_file (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  label TEXT NOT NULL,
  byte_length INTEGER NOT NULL,
  relative_path TEXT NOT NULL,
  retention TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE change_log (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE idempotency (
  owner_id TEXT NOT NULL,
  key TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, key)
);

CREATE TABLE feedback (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE identity (
  sub TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE account (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  name TEXT NOT NULL,
  currency TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE ledger_entry (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  account_id TEXT,
  payload_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE statement_note (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  signature TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE login_attempt (
  state TEXT PRIMARY KEY,
  verifier TEXT NOT NULL,
  created_at TEXT NOT NULL,
  used INTEGER NOT NULL
);

CREATE TABLE app_session (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  sub TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO schema_migration (version) VALUES (1), (2), (3);

-- Incremento 004IA, equivalente à migration 4 de store.py.
CREATE TABLE ai_job (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL,
  context_hash TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL,
  result_json TEXT, error_code TEXT, created_at TEXT NOT NULL,
  started_at TEXT, finished_at TEXT
);
CREATE INDEX ai_job_owner_idx ON ai_job(owner_id, created_at);
CREATE INDEX ai_job_pending_idx ON ai_job(status, created_at);
CREATE TABLE ai_quota (id INTEGER PRIMARY KEY, marker INTEGER NOT NULL);
INSERT INTO ai_quota (id,marker) VALUES (1,0);
INSERT INTO schema_migration (version) VALUES (4);
