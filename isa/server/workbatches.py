"""Lote de trabalho. Capa escolhida pela pessoa, separada do lote técnico da importação.

O total sai dos lançamentos vinculados. A capa não é uma despesa nem um saldo.
"""

import json
import unicodedata

CRITERIA = {"evento": "Evento", "periodo": "Período", "documento": "Documento", "outro": "Outro"}
STATEMENT_SOURCES = {"exemplo-sintetico", "arquivo-teste", "extrato-sintetico", "extrato-bb-arquivo"}


class Conflict(Exception):
    """A capa foi alterada em outro lugar. Nada desta gravação foi aplicado."""


def migrate(conn):
    for statement in (
        """CREATE TABLE IF NOT EXISTS work_batch (
          id TEXT PRIMARY KEY,
          owner_id TEXT NOT NULL,
          name TEXT NOT NULL,
          criterion TEXT NOT NULL,
          state TEXT NOT NULL,
          period_start TEXT NOT NULL DEFAULT '',
          period_end TEXT NOT NULL DEFAULT '',
          document_ref TEXT NOT NULL DEFAULT '',
          supplier TEXT NOT NULL DEFAULT '',
          note TEXT NOT NULL DEFAULT '',
          reference_minor INTEGER,
          reference_currency TEXT NOT NULL DEFAULT '',
          default_account_id TEXT NOT NULL DEFAULT '',
          version INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS work_member (
          batch_id TEXT NOT NULL,
          entry_id TEXT NOT NULL,
          owner_id TEXT NOT NULL,
          active INTEGER NOT NULL,
          added_at TEXT NOT NULL,
          PRIMARY KEY (batch_id, entry_id)
        )""",
        """CREATE UNIQUE INDEX IF NOT EXISTS work_member_active_entry
          ON work_member(owner_id, entry_id) WHERE active = 1""",
        """CREATE TABLE IF NOT EXISTS work_event (
          id TEXT PRIMARY KEY,
          owner_id TEXT NOT NULL,
          batch_id TEXT NOT NULL,
          entry_id TEXT NOT NULL DEFAULT '',
          kind TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS work_preference (
          owner_id TEXT PRIMARY KEY,
          active_batch_id TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL
        )""",
    ):
        conn.execute(statement)


def fold(value):
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.casefold()


def bucket(entry):
    nature = entry.get("nature") or ""
    source = entry.get("source") or ""
    statement = source in STATEMENT_SOURCES
    if nature == "bb_rende_facil":
        return "rende"
    if nature == "aplicacao":
        return "aplicacoes"
    if nature in ("transferencia", "reembolso", "emprestimo"):
        return "transferencias"
    if nature == "a_conferir" or (statement and not nature) or nature not in ("consumo", ""):
        return "conferir"
    direction = entry.get("direction")
    status = entry.get("status")
    if direction == "gasto" and status == "pago":
        return "gastosPagos"
    if direction == "gasto" and status == "a_pagar":
        return "gastosAPagar"
    if direction == "ganho" and status == "recebido":
        return "ganhosRecebidos"
    if direction == "ganho" and status == "a_receber":
        return "ganhosAReceber"
    return "conferir"


def _slot():
    return {
        "gastosPagos": 0,
        "gastosAPagar": 0,
        "ganhosRecebidos": 0,
        "ganhosAReceber": 0,
        "transferencias": 0,
        "aplicacoes": 0,
        "rende": 0,
        "conferir": 0,
    }


def summarize(entries):
    currencies = {}
    archived = 0
    for entry in entries or []:
        if entry.get("archived"):
            archived += 1
            continue
        code = entry.get("currency") or "BRL"
        kind = bucket(entry)
        target = currencies.setdefault(code, _slot())
        target[kind] = target.get(kind, 0) + int(entry.get("amountMinor") or 0)
    return {"byCurrency": currencies, "archived": archived}


