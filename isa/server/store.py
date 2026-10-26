"""Base local da ISA. O dono vem de fora. O corpo do pedido não escolhe o proprietário."""

import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from engine import project
from explain import RULE_VERSION, PROMPT_VERSION, explain_alternative, explain_current, explain_spend
from overview import build_overview

RETENTION = "laboratorio-7-dias"
CURRENCIES = {
    "BRL": {"name": "Real", "exponent": 2},
    "USD": {"name": "Dólar americano", "exponent": 2},
    "EUR": {"name": "Euro", "exponent": 2},
}
ACCOUNT_KINDS = {"corrente": "Conta corrente", "poupanca": "Poupança", "investimento": "Investimento"}
ACCOUNT_INTAKE = {"manual": "Lançamento manual", "arquivo": "Importação por arquivo"}
CONTACT_ROLES = {
    "gerente_conta": "Gerente da conta",
    "gerente_agencia": "Gerente da agência",
    "atendimento": "Atendimento",
    "outro": "Outro",
}
CONTACT_SCOPES = {"conta": "Esta conta", "agencia": "A agência", "instituicao": "A instituição"}
EMAIL_TEXT = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
import catalog_str


def today():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def reference_date():
    return today() if os.environ.get("ISA_ENV") == "production" else "2026-10-16"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


bootstrap_counts = {"migrate": 0, "erasure": 0}
_erased = set()


def connect(db_path, bootstrap=None):
    """bootstrap=True migra e reaplica exclusões. O pedido de produção passa False."""
    if bootstrap is None:
        bootstrap = True
    if str(db_path).startswith("postgres"):
        from pgconn import connect as pg_connect
        conn = pg_connect(db_path)
    else:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    if not bootstrap:
        return conn
    try:
        migrate(conn)
        reapply_erasures(conn)
    except Exception:
        if getattr(conn, "isa_pg", False):
            conn.broken = True
        conn.close()
        raise
    return conn


_migrate_lock = __import__("threading").Lock()


def migrate(conn):
    bootstrap_counts["migrate"] += 1
    with _migrate_lock:
        _migrate_body(conn)


