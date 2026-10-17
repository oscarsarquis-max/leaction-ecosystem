"""Base local da ISA. O dono vem de fora. O corpo do pedido não escolhe o proprietário."""

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from engine import project
from explain import RULE_VERSION, PROMPT_VERSION, explain_alternative, explain_current, explain_spend
from overview import build_overview

RETENTION = "laboratorio-7-dias"


def today():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def reference_date():
    return today() if os.environ.get("ISA_ENV") == "production" else "2026-10-16"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path):
    if str(db_path).startswith("postgres"):
        from pgconn import connect as pg_connect
        conn = pg_connect(db_path)
    else:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    reapply_erasures(conn)
    return conn


def migrate(conn):
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
    conn.execute("BEGIN IMMEDIATE")
    try:
        previous = one(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1", (owner,))
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
        }
        conn.execute(
            "INSERT INTO availability (id, owner_id, amount_cents, as_of, protected_cents, source, convention, created_at, active) VALUES (?,?,?,?,?,?,?,?,?)",
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
    recent = rows(conn, "SELECT * FROM inflow WHERE owner_id = ? ORDER BY created_at DESC LIMIT 8", (owner,))
    copy = _recent_match(recent, lambda item: item["label"] == label and item["amount_cents"] == amount and item["due_on"] == due and item["state"] == state)
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
    }
    conn.execute(
        "INSERT INTO inflow (id, owner_id, label, amount_cents, due_on, state, recurrence, series_id, origin, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (item["id"], item["owner_id"], item["label"], item["amount_cents"], item["due_on"], item["state"], item["recurrence"], item["series_id"], item["origin"], item["created_at"]),
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
    recent = rows(conn, "SELECT * FROM commitment WHERE owner_id = ? ORDER BY created_at DESC LIMIT 8", (owner,))
    copy = _recent_match(recent, lambda item: item["label"] == label and item["total_cents"] == total and item["due_on"] == due)
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
    }
    conn.execute(
        "INSERT INTO commitment (id, owner_id, label, total_cents, remaining_cents, due_on, original_due_on, essential, priority, recurrence, series_id, origin, conditions_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (item["id"], owner, item["label"], item["total_cents"], item["remaining_cents"], item["due_on"], item["original_due_on"], item["essential"], item["priority"], item["recurrence"], item["series_id"], item["origin"], item["conditions_json"], now()),
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


def _events(conn, owner):
    events = []
    for item in rows(conn, "SELECT * FROM inflow WHERE owner_id = ?", (owner,)):
        events.append({
            "id": item["id"],
            "kind": "entrada",
            "label": item["label"],
            "on": item["due_on"],
            "cents": item["amount_cents"],
            "included": item["state"] == "confirmada" and item["amount_cents"] is not None and bool(item["due_on"]),
        })
    for item in rows(conn, "SELECT * FROM commitment WHERE owner_id = ?", (owner,)):
        events.append({
            "id": item["id"],
            "kind": "saida",
            "label": item["label"],
            "on": item["due_on"],
            "cents": item["remaining_cents"],
            "included": item["remaining_cents"] is not None and bool(item["due_on"]) and int(item["remaining_cents"]) != 0,
        })
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


def _base(conn, owner):
    row = one(conn, "SELECT * FROM availability WHERE owner_id = ? AND active = 1", (owner,))
    if not row:
        return {"known": False}
    return {
        "known": True,
        "as_of": row["as_of"],
        "amount_cents": row["amount_cents"],
        "protected_cents": row["protected_cents"],
        "convention": row["convention"],
        "source": row["source"],
    }


def projection(conn, owner, reference, changes=None, extra=None, include_uncertain=False):
    base = _base(conn, owner)
    events = _events(conn, owner)
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
    return project(base, events, reference, extra=extra)


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


def planning_guide(conn, owner, inflows, commitments):
    """Estado da jornada. A navegação usa estes campos, não o texto das mensagens."""
    base = _base(conn, owner)
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


def home(conn, owner, reference=None):
    reference = reference or reference_date()
    result = projection(conn, owner, reference)
    explanation = explain_current(result)
    observations = rows(conn, "SELECT id, amount_cents, as_of, kind, source FROM balance_observation WHERE owner_id = ? ORDER BY as_of", (owner,))
    pending = rows(conn, "SELECT id, signature, state FROM occurrence WHERE owner_id = ? AND state = 'pendente'", (owner,))
    chosen = one(conn, "SELECT id, name, note FROM scenario WHERE owner_id = ? AND chosen = 1", (owner,))
    inflows = rows(conn, "SELECT id, label, due_on, amount_cents, state FROM inflow WHERE owner_id = ? ORDER BY due_on", (owner,))
    commitments = rows(conn, "SELECT id, label, due_on, original_due_on, remaining_cents, total_cents, essential, priority, conditions_json FROM commitment WHERE owner_id = ? ORDER BY due_on", (owner,))
    guide = planning_guide(conn, owner, inflows, commitments)
    overview = build_overview(result.get("reference") or reference, result, guide, commitments, inflows)
    hidden = _draft_body(conn, owner, "insights-hoje")
    dismissed = hidden.get("dismissed") if hidden.get("day") == overview["reference"] and isinstance(hidden.get("dismissed"), list) else []
    overview["insightHistory"] = overview["insights"]
    overview["insights"] = [item for item in overview["insights"] if item["id"] not in dismissed]
    overview["dismissed"] = dismissed
    reading = one(conn, "SELECT status, result_json, payload_json, created_at FROM ai_job WHERE owner_id = ? AND kind = 'insight' ORDER BY created_at DESC LIMIT 1", (owner,))
    if reading:
        loaded = json.loads(reading["payload_json"])
        reading_result = json.loads(reading["result_json"]) if reading.get("result_json") else None
        overview["reading"] = {"status": reading["status"], "day": loaded.get("day"), "createdAt": reading["created_at"], "stale": loaded.get("day") != overview["reference"] or loaded.get("fingerprint") != overview.get("fingerprint"), "explanation": (reading_result or {}).get("explanation")}
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
        "saveState": "salvo",
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
    if row["owner_id"] in erased_owners():
        return None
    return row


def drop_session(conn, session_id):
    conn.execute("DELETE FROM app_session WHERE id = ?", (session_id,))


def save_account(conn, owner, body):
    name = " ".join(str(body.get("name") or "").split())
    if not name:
        raise ValueError("A conta precisa de um nome.")
    currency = body.get("currency") or "BRL"
    if currency != "BRL":
        raise ValueError("Esta leitura só entra numa conta em Real.")
    item_id = body.get("id") or _id()
    current = one(conn, "SELECT * FROM account WHERE id = ? AND owner_id = ?", (item_id, owner))
    if current:
        return current
    conn.execute(
        "INSERT INTO account (id, owner_id, name, currency, created_at) VALUES (?,?,?,?,?)",
        (item_id, owner, name, currency, now()),
    )
    return owned(conn, "account", owner, item_id)


def save_entry(conn, owner, body):
    payload = dict(body)
    payload.pop("ownerId", None)
    payload.pop("owner_id", None)
    item_id = payload.get("id") or _id()
    payload["id"] = item_id
    payload["ownerId"] = owner
    current = one(conn, "SELECT id, payload_json FROM ledger_entry WHERE id = ? AND owner_id = ?", (item_id, owner))
    previous = json.loads(current["payload_json"]) if current else None
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
            "UPDATE ledger_entry SET payload_json = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
            (json.dumps(payload), now(), item_id, owner),
        )
    else:
        conn.execute(
            "INSERT INTO ledger_entry (id, owner_id, account_id, payload_json, updated_at) VALUES (?,?,?,?,?)",
            (item_id, owner, payload.get("accountId") or "", json.dumps(payload), now()),
        )
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
    account = save_account(conn, owner, body.get("account") or {"name": "Conta"})
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


def workspace(conn, owner):
    sync_entries(conn, owner)
    accounts = rows(conn, "SELECT id, name, currency FROM account WHERE owner_id = ? ORDER BY created_at", (owner,))
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
    return {
        "ownerId": owner,
        "accounts": [{"id": item["id"], "ownerId": owner, "name": item["name"], "currency": item["currency"], "declared": True} for item in accounts],
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
    "statement_note", "feedback", "app_session", "ai_job",
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
    removed = []
    for owner in sorted(erased_owners()):
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