def composition(entries, currency, base="pagos"):
    groups = {}
    for entry in entries or []:
        if entry.get("archived"):
            continue
        if (entry.get("currency") or "BRL") != currency:
            continue
        kind = bucket(entry)
        if base == "pagos" and kind != "gastosPagos":
            continue
        if base == "a_pagar" and kind != "gastosAPagar":
            continue
        if base == "registrados" and kind not in ("gastosPagos", "gastosAPagar"):
            continue
        if base not in ("pagos", "a_pagar", "registrados"):
            continue
        label = (entry.get("category") or "").strip() or "A categorizar"
        item = groups.setdefault(label, {"category": label, "amount": 0, "count": 0})
        item["amount"] += int(entry.get("amountMinor") or 0)
        item["count"] += 1
    ordered = sorted(groups.values(), key=lambda item: (-item["amount"], item["category"]))
    return {
        "currency": currency,
        "base": base,
        "items": ordered,
        "total": sum(item["amount"] for item in ordered),
    }


def reference_gap(batch, totals):
    minor = batch.get("reference_minor")
    currency = batch.get("reference_currency") or ""
    if minor is None or minor == "" or not currency:
        return None
    registered_currencies = []
    for code, slot in (totals.get("byCurrency") or {}).items():
        registered = int(slot["gastosPagos"]) + int(slot["gastosAPagar"])
        if registered:
            registered_currencies.append(code)
    if registered_currencies != [currency]:
        return None
    registered = int(totals["byCurrency"][currency]["gastosPagos"]) + int(totals["byCurrency"][currency]["gastosAPagar"])
    expected = int(minor)
    return {"currency": currency, "expected": expected, "registered": registered, "delta": registered - expected}


def _store():
    import store
    return store


def _clean(value, limit=160):
    return " ".join(str(value or "").split())[:limit]


def _event(conn, owner, batch_id, kind, entry_id="", note=""):
    store = _store()
    conn.execute(
        "INSERT INTO work_event (id, owner_id, batch_id, entry_id, kind, note, created_at) VALUES (?,?,?,?,?,?,?)",
        (store._id(), owner, batch_id, entry_id or "", kind, note or "", store.now()),
    )


def _owned_batch(conn, owner, batch_id):
    store = _store()
    batch = store.one(conn, "SELECT * FROM work_batch WHERE id = ? AND owner_id = ?", (batch_id, owner))
    if not batch:
        raise ValueError("Este lote não está na sua conta.")
    return batch


def require_batch(conn, owner, batch_id):
    return _owned_batch(conn, owner, batch_id)


def active_batch_id(conn, owner, entry_id):
    store = _store()
    row = store.one(
        conn,
        "SELECT batch_id FROM work_member WHERE owner_id = ? AND entry_id = ? AND active = 1",
        (owner, entry_id),
    )
    return row["batch_id"] if row else ""


def _bump(conn, owner, batch_id):
    store = _store()
    conn.execute(
        "UPDATE work_batch SET version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ?",
        (store.now(), batch_id, owner),
    )


def _stamp_entry(conn, owner, entry_id, batch_id):
    store = _store()
    row = store.one(conn, "SELECT payload_json FROM ledger_entry WHERE id = ? AND owner_id = ?", (entry_id, owner))
    if not row:
        return
    payload = json.loads(row["payload_json"])
    payload["id"] = entry_id
    payload["workBatchId"] = batch_id or ""
    store.write_entry(conn, owner, payload)