def _migrate_body(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migration (version INTEGER PRIMARY KEY)")
    version = conn.execute("SELECT MAX(version) AS v FROM schema_migration").fetchone()["v"] or 0
    if version < 1:
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO schema_migration (version) VALUES (1)")
        version = 1
    if version < 2:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS feedback (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              body TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identity (
              sub TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL
            );
            """
        )
        conn.execute("INSERT INTO schema_migration (version) VALUES (2)")
        version = 2
    if version < 3:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS account (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              name TEXT NOT NULL,
              currency TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ledger_entry (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              account_id TEXT,
              payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS statement_note (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              account_id TEXT NOT NULL,
              signature TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempt (
              state TEXT PRIMARY KEY,
              verifier TEXT NOT NULL,
              created_at TEXT NOT NULL,
              used INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_session (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              sub TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        conn.execute("INSERT INTO schema_migration (version) VALUES (3)")
    if version < 4:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ai_job (
              id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL,
              context_hash TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL,
              result_json TEXT, error_code TEXT, created_at TEXT NOT NULL,
              started_at TEXT, finished_at TEXT
            );
            CREATE INDEX IF NOT EXISTS ai_job_owner_idx ON ai_job(owner_id, created_at);
            CREATE INDEX IF NOT EXISTS ai_job_pending_idx ON ai_job(status, created_at);
            CREATE TABLE IF NOT EXISTS ai_quota (id INTEGER PRIMARY KEY, marker INTEGER NOT NULL);
            INSERT INTO ai_quota (id, marker) VALUES (1,0) ON CONFLICT (id) DO NOTHING;
            INSERT INTO schema_migration (version) VALUES (4) ON CONFLICT (version) DO NOTHING;
        """)
    if version < 5:
        for statement in (
            "ALTER TABLE account ADD COLUMN institution TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN kind TEXT NOT NULL DEFAULT 'corrente'",
            "ALTER TABLE account ADD COLUMN intake TEXT NOT NULL DEFAULT 'arquivo'",
            "ALTER TABLE account ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
            "ALTER TABLE account ADD COLUMN liquid INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE account ADD COLUMN updated_at TEXT",
            "ALTER TABLE availability ADD COLUMN account_id TEXT",
            "ALTER TABLE inflow ADD COLUMN account_id TEXT",
            "ALTER TABLE commitment ADD COLUMN account_id TEXT",
            """CREATE TABLE IF NOT EXISTS account_preference (
              owner_id TEXT PRIMARY KEY,
              context TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )""",
        ):
            conn.execute(statement)
        conn.execute("INSERT INTO schema_migration (version) VALUES (5)")
    if version < 6:
        for statement in (
            "ALTER TABLE account ADD COLUMN account_number TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN country TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN bank_code TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN agency TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN account_digit TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN nickname TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN bank_email TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN agency_email TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE account ADD COLUMN agency_phone TEXT NOT NULL DEFAULT ''",
            """CREATE TABLE IF NOT EXISTS person_profile (
              owner_id TEXT PRIMARY KEY,
              display_name TEXT NOT NULL DEFAULT '',
              verified_name TEXT NOT NULL DEFAULT '',
              access_email TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS account_contact (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              name TEXT NOT NULL DEFAULT '',
              role TEXT NOT NULL DEFAULT '',
              role_note TEXT NOT NULL DEFAULT '',
              email TEXT NOT NULL DEFAULT '',
              phone TEXT NOT NULL DEFAULT '',
              extension TEXT NOT NULL DEFAULT '',
              scope TEXT NOT NULL DEFAULT 'conta',
              primary_contact INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'active',
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS account_contact_link (
              contact_id TEXT NOT NULL,
              account_id TEXT NOT NULL,
              owner_id TEXT NOT NULL,
              PRIMARY KEY (contact_id, account_id)
            )""",
        ):
            conn.execute(statement)
        conn.execute("INSERT INTO schema_migration (version) VALUES (6)")
    if version < 7:
        import workbatches
        workbatches.migrate(conn)
        conn.execute("INSERT INTO schema_migration (version) VALUES (7)")
    if version < 8:
        conn.execute("ALTER TABLE account ADD COLUMN agency_name TEXT NOT NULL DEFAULT ''")
        conn.execute("INSERT INTO schema_migration (version) VALUES (8)")
    if version < 9:
        conn.execute("ALTER TABLE account ADD COLUMN bank_ispb TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS catalog_request (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              query TEXT NOT NULL,
              created_at TEXT NOT NULL
            )"""
        )
        conn.execute("INSERT INTO schema_migration (version) VALUES (9)")


SCHEMA = """
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
"""


def _id():
    return uuid.uuid4().hex


def log(conn, owner, entity, entity_id, action, before, after):
    conn.execute(
        "INSERT INTO change_log (id, owner_id, entity, entity_id, action, before_json, after_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (_id(), owner, entity, entity_id, action, json.dumps(before) if before is not None else None, json.dumps(after) if after is not None else None, now()),
    )


def rows(conn, sql, args=()):
    return [dict(row) for row in conn.execute(sql, args).fetchall()]


def one(conn, sql, args=()):
    row = conn.execute(sql, args).fetchone()
    return dict(row) if row else None


def owned(conn, table, owner, entity_id):
    return one(conn, f"SELECT * FROM {table} WHERE id = ? AND owner_id = ?", (entity_id, owner))


def save_availability(conn, owner, body):
    amount = body.get("amountCents")
    as_of = body.get("asOf")
    if amount is None or not as_of:
        raise ValueError("Falta o valor ou a data. Isso não vira zero.")
    protected = int(body.get("protectedCents") or 0)
    if protected > int(amount) and int(amount) >= 0:
        raise ValueError("A reserva protegida não pode ser maior que o disponível declarado.")
    account_id = _owned_account_id(conn, owner, body.get("accountId"))
    conn.execute("BEGIN IMMEDIATE")
    try:
        if account_id:
            previous = one(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1 AND account_id = ?", (owner, account_id))
        else:
            previous = one(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1 AND account_id IS NULL", (owner,))
        if previous:
            conn.execute("UPDATE availability SET active = 0 WHERE id = ?", (previous["id"],))
        item = {
            "id": _id(),
            "owner_id": owner,
            "amount_cents": int(amount),
            "as_of": as_of,
            "protected_cents": protected,
            "source": body.get("source") or "declarada",
            "convention": "encerramento_do_dia",
            "created_at": now(),
            "active": 1,
            "account_id": account_id,
        }
        conn.execute(
            "INSERT INTO availability (id, owner_id, amount_cents, as_of, protected_cents, source, convention, created_at, active, account_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            tuple(item.values()),
        )
        log(conn, owner, "availability", item["id"], "corrigir" if previous else "criar", previous, item)
        _invalidate_suggestions(conn, owner, "A disponibilidade mudou.")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return item


def add_observation(conn, owner, body):
    if body.get("amountCents") is None or not body.get("asOf"):
        raise ValueError("A observação precisa de valor e data.")
    item = {
        "id": _id(),
        "owner_id": owner,
        "amount_cents": int(body["amountCents"]),
        "as_of": body["asOf"],
        "kind": body.get("kind") or "saldo_informado",
        "source": body.get("source") or "extrato",
        "created_at": now(),
    }
    conn.execute(
        "INSERT INTO balance_observation (id, owner_id, amount_cents, as_of, kind, source, created_at) VALUES (?,?,?,?,?,?,?)",
        tuple(item.values()),
    )
    return item


def add_inflow(conn, owner, body):
    state = body.get("state") or "pendente"
    if state not in ("confirmada", "incerta", "pendente"):
        raise ValueError("Estado de confirmação desconhecido.")
    label = (body.get("label") or "Entrada").strip()
    amount = None if body.get("amountCents") is None else int(body["amountCents"])
    due = body.get("dueOn") or None
    account_id = _owned_account_id(conn, owner, body.get("accountId"))
    recent = rows(conn, "SELECT * FROM inflow WHERE owner_id = ? ORDER BY created_at DESC LIMIT 8", (owner,))
    copy = _recent_match(recent, lambda item: item["label"] == label and item["amount_cents"] == amount and item["due_on"] == due and item["state"] == state and (item.get("account_id") or None) == account_id)
    if copy:
        return copy
    item = {
        "id": _id(),
        "owner_id": owner,
        "label": label,
        "amount_cents": amount,
        "due_on": due,
        "state": state,
        "recurrence": body.get("recurrence"),
        "series_id": body.get("seriesId") or _id(),
        "origin": body.get("origin") or "declarada",
        "created_at": now(),
        "account_id": account_id,
    }
    conn.execute(
        "INSERT INTO inflow (id, owner_id, label, amount_cents, due_on, state, recurrence, series_id, origin, created_at, account_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (item["id"], item["owner_id"], item["label"], item["amount_cents"], item["due_on"], item["state"], item["recurrence"], item["series_id"], item["origin"], item["created_at"], item["account_id"]),
    )
    log(conn, owner, "inflow", item["id"], "criar", None, item)
    _invalidate_suggestions(conn, owner, "Uma entrada mudou.")
    return item


def patch_inflow(conn, owner, entity_id, body):
    current = owned(conn, "inflow", owner, entity_id)
    if not current:
        return None
    if body.get("state"):
        current["state"] = body["state"]
    if body.get("label"):
        current["label"] = str(body["label"]).strip() or current["label"]
    if "amountCents" in body:
        current["amount_cents"] = None if body["amountCents"] is None else int(body["amountCents"])
    if "dueOn" in body:
        current["due_on"] = body["dueOn"] or None
    conn.execute("UPDATE inflow SET label = ?, state = ?, amount_cents = ?, due_on = ? WHERE id = ? AND owner_id = ?", (current["label"], current["state"], current["amount_cents"], current["due_on"], entity_id, owner))
    log(conn, owner, "inflow", entity_id, "corrigir", None, current)
    return current


def add_commitment(conn, owner, body):
    total = None if body.get("totalCents") is None else int(body["totalCents"])
    remaining = total if body.get("remainingCents") is None else (None if body.get("remainingCents") is None and total is None else int(body.get("remainingCents") if body.get("remainingCents") is not None else total))
    if body.get("remainingCents") is None and total is not None:
        remaining = total
    due = body.get("dueOn") or None
    label = (body.get("label") or "").strip()
    if not label:
        raise ValueError("Falta dizer o que é o compromisso.")
    account_id = _owned_account_id(conn, owner, body.get("accountId"))
    recent = rows(conn, "SELECT * FROM commitment WHERE owner_id = ? ORDER BY created_at DESC LIMIT 8", (owner,))
    copy = _recent_match(recent, lambda item: item["label"] == label and item["total_cents"] == total and item["due_on"] == due and (item.get("account_id") or None) == account_id)
    if copy:
        return copy
    item = {
        "id": _id(),
        "label": label,
        "total_cents": total,
        "remaining_cents": remaining,
        "due_on": due,
        "original_due_on": due,
        "essential": 1 if body.get("essential") else 0,
        "priority": body.get("priority"),
        "recurrence": body.get("recurrence"),
        "series_id": body.get("seriesId") or _id(),
        "origin": body.get("origin") or "declarada",
        "conditions_json": json.dumps(body.get("conditions") or {"custo": "desconhecido", "aceite": "desconhecido"}),
        "account_id": account_id,
    }
    conn.execute(
        "INSERT INTO commitment (id, owner_id, label, total_cents, remaining_cents, due_on, original_due_on, essential, priority, recurrence, series_id, origin, conditions_json, created_at, account_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (item["id"], owner, item["label"], item["total_cents"], item["remaining_cents"], item["due_on"], item["original_due_on"], item["essential"], item["priority"], item["recurrence"], item["series_id"], item["origin"], item["conditions_json"], now(), item["account_id"]),
    )
    log(conn, owner, "commitment", item["id"], "criar", None, item)
    _invalidate_suggestions(conn, owner, "Um compromisso mudou.")
    return owned(conn, "commitment", owner, item["id"])


def patch_commitment(conn, owner, entity_id, body):
    current = owned(conn, "commitment", owner, entity_id)
    if not current:
        return None
    before = dict(current)
    if "dueOn" in body:
        current["due_on"] = body["dueOn"] or None
    if "remainingCents" in body:
        current["remaining_cents"] = None if body["remainingCents"] is None else int(body["remainingCents"])
    if "totalCents" in body:
        current["total_cents"] = None if body["totalCents"] is None else int(body["totalCents"])
    if "label" in body and body["label"]:
        current["label"] = body["label"].strip()
    if "priority" in body:
        current["priority"] = body["priority"]
    if "essential" in body:
        current["essential"] = 1 if body["essential"] else 0
    conn.execute(
        "UPDATE commitment SET label = ?, total_cents = ?, remaining_cents = ?, due_on = ?, essential = ?, priority = ? WHERE id = ? AND owner_id = ?",
        (current["label"], current["total_cents"], current["remaining_cents"], current["due_on"], current["essential"], current["priority"], entity_id, owner),
    )
    log(conn, owner, "commitment", entity_id, "corrigir", before, current)
    _invalidate_suggestions(conn, owner, "Um compromisso mudou.")
    siblings = rows(conn, "SELECT id, due_on FROM commitment WHERE owner_id = ? AND series_id = ? AND id <> ?", (owner, current["series_id"], entity_id))
    current["siblings_unchanged"] = siblings
    return current


def add_reserve(conn, owner, body):
    item_id = _id()
    conn.execute(
        "INSERT INTO reserve (id, owner_id, label, amount_cents, usable_cents, available_on, included_in_base, kind_detail, restrictions, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            item_id,
            owner,
            body.get("label") or "Reserva",
            None if body.get("amountCents") is None else int(body["amountCents"]),
            None if body.get("usableCents") is None else int(body["usableCents"]),
            body.get("availableOn"),
            1 if body.get("includedInBase") else 0,
            body.get("kindDetail") or "reserva",
            body.get("restrictions"),
            now(),
        ),
    )
    return owned(conn, "reserve", owner, item_id)


def _account_map(conn, owner):
    return {item["id"]: item for item in rows(conn, "SELECT * FROM account WHERE owner_id = ?", (owner,))}


def _in_scope(item, account_id, currency, accounts):
    linked = item.get("account_id") or ""
    if account_id:
        return linked == account_id
    if not currency:
        return True
    if not linked:
        return currency == "BRL"
    account = accounts.get(linked)
    return bool(account) and account.get("currency") == currency


def _events(conn, owner, account_id=None, currency=None):
    accounts = _account_map(conn, owner)
    events = []
    for item in rows(conn, "SELECT * FROM inflow WHERE owner_id = ?", (owner,)):
        if not _in_scope(item, account_id, currency, accounts):
            continue
        events.append({
            "id": item["id"],
            "kind": "entrada",
            "label": item["label"],
            "on": item["due_on"],
            "cents": item["amount_cents"],
            "account_id": item.get("account_id") or "",
            "included": item["state"] == "confirmada" and item["amount_cents"] is not None and bool(item["due_on"]),
        })
    for item in rows(conn, "SELECT * FROM commitment WHERE owner_id = ?", (owner,)):
        if not _in_scope(item, account_id, currency, accounts):
            continue
        events.append({
            "id": item["id"],
            "kind": "saida",
            "label": item["label"],
            "on": item["due_on"],
            "cents": item["remaining_cents"],
            "account_id": item.get("account_id") or "",
            "included": item["remaining_cents"] is not None and bool(item["due_on"]) and int(item["remaining_cents"]) != 0,
        })
    if account_id or (currency and currency != "BRL"):
        return events
    for item in rows(conn, "SELECT * FROM reserve WHERE owner_id = ?", (owner,)):
        events.append({
            "id": item["id"],
            "kind": "reserva",
            "label": item["label"],
            "on": item["available_on"],
            "cents": item["usable_cents"],
            "included_in_base": bool(item["included_in_base"]),
            "usable": item["usable_cents"] is not None and bool(item["available_on"]) and not item["included_in_base"],
            "kind_detail": item["kind_detail"],
        })
    return events


def _base(conn, owner, account_id=None, currency=None):
    accounts = _account_map(conn, owner)
    if account_id:
        account = accounts.get(account_id)
        row = one(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1 AND account_id = ?", (owner, account_id))
        if account and account.get("kind") == "investimento" and not int(account.get("liquid") or 0):
            position = None if not row else {"amount_cents": row["amount_cents"], "as_of": row["as_of"], "currency": account["currency"]}
            return {"known": False, "reason": "investimento", "position": position}
        if not row:
            return {"known": False}
        return _known_base(row)
    personal = one(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1 AND account_id IS NULL", (owner,))
    scoped = [item for item in rows(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1 AND account_id IS NOT NULL", (owner,)) if _in_scope(item, None, currency, accounts)] if currency else []
    if currency:
        if currency == "BRL" and personal and scoped:
            return {"known": False, "reason": "reconciliar", "personal": _known_base(personal), "accounts": [_known_base(item) for item in scoped]}
        if scoped:
            missing = [item["id"] for item in accounts.values() if item.get("currency") == currency and item.get("status") != "inactive" and item["id"] not in {row["account_id"] for row in scoped}]
            total = sum(int(item["amount_cents"]) for item in scoped)
            protected = sum(int(item["protected_cents"] or 0) for item in scoped)
            latest = max(item["as_of"] for item in scoped)
            return {"known": not missing, "as_of": latest, "amount_cents": total, "protected_cents": protected, "convention": "soma_das_contas", "source": "contas", "partial": bool(missing), "missingAccounts": missing}
        if currency == "BRL" and personal:
            return _known_base(personal)
        return {"known": False}
    if not personal:
        return {"known": False}
    return _known_base(personal)


def _known_base(row):
    return {
        "known": True,
        "as_of": row["as_of"],
        "amount_cents": row["amount_cents"],
        "protected_cents": row["protected_cents"],
        "convention": row["convention"],
        "source": row["source"],
    }


def projection(conn, owner, reference, changes=None, extra=None, include_uncertain=False, account_id=None, currency=None):
    base = _base(conn, owner, account_id, currency)
    events = _events(conn, owner, account_id, currency)
    if include_uncertain:
        for item in events:
            if item["kind"] == "entrada" and item.get("cents") is not None and item.get("on"):
                item["included"] = True
    if changes:
        by_id = {item["id"]: item for item in events}
        for change in changes:
            target = by_id.get(change.get("commitmentId"))
            if not target or target["kind"] != "saida":
                continue
            if change.get("dueOn"):
                target["on"] = change["dueOn"]
                target["included"] = target.get("cents") is not None
            if change.get("amountCents") is not None:
                target["cents"] = int(change["amountCents"])
                target["included"] = True
    result = project(base, events, reference, extra=extra)
    if base.get("reason"):
        result["reason"] = base["reason"]
        result["position"] = base.get("position")
    return result


def save_scenario(conn, owner, body):
    reference = body.get("reference") or reference_date()
    changes = body.get("changes") or []
    result = projection(conn, owner, reference, changes=changes)
    current = projection(conn, owner, reference)
    label = body.get("label") or "a data de um compromisso muda"
    note = explain_alternative(current, result, label)["text"] if current.get("complete") and result.get("complete") else "A comparação espera a disponibilidade e os compromissos."
    item_id = _id()
    premise = {"reference": reference, "changes": changes, "base": _base(conn, owner)}
    conn.execute(
        "INSERT INTO scenario (id, owner_id, name, reference_on, premise_json, result_json, engine_version, chosen, note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (item_id, owner, body.get("name") or "Alternativa", reference, json.dumps(premise), json.dumps(result), result.get("engine_version") or "", 0, note, now()),
    )
    return owned(conn, "scenario", owner, item_id)


def choose_scenario(conn, owner, scenario_id):
    item = owned(conn, "scenario", owner, scenario_id)
    if not item:
        return None
    conn.execute("UPDATE scenario SET chosen = 0 WHERE owner_id = ?", (owner,))
    conn.execute("UPDATE scenario SET chosen = 1, name = 'Plano escolhido' WHERE id = ? AND owner_id = ?", (scenario_id, owner))
    item["chosen"] = 1
    item["name"] = "Plano escolhido"
    log(conn, owner, "scenario", scenario_id, "plano-escolhido", None, {"chosen": 1})
    return item


def plan_occurrences(stored, movements):
    groups = {}
    for row in movements:
        groups.setdefault(row["signature"], []).append(row)
    imported, pending, reused = [], [], 0
    for signature, group in groups.items():
        incorporated = sum(1 for item in stored if item["signature"] == signature and item["state"] == "incorporada")
        waiting = sum(1 for item in stored if item["signature"] == signature and item["state"] == "pendente")
        same = sum(1 for item in stored if item["signature"] == signature and item["state"] == "mesma")
        covered = waiting + same
        if incorporated == 0 and covered == 0:
            imported.extend(group)
            continue
        if covered >= len(group):
            reused += len(group)
            continue
        pending.extend(group[: len(group) - covered])
        reused += covered
    return imported, pending, reused


def import_batch(conn, owner, body):
    key = body.get("batchKey")
    origin = body.get("origin") or "exemplo-sintetico"
    movements = body.get("movements") or []
    if not key:
        raise ValueError("Falta a identidade do lote.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = one(conn, "SELECT * FROM batch WHERE owner_id = ? AND batch_key = ?", (owner, key))
        if existing:
            conn.execute("COMMIT")
            existing["repeated"] = True
            return existing
        stored = rows(conn, "SELECT signature, state FROM occurrence WHERE owner_id = ?", (owner,))
        imported, pending, reused = plan_occurrences(stored, movements)
        batch_id = _id()
        for row in imported:
            occurrence_id = _id()
            movement_id = _id()
            conn.execute(
                "INSERT INTO occurrence (id, owner_id, batch_id, signature, state, movement_id, payload_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (occurrence_id, owner, batch_id, row["signature"], "incorporada", movement_id, json.dumps(row), now()),
            )
            conn.execute(
                "INSERT INTO movement (id, owner_id, occurrence_id, amount_cents, direction, nature, booked_on, label, source, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (movement_id, owner, occurrence_id, int(row["cents"]), row.get("direction") or "saida", row.get("nature") or "a_conferir", row["date"], row.get("label") or "", origin, now()),
            )
        for row in pending:
            conn.execute(
                "INSERT INTO occurrence (id, owner_id, batch_id, signature, state, movement_id, payload_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (_id(), owner, batch_id, row["signature"], "pendente", None, json.dumps(row), now()),
            )
        conn.execute(
            "INSERT INTO batch (id, owner_id, batch_key, origin, imported, pending, created_at) VALUES (?,?,?,?,?,?,?)",
            (batch_id, owner, key, origin, len(imported), len(pending), now()),
        )
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
        existing = one(conn, "SELECT * FROM batch WHERE owner_id = ? AND batch_key = ?", (owner, key))
        if existing:
            existing["repeated"] = True
            return existing
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    sync_entries(conn, owner)
    created = one(conn, "SELECT * FROM batch WHERE id = ?", (batch_id,))
    created["repeated"] = False
    created["reused"] = reused
    return created


def decide_occurrence(conn, owner, occurrence_id, kind):
    if kind not in ("mesma", "outra"):
        raise ValueError("A decisão precisa ser a mesma operação ou outra.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        item = one(conn, "SELECT * FROM occurrence WHERE id = ? AND owner_id = ?", (occurrence_id, owner))
        if not item:
            conn.execute("COMMIT")
            return None
        if item["state"] != "pendente":
            conn.execute("COMMIT")
            item["repeated"] = True
            return item
        if kind == "mesma":
            conn.execute("UPDATE occurrence SET state = 'mesma' WHERE id = ?", (occurrence_id,))
            item["state"] = "mesma"
        else:
            movement_id = _id()
            payload = json.loads(item["payload_json"])
            conn.execute(
                "INSERT INTO movement (id, owner_id, occurrence_id, amount_cents, direction, nature, booked_on, label, source, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (movement_id, owner, occurrence_id, int(payload["cents"]), payload.get("direction") or "saida", payload.get("nature") or "a_conferir", payload["date"], payload.get("label") or "", "decisao", now()),
            )
            conn.execute("UPDATE occurrence SET state = 'incorporada', movement_id = ? WHERE id = ?", (movement_id, occurrence_id))
            item["state"] = "incorporada"
            item["movement_id"] = movement_id
        item["repeated"] = False
        log(conn, owner, "occurrence", occurrence_id, kind, None, {"state": item["state"]})
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
        item = one(conn, "SELECT * FROM occurrence WHERE id = ? AND owner_id = ?", (occurrence_id, owner))
        if item:
            item["repeated"] = True
        return item
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return item


def link_movement(conn, owner, body):
    if not body.get("confirmed"):
        raise ValueError("O vínculo precisa de confirmação. Uma sugestão não quita o compromisso.")
    movement = owned(conn, "movement", owner, body.get("movementId"))
    commitment = owned(conn, "commitment", owner, body.get("commitmentId"))
    if not movement or not commitment:
        return None
    amount = int(body.get("amountCents") if body.get("amountCents") is not None else movement["amount_cents"])
    already = one(conn, "SELECT id FROM link_row WHERE owner_id = ? AND movement_id = ? AND commitment_id = ?", (owner, movement["id"], commitment["id"]))
    if already:
        return {"repeated": True, "commitment": commitment}
    remaining = commitment["remaining_cents"]
    if remaining is None:
        raise ValueError("O restante do compromisso ainda não está definido.")
    updated = max(0, int(remaining) - amount)
    conn.execute("UPDATE commitment SET remaining_cents = ? WHERE id = ? AND owner_id = ?", (updated, commitment["id"], owner))
    conn.execute(
        "INSERT INTO link_row (id, owner_id, movement_id, commitment_id, amount_cents, created_at) VALUES (?,?,?,?,?,?)",
        (_id(), owner, movement["id"], commitment["id"], amount, now()),
    )
    commitment["remaining_cents"] = updated
    return {"repeated": False, "commitment": commitment}


def dismiss_insight(conn, owner, body):
    item_id = str(body.get("id") or "").strip()
    if not item_id:
        raise ValueError("Falta dizer qual aviso.")
    day = reference_date()
    current = _draft_body(conn, owner, "insights-hoje")
    if current.get("day") != day or not isinstance(current.get("dismissed"), list):
        current = {"day": day, "dismissed": []}
    if item_id not in current["dismissed"]:
        current["dismissed"].append(item_id)
    save_draft(conn, owner, "insights-hoje", current)
    return {"saved": True, "id": item_id}


def save_draft(conn, owner, key, body):
    conn.execute(
        "INSERT INTO draft (owner_id, key, body_json, updated_at) VALUES (?,?,?,?) ON CONFLICT(owner_id, key) DO UPDATE SET body_json = excluded.body_json, updated_at = excluded.updated_at",
        (owner, key, json.dumps(body), now()),
    )
    return {"key": key, "saved": True}


def read_draft(conn, owner, key):
    row = one(conn, "SELECT * FROM draft WHERE owner_id = ? AND key = ?", (owner, key))
    if not row:
        return None
    return {"key": key, "body": json.loads(row["body_json"]), "updatedAt": row["updated_at"]}


def _invalidate_suggestions(conn, owner, reason):
    open_rows = rows(conn, "SELECT * FROM suggestion WHERE owner_id = ? AND status IN ('gerada', 'apresentada')", (owner,))
    for item in open_rows:
        conn.execute("UPDATE suggestion SET status = 'desatualizada' WHERE id = ?", (item["id"],))
        conn.execute(
            "INSERT INTO suggestion_event (id, owner_id, suggestion_id, event, actor, note, created_at) VALUES (?,?,?,?,?,?,?)",
            (_id(), owner, item["id"], "invalidada", "sistema", reason, now()),
        )


def create_suggestion(conn, owner, reference=None):
    reference = reference or reference_date()
    current = projection(conn, owner, reference)
    commitments = rows(conn, "SELECT * FROM commitment WHERE owner_id = ? ORDER BY due_on", (owner,))
    target = next((item for item in commitments if item["remaining_cents"] == 50000), commitments[0] if commitments else None)
    changes = []
    label = "não há compromisso para comparar"
    if target and target["due_on"]:
        year, month, day = target["due_on"].split("-")
        delayed = f"{year}-{month}-{int(day) + 6:02d}" if int(day) + 6 <= 28 else target["due_on"]
        if target["due_on"] == "2026-10-20":
            delayed = "2026-10-26"
        changes = [{"commitmentId": target["id"], "dueOn": delayed}]
        label = "somente " + target["label"] + " passar de " + target["due_on"] + " para " + delayed
    alternative = projection(conn, owner, reference, changes=changes)
    text = explain_alternative(current, alternative, label)["text"] if current.get("complete") and alternative.get("complete") else explain_current(current)["text"]
    item_id = _id()
    premise = {"reference": reference, "changes": changes, "base": _base(conn, owner), "snapshot": True}
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "INSERT INTO suggestion (id, owner_id, agent, purpose, origin, provider, model, prompt_version, rule_version, premise_json, result_json, content, justification, status, revision_of, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (item_id, owner, "planejamento", "comparar-alternativa", "regras-demonstrativas", None, None, PROMPT_VERSION, RULE_VERSION, json.dumps(premise), json.dumps({"current": current, "alternative": alternative}), text, "Os números vêm do motor " + (current.get("engine_version") or "") + ".", "gerada", None, now()),
        )
        conn.execute(
            "INSERT INTO suggestion_event (id, owner_id, suggestion_id, event, actor, note, created_at) VALUES (?,?,?,?,?,?,?)",
            (_id(), owner, item_id, "gerada", "sistema", "Ainda não apresentada.", now()),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return owned(conn, "suggestion", owner, item_id)


def suggestion_event(conn, owner, suggestion_id, event, note=""):
    item = owned(conn, "suggestion", owner, suggestion_id)
    if not item:
        return None
    if item["origin"] == "ia-real":
        raise ValueError("Esta análise deve ser revista na ajuda da ISA; ela não altera compromissos.")
    if item["status"] == "desatualizada" and event == "aceita":
        raise ValueError("Os dados mudaram. Recalcule antes de escolher.")
    if event == "aceita":
        prior = one(conn, "SELECT id FROM suggestion_event WHERE suggestion_id = ? AND event = 'aceita'", (suggestion_id,))
        if prior or item["status"] in ("aceita", "recusada"):
            item["repeated"] = True
            return item
    if event == "apresentada" and item["status"] == "gerada":
        conn.execute("UPDATE suggestion SET status = 'apresentada' WHERE id = ?", (suggestion_id,))
        item["status"] = "apresentada"
    elif event == "recusada":
        conn.execute("UPDATE suggestion SET status = 'recusada' WHERE id = ?", (suggestion_id,))
        item["status"] = "recusada"
    elif event == "aceita":
        premise = json.loads(item["premise_json"])
        scenario = save_scenario(conn, owner, {"name": "Plano escolhido", "reference": premise.get("reference"), "changes": premise.get("changes") or [], "label": "a alternativa guardada"})
        choose_scenario(conn, owner, scenario["id"])
        conn.execute("UPDATE suggestion SET status = 'aceita' WHERE id = ?", (suggestion_id,))
        item["status"] = "aceita"
        item["scenario_id"] = scenario["id"]
    elif event == "corrigida":
        revised = create_suggestion(conn, owner)
        conn.execute("UPDATE suggestion SET revision_of = ? WHERE id = ?", (suggestion_id, revised["id"]))
        revised["revision_of"] = suggestion_id
        item = revised
    conn.execute(
        "INSERT INTO suggestion_event (id, owner_id, suggestion_id, event, actor, note, created_at) VALUES (?,?,?,?,?,?,?)",
        (_id(), owner, item["id"], event, "pessoa", note, now()),
    )
    item["repeated"] = False
    return item


def spend(conn, owner, body):
    reference = body.get("reference") or reference_date()
    extra = {"on": body.get("on") or reference, "cents": body.get("amountCents"), "label": body.get("label") or body.get("category") or "Gasto"}
    if extra["cents"] is None:
        raise ValueError("Falta o valor. Isso não vira zero.")
    result = projection(conn, owner, reference, extra=extra)
    explained = explain_spend(result, extra["label"], int(extra["cents"]), extra["on"])
    return {"result": result, "explanation": explained}


def _draft_body(conn, owner, key):
    try:
        row = read_draft(conn, owner, key)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    body = row.get("body") if row else {}
    return body if isinstance(body, dict) else {}


def _recent_match(found, predicate):
    moment = datetime.now(timezone.utc)
    for current in found:
        if not predicate(current):
            continue
        try:
            age = moment - datetime.fromisoformat(current["created_at"])
        except (TypeError, ValueError):
            continue
        if 0 <= age.total_seconds() <= 20:
            current["repeated"] = True
            return current
    return None


def planning_guide(conn, owner, inflows, commitments, account_id=None, currency=None):
    """Estado da jornada. A navegação usa estes campos, não o texto das mensagens."""
    base = _base(conn, owner, account_id, currency)
    draft = _draft_body(conn, owner, "planejar")
    confirmed = any(item["state"] == "confirmada" and item["amount_cents"] is not None and item["due_on"] for item in inflows)
    uncertain = any(item["state"] == "incerta" for item in inflows)
    pending_commitments = sum(1 for item in commitments if item["remaining_cents"] is None or not item["due_on"])
    declared_none = bool(draft.get("commitmentsDeclaredNone")) and not commitments
    known = bool(base.get("known"))
    availability_pending = (not known) and bool(draft.get("availabilityUnknown"))
    past_availability = bool(draft.get("continuePastAvailability"))
    commitment_unknown = bool(draft.get("commitmentUnknown")) and not commitments
    past_commitments = bool(draft.get("continuePastCommitments"))

    def after_availability():
        if not confirmed:
            if uncertain and not draft.get("continuePastInflow"):
                return "inflow-pending"
            if not uncertain:
                return "inflow"
        if not commitments and commitment_unknown and not past_commitments and not declared_none:
            return "commitments-pending"
        if not commitments and not declared_none and not past_commitments:
            return "commitments"
        return "summary"

    if not known and availability_pending and not past_availability:
        step = "availability-pending"
    elif not known and not past_availability:
        step = "availability"
    else:
        step = after_availability()
    gaps = []
    if not known:
        gaps.append("availability")
    if not confirmed:
        gaps.append("inflow")
    if not commitments and not declared_none:
        gaps.append("commitments")
    if pending_commitments:
        gaps.append("commitment-values")
    return {
        "step": step,
        "gaps": gaps,
        "availabilityKnown": known,
        "availability": None if not known else {
            "amountCents": base["amount_cents"],
            "asOf": base["as_of"],
            "protectedCents": base["protected_cents"],
        },
        "availabilityPending": availability_pending,
        "inflowConfirmed": confirmed,
        "inflowUncertain": uncertain,
        "commitmentCount": len(commitments),
        "commitmentsPending": pending_commitments,
        "commitmentsDeclaredNone": declared_none,
        "draftSaved": bool(draft),
    }


def _owned_account_id(conn, owner, account_id):
    if not account_id:
        return None
    account = one(conn, "SELECT * FROM account WHERE id = ? AND owner_id = ?", (account_id, owner))
    if not account or account.get("status") == "inactive":
        raise ValueError("Escolha uma conta ativa sua.")
    return account["id"]


def _active_currencies(conn, owner):
    found = []
    for item in rows(conn, "SELECT currency FROM account WHERE owner_id = ? AND status != 'inactive' ORDER BY created_at", (owner,)):
        code = item["currency"]
        if code not in found:
            found.append(code)
    return found


def _scoped_plans(conn, owner, account_id, currency):
    accounts = _account_map(conn, owner)
    inflows = [item for item in rows(conn, "SELECT id, label, due_on, amount_cents, state, account_id FROM inflow WHERE owner_id = ? ORDER BY due_on", (owner,)) if _in_scope(item, account_id, currency, accounts)]
    commitments = [item for item in rows(conn, "SELECT id, label, due_on, original_due_on, remaining_cents, total_cents, essential, priority, conditions_json, account_id FROM commitment WHERE owner_id = ? ORDER BY due_on", (owner,)) if _in_scope(item, account_id, currency, accounts)]
    return inflows, commitments


def _outside_count(conn, owner, account_id):
    if not account_id:
        return 0
    return len(rows(conn, "SELECT id FROM commitment WHERE owner_id = ? AND account_id IS NULL", (owner,)))


def _currency_home(conn, owner, reference, currency):
    result = projection(conn, owner, reference, currency=currency)
    inflows, commitments = _scoped_plans(conn, owner, None, currency)
    guide = planning_guide(conn, owner, inflows, commitments, None, currency)
    overview = build_overview(result.get("reference") or reference, result, guide, commitments, inflows)
    return {"currency": currency, "projection": result, "guide": guide, "commitments": commitments, "inflows": inflows, "overview": overview}


def account_context(conn, owner, requested, persist=False):
    accounts = rows(conn, "SELECT * FROM account WHERE owner_id = ? ORDER BY created_at", (owner,))
    preference = one(conn, "SELECT context FROM account_preference WHERE owner_id = ?", (owner,))
    choice = requested if requested not in (None, "") else ((preference or {}).get("context") or "all")
    notice = ""
    selected = None
    if choice != "all":
        selected = next((item for item in accounts if item["id"] == choice), None)
        if not selected or selected.get("status") == "inactive":
            notice = "A conta escolhida não está disponível. A visão voltou para todas as contas."
            choice = "all"
            selected = None
    if persist or notice:
        conn.execute(
            "INSERT INTO account_preference (owner_id, context, updated_at) VALUES (?,?,?) ON CONFLICT (owner_id) DO UPDATE SET context = excluded.context, updated_at = excluded.updated_at",
            (owner, choice, now()),
        )
    public = [_public_account(conn, owner, item) for item in accounts]
    return {
        "scope": "all" if choice == "all" else "account",
        "accountId": "" if choice == "all" else choice,
        "label": "Todas as contas" if choice == "all" else selected["name"],
        "currency": "" if choice == "all" else selected["currency"],
        "notice": notice,
        "accounts": public,
        "currencies": _active_currencies(conn, owner),
    }


def mask_account_number(value):
    text = str(value or "").strip()
    if not text:
        return ""
    visible = text[-2:] if len(text) > 2 else text
    return ("•" * (len(text) - len(visible))) + visible


def account_label(institution, number, nickname=""):
    nick = " ".join(str(nickname or "").split())
    if nick:
        return nick
    bank = " ".join(str(institution or "").split())
    masked = mask_account_number(number)
    if bank and masked:
        return bank + " · " + masked
    return bank or masked or "Conta"


def _email_or_blank(value, label):
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 160 or not EMAIL_TEXT.match(text):
        raise ValueError(label + " precisa ter o formato de um e-mail.")
    return text


def _presentation_name(claims):
    name = " ".join(str((claims or {}).get("name") or "").split())
    if not name:
        given = " ".join(str((claims or {}).get("given_name") or "").split())
        family = " ".join(str((claims or {}).get("family_name") or "").split())
        name = " ".join(part for part in (given, family) if part)
    if not name or "@" in name:
        return ""
    return name[:80]


def profile_public(conn, owner):
    row = one(conn, "SELECT display_name, verified_name, access_email FROM person_profile WHERE owner_id = ?", (owner,)) or {}
    saved = row.get("display_name") or ""
    verified = row.get("verified_name") or ""
    email = row.get("access_email") or ""
    return {
        "displayName": saved or verified,
        "savedName": saved,
        "accessLabel": email or "Sessão individual deste piloto",
        "ready": True,
    }


def remember_verified_profile(conn, owner, claims):
    name = _presentation_name(claims)
    email = ""
    try:
        email = _email_or_blank((claims or {}).get("email"), "O e-mail de acesso")
    except ValueError:
        email = ""
    current = one(conn, "SELECT owner_id FROM person_profile WHERE owner_id = ?", (owner,))
    if current:
        conn.execute(
            "UPDATE person_profile SET verified_name = ?, access_email = ?, updated_at = ? WHERE owner_id = ?",
            (name, email, now(), owner),
        )
    else:
        conn.execute(
            "INSERT INTO person_profile (owner_id, display_name, verified_name, access_email, updated_at) VALUES (?,?,?,?,?)",
            (owner, "", name, email, now()),
        )
    return profile_public(conn, owner)


def save_profile(conn, owner, body):
    if body.get("ownerId") or body.get("owner_id") or body.get("sub") or body.get("email"):
        raise ValueError("O nome de apresentação não altera o acesso.")
    name = " ".join(str(body.get("displayName") or "").split())
    if len(name) > 80:
        raise ValueError("O nome de apresentação cabe em 80 caracteres.")
    if "@" in name:
        raise ValueError("Use o nome como você quer aparecer, sem o e-mail de acesso.")
    current = one(conn, "SELECT owner_id FROM person_profile WHERE owner_id = ?", (owner,))
    if current:
        conn.execute("UPDATE person_profile SET display_name = ?, updated_at = ? WHERE owner_id = ?", (name, now(), owner))
    else:
        conn.execute(
            "INSERT INTO person_profile (owner_id, display_name, verified_name, access_email, updated_at) VALUES (?,?,?,?,?)",
            (owner, name, "", "", now()),
        )
    return profile_public(conn, owner)


def _contacts_for(conn, owner, account_id):
    linked = rows(
        conn,
        """SELECT c.* FROM account_contact c
           JOIN account_contact_link l ON l.contact_id = c.id
           WHERE l.owner_id = ? AND l.account_id = ? AND c.owner_id = ? AND c.status = 'active'
           ORDER BY c.primary_contact DESC, c.created_at""",
        (owner, account_id, owner),
    )
    return [_public_contact(item) for item in linked]


def _public_contact(item):
    return {
        "id": item["id"],
        "name": item.get("name") or "",
        "role": item.get("role") or "",
        "roleLabel": CONTACT_ROLES.get(item.get("role") or "", "Contato"),
        "roleNote": item.get("role_note") or "",
        "email": item.get("email") or "",
        "phone": item.get("phone") or "",
        "extension": item.get("extension") or "",
        "scope": item.get("scope") or "conta",
        "scopeLabel": CONTACT_SCOPES.get(item.get("scope") or "conta", "Esta conta"),
        "primary": bool(int(item.get("primary_contact") or 0)),
        "note": item.get("note") or "",
    }


def _save_contacts(conn, owner, account_id, incoming):
    if incoming is None:
        return
    if not isinstance(incoming, list):
        raise ValueError("Os contatos precisam estar em uma lista.")
    seen = []
    primary_used = False
    for raw in incoming:
        if not isinstance(raw, dict):
            raise ValueError("Um contato não foi reconhecido.")
        name = " ".join(str(raw.get("name") or "").split())
        role = raw.get("role") or ""
        email = _email_or_blank(raw.get("email"), "O e-mail do contato")
        phone = " ".join(str(raw.get("phone") or "").split())
        extension = " ".join(str(raw.get("extension") or "").split())
        note = " ".join(str(raw.get("note") or "").split())
        role_note = " ".join(str(raw.get("roleNote") or "").split())
        scope = raw.get("scope") or "conta"
        if scope not in CONTACT_SCOPES:
            raise ValueError("Diga se o contato atende a conta, a agência ou a instituição.")
        if role and role not in CONTACT_ROLES:
            raise ValueError("Escolha a função do contato.")
        if role == "outro" and not role_note and (name or email or phone):
            raise ValueError("Descreva a função quando escolher Outro.")
        if not any((name, role, email, phone, note, extension, role_note)):
            continue
        primary = bool(raw.get("primary")) and not primary_used
        if raw.get("primary"):
            primary_used = True
        contact_id = raw.get("id") or _id()
        current = one(conn, "SELECT id FROM account_contact WHERE id = ? AND owner_id = ?", (contact_id, owner))
        if current:
            conn.execute(
                """UPDATE account_contact
                   SET name = ?, role = ?, role_note = ?, email = ?, phone = ?, extension = ?, scope = ?,
                       primary_contact = ?, status = 'active', note = ?, updated_at = ?
                   WHERE id = ? AND owner_id = ?""",
                (name, role, role_note, email, phone, extension, scope, 1 if primary else 0, note, now(), contact_id, owner),
            )
        else:
            conn.execute(
                """INSERT INTO account_contact
                   (id, owner_id, name, role, role_note, email, phone, extension, scope, primary_contact, status, note, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (contact_id, owner, name, role, role_note, email, phone, extension, scope, 1 if primary else 0, "active", note, now(), now()),
            )
        conn.execute(
            "INSERT INTO account_contact_link (contact_id, account_id, owner_id) VALUES (?,?,?) ON CONFLICT (contact_id, account_id) DO NOTHING",
            (contact_id, account_id, owner),
        )
        seen.append(contact_id)
    linked = rows(conn, "SELECT contact_id FROM account_contact_link WHERE owner_id = ? AND account_id = ?", (owner, account_id))
    for item in linked:
        if item["contact_id"] in seen:
            continue
        conn.execute(
            "DELETE FROM account_contact_link WHERE owner_id = ? AND account_id = ? AND contact_id = ?",
            (owner, account_id, item["contact_id"]),
        )
        still = one(conn, "SELECT contact_id FROM account_contact_link WHERE owner_id = ? AND contact_id = ?", (owner, item["contact_id"]))
        if not still:
            conn.execute(
                "UPDATE account_contact SET status = 'inactive', updated_at = ? WHERE id = ? AND owner_id = ?",
                (now(), item["contact_id"], owner),
            )


def _public_account(conn, owner, item):
    last = one(conn, "SELECT updated_at FROM ledger_entry WHERE owner_id = ? AND account_id = ? ORDER BY updated_at DESC", (owner, item["id"]))
    balance = one(conn, "SELECT amount_cents, as_of, source FROM availability WHERE owner_id = ? AND account_id = ? AND active = 1", (owner, item["id"]))
    currency = item.get("currency") or "BRL"
    readers = "Arquivo CSV do Banco do Brasil, em Real." if currency == "BRL" else "Não há leitor de arquivo para esta moeda."
    number = item.get("account_number") or ""
    contacts = _contacts_for(conn, owner, item["id"])
    code = item.get("bank_code") or ""
    return {
        "id": item["id"],
        "name": item["name"],
        "nickname": item.get("nickname") or "",
        "institution": item.get("institution") or "",
        "bankCode": code,
        "bankCatalog": (catalog_str.BY_CODE.get(code) or [{}])[0].get("name", "") if code else "",
        "bankIspb": item.get("bank_ispb") or "",
        "country": item.get("country") or "",
        "agency": item.get("agency") or "",
        "agencyName": item.get("agency_name") or "",
        "accountNumber": number,
        "numberMasked": mask_account_number(number),
        "accountDigit": item.get("account_digit") or "",
        "kind": item.get("kind") or "corrente",
        "kindLabel": ACCOUNT_KINDS.get(item.get("kind") or "", item.get("kind") or "Conta"),
        "currency": currency,
        "currencyName": CURRENCIES.get(currency, {}).get("name", currency),
        "currencyLocked": _account_used(conn, owner, item["id"]),
        "intake": item.get("intake") or "manual",
        "intakeLabel": ACCOUNT_INTAKE.get(item.get("intake") or "manual", "Lançamento manual"),
        "status": item.get("status") or "active",
        "liquid": bool(int(item.get("liquid") or 0)) if item.get("kind") == "investimento" else True,
        "reader": readers,
        "formats": ["CSV do Banco do Brasil"] if currency == "BRL" else [],
        "ownerId": owner,
        "declared": True,
        "bankEmail": item.get("bank_email") or "",
        "agencyEmail": item.get("agency_email") or "",
        "agencyPhone": item.get("agency_phone") or "",
        "contacts": contacts,
        "contactCount": len(contacts),
        "connection": {
            "available": False,
            "state": "indisponível",
            "provider": "",
            "lastSuccess": "",
            "message": "Não há integração automática com este banco. Você pode importar um arquivo compatível.",
        },
        "lastImport": None if not last else last.get("updated_at"),
        "balance": None if not balance else {
            "cents": balance["amount_cents"],
            "asOf": balance["as_of"],
            "source": balance["source"],
            "meaning": "Valor informado para esta conta. Não é um saldo confirmado pelo banco.",
        },
    }


def list_accounts(conn, owner, requested=None):
    context = account_context(conn, owner, requested, persist=False)
    return {
        "accounts": context["accounts"],
        "context": context,
        "currencies": [{"code": code, "name": item["name"], "exponent": item["exponent"]} for code, item in CURRENCIES.items()],
        "profile": profile_public(conn, owner),
        "banks": catalog_str.public_banks(),
        "bankCatalog": catalog_str.summary(),
    }


def select_account(conn, owner, body):
    choice = body.get("context") or "all"
    return account_context(conn, owner, choice, persist=True)


def assign_records(conn, owner, body):
    account_id = _owned_account_id(conn, owner, body.get("accountId"))
    kind = body.get("kind")
    tables = {"commitment": "commitment", "inflow": "inflow", "entry": "ledger_entry"}
    if kind not in tables:
        raise ValueError("Escolha compromisso, entrada ou lançamento.")
    ids = [item for item in (body.get("ids") or []) if item]
    if not ids:
        raise ValueError("Escolha ao menos um registro.")
    table = tables[kind]
    preview = []
    for item_id in ids:
        current = one(conn, "SELECT * FROM " + table + " WHERE id = ? AND owner_id = ?", (item_id, owner))
        if not current:
            raise ValueError("Um dos registros não é desta pessoa.")
        if kind == "entry":
            payload = json.loads(current["payload_json"])
            preview.append({"id": item_id, "label": payload.get("merchant") or "Lançamento", "cents": payload.get("amountMinor"), "on": payload.get("noteDate") or payload.get("statusDate")})
        else:
            preview.append({"id": item_id, "label": current.get("label"), "cents": current.get("remaining_cents", current.get("amount_cents")), "on": current.get("due_on")})
    if not body.get("confirm"):
        return {"preview": preview, "accountId": account_id, "saved": False}
    for item_id in ids:
        if kind == "entry":
            current = one(conn, "SELECT payload_json FROM ledger_entry WHERE id = ? AND owner_id = ?", (item_id, owner))
            payload = json.loads(current["payload_json"])
            payload["accountId"] = account_id
            conn.execute("UPDATE ledger_entry SET account_id = ?, payload_json = ?, updated_at = ? WHERE id = ? AND owner_id = ?", (account_id, json.dumps(payload), now(), item_id, owner))
        else:
            conn.execute("UPDATE " + table + " SET account_id = ? WHERE id = ? AND owner_id = ?", (account_id, item_id, owner))
    _invalidate_suggestions(conn, owner, "Um registro mudou de conta.")
    return {"preview": preview, "accountId": account_id, "saved": True, "changed": len(ids)}


def describe_balance(conn, owner, reference, account_id=None, currency=None):
    accounts = _account_map(conn, owner)
    base = _base(conn, owner, account_id, currency)
    lines = []
    for item in rows(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1 AND account_id IS NOT NULL", (owner,)):
        account = accounts.get(item["account_id"])
        if not account or account.get("status") == "inactive":
            continue
        if account_id and item["account_id"] != account_id:
            continue
        if currency and account.get("currency") != currency:
            continue
        liquid = not (account.get("kind") == "investimento" and not int(account.get("liquid") or 0))
        lines.append({
            "accountId": item["account_id"],
            "name": account.get("name") or account.get("institution") or "Conta",
            "currency": account.get("currency") or "BRL",
            "cents": int(item["amount_cents"]),
            "asOf": item["as_of"],
            "source": item.get("source") or "",
            "protectedCents": int(item.get("protected_cents") or 0),
            "coversToday": item["as_of"] >= reference and liquid,
            "excluded": "" if liquid else "Investimento sem liquidez. Fica fora do utilizável.",
        })
    missing = []
    for account in accounts.values():
        if account.get("status") == "inactive":
            continue
        if account_id and account["id"] != account_id:
            continue
        if currency and account.get("currency") != currency:
            continue
        if account["id"] in {line["accountId"] for line in lines}:
            continue
        if account.get("kind") == "investimento" and not int(account.get("liquid") or 0):
            lines.append({
                "accountId": account["id"],
                "name": account.get("name") or "Investimento",
                "currency": account.get("currency") or "",
                "cents": None,
                "asOf": "",
                "source": "",
                "protectedCents": 0,
                "coversToday": False,
                "excluded": "Investimento sem liquidez. Fica fora do utilizável.",
            })
            continue
        missing.append({"accountId": account["id"], "name": account.get("name") or "Conta", "currency": account.get("currency") or ""})
    stale = any(line.get("asOf") and line["asOf"] < reference and not line.get("excluded") for line in lines)
    partial = bool(missing) or base.get("partial") or base.get("reason") == "reconciliar"
    usable = bool(base.get("known")) and not stale and not partial and base.get("reason") not in ("investimento", "reconciliar") and base.get("as_of") == reference
    if base.get("reason") == "investimento":
        label = "Valor investido"
    elif not lines and not base.get("known"):
        label = "Ainda não informado"
    elif partial:
        label = "Total conhecido"
    elif stale or (base.get("as_of") and base["as_of"] < reference):
        label = "Último saldo conhecido"
    else:
        label = "Disponível hoje"
    origin = ""
    source = base.get("source") or ""
    if source in ("declarada", "informada", "cenario-sintetico-004"):
        origin = "Informado por você"
    elif source == "contas":
        origin = "Soma das contas com referência"
    elif source:
        origin = "Registro " + source
    return {
        "label": label,
        "cents": base.get("amount_cents"),
        "asOf": base.get("as_of") or "",
        "origin": origin,
        "usableToday": usable,
        "partial": partial,
        "stale": stale or bool(base.get("as_of") and base["as_of"] < reference),
        "protectedCents": base.get("protected_cents") or 0,
        "lines": lines,
        "missing": missing,
        "reason": base.get("reason") or "",
    }


def calendar_month(value):
    text = str(value or "")
    if len(text) != 7 or text[4] != "-" or not text[:4].isdigit() or not text[5:7].isdigit():
        raise ValueError("O mês informado não é válido.")
    year = int(text[:4])
    mon = int(text[5:7])
    if year < 2000 or year > 2100 or mon < 1 or mon > 12:
        raise ValueError("O mês informado não é válido.")
    return text


def _payload(text):
    try:
        loaded = json.loads(text or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def month_picture(conn, owner, month, reference, account_id=None):
    month = calendar_month(month)
    start = month + "-01"
    year, mon = [int(part) for part in month.split("-")]
    if mon == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{mon + 1:02d}-01"
    phase = "atual" if month == reference[:7] else ("passado" if month < reference[:7] else "futuro")
    accounts = {}
    for item in rows(conn, "SELECT id, payload_json FROM occurrence WHERE owner_id = ?", (owner,)):
        payload = _payload(item["payload_json"])
        accounts[item["id"]] = payload.get("accountId") or ""
    seen = set()
    realized_in = realized_out = 0
    forecast_in = forecast_out = 0
    pending_nature = 0
    records = []
    for row in rows(conn, "SELECT * FROM movement WHERE owner_id = ? AND booked_on >= ? AND booked_on < ?", (owner, start, end)):
        account = accounts.get(row["occurrence_id"]) or ""
        if account_id and account != account_id:
            continue
        nature = row["nature"] or ""
        booked = row["booked_on"] or ""
        future = booked > reference
        transfer = nature in ("transferencia", "reembolso", "emprestimo")
        rende = nature == "bb_rende_facil"
        unknown = nature in ("", "a_conferir")
        amount = int(row["amount_cents"] or 0)
        direction = row["direction"]
        state = "previsto" if future else "realizado"
        if future:
            state = "data futura"
        elif transfer:
            state = "transferência"
        elif rende:
            state = "aplicação"
        if state == "realizado" and not transfer and not rende:
            if unknown:
                pending_nature += amount
            elif direction == "entrada":
                realized_in += amount
            else:
                realized_out += amount
        records.append({
            "id": row["id"],
            "on": booked,
            "label": row["label"],
            "cents": amount,
            "direction": direction,
            "state": state,
            "nature": nature,
        })
        seen.add(row["occurrence_id"])
    for item in rows(conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ?", (owner,)):
        payload = _payload(item["payload_json"])
        if payload.get("occurrenceId") in seen or payload.get("archived"):
            continue
        when = payload.get("statusDate") or payload.get("noteDate") or ""
        if not when.startswith(month):
            continue
        if account_id and (payload.get("accountId") or "") != account_id:
            continue
        amount = int(payload.get("amountMinor") or 0)
        direction = "entrada" if payload.get("direction") == "ganho" or payload.get("status") == "recebido" else "saida"
        nature = payload.get("nature") or ""
        future = when > reference
        transfer = nature in ("transferencia", "reembolso", "emprestimo")
        state = "data futura" if future else ("transferência" if transfer else "realizado")
        if state == "realizado" and not transfer and nature != "bb_rende_facil":
            if nature in ("", "a_conferir"):
                pending_nature += amount
            elif direction == "entrada":
                realized_in += amount
            else:
                realized_out += amount
        records.append({"id": payload.get("id") or "", "on": when, "label": payload.get("merchant") or "Lançamento", "cents": amount, "direction": direction, "state": state, "nature": nature})
    open_items = []
    for item in rows(conn, "SELECT * FROM commitment WHERE owner_id = ?", (owner,)):
        due = item["due_on"] or ""
        if account_id and (item.get("account_id") or "") != account_id:
            continue
        remaining = item["remaining_cents"]
        if remaining in (None, 0):
            continue
        if due and start <= due < end:
            label_state = "em aberto" if due <= reference else "previsto"
            if phase == "futuro":
                label_state = "previsto"
            forecast_out += int(remaining)
            open_items.append({"id": item["id"], "on": due, "label": item["label"], "cents": int(remaining), "direction": "saida", "state": label_state})
        elif due and due < start and phase != "futuro":
            open_items.append({"id": item["id"], "on": due, "label": item["label"], "cents": int(remaining), "direction": "saida", "state": "vencido"})
    for item in rows(conn, "SELECT * FROM inflow WHERE owner_id = ?", (owner,)):
        due = item["due_on"] or ""
        if account_id and (item.get("account_id") or "") != account_id:
            continue
        if not due or not (start <= due < end) or item["amount_cents"] is None:
            continue
        state = "previsto" if item["state"] == "confirmada" else "incerta"
        if item["state"] == "confirmada" and due > reference:
            forecast_in += int(item["amount_cents"])
        open_items.append({"id": item["id"], "on": due, "label": item["label"], "cents": int(item["amount_cents"]), "direction": "entrada", "state": state})
    records.extend(open_items)
    records.sort(key=lambda item: (item.get("on") or "9999", item.get("label") or ""))
    return {
        "month": month,
        "phase": phase,
        "realizedIn": realized_in,
        "realizedOut": realized_out,
        "forecastIn": forecast_in,
        "forecastOut": forecast_out,
        "pendingNatureCents": pending_nature,
        "records": records,
        "emptyForecast": phase == "futuro" and not open_items,
    }


def person_presence(conn, owner):
    def count(sql):
        row = one(conn, sql, (owner,))
        return int((row or {}).get("n") or 0)

    accounts = count("SELECT COUNT(*) AS n FROM account WHERE owner_id = ? AND COALESCE(status, 'active') != 'inactive'")
    movements = count("SELECT COUNT(*) AS n FROM movement WHERE owner_id = ?")
    commitments = count("SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ?")
    inflows = count("SELECT COUNT(*) AS n FROM inflow WHERE owner_id = ?")
    entries = count("SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?")
    balances = count("SELECT COUNT(*) AS n FROM availability WHERE owner_id = ? AND active = 1")
    unassigned = count("SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ? AND account_id IS NULL AND COALESCE(remaining_cents, 0) != 0")
    unassigned += count("SELECT COUNT(*) AS n FROM movement WHERE owner_id = ? AND (occurrence_id IS NULL OR occurrence_id = '')")
    financial = bool(movements or commitments or inflows or entries or balances)
    return {
        "accounts": accounts,
        "movements": movements,
        "commitments": commitments,
        "inflows": inflows,
        "entries": entries,
        "balances": balances,
        "unassignedRecords": unassigned,
        "hasFinancialRecord": financial,
        "emptyPerson": accounts == 0 and not financial,
    }


def home(conn, owner, reference=None, account=None):
    reference = reference or reference_date()
    context = account_context(conn, owner, account, persist=account not in (None, ""))
    context["unassignedCommitments"] = len(rows(conn, "SELECT id FROM commitment WHERE owner_id = ? AND account_id IS NULL", (owner,)))
    account_id = context["accountId"] or None
    currencies = _active_currencies(conn, owner)
    if context["scope"] == "all" and len(currencies) > 1:
        groups = [_currency_home(conn, owner, reference, code) for code in currencies]
        page = _assemble_home(conn, owner, reference, groups[0]["projection"], groups[0]["guide"], groups[0]["commitments"], groups[0]["inflows"], context)
        facts = []
        for item in groups:
            for insight in item["overview"].get("insightHistory") or item["overview"].get("insights") or []:
                copied = dict(insight)
                copied["id"] = item["currency"] + "-" + str(insight.get("id"))
                copied["title"] = CURRENCIES[item["currency"]]["name"] + ": " + str(insight.get("title") or "")
                facts.append(copied)
        page["groups"] = [{"currency": item["currency"], "name": CURRENCIES[item["currency"]]["name"], "overview": item["overview"]} for item in groups]
        page["overview"] = {
            "kind": "moedas",
            "reference": reference,
            "fingerprint": "|".join((item["overview"].get("fingerprint") or "") for item in groups),
            "groups": page["groups"],
            "situation": {"kind": "partial", "text": "Há mais de uma moeda. Os valores não foram somados."},
            "informed": None,
            "payables": {},
            "insights": facts,
            "insightHistory": facts,
            "context": context,
        }
        page["balance"] = {"label": "Moedas separadas", "usableToday": False, "partial": True, "lines": [], "missing": [], "cents": None, "asOf": "", "origin": "", "protectedCents": 0, "stale": False, "reason": "moedas"}
        page["month"] = {"month": reference[:7], "phase": "atual", "records": [], "realizedIn": 0, "realizedOut": 0, "forecastIn": 0, "forecastOut": 0, "pendingNatureCents": 0, "emptyForecast": False}
        return page
    currency = context.get("currency") or None
    if context["scope"] == "all" and currencies == ["BRL"]:
        currency = "BRL"
    result = projection(conn, owner, reference, account_id=account_id, currency=currency if context["scope"] == "all" else None)
    inflows, commitments = _scoped_plans(conn, owner, account_id, currency if context["scope"] == "all" else None)
    guide = planning_guide(conn, owner, inflows, commitments, account_id, currency if context["scope"] == "all" else None)
    page = _assemble_home(conn, owner, reference, result, guide, commitments, inflows, context)
    outside = _outside_count(conn, owner, account_id)
    if account_id and outside:
        state = page["overview"]["situation"]
        note = "Há " + str(outside) + (" compromisso sem conta, fora desta visão." if outside == 1 else " compromissos sem conta, fora desta visão.")
        if state.get("kind") == "covers":
            page["overview"]["situation"] = {"kind": "partial", "text": "Nesta conta, os compromissos vinculados cabem no período. " + note}
        else:
            state["outsideText"] = note
        page["overview"]["outsideCommitments"] = outside
    if result.get("reason") == "investimento":
        page["overview"]["position"] = result.get("position")
        page["overview"]["situation"] = {"kind": "partial", "text": "O valor investido não entra na margem disponível. Informe a liquidez se ele puder pagar compromissos."}
    if result.get("reason") == "reconciliar":
        page["overview"]["situation"] = {"kind": "partial", "text": "Há um disponível da pessoa e disponíveis por conta. Eles não foram somados. Reconcile a declaração."}
        page["overview"]["informed"] = None
    page["balance"] = describe_balance(conn, owner, reference, account_id, currency if context["scope"] == "all" else None)
    page["month"] = month_picture(conn, owner, reference[:7], reference, account_id)
    return page


def _assemble_home(conn, owner, reference, result, guide, commitments, inflows, context):
    explanation = explain_current(result)
    observations = rows(conn, "SELECT id, amount_cents, as_of, kind, source FROM balance_observation WHERE owner_id = ? ORDER BY as_of", (owner,))
    pending = rows(conn, "SELECT id, signature, state FROM occurrence WHERE owner_id = ? AND state = 'pendente'", (owner,))
    chosen = one(conn, "SELECT id, name, note FROM scenario WHERE owner_id = ? AND chosen = 1", (owner,))
    overview = build_overview(result.get("reference") or reference, result, guide, commitments, inflows)
    hidden = _draft_body(conn, owner, "insights-hoje")
    dismissed = hidden.get("dismissed") if hidden.get("day") == overview["reference"] and isinstance(hidden.get("dismissed"), list) else []
    overview["insightHistory"] = overview["insights"]
    overview["insights"] = [item for item in overview["insights"] if item["id"] not in dismissed]
    overview["dismissed"] = dismissed
    account_key = (context or {}).get("accountId") or "all"
    for reading in rows(conn, "SELECT status, result_json, payload_json, created_at FROM ai_job WHERE owner_id = ? AND kind = 'insight' ORDER BY created_at DESC LIMIT 30", (owner,)):
        loaded = json.loads(reading["payload_json"])
        if (loaded.get("account") or "all") != account_key:
            continue
        reading_result = json.loads(reading["result_json"]) if reading.get("result_json") else None
        overview["reading"] = {"status": reading["status"], "day": loaded.get("day"), "createdAt": reading["created_at"], "stale": loaded.get("day") != overview["reference"] or loaded.get("fingerprint") != overview.get("fingerprint"), "explanation": (reading_result or {}).get("explanation")}
        break
    overview["context"] = context
    return {
        "projection": result,
        "explanation": explanation,
        "observations": observations,
        "pending": pending,
        "chosenPlan": chosen,
        "commitments": commitments,
        "inflows": inflows,
        "guide": guide,
        "overview": overview,
        "context": context,
        "saveState": "salvo",
        "profile": profile_public(conn, owner),
        "ownerId": owner,
        "presence": person_presence(conn, owner),
    }


def snapshot(conn, owner):
    return {
        "availability": rows(conn, "SELECT * FROM availability WHERE owner_id = ?", (owner,)),
        "inflows": rows(conn, "SELECT * FROM inflow WHERE owner_id = ?", (owner,)),
        "commitments": rows(conn, "SELECT * FROM commitment WHERE owner_id = ?", (owner,)),
        "reserves": rows(conn, "SELECT * FROM reserve WHERE owner_id = ?", (owner,)),
        "scenarios": rows(conn, "SELECT id, name, chosen, note, engine_version FROM scenario WHERE owner_id = ?", (owner,)),
        "batches": rows(conn, "SELECT * FROM batch WHERE owner_id = ?", (owner,)),
        "occurrences": rows(conn, "SELECT id, state, signature FROM occurrence WHERE owner_id = ?", (owner,)),
        "movements": rows(conn, "SELECT id, amount_cents, occurrence_id FROM movement WHERE owner_id = ?", (owner,)),
        "links": rows(conn, "SELECT * FROM link_row WHERE owner_id = ?", (owner,)),
        "suggestions": rows(conn, "SELECT id, status, revision_of, content, origin FROM suggestion WHERE owner_id = ?", (owner,)),
        "suggestionEvents": rows(conn, "SELECT suggestion_id, event FROM suggestion_event WHERE owner_id = ?", (owner,)),
        "drafts": rows(conn, "SELECT key, body_json FROM draft WHERE owner_id = ?", (owner,)),
        "files": rows(conn, "SELECT id, sha256, byte_length, label FROM stored_file WHERE owner_id = ?", (owner,)),
    }


def store_file(conn, root, owner, label, blob):
    if not str(label).startswith("sintetico"):
        raise ValueError("Nesta etapa a base demonstrativa só guarda arquivo sintético.")
    digest = hashlib.sha256(blob).hexdigest()
    file_id = _id()
    relative = os.path.join("files", owner, file_id)
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(blob)
    conn.execute(
        "INSERT INTO stored_file (id, owner_id, sha256, label, byte_length, relative_path, retention, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (file_id, owner, digest, label, len(blob), relative.replace("\\", "/"), RETENTION, now()),
    )
    return {"id": file_id, "sha256": digest, "byteLength": len(blob)}


def add_feedback(conn, owner, body):
    text = " ".join(str(body.get("text") or "").split())
    if not text:
        raise ValueError("Escreva o recado. Um texto vazio não é enviado.")
    if len(text) > 1000:
        raise ValueError("O recado cabe em mil caracteres.")
    item_id = _id()
    conn.execute(
        "INSERT INTO feedback (id, owner_id, body, created_at) VALUES (?,?,?,?)",
        (item_id, owner, text, now()),
    )
    log(conn, owner, "feedback", item_id, "criar", None, {"chars": len(text)})
    return {"id": item_id, "saved": True}


def ensure_identity(conn, sub):
    current = one(conn, "SELECT owner_id FROM identity WHERE sub = ?", (sub,))
    if current:
        return current["owner_id"]
    owner = "pessoa-" + hashlib.sha256(sub.encode("utf-8")).hexdigest()[:24]
    conn.execute(
        "INSERT INTO identity (sub, owner_id, created_at) VALUES (?,?,?)",
        (sub, owner, now()),
    )
    return owner


def start_attempt(conn, verifier):
    state = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO login_attempt (state, verifier, created_at, used) VALUES (?,?,?,?)",
        (state, verifier, now(), 0),
    )
    return state


def take_attempt(conn, state):
    row = one(conn, "SELECT * FROM login_attempt WHERE state = ?", (state,))
    if not row or row["used"]:
        return None
    created = datetime.fromisoformat(row["created_at"])
    if datetime.now(timezone.utc) - created > timedelta(minutes=10):
        return None
    claimed = conn.execute(
        "UPDATE login_attempt SET used = 1 WHERE state = ? AND used = 0 RETURNING state",
        (state,),
    ).fetchone()
    return row if claimed else None


def save_session(conn, owner, sub, expires_at):
    item_id = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO app_session (id, owner_id, sub, expires_at, created_at) VALUES (?,?,?,?,?)",
        (item_id, owner, sub, expires_at, now()),
    )
    return item_id


def read_session(conn, session_id):
    row = one(conn, "SELECT * FROM app_session WHERE id = ?", (session_id,))
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        conn.execute("DELETE FROM app_session WHERE id = ?", (session_id,))
        return None
    if row["owner_id"] in _erased:
        return None
    return row


def drop_session(conn, session_id):
    conn.execute("DELETE FROM app_session WHERE id = ?", (session_id,))


def _account_used(conn, owner, account_id):
    if one(conn, "SELECT id FROM ledger_entry WHERE owner_id = ? AND account_id = ?", (owner, account_id)):
        return True
    if one(conn, "SELECT id FROM commitment WHERE owner_id = ? AND account_id = ?", (owner, account_id)):
        return True
    return bool(one(conn, "SELECT id FROM inflow WHERE owner_id = ? AND account_id = ?", (owner, account_id)))


def _paired_bank(body, current):
    code = " ".join(str(body.get("bankCode") if "bankCode" in body else (current or {}).get("bank_code") or "").split())
    institution = " ".join(str(body.get("institution") if "institution" in body else (current or {}).get("institution") or "").split())
    ispb = str(body.get("bankIspb") if "bankIspb" in body else (current or {}).get("bank_ispb") or "").strip()
    chosen = catalog_str.match_choice(code, institution, ispb)
    if chosen:
        return chosen["name"], chosen["code"], chosen["ispb"]
    same = bool(current) and institution == (current.get("institution") or "") and code == (current.get("bank_code") or "") and ispb == (current.get("bank_ispb") or "")
    if same or not (code or institution or ispb):
        return institution, code, ispb
    raise ValueError("O banco escolhido não confere com o código.")


def _account_fields(body, current, registration):
    if registration:
        institution, paired_code, paired_ispb = _paired_bank(body, current)
    else:
        institution = " ".join(str(body.get("institution") if "institution" in body else (current or {}).get("institution") or "").split())
        paired_code = None
        paired_ispb = None
    number = str(body.get("accountNumber") if "accountNumber" in body else (current or {}).get("account_number") or "").strip()
    if len(number) > 40:
        raise ValueError("O número da conta está longo demais.")
    kind = body.get("kind") if "kind" in body else (current or {}).get("kind")
    if registration and not current:
        if not institution:
            raise ValueError("Escolha um banco da lista.")
        if not number:
            raise ValueError("Informe o número da conta.")
        if kind not in ACCOUNT_KINDS:
            raise ValueError("Escolha o tipo da conta.")
    elif registration and kind not in ACCOUNT_KINDS:
        raise ValueError("Escolha o tipo da conta.")
    elif kind and kind not in ACCOUNT_KINDS:
        raise ValueError("Escolha o tipo da conta.")
    kind = kind or (current or {}).get("kind") or "corrente"
    currency = str(body.get("currency") or (current or {}).get("currency") or "BRL").upper()
    if currency not in CURRENCIES:
        raise ValueError("Escolha Real, Dólar americano ou Euro.")
    intake = body.get("intake") or (current or {}).get("intake") or "manual"
    if intake not in ACCOUNT_INTAKE:
        raise ValueError("Escolha lançamento manual ou importação por arquivo.")
    nickname = " ".join(str(body.get("nickname") if "nickname" in body else (current or {}).get("nickname") or "").split())
    if registration:
        name = account_label(institution, number, nickname)
    else:
        name = " ".join(str(body.get("name") or "").split()) or (current or {}).get("name") or account_label(institution, number, nickname)
    if kind == "investimento":
        liquid = 1 if body.get("liquid") else 0
        if current and "liquid" not in body:
            liquid = int(current.get("liquid") or 0)
    else:
        liquid = 1
    code = paired_code if registration else " ".join(str(body.get("bankCode") if "bankCode" in body else (current or {}).get("bank_code") or "").split())
    if not registration and code and code not in catalog_str.BY_CODE and not re.fullmatch(r"[A-Za-z0-9]{1,12}", code):
        raise ValueError("O código do banco usa letras ou números, sem o número da conta.")
    return {
        "name": name,
        "nickname": nickname,
        "institution": institution,
        "account_number": number,
        "kind": kind,
        "currency": currency,
        "intake": intake,
        "liquid": liquid,
        "country": " ".join(str(body.get("country") if "country" in body else (current or {}).get("country") or "").split())[:60],
        "bank_code": code,
        "bank_ispb": paired_ispb if registration else str(body.get("bankIspb") if "bankIspb" in body else (current or {}).get("bank_ispb") or "").strip()[:8],
        "agency": str(body.get("agency") if "agency" in body else (current or {}).get("agency") or "").strip()[:20],
        "agency_name": " ".join(str(body.get("agencyName") if "agencyName" in body else (current or {}).get("agency_name") or "").split())[:80],
        "account_digit": str(body.get("accountDigit") if "accountDigit" in body else (current or {}).get("account_digit") or "").strip()[:8],
        "bank_email": _email_or_blank(body.get("bankEmail") if "bankEmail" in body else (current or {}).get("bank_email"), "O e-mail do banco"),
        "agency_email": _email_or_blank(body.get("agencyEmail") if "agencyEmail" in body else (current or {}).get("agency_email"), "O e-mail da agência"),
        "agency_phone": " ".join(str(body.get("agencyPhone") if "agencyPhone" in body else (current or {}).get("agency_phone") or "").split())[:40],
    }


def save_account(conn, owner, body):
    if body.get("ownerId") or body.get("owner_id"):
        raise ValueError("A conta continua com a mesma pessoa.")
    item_id = body.get("id") or _id()
    current = one(conn, "SELECT * FROM account WHERE id = ? AND owner_id = ?", (item_id, owner))
    if current and not body.get("edit"):
        return current
    fields = _account_fields(body, current, bool(body.get("registration")))
    if current:
        if fields["currency"] != current["currency"] and _account_used(conn, owner, item_id):
            raise ValueError("Esta conta já tem movimentação. A moeda permanece a mesma.")
        if current.get("account_number") and "accountNumber" in body and not fields["account_number"]:
            raise ValueError("O número da conta permanece até você informar outro.")
        status = body.get("status") or current.get("status") or "active"
        if status not in ("active", "inactive"):
            raise ValueError("A situação da conta não foi reconhecida.")
        conn.execute(
            """UPDATE account SET name = ?, institution = ?, kind = ?, currency = ?, intake = ?, status = ?, liquid = ?, updated_at = ?,
               account_number = ?, country = ?, bank_code = ?, bank_ispb = ?, agency = ?, agency_name = ?, account_digit = ?, nickname = ?,
               bank_email = ?, agency_email = ?, agency_phone = ?
               WHERE id = ? AND owner_id = ?""",
            (
                fields["name"], fields["institution"], fields["kind"], fields["currency"], fields["intake"], status, fields["liquid"], now(),
                fields["account_number"], fields["country"], fields["bank_code"], fields["bank_ispb"], fields["agency"], fields["agency_name"], fields["account_digit"], fields["nickname"],
                fields["bank_email"], fields["agency_email"], fields["agency_phone"], item_id, owner,
            ),
        )
    else:
        if not body.get("registration") and not fields["name"]:
            raise ValueError("A conta precisa de um nome.")
        conn.execute(
            """INSERT INTO account (
                 id, owner_id, name, currency, created_at, institution, kind, intake, status, liquid, updated_at,
                 account_number, country, bank_code, bank_ispb, agency, agency_name, account_digit, nickname, bank_email, agency_email, agency_phone
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item_id, owner, fields["name"], fields["currency"], now(), fields["institution"], fields["kind"], fields["intake"], "active", fields["liquid"], now(),
                fields["account_number"], fields["country"], fields["bank_code"], fields["bank_ispb"], fields["agency"], fields["agency_name"], fields["account_digit"], fields["nickname"],
                fields["bank_email"], fields["agency_email"], fields["agency_phone"],
            ),
        )
    if "contacts" in body:
        _save_contacts(conn, owner, item_id, body.get("contacts"))
    return owned(conn, "account", owner, item_id)


def save_catalog_request(conn, owner, body):
    query = " ".join(str((body or {}).get("query") or "").split())[:120]
    if len(query) < 2:
        raise ValueError("Escreva o nome ou o código que não encontrou.")
    item_id = "pedido-" + uuid.uuid4().hex[:16]
    conn.execute(
        "INSERT INTO catalog_request (id, owner_id, query, created_at) VALUES (?,?,?,?)",
        (item_id, owner, query, now()),
    )
    return {"ok": True, "id": item_id}


def account_detail(conn, owner, account_id):
    current = one(conn, "SELECT * FROM account WHERE id = ? AND owner_id = ?", (account_id, owner))
    if not current:
        return None
    return {"account": _public_account(conn, owner, current), "profile": profile_public(conn, owner)}


def save_entry(conn, owner, body):
    import workbatches
    payload = dict(body)
    payload.pop("ownerId", None)
    payload.pop("owner_id", None)
    explicit_batch = "workBatchId" in payload
    requested_batch = payload.pop("workBatchId", None) if explicit_batch else None
    item_id = payload.get("id") or _id()
    payload["id"] = item_id
    payload["ownerId"] = owner
    if explicit_batch and requested_batch:
        workbatches.require_batch(conn, owner, requested_batch)
    current = one(conn, "SELECT id, payload_json FROM ledger_entry WHERE id = ? AND owner_id = ?", (item_id, owner))
    previous = json.loads(current["payload_json"]) if current else None
    account_id = payload.get("accountId") or ""
    if account_id:
        account = one(conn, "SELECT * FROM account WHERE id = ? AND owner_id = ?", (account_id, owner))
        if not account:
            raise ValueError("Escolha uma conta sua.")
        if payload.get("currency") and payload.get("currency") != account["currency"]:
            raise ValueError("O lançamento precisa usar a moeda da conta.")
        payload["currency"] = account["currency"]
    else:
        payload["accountId"] = ""
        payload["currency"] = payload.get("currency") or "BRL"
    conn.execute("BEGIN IMMEDIATE")
    try:
        if previous and payload.get("category") != previous.get("category"):
            payload["userLocked"] = True
            payload["categoryOrigin"] = "pessoa"
            payload.pop("aiReason", None)
            payload.pop("aiSuggestionId", None)
            log(conn, owner, "ledger_entry", item_id, "categoria-corrigida", previous, payload)
        elif previous and previous.get("userLocked"):
            payload["userLocked"] = True
        if current:
            conn.execute(
                "UPDATE ledger_entry SET account_id = ?, payload_json = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
                (account_id, json.dumps(payload), now(), item_id, owner),
            )
        else:
            conn.execute(
                "INSERT INTO ledger_entry (id, owner_id, account_id, payload_json, updated_at) VALUES (?,?,?,?,?)",
                (item_id, owner, account_id, json.dumps(payload), now()),
            )
        if explicit_batch and requested_batch:
            linked = workbatches.remember_link(conn, owner, item_id, requested_batch)
        else:
            linked = workbatches.active_batch_id(conn, owner, item_id) or (previous or {}).get("workBatchId") or ""
        payload["workBatchId"] = linked or ""
        conn.execute(
            "UPDATE ledger_entry SET payload_json = ? WHERE id = ? AND owner_id = ?",
            (json.dumps(payload), item_id, owner),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return payload


def sync_entries(conn, owner):
    known = set()
    for item in rows(conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ?", (owner,)):
        known.add(json.loads(item["payload_json"]).get("occurrenceId"))
    for item in rows(conn, "SELECT id, state, movement_id, payload_json FROM occurrence WHERE owner_id = ?", (owner,)):
        if item["state"] != "incorporada" or item["id"] in known:
            continue
        payload = json.loads(item["payload_json"])
        direction = payload.get("direction") or "saida"
        save_entry(conn, owner, {
            "id": item["movement_id"] or _id(),
            "accountId": payload.get("accountId") or "",
            "occurrenceId": item["id"],
            "lineSignature": item.get("signature") if False else payload.get("signature") or "",
            "direction": "ganho" if direction == "entrada" else "gasto",
            "nature": payload.get("nature") or "a_conferir",
            "merchant": payload.get("label") or payload.get("history") or "",
            "noteDate": payload.get("date") or "",
            "dueDate": "",
            "statusDate": payload.get("date") or "",
            "amountMinor": abs(int(payload.get("cents") or 0)),
            "currency": "BRL",
            "category": "",
            "categorizationStatus": "a_categorizar",
            "status": "recebido" if direction == "entrada" else "pago",
            "source": payload.get("source") or "",
            "simulated": (payload.get("source") or "") == "exemplo-sintetico",
            "bankDocument": payload.get("document") or "",
            "archived": False,
            "updatedAt": now(),
        })


def import_statement(conn, owner, body):
    requested = dict(body.get("account") or {})
    if requested.get("id"):
        account = one(conn, "SELECT * FROM account WHERE id = ? AND owner_id = ?", (requested["id"], owner))
        if not account:
            raise ValueError("Escolha uma conta sua.")
        if account.get("currency") != "BRL":
            raise ValueError("Este arquivo está em Real. A conta escolhida usa outra moeda.")
        if account.get("status") == "inactive":
            raise ValueError("Esta conta está inativa. Escolha outra conta em Real.")
    else:
        if str(requested.get("currency") or "BRL").upper() != "BRL":
            raise ValueError("Este arquivo está em Real. Ele não entra numa conta em outra moeda.")
        if not " ".join(str(requested.get("name") or "").split()):
            raise ValueError("Dê um nome à conta antes de importar.")
        requested["currency"] = "BRL"
        requested["intake"] = "arquivo"
        requested["kind"] = requested.get("kind") or "corrente"
        account = save_account(conn, owner, requested)
    movements = []
    for row in body.get("movements") or []:
        item = dict(row)
        item["accountId"] = account["id"]
        item["batchId"] = body.get("batchKey")
        item["source"] = body.get("origin") or "exemplo-sintetico"
        movements.append(item)
    result = import_batch(conn, owner, {
        "batchKey": body.get("batchKey"),
        "origin": body.get("origin") or "exemplo-sintetico",
        "movements": movements,
    })
    for note in body.get("notes") or []:
        signature = note.get("signature")
        if not signature or one(conn, "SELECT id FROM statement_note WHERE owner_id = ? AND signature = ?", (owner, signature)):
            continue
        payload = dict(note)
        payload["ownerId"] = owner
        payload["accountId"] = account["id"]
        conn.execute(
            "INSERT INTO statement_note (id, owner_id, account_id, signature, payload_json) VALUES (?,?,?,?,?)",
            (_id(), owner, account["id"], signature, json.dumps(payload)),
        )
    result["workspace"] = workspace(conn, owner)
    return result


def workspace(conn, owner, account=None):
    context = account_context(conn, owner, account, persist=False)
    entries = [json.loads(item["payload_json"]) for item in rows(conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ? ORDER BY updated_at", (owner,))]
    occurrences = []
    for item in rows(conn, "SELECT id, signature, state, movement_id, payload_json FROM occurrence WHERE owner_id = ?", (owner,)):
        payload = json.loads(item["payload_json"])
        occurrences.append({
            "id": item["id"],
            "ownerId": owner,
            "accountId": payload.get("accountId") or "",
            "batchId": payload.get("batchId") or "",
            "signature": item["signature"],
            "date": payload.get("date"),
            "history": payload.get("label") or payload.get("history") or "",
            "cents": payload.get("cents"),
            "class": "entrada" if payload.get("direction") == "entrada" else "saida",
            "family": payload.get("nature") if payload.get("nature") not in (None, "a_conferir") else "",
            "document": payload.get("document") or "",
            "source": payload.get("source") or "",
            "simulated": payload.get("source") == "exemplo-sintetico",
            "state": item["state"],
            "movementId": item["movement_id"] or "",
            "decided": item["state"] != "pendente",
        })
    notes = [json.loads(item["payload_json"]) for item in rows(conn, "SELECT payload_json FROM statement_note WHERE owner_id = ?", (owner,))]
    batches = rows(conn, "SELECT id, batch_key, origin, imported, pending FROM batch WHERE owner_id = ?", (owner,))
    account_by_batch = {}
    for item in occurrences:
        if item["batchId"]:
            account_by_batch[item["batchId"]] = item["accountId"]
    if context["scope"] == "account":
        entries = [item for item in entries if (item.get("accountId") or "") == context["accountId"]]
        occurrences = [item for item in occurrences if (item.get("accountId") or "") == context["accountId"]]
    return {
        "ownerId": owner,
        "accounts": context["accounts"],
        "context": context,
        "entries": entries,
        "occurrences": occurrences,
        "notes": notes,
        "batches": [{
            "ownerId": owner,
            "accountId": account_by_batch.get(item["batch_key"], ""),
            "batchId": item["batch_key"],
            "imported": item["imported"],
            "pending": item["pending"],
        } for item in batches],
        "profile": profile_public(conn, owner),
        "banks": catalog_str.public_banks(),
        "bankCatalog": catalog_str.summary(),
        "workBatches": __import__("workbatches").list_batches(conn, owner),
    }


def load_october(conn, owner):
    """Fixture explícita. Não lê sessionStorage nem extrato real."""
    if one(conn, "SELECT id FROM commitment WHERE owner_id = ? AND origin = ?", (owner, "cenario-sintetico-004")):
        return home(conn, owner)
    save_availability(conn, owner, {"amountCents": 60000, "asOf": "2026-10-16", "protectedCents": 10000, "source": "cenario-sintetico-004"})
    add_inflow(conn, owner, {"label": "Pagamento", "amountCents": 120000, "dueOn": "2026-10-25", "state": "confirmada", "origin": "cenario-sintetico-004"})
    add_inflow(conn, owner, {"label": "Talvez um extra", "amountCents": 40000, "dueOn": "2026-10-27", "state": "incerta", "origin": "cenario-sintetico-004"})
    add_commitment(conn, owner, {"label": "Luz", "totalCents": 20000, "dueOn": "2026-10-18", "origin": "cenario-sintetico-004"})
    add_commitment(conn, owner, {"label": "Aluguel", "totalCents": 50000, "dueOn": "2026-10-20", "essential": True, "origin": "cenario-sintetico-004"})
    add_commitment(conn, owner, {"label": "Mercado", "totalCents": 30000, "dueOn": "2026-10-28", "origin": "cenario-sintetico-004"})
    add_commitment(conn, owner, {"label": "Condomínio", "totalCents": 10000, "dueOn": "2026-11-05", "origin": "cenario-sintetico-004"})
    add_reserve(conn, owner, {"label": "Reserva já contada", "amountCents": 10000, "usableCents": 10000, "availableOn": "2026-10-16", "includedInBase": True, "kindDetail": "reserva"})
    return home(conn, owner)


OWNER_TABLES = (
    "availability", "balance_observation", "inflow", "commitment", "reserve", "scenario",
    "occurrence", "movement", "link_row", "draft", "suggestion_event", "suggestion",
    "stored_file", "change_log", "idempotency", "batch", "account", "ledger_entry",
    "statement_note", "feedback", "app_session", "ai_job", "account_preference",
    "person_profile", "account_contact", "account_contact_link",
    "work_event", "work_member", "work_batch", "work_preference", "catalog_request",
)


def ledger_path():
    path = os.environ.get("ISA_ERASURE_LEDGER")
    if not path:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "erasure-ledger.jsonl")
    return os.path.abspath(path)


class LedgerError(RuntimeError):
    pass


def record_erasure(owner):
    body = json.dumps({"owner": owner, "at": now()}).encode("utf-8")
    bucket = os.environ.get("ISA_BACKUP_BUCKET") or ""
    if bucket:
        import boto3
        key = "erasures/" + hashlib.sha256(owner.encode("utf-8")).hexdigest() + ".json"
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=body, ServerSideEncryption="AES256")
        return
    path = ledger_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(body.decode("utf-8") + "\n")


def erased_owners():
    bucket = os.environ.get("ISA_BACKUP_BUCKET") or ""
    if bucket:
        print("ISA erasure ledger read", flush=True)
        try:
            import boto3
            client = boto3.client("s3")
            found = set()
            pages = client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="erasures/")
            for page in pages:
                for item in page.get("Contents") or []:
                    payload = client.get_object(Bucket=bucket, Key=item["Key"])["Body"].read()
                    found.add(json.loads(payload)["owner"])
            return found
        except Exception as exc:
            raise LedgerError("Não foi possível ler o livro de exclusões.") from exc
    path = ledger_path()
    if not os.path.isfile(path):
        return set()
    try:
        found = set()
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    found.add(json.loads(line)["owner"])
        return found
    except Exception as exc:
        raise LedgerError("Não foi possível ler o livro de exclusões.") from exc


def snapshot_tables(conn):
    """Cópia consistente sem sessão, código de acesso ou verificador."""
    conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    try:
        payload = {name: rows(conn, "SELECT * FROM " + name) for name in SNAPSHOT_TABLES}
        if payload.get("stored_file"):
            raise RuntimeError("Há anexos. A cópia precisa incluir os arquivos antes de declarar sucesso.")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return payload


def reapply_erasures(conn):
    global _erased
    bootstrap_counts["erasure"] += 1
    owners = erased_owners()
    _erased = set(owners)
    removed = []
    for owner in sorted(owners):
        _delete_owner_rows(conn, None, owner)
        removed.append(owner)
    return removed


def _delete_owner_rows(conn, root, owner):
    if root:
        for row in rows(conn, "SELECT relative_path FROM stored_file WHERE owner_id = ?", (owner,)):
            path = os.path.join(root, row["relative_path"])
            if os.path.isfile(path):
                os.remove(path)
    for table in OWNER_TABLES:
        conn.execute(f"DELETE FROM {table} WHERE owner_id = ?", (owner,))
    conn.execute("DELETE FROM identity WHERE owner_id = ?", (owner,))


def forget_owner(conn, root, owner):
    record_erasure(owner)
    _erased.add(owner)
    _delete_owner_rows(conn, root, owner)
    return {"forgotten": True, "backupRetention": RETENTION, "exposed": False}


def backup_dir(src, dest):
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    if src == dest or dest.startswith(src + os.sep) or src.startswith(dest + os.sep):
        raise ValueError("A cópia precisa de um destino separado do armazenamento ativo.")
    os.makedirs(dest, exist_ok=True)
    db_src = os.path.join(src, "isa.sqlite")
    if not os.path.isfile(db_src):
        raise ValueError("Não há base ativa para copiar.")
    db_dest = os.path.join(dest, "isa.sqlite")
    source = sqlite3.connect(db_src)
    target = sqlite3.connect(db_dest)
    source.backup(target)
    source.close()
    target.close()
    files_src = os.path.join(src, "files")
    if os.path.isdir(files_src):
        shutil.copytree(files_src, os.path.join(dest, "files"), dirs_exist_ok=True)
    manifest = {"createdAt": now(), "retention": RETENTION, "sameDiskLimitation": True}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle)
    return manifest


def restore_dir(backup, dest):
    backup = os.path.abspath(backup)
    dest = os.path.abspath(dest)
    if backup == dest or dest.startswith(backup + os.sep):
        raise ValueError("A restauração precisa de um ambiente separado da cópia.")
    if os.path.isdir(dest) and os.listdir(dest):
        raise ValueError("O ambiente de restauração precisa começar vazio.")
    os.makedirs(dest, exist_ok=True)
    shutil.copy2(os.path.join(backup, "isa.sqlite"), os.path.join(dest, "isa.sqlite"))
    files = os.path.join(backup, "files")
    if os.path.isdir(files):
        shutil.copytree(files, os.path.join(dest, "files"))
    restored = connect(os.path.join(dest, "isa.sqlite"))
    reapply_erasures(restored)
    restored.close()
    return {"restored": True, "erasuresReapplied": True}


DATA_TABLES = (
    "availability", "balance_observation", "inflow", "commitment", "reserve", "scenario",
    "batch", "occurrence", "movement", "link_row", "draft", "suggestion", "suggestion_event",
    "stored_file", "change_log", "idempotency", "feedback", "identity", "account",
    "ledger_entry", "statement_note", "login_attempt", "app_session", "ai_job",
    "account_preference", "person_profile", "account_contact", "account_contact_link",
    "work_batch", "work_member", "work_event", "work_preference", "catalog_request",
)


SNAPSHOT_TABLES = tuple(name for name in DATA_TABLES if name not in ("login_attempt", "app_session"))


def logical_dump(conn, dest):
    """Cópia lógica das tabelas. Não inclui o livro de exclusões e não agenda nada."""
    dest = os.path.abspath(dest)
    if os.path.isdir(dest) and os.listdir(dest):
        raise ValueError("O destino da cópia precisa começar vazio.")
    os.makedirs(dest, exist_ok=True)
    payload = {table: rows(conn, "SELECT * FROM " + table) for table in SNAPSHOT_TABLES}
    with open(os.path.join(dest, "dump.json"), "w", encoding="utf-8") as handle:
        json.dump({"engine": "postgres", "tables": payload}, handle)
    manifest = {
        "createdAt": now(),
        "engine": "postgres",
        "retention": "nao-implantada",
        "externalDestination": False,
        "schedule": False,
        "sameDiskLimitation": True,
    }
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle)
    return manifest


def logical_restore(conn, backup):
    """Carrega a cópia e só então reaplica o livro de exclusões, antes de qualquer consulta."""
    path = os.path.join(os.path.abspath(backup), "dump.json")
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    tables = payload.get("tables") or {}
    for table in DATA_TABLES:
        items = tables.get(table) or []
        if not items:
            continue
        columns = list(items[0].keys())
        marks = ",".join(["?"] * len(columns))
        names = ",".join(columns)
        for item in items:
            conn.execute(
                "INSERT INTO " + table + " (" + names + ") VALUES (" + marks + ")",
                tuple(item[column] for column in columns),
            )
    reapply_erasures(conn)
    return {"restored": True, "erasuresReapplied": True, "engine": "postgres"}


def expire_backups(folder, days=7, today=None):
    removed = []
    today = today or datetime.now(timezone.utc)
    if not os.path.isdir(folder):
        return removed
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        manifest_path = os.path.join(path, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, encoding="utf-8") as handle:
            created = datetime.fromisoformat(json.load(handle)["createdAt"])
        if created < today - timedelta(days=days):
            shutil.rmtree(path)
            removed.append(name)
    return removed