def attach(conn, owner, batch_id, entry_id):
    """Vincula sem abrir transação. O chamador confirma o conjunto."""
    store = _store()
    _owned_batch(conn, owner, batch_id)
    entry = store.one(conn, "SELECT id FROM ledger_entry WHERE id = ? AND owner_id = ?", (entry_id, owner))
    if not entry:
        raise ValueError("Este lançamento não está na sua conta.")
    current = store.one(
        conn,
        "SELECT batch_id, active FROM work_member WHERE owner_id = ? AND entry_id = ? AND active = 1",
        (owner, entry_id),
    )
    if current and current["batch_id"] == batch_id:
        return
    if current:
        conn.execute(
            "UPDATE work_member SET active = 0 WHERE owner_id = ? AND entry_id = ? AND active = 1",
            (owner, entry_id),
        )
        _event(conn, owner, current["batch_id"], "desvinculado", entry_id, "Movido para outro lote.")
        _bump(conn, owner, current["batch_id"])
    existing = store.one(
        conn,
        "SELECT batch_id FROM work_member WHERE batch_id = ? AND entry_id = ? AND owner_id = ?",
        (batch_id, entry_id, owner),
    )
    if existing:
        conn.execute(
            "UPDATE work_member SET active = 1, added_at = ? WHERE batch_id = ? AND entry_id = ? AND owner_id = ?",
            (store.now(), batch_id, entry_id, owner),
        )
    else:
        conn.execute(
            "INSERT INTO work_member (batch_id, entry_id, owner_id, active, added_at) VALUES (?,?,?,?,?)",
            (batch_id, entry_id, owner, 1, store.now()),
        )
    _event(conn, owner, batch_id, "vinculado", entry_id, "")
    _bump(conn, owner, batch_id)


def _cover(body, current=None):
    store = _store()
    name = _clean(body.get("name") if "name" in body else (current or {}).get("name"), 80)
    if not name:
        name = "Registros de hoje"
    criterion = body.get("criterion") if "criterion" in body else (current or {}).get("criterion") or "outro"
    if criterion not in CRITERIA:
        raise ValueError("Escolha evento, período, documento ou outro.")
    reference = body.get("referenceMinor") if "referenceMinor" in body else (current or {}).get("reference_minor")
    if reference in ("", None):
        reference_minor = None
    else:
        reference_minor = int(reference)
        if reference_minor < 0:
            raise ValueError("O valor de referência não pode ser negativo.")
    currency = _clean(body.get("referenceCurrency") if "referenceCurrency" in body else (current or {}).get("reference_currency"), 3).upper()
    if currency and currency not in store.CURRENCIES:
        raise ValueError("A moeda do valor de referência precisa ser Real, dólar ou euro.")
    account_id = _clean(body.get("defaultAccountId") if "defaultAccountId" in body else (current or {}).get("default_account_id"), 80)
    return {
        "name": name,
        "criterion": criterion,
        "period_start": _clean(body.get("periodStart") if "periodStart" in body else (current or {}).get("period_start"), 10),
        "period_end": _clean(body.get("periodEnd") if "periodEnd" in body else (current or {}).get("period_end"), 10),
        "document_ref": _clean(body.get("documentRef") if "documentRef" in body else (current or {}).get("document_ref"), 80),
        "supplier": _clean(body.get("supplier") if "supplier" in body else (current or {}).get("supplier"), 80),
        "note": _clean(body.get("note") if "note" in body else (current or {}).get("note"), 280),
        "reference_minor": reference_minor,
        "reference_currency": currency,
        "default_account_id": account_id,
    }


def _check_account(conn, owner, account_id):
    if not account_id:
        return
    store = _store()
    account = store.one(conn, "SELECT id FROM account WHERE id = ? AND owner_id = ?", (account_id, owner))
    if not account:
        raise ValueError("A conta padrão precisa ser uma conta sua.")


def create_batch(conn, owner, body):
    store = _store()
    body = body or {}
    cover = _cover(body)
    _check_account(conn, owner, cover["default_account_id"])
    batch_id = _clean(body.get("id"), 80) or store._id()
    existing = store.one(conn, "SELECT * FROM work_batch WHERE id = ?", (batch_id,))
    if existing:
        if existing["owner_id"] != owner:
            raise ValueError("Este lote não está na sua conta.")
        return public_batch(conn, owner, existing)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """INSERT INTO work_batch (
              id, owner_id, name, criterion, state, period_start, period_end, document_ref, supplier, note,
              reference_minor, reference_currency, default_account_id, version, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                batch_id, owner, cover["name"], cover["criterion"], "aberto",
                cover["period_start"], cover["period_end"], cover["document_ref"], cover["supplier"], cover["note"],
                cover["reference_minor"], cover["reference_currency"], cover["default_account_id"],
                1, store.now(), store.now(),
            ),
        )
        _event(conn, owner, batch_id, "criado", "", cover["criterion"])
        if body.get("activate", True):
            _set_preference(conn, owner, batch_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return public_batch(conn, owner, store.one(conn, "SELECT * FROM work_batch WHERE id = ? AND owner_id = ?", (batch_id, owner)))


def update_batch(conn, owner, batch_id, body):
    store = _store()
    current = _owned_batch(conn, owner, batch_id)
    if int(body.get("version") or 0) != int(current["version"]):
        raise Conflict("Este lote mudou em outro lugar. Atualize antes de gravar a capa.")
    cover = _cover(body, current)
    _check_account(conn, owner, cover["default_account_id"])
    conn.execute("BEGIN IMMEDIATE")
    try:
        fresh = _owned_batch(conn, owner, batch_id)
        if int(fresh["version"]) != int(current["version"]):
            raise Conflict("Este lote mudou em outro lugar. Atualize antes de gravar a capa.")
        conn.execute(
            """UPDATE work_batch SET name = ?, criterion = ?, period_start = ?, period_end = ?, document_ref = ?,
               supplier = ?, note = ?, reference_minor = ?, reference_currency = ?, default_account_id = ?,
               version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ? AND version = ?""",
            (
                cover["name"], cover["criterion"], cover["period_start"], cover["period_end"], cover["document_ref"],
                cover["supplier"], cover["note"], cover["reference_minor"], cover["reference_currency"],
                cover["default_account_id"], store.now(), batch_id, owner, current["version"],
            ),
        )
        _event(conn, owner, batch_id, "capa", "", "")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return public_batch(conn, owner, store.one(conn, "SELECT * FROM work_batch WHERE id = ? AND owner_id = ?", (batch_id, owner)))


def _set_state(conn, owner, batch_id, state, kind):
    store = _store()
    _owned_batch(conn, owner, batch_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE work_batch SET state = ?, version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ?",
            (state, store.now(), batch_id, owner),
        )
        _event(conn, owner, batch_id, kind, "", "")
        if state == "concluido":
            pref = store.one(conn, "SELECT active_batch_id FROM work_preference WHERE owner_id = ?", (owner,))
            if pref and pref["active_batch_id"] == batch_id:
                _set_preference(conn, owner, "")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return public_batch(conn, owner, store.one(conn, "SELECT * FROM work_batch WHERE id = ? AND owner_id = ?", (batch_id, owner)))


def conclude_batch(conn, owner, batch_id):
    return _set_state(conn, owner, batch_id, "concluido", "concluido")


def reopen_batch(conn, owner, batch_id):
    result = _set_state(conn, owner, batch_id, "aberto", "reaberto")
    _set_preference(conn, owner, batch_id)
    return public_batch(conn, owner, _store().one(conn, "SELECT * FROM work_batch WHERE id = ? AND owner_id = ?", (batch_id, owner)))


def link_entry(conn, owner, batch_id, entry_id):
    conn.execute("BEGIN IMMEDIATE")
    try:
        attach(conn, owner, batch_id, entry_id)
        _stamp_entry(conn, owner, entry_id, batch_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return public_batch(conn, owner, _owned_batch(conn, owner, batch_id))


def move_entry(conn, owner, batch_id, entry_id, to_batch_id):
    if not to_batch_id or to_batch_id == batch_id:
        raise ValueError("Escolha o lote de destino.")
    _owned_batch(conn, owner, to_batch_id)
    current = active_batch_id(conn, owner, entry_id)
    if current != batch_id:
        raise ValueError("Este lançamento não está neste lote.")
    return link_entry(conn, owner, to_batch_id, entry_id)


def unlink_entry(conn, owner, batch_id, entry_id):
    store = _store()
    _owned_batch(conn, owner, batch_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        current = store.one(
            conn,
            "SELECT batch_id FROM work_member WHERE owner_id = ? AND entry_id = ? AND batch_id = ? AND active = 1",
            (owner, entry_id, batch_id),
        )
        if not current:
            raise ValueError("Este lançamento não está neste lote.")
        conn.execute(
            "UPDATE work_member SET active = 0 WHERE owner_id = ? AND entry_id = ? AND batch_id = ?",
            (owner, entry_id, batch_id),
        )
        _stamp_entry(conn, owner, entry_id, "")
        _event(conn, owner, batch_id, "desvinculado", entry_id, "Saída do lote, sem apagar o lançamento.")
        _bump(conn, owner, batch_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return public_batch(conn, owner, _owned_batch(conn, owner, batch_id))


def _set_preference(conn, owner, batch_id):
    store = _store()
    if batch_id:
        _owned_batch(conn, owner, batch_id)
    conn.execute(
        """INSERT INTO work_preference (owner_id, active_batch_id, updated_at) VALUES (?,?,?)
           ON CONFLICT(owner_id) DO UPDATE SET active_batch_id = excluded.active_batch_id, updated_at = excluded.updated_at""",
        (owner, batch_id or "", store.now()),
    )


def set_preference(conn, owner, batch_id):
    conn.execute("BEGIN IMMEDIATE")
    try:
        _set_preference(conn, owner, batch_id or "")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"activeWorkBatchId": batch_id or ""}


def _entries_for(conn, owner, batch_id):
    store = _store()
    members = store.rows(
        conn,
        "SELECT entry_id, added_at FROM work_member WHERE owner_id = ? AND batch_id = ? AND active = 1 ORDER BY added_at, entry_id",
        (owner, batch_id),
    )
    wanted = [member["entry_id"] for member in members]
    found = {}
    for start in range(0, len(wanted), 400):
        part = wanted[start:start + 400]
        marks = ",".join("?" for _ in part)
        for row in store.rows(
            conn,
            "SELECT id, payload_json FROM ledger_entry WHERE owner_id = ? AND id IN (" + marks + ")",
            tuple([owner] + part),
        ):
            found[row["id"]] = json.loads(row["payload_json"])
    return [found[item] for item in wanted if item in found]


def _public_row(batch, entries, account_id=""):
    totals = summarize(entries)
    compositions = []
    for code, slot in totals["byCurrency"].items():
        if slot["gastosPagos"] or slot["gastosAPagar"]:
            compositions.append(composition(entries, code, "pagos"))
    return {
        "id": batch["id"],
        "ownerId": batch["owner_id"],
        "name": batch["name"],
        "criterion": batch["criterion"],
        "criterionLabel": CRITERIA.get(batch["criterion"], batch["criterion"]),
        "state": batch["state"],
        "periodStart": batch["period_start"],
        "periodEnd": batch["period_end"],
        "documentRef": batch["document_ref"],
        "supplier": batch["supplier"],
        "note": batch["note"],
        "referenceMinor": batch["reference_minor"],
        "referenceCurrency": batch["reference_currency"],
        "defaultAccountId": batch["default_account_id"],
        "version": batch["version"],
        "createdAt": batch["created_at"],
        "updatedAt": batch["updated_at"],
        "count": len([item for item in entries if not item.get("archived")]),
        "memberIds": [item.get("id") for item in entries],
        "outsideAccount": sum(1 for item in entries if account_id and (item.get("accountId") or "") != account_id),
        "totals": totals,
        "compositions": compositions,
        "referenceGap": reference_gap(batch, totals),
    }


def public_batch(conn, owner, batch):
    if batch["owner_id"] != owner:
        raise ValueError("Este lote não está na sua conta.")
    return _public_row(batch, _entries_for(conn, owner, batch["id"]))


def list_batches(conn, owner, account_id=""):
    store = _store()
    preference = store.one(conn, "SELECT active_batch_id FROM work_preference WHERE owner_id = ?", (owner,))
    items = []
    for batch in store.rows(conn, "SELECT * FROM work_batch WHERE owner_id = ? ORDER BY updated_at DESC, id", (owner,)):
        items.append(_public_row(batch, _entries_for(conn, owner, batch["id"]), account_id))
    active = preference["active_batch_id"] if preference else ""
    if active and not any(item["id"] == active and item["state"] == "aberto" for item in items):
        active = ""
    return {"items": items, "activeWorkBatchId": active}


def remember_link(conn, owner, entry_id, requested):
    """Usado dentro da transação de save_entry. requested None preserva o vínculo."""
    if requested:
        attach(conn, owner, requested, entry_id)
        return requested
    return active_batch_id(conn, owner, entry_id)


def _entry_text(entry):
    return " ".join([
        entry.get("merchant") or "",
        entry.get("supplier") or "",
        entry.get("category") or "",
        entry.get("documentId") or "",
        entry.get("bankDocument") or "",
        entry.get("note") or "",
    ])


def _match_entry(entry, query):
    text = fold(query.get("q") or "")
    if text and text not in fold(_entry_text(entry)):
        batch_text = fold(query.get("_batchText") or "")
        if text not in batch_text:
            return False
    if query.get("accountId") and (entry.get("accountId") or "") != query["accountId"]:
        return False
    if query.get("currency") and (entry.get("currency") or "BRL") != query["currency"]:
        return False
    if query.get("category") and (entry.get("category") or "") != query["category"]:
        return False
    if query.get("status") and (entry.get("status") or "") != query["status"]:
        return False
    when = entry.get("statusDate") or entry.get("dueDate") or entry.get("noteDate") or ""
    if query.get("dateFrom") and when < query["dateFrom"]:
        return False
    if query.get("dateTo") and when > query["dateTo"]:
        return False
    amount = int(entry.get("amountMinor") or 0)
    if query.get("amountMin") not in (None, ""):
        if amount < int(query["amountMin"]):
            return False
    if query.get("amountMax") not in (None, ""):
        if amount > int(query["amountMax"]):
            return False
    if query.get("batchId") and (entry.get("workBatchId") or "") != query["batchId"]:
        return False
    return True


def search(conn, owner, query):
    store = _store()
    query = dict(query or {})
    listed = list_batches(conn, owner)
    by_id = {item["id"]: item for item in listed["items"]}
    entries = []
    for row in store.rows(conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ?", (owner,)):
        entries.append(json.loads(row["payload_json"]))
    text = fold(query.get("q") or "")
    matched = []
    for entry in entries:
        batch = by_id.get(entry.get("workBatchId") or "")
        probe = dict(query)
        probe["_batchText"] = " ".join([
            (batch or {}).get("name") or "",
            (batch or {}).get("documentRef") or "",
            (batch or {}).get("supplier") or "",
            (batch or {}).get("criterionLabel") or "",
        ]) if batch else ""
        if text and text not in fold(_entry_text(entry)) and text not in fold(probe["_batchText"]):
            continue
        probe["q"] = ""
        if not _match_entry(entry, probe):
            continue
        matched.append(entry)
    matched.sort(key=lambda item: (
        item.get("statusDate") or item.get("dueDate") or item.get("noteDate") or "",
        item.get("id") or "",
    ))
    groups = {}
    for entry in matched:
        key = entry.get("workBatchId") or ""
        groups.setdefault(key, []).append(entry)
    batches = []
    for key, found in groups.items():
        if key and key in by_id:
            full = by_id[key]
            batches.append({
                "id": key,
                "name": full["name"],
                "criterionLabel": full["criterionLabel"],
                "state": full["state"],
                "periodStart": full["periodStart"],
                "periodEnd": full["periodEnd"],
                "foundCount": len(found),
                "count": full["count"],
                "foundTotals": summarize(found),
                "totals": full["totals"],
                "memberIds": [item.get("id") for item in found],
            })
        elif not key:
            batches.append({
                "id": "",
                "name": "Sem lote",
                "criterionLabel": "",
                "state": "",
                "periodStart": "",
                "periodEnd": "",
                "foundCount": len(found),
                "count": len(found),
                "foundTotals": summarize(found),
                "totals": summarize(found),
                "memberIds": [item.get("id") for item in found],
                "section": True,
            })
    page_size = int(query.get("pageSize") or 50)
    page_size = min(max(page_size, 1), 100)
    page = max(int(query.get("page") or 1), 1)
    start = (page - 1) * page_size
    return {
        "entries": matched[start:start + page_size],
        "entryCount": len(matched),
        "totals": summarize(matched),
        "batches": batches,
        "page": page,
        "pageSize": page_size,
    }
