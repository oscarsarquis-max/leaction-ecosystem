"""Sincronização bancária. O pedido HTTP só grava o evento. O trabalho corre depois."""

import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import pluggy
import store

DENIED = "A conexão com bancos ainda não está disponível para a sua conta."
AUTHORIZE = "É preciso autorizar de novo no seu banco."
CONNECTING = "Conectando… pode levar alguns minutos"
HEADER = "X-ISA-Bank-Secret"
PROVIDER = "pluggy"
ZONE = ZoneInfo("America/Sao_Paulo")
WEBHOOK_URL = "https://isa.actionhub.com.br/api/bank/webhook"

# Nomes que a documentação da Pluggy mostra. O que não está aqui fica sem categoria da ISA.
CATEGORIES = {
    "groceries": "Alimentação",
    "eating out": "Alimentação",
    "food and drinks": "Alimentação",
    "rent": "Moradia",
    "housing": "Moradia",
    "utilities": "Moradia",
    "transportation": "Transporte",
    "transport": "Transporte",
    "healthcare": "Saúde",
    "health": "Saúde",
    "pharmacy": "Saúde",
    "education": "Educação",
    "entertainment": "Lazer",
    "video streaming": "Lazer",
    "leisure": "Lazer",
    "shopping": "Compras",
    "salary": "Salário",
    "income": "Salário",
    "services": "Serviços",
}

KINDS = {
    ("BANK", "CHECKING_ACCOUNT"): "corrente",
    ("BANK", "SAVINGS_ACCOUNT"): "poupanca",
    ("CREDIT", "CREDIT_CARD"): "cartao",
}


def allowed(subject):
    if os.environ.get("ISA_PLUGGY_ENABLED") != "1":
        return False
    permitted = [item.strip() for item in (os.environ.get("ISA_PLUGGY_ALLOWED_SUBS") or "").split(",") if item.strip()]
    return bool(subject) and subject in permitted


def client_user_id(owner):
    return hashlib.sha256(owner.encode("utf-8")).hexdigest()


def _webhook_url():
    return (os.environ.get("ISA_PLUGGY_WEBHOOK_URL") or WEBHOOK_URL).strip()


def _secret():
    return pluggy.load_credentials().get("webhookSecret") or ""


def _cents(amount):
    return int((Decimal(str(amount)).copy_abs() * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _civil(value):
    text = str(value or "")
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    if "T" not in text:
        return ""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return moment.astimezone(ZONE).date().isoformat()


def _shift(day, days):
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def _norm(value):
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _contains(left, right):
    return len(left) >= 8 and len(right) >= 8 and (left in right or right in left)


def suggest_category(name):
    return CATEGORIES.get(str(name or "").strip().lower(), "")


def _notice(link):
    status = link.get("status") or ""
    detail = link.get("status_detail") or ""
    if status == "desligado":
        return "Desligado. O histórico já trazido permanece."
    if status in ("LOGIN_ERROR", "WAITING_USER_INPUT") or detail in ("item/error", "item/waiting_user_action", "item/waiting_user_input"):
        return AUTHORIZE
    if status in ("novo", "UPDATING"):
        return CONNECTING
    return ""


def public_links(conn, owner):
    items = []
    for link in store.rows(conn, "SELECT id, connector_name, status, status_detail, last_synced_at FROM bank_link WHERE owner_id = ? ORDER BY created_at", (owner,)):
        items.append({
            "id": link["id"],
            "name": link["connector_name"] or "Banco",
            "status": link["status"],
            "notice": _notice(link),
            "lastSyncedAt": link["last_synced_at"] or "",
        })
    return items


def present(conn, owner, subject, page):
    page = dict(page)
    page["bankConnect"] = allowed(subject)
    page["bankLinks"] = public_links(conn, owner) if page["bankConnect"] else []
    if not page["bankConnect"]:
        return page
    linked = {row["id"]: row["bank_link_id"] for row in store.rows(conn, "SELECT id, bank_link_id FROM account WHERE owner_id = ? AND bank_link_id IS NOT NULL", (owner,))}
    accounts = []
    for account in page.get("accounts") or []:
        if account.get("id") not in linked:
            accounts.append(account)
            continue
        current = dict(account)
        current["intakeLabel"] = "Conexão bancária"
        current["connection"] = {
            "available": True,
            "state": "conectado",
            "provider": "",
            "lastSuccess": "",
            "message": "Os movimentos desta conta chegam do banco. A ISA não pede senha do banco.",
        }
        accounts.append(current)
    page["accounts"] = accounts
    return page


def route(conn, owner, subject, method, path, body):
    if not allowed(subject):
        return 403, {"error": DENIED}
    if method == "GET" and path == "/api/bank/connect-token":
        return _connect_token(owner)
    if method == "POST" and path == "/api/bank/links":
        return _save_link(conn, owner, (body or {}).get("itemId") or "")
    parts = [item for item in path.split("/") if item]
    if method == "POST" and len(parts) == 5 and parts[:3] == ["api", "bank", "links"] and parts[4] == "disconnect":
        return _disconnect(conn, owner, parts[3])
    return 404, {"error": "Não encontrado para esta pessoa."}


def _connect_token(owner):
    try:
        token = pluggy.client().connect_token(client_user_id(owner), _webhook_url())
    except pluggy.PluggyError as exc:
        print("ISA bank " + (exc.code or "token"), flush=True)
        return 503, {"error": str(exc)}
    return 200, {"accessToken": token, "sandbox": os.environ.get("ISA_ENV") != "production" and os.environ.get("ISA_PLUGGY_SANDBOX") == "1"}


def _save_link(conn, owner, item_id):
    item_id = str(item_id or "").strip()
    if not item_id:
        return 400, {"error": "Falta a conexão devolvida pelo banco."}
    try:
        remote = pluggy.client().item(item_id)
    except pluggy.PluggyError as exc:
        print("ISA bank " + (exc.code or "item"), flush=True)
        return 400, {"error": str(exc)}
    if (remote.get("clientUserId") or "") != client_user_id(owner):
        print("ISA bank client-mismatch", flush=True)
        return 403, {"error": "Esta conexão não pertence a esta conta."}
    current = store.one(conn, "SELECT * FROM bank_link WHERE item_id = ?", (item_id,))
    if current and current["owner_id"] != owner:
        return 403, {"error": "Esta conexão não pertence a esta conta."}
    now = store.now()
    connector = ((remote.get("connector") or {}).get("name") or "Banco")[:80]
    status = remote.get("status") or "UPDATING"
    detail = ((remote.get("error") or {}).get("code") or remote.get("executionStatus") or "")[:80]
    consent = remote.get("consentExpiresAt") or None
    if current:
        link_id = current["id"]
        conn.execute(
            "UPDATE bank_link SET connector_name = ?, status = ?, status_detail = ?, consent_expires_at = ?, updated_at = ? WHERE id = ?",
            (connector, status, detail, consent, now, link_id),
        )
    else:
        link_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO bank_link (id, owner_id, provider, item_id, connector_name, status, status_detail, consent_expires_at, last_synced_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (link_id, owner, PROVIDER, item_id, connector, "novo", detail, consent, None, now, now),
        )
        store.log(conn, owner, "bank_link", link_id, "conectar", None, {"id": link_id, "connector": connector})
    _queue(conn, owner, item_id, "sync/requested", {})
    return 200, {"id": link_id, "notice": CONNECTING}


def _disconnect(conn, owner, link_id):
    link = store.one(conn, "SELECT * FROM bank_link WHERE id = ? AND owner_id = ?", (link_id, owner))
    if not link:
        return 404, {"error": "Não encontrado para esta pessoa."}
    try:
        pluggy.client().delete_item(link["item_id"])
    except pluggy.PluggyError as exc:
        if exc.code != "not_found":
            print("ISA bank " + (exc.code or "delete"), flush=True)
            return 503, {"error": str(exc)}
    conn.execute("UPDATE bank_link SET status = ?, status_detail = ?, updated_at = ? WHERE id = ?", ("desligado", "", store.now(), link["id"]))
    store.log(conn, owner, "bank_link", link["id"], "desligar", {"status": link["status"]}, {"status": "desligado"})
    return 200, {"id": link["id"], "notice": "Desligado. O histórico já trazido permanece."}


def accept_webhook(conn, header, body):
    secret = _secret()
    sent = header or ""
    if not secret or not hmac.compare_digest(sent, secret):
        return 401, {"error": "Não autorizado."}
    event_id = str((body or {}).get("eventId") or "").strip()
    event = str((body or {}).get("event") or "").strip()
    if not event_id or not event:
        return 400, {"error": "Evento incompleto."}
    item_id = str((body or {}).get("itemId") or "")
    link = store.one(conn, "SELECT owner_id FROM bank_link WHERE item_id = ?", (item_id,)) if item_id else None
    owner = link["owner_id"] if link else None
    payload = {
        "accountId": (body or {}).get("accountId") or "",
        "transactionIds": (body or {}).get("transactionIds") or [],
        "createdTransactionsLink": (body or {}).get("createdTransactionsLink") or "",
    }
    try:
        conn.execute(
            "INSERT INTO bank_event (event_id, owner_id, event, item_id, received_at, processed_at, status, error_code, payload_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (event_id, owner, event, item_id, store.now(), None, "recebido", "", json.dumps(payload)),
        )
    except sqlite3.IntegrityError:
        return 200, {"ok": True}
    known = {
        "item/created", "item/updated", "item/error", "item/waiting_user_action", "item/waiting_user_input", "item/deleted",
        "transactions/created", "transactions/updated", "transactions/deleted", "sync/requested",
    }
    print("ISA bank " + (event if event in known else "evento"), flush=True)
    return 200, {"ok": True}


def _queue(conn, owner, item_id, event, payload):
    conn.execute(
        "INSERT INTO bank_event (event_id, owner_id, event, item_id, received_at, processed_at, status, error_code, payload_json) VALUES (?,?,?,?,?,?,?,?,?)",
        (uuid.uuid4().hex, owner, event, item_id, store.now(), None, "recebido", "", json.dumps(payload)),
    )


def release_owner(conn, owner):
    links = store.rows(conn, "SELECT item_id, status FROM bank_link WHERE owner_id = ?", (owner,))
    if not links:
        return
    remote = None
    for link in links:
        if link["status"] == "desligado":
            continue
        try:
            if remote is None:
                remote = pluggy.client()
            remote.delete_item(link["item_id"])
        except Exception as exc:
            print("ISA bank release " + type(exc).__name__, flush=True)


def work_once(conn, transport=None, clock=None):
    event = store.one(conn, "SELECT * FROM bank_event WHERE processed_at IS NULL ORDER BY received_at, event_id LIMIT 1")
    if event:
        claimed = conn.execute(
            "UPDATE bank_event SET status = ? WHERE event_id = ? AND processed_at IS NULL",
            ("processando", event["event_id"]),
        ).rowcount
        if not claimed:
            return True
        code = ""
        try:
            _process_event(conn, event, transport, clock)
            status = "feito"
        except pluggy.PluggyError as exc:
            status = "falhou"
            code = exc.code or "erro"
            print("ISA bank " + code, flush=True)
        except Exception as exc:
            status = "falhou"
            code = type(exc).__name__
            print("ISA bank " + code, flush=True)
        conn.execute(
            "UPDATE bank_event SET processed_at = ?, status = ?, error_code = ? WHERE event_id = ?",
            (store.now(), status, code, event["event_id"]),
        )
        return True
    cutoff = _shift(store.reference_date(), -1) + "T00:00:00+00:00"
    link = store.one(
        conn,
        "SELECT * FROM bank_link WHERE status != ? AND (status = ? OR last_synced_at IS NULL OR last_synced_at < ?) ORDER BY updated_at LIMIT 1",
        ("desligado", "novo", cutoff),
    )
    if not link:
        return False
    claimed = conn.execute(
        "UPDATE bank_link SET updated_at = ? WHERE id = ? AND updated_at = ?",
        (store.now(), link["id"], link["updated_at"]),
    ).rowcount
    if not claimed:
        return True
    try:
        sync_link(conn, link, transport=transport, clock=clock)
    except Exception as exc:
        code = exc.code if isinstance(exc, pluggy.PluggyError) else type(exc).__name__
        print("ISA bank " + code, flush=True)
    return True


def _process_event(conn, event, transport, clock):
    payload = json.loads(event["payload_json"] or "{}")
    name = event["event"]
    link = store.one(conn, "SELECT * FROM bank_link WHERE item_id = ?", (event["item_id"],)) if event["item_id"] else None
    if name in ("item/error", "item/waiting_user_action", "item/waiting_user_input"):
        if link:
            conn.execute(
                "UPDATE bank_link SET status = ?, status_detail = ?, updated_at = ? WHERE id = ?",
                ("LOGIN_ERROR" if name == "item/error" else "WAITING_USER_INPUT", name, store.now(), link["id"]),
            )
        return
    if not link or link["status"] == "desligado":
        return
    if name in ("item/updated", "item/created", "sync/requested"):
        sync_link(conn, link, transport=transport, clock=clock, full=name == "sync/requested" and not link["last_synced_at"])
        return
    remote = _remote(transport, clock)
    if name == "transactions/deleted":
        _mark_removed(conn, link["owner_id"], payload.get("transactionIds") or [])
        return
    if name == "transactions/created" and payload.get("createdTransactionsLink"):
        rows = remote.follow_link(payload["createdTransactionsLink"])
        _apply_transactions(conn, link, rows, remote)
        _settle_payments(conn, link["owner_id"])
        return
    if name == "transactions/updated":
        account_id = payload.get("accountId") or ""
        identifiers = payload.get("transactionIds") or []
        if account_id and identifiers:
            rows = remote.transactions_by_ids(account_id, identifiers)
            _apply_transactions(conn, link, rows, remote)
            _settle_payments(conn, link["owner_id"])
        return
    if name == "transactions/created":
        sync_link(conn, link, transport=transport, clock=clock, full=False)


def _remote(transport, clock):
    return pluggy.client(transport=transport, clock=clock)


def sync_link(conn, link, transport=None, clock=None, full=None):
    remote = _remote(transport, clock)
    item = remote.item(link["item_id"])
    if (item.get("clientUserId") or "") != client_user_id(link["owner_id"]):
        raise pluggy.PluggyError("Esta conexão não pertence a esta conta.", "client-mismatch")
    status = item.get("status") or link["status"]
    detail = ((item.get("error") or {}).get("code") or item.get("executionStatus") or "")[:80]
    conn.execute(
        "UPDATE bank_link SET connector_name = ?, status = ?, status_detail = ?, consent_expires_at = ?, updated_at = ? WHERE id = ?",
        (((item.get("connector") or {}).get("name") or link["connector_name"])[:80], status, detail, item.get("consentExpiresAt") or link.get("consent_expires_at"), store.now(), link["id"]),
    )
    link = store.one(conn, "SELECT * FROM bank_link WHERE id = ?", (link["id"],))
    accounts = remote.accounts(link["item_id"])
    local_accounts = []
    for account in accounts:
        saved = _upsert_account(conn, link, account)
        if saved:
            local_accounts.append((saved, account))
    today = store.reference_date()
    for saved, account in local_accounts:
        if saved.get("kind") in ("corrente", "poupanca"):
            _balance(conn, link["owner_id"], saved, account, item.get("lastUpdatedAt") or "")
        if saved.get("kind") == "cartao":
            _bill(conn, link["owner_id"], saved, account)
        if account.get("id"):
            start = _window_start(conn, link["owner_id"], [saved["id"]], today, bool(full))
            rows = remote.transactions(account["id"], start, today)
            _apply_transactions(conn, link, rows, remote, saved, start)
    for position in remote.investments(link["item_id"]):
        _position(conn, link, position)
    _settle_payments(conn, link["owner_id"])
    conn.execute("UPDATE bank_link SET last_synced_at = ?, updated_at = ? WHERE id = ?", (store.now(), store.now(), link["id"]))


def _window_start(conn, owner, account_ids, today, first):
    if first or not account_ids:
        return _shift(today, -365)
    marks = []
    for account_id in account_ids:
        row = store.one(conn, "SELECT MAX(booked_on) AS day FROM ledger_entry WHERE owner_id = ? AND account_id = ? AND external_id IS NOT NULL AND external_id != ''", (owner, account_id))
        if row and row["day"]:
            marks.append(row["day"])
    if not marks:
        return _shift(today, -365)
    return _shift(max(marks), -7)


def _parts(account):
    transfer = ((account.get("bankData") or {}).get("transferNumber") or "")
    pieces = [item.strip() for item in transfer.split("/") if item.strip()]
    if len(pieces) >= 3:
        return _digits(pieces[0]), _digits(pieces[1]), _digits(pieces[2])
    number = str(account.get("number") or "")
    chunks = [item.strip() for item in number.split("/") if item.strip()]
    if len(chunks) == 2:
        return "", _digits(chunks[0]), _digits(chunks[1])
    return "", "", _digits(number)


def _kind(account):
    return KINDS.get(((account.get("type") or "").upper(), (account.get("subtype") or "").upper()))


def _upsert_account(conn, link, account):
    kind = _kind(account)
    if not kind:
        print("ISA bank tipo-nao-mapeado", flush=True)
        return None
    owner = link["owner_id"]
    external = str(account.get("id") or "")
    currency = str(account.get("currencyCode") or "BRL").upper()
    if len(currency) != 3:
        return None
    current = store.one(conn, "SELECT * FROM account WHERE owner_id = ? AND external_id = ?", (owner, external)) if external else None
    if not current:
        matched = _match_manual(conn, owner, account, currency)
        if matched == "ambiguous":
            print("ISA bank vinculo-ambiguo", flush=True)
            return None
        current = matched
        if current:
            store.log(conn, owner, "account", current["id"], "conta-vinculada-banco", {"external_id": None}, {"external_id": external})
    compe, agency, number = _parts(account)
    if current:
        if current.get("currency") != currency:
            return current
        conn.execute(
            "UPDATE account SET external_id = ?, provider = ?, bank_link_id = ?, external_type = ?, external_subtype = ?, kind = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
            (external, PROVIDER, link["id"], account.get("type") or "", account.get("subtype") or "", kind, store.now(), current["id"], owner),
        )
        return store.one(conn, "SELECT * FROM account WHERE id = ?", (current["id"],))
    import catalog_str
    institution = link["connector_name"]
    code = compe
    if compe and compe in catalog_str.BY_CODE:
        institution = catalog_str.BY_CODE[compe][0]["name"]
        code = catalog_str.BY_CODE[compe][0]["code"]
    body = {
        "name": (account.get("name") or "Conta")[:80],
        "institution": institution,
        "kind": kind,
        "currency": currency if currency in store.CURRENCIES else "BRL",
        "accountNumber": (account.get("number") or number or "sem número")[:40],
        "bankCode": code,
        "agency": agency,
        "intake": "manual",
        "registration": False,
    }
    if currency not in store.CURRENCIES:
        body["currency"] = "BRL"
    created = store.save_account(conn, owner, body)
    if currency not in store.CURRENCIES:
        conn.execute("UPDATE account SET currency = ? WHERE id = ? AND owner_id = ?", (currency, created["id"], owner))
    conn.execute(
        "UPDATE account SET external_id = ?, provider = ?, bank_link_id = ?, external_type = ?, external_subtype = ?, liquid = ? WHERE id = ? AND owner_id = ?",
        (external, PROVIDER, link["id"], account.get("type") or "", account.get("subtype") or "", 0 if kind == "cartao" else created.get("liquid") or 0, created["id"], owner),
    )
    return store.one(conn, "SELECT * FROM account WHERE id = ?", (created["id"],))


def _match_manual(conn, owner, account, currency):
    compe, agency, number = _parts(account)
    if not number:
        return None
    found = []
    for row in store.rows(conn, "SELECT * FROM account WHERE owner_id = ? AND (external_id IS NULL OR external_id = '')", (owner,)):
        if (row.get("currency") or "BRL") != currency:
            continue
        local = _digits((row.get("account_number") or "") + (row.get("account_digit") or ""))
        if not local or local != number and not (local.endswith(number) or number.endswith(local)):
            continue
        if compe and _digits(row.get("bank_code")) and _digits(row.get("bank_code")) != compe:
            continue
        if agency and _digits(row.get("agency")) and _digits(row.get("agency")) != agency:
            continue
        if not compe:
            continue
        found.append(row)
    if len(found) > 1:
        return "ambiguous"
    return found[0] if found else None


def _balance(conn, owner, saved, account, observed_at):
    """A data do saldo é lastUpdatedAt do item. Sem esse campo, não usa a hora da sincronização."""
    if saved.get("kind") not in ("corrente", "poupanca") or account.get("balance") is None:
        return
    civil = _civil(observed_at)
    if not civil:
        return
    store.save_availability(conn, owner, {
        "accountId": saved["id"],
        "amountCents": int((Decimal(str(account["balance"])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "asOf": civil,
        "observedAt": str(observed_at),
        "source": "banco",
    })


def _bill(conn, owner, saved, account):
    credit = account.get("creditData") or {}
    balance = account.get("balance")
    if balance is None:
        return
    cents = int((Decimal(str(balance)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents < 0:
        cents = 0
    minimum = credit.get("minimumPayment")
    conditions = {
        "custo": "desconhecido",
        "aceite": "desconhecido",
        "pluggyOpenBill": saved.get("external_id") or saved["id"],
    }
    if minimum is not None:
        conditions["minimumPaymentCents"] = _cents(minimum)
    due = str(credit.get("balanceDueDate") or "")[:10]
    if len(due) != 10:
        due = ""
    key = conditions["pluggyOpenBill"]
    current = None
    for row in store.rows(conn, "SELECT * FROM commitment WHERE owner_id = ? AND origin = ?", (owner, "banco")):
        try:
            body = json.loads(row["conditions_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if body.get("pluggyOpenBill") == key:
            current = row
            break
    label = "Fatura do cartão"
    tail = _digits(account.get("number"))
    if tail:
        label = "Fatura do cartão " + tail[-4:]
    if current:
        try:
            previous = json.loads(current["conditions_json"] or "{}")
        except json.JSONDecodeError:
            previous = {}
        conditions["appliedPayments"] = previous.get("appliedPayments") or []
        conditions["settledCents"] = previous.get("settledCents") or 0
        previous_total = int(current["total_cents"] or 0)
        previous_remaining = int(current["remaining_cents"] or 0)
        remaining = cents if cents > previous_total else min(cents, previous_remaining)
        conn.execute(
            "UPDATE commitment SET total_cents = ?, remaining_cents = ?, due_on = ?, conditions_json = ?, account_id = ? WHERE id = ? AND owner_id = ?",
            (cents, remaining, due or None, json.dumps(conditions), saved["id"], current["id"], owner),
        )
        return
    if cents == 0 and minimum is None:
        return
    item_id = store._id()
    conn.execute(
        "INSERT INTO commitment (id, owner_id, label, total_cents, remaining_cents, due_on, original_due_on, essential, priority, recurrence, series_id, origin, conditions_json, created_at, account_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (item_id, owner, label, cents, cents, due or None, due or None, 0, None, None, store._id(), "banco", json.dumps(conditions), store.now(), saved["id"]),
    )
    store.log(conn, owner, "commitment", item_id, "criar", None, {"id": item_id, "origin": "banco"})


def _movement(tx, account_type):
    kind = str(tx.get("type") or "").upper()
    if kind == "CREDIT":
        return "ganho", "recebido", "entrada"
    if kind == "DEBIT":
        return "gasto", "pago", "saida"
    if account_type == "CREDIT" and tx.get("amount") is not None:
        return ("gasto", "pago", "saida") if Decimal(str(tx["amount"])) > 0 else ("ganho", "recebido", "entrada")
    return None


def text_closeness(left, right):
    first, second = _norm(left), _norm(right)
    if not _contains(first, second):
        return 0
    short = min(len(first), len(second))
    long = max(len(first), len(second))
    return short / long


def assign_pairs(left_rows, right_rows):
    """Um a um. A assinatura mais próxima vem primeiro; empate segue a ordem de chegada."""
    ranked = []
    for i, left in enumerate(left_rows):
        for j, right in enumerate(right_rows):
            score = text_closeness(left.get("text") or "", right.get("text") or "")
            if score <= 0:
                continue
            ranked.append((-score, left.get("order", i), right.get("order", j), i, j))
    ranked.sort()
    used_left, used_right = set(), set()
    pairs = []
    for _, _, _, i, j in ranked:
        if i in used_left or j in used_right:
            continue
        used_left.add(i)
        used_right.add(j)
        pairs.append((left_rows[i], right_rows[j]))
    return (
        pairs,
        [row for i, row in enumerate(left_rows) if i not in used_left],
        [row for j, row in enumerate(right_rows) if j not in used_right],
    )


def _apply_transactions(conn, link, rows, remote, account=None, start=None):
    owner = link["owner_id"]
    today = store.reference_date()
    if not start:
        start = _shift(today, -365)
    pending = []
    for tx in rows:
        if str(tx.get("status") or "").upper() != "POSTED":
            continue
        external = str(tx.get("id") or "")
        if not external:
            continue
        civil = _civil(tx.get("date"))
        if not civil:
            continue
        local = account
        if local is None or (tx.get("accountId") and local.get("external_id") != tx.get("accountId")):
            local = store.one(conn, "SELECT * FROM account WHERE owner_id = ? AND external_id = ?", (owner, tx.get("accountId")))
        if not local:
            continue
        if civil < start or civil > today:
            continue
        mapped = _movement(tx, local.get("external_type") or "")
        if not mapped or tx.get("amount") is None:
            print("ISA bank tipo-transacao", flush=True)
            continue
        direction, status, column = mapped
        try:
            amount = _cents(tx["amount"])
        except Exception:
            continue
        currency = str(tx.get("currencyCode") or local.get("currency") or "BRL").upper()
        category_name = tx.get("category") or ""
        suggested = suggest_category(category_name)
        existing = store.one(conn, "SELECT * FROM ledger_entry WHERE owner_id = ? AND external_id = ?", (owner, external))
        if not existing and tx.get("providerId"):
            existing = _by_provider(conn, owner, local["id"], tx.get("providerId"))
        if existing:
            _refresh_entry(conn, owner, existing, tx, civil, direction, status, amount, currency, category_name, suggested, external)
            continue
        pending.append({
            "tx": tx,
            "local": local,
            "civil": civil,
            "direction": direction,
            "status": status,
            "column": column,
            "amount": amount,
            "currency": currency,
            "category_name": category_name,
            "suggested": suggested,
            "external": external,
            "order": len(pending),
        })
    _place_pending(conn, owner, pending)
    _settle_payments(conn, owner)


def _refresh_entry(conn, owner, existing, tx, civil, direction, status, amount, currency, category_name, suggested, external):
    payload = json.loads(existing["payload_json"])
    if payload.get("originRemoved"):
        payload["originRemoved"] = False
    payload["id"] = existing["id"]
    payload["pluggyCategory"] = category_name
    payload["statusDate"] = civil
    payload["noteDate"] = civil
    payload["amountMinor"] = amount
    payload["direction"] = direction
    payload["status"] = status
    payload["currency"] = currency
    if tx.get("providerId"):
        payload["providerId"] = tx.get("providerId")
    if suggested and payload.get("categorizationStatus") in ("", "a_categorizar", "sugerida"):
        payload["category"] = suggested
        payload["categorizationStatus"] = "sugerida"
    payload["externalId"] = external
    store.write_entry(conn, owner, payload)


def _by_provider(conn, owner, account_id, provider_id):
    for row in store.rows(conn, "SELECT * FROM ledger_entry WHERE owner_id = ? AND account_id = ?", (owner, account_id)):
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            continue
        if payload.get("providerId") == provider_id:
            return row
    return None


def _statement_text(payload):
    return (payload.get("merchant") or "") + " " + (payload.get("lineSignature") or "")


def _place_pending(conn, owner, pending):
    groups = {}
    for item in pending:
        key = (item["local"]["id"], item["civil"], item["amount"], item["column"])
        groups.setdefault(key, []).append(item)
    for (account_id, civil, amount, column), items in groups.items():
        statements = []
        for index, row in enumerate(store.rows(
            conn,
            "SELECT * FROM ledger_entry WHERE owner_id = ? AND account_id = ? AND booked_on = ? AND amount_cents = ? AND direction = ? AND (external_id IS NULL OR external_id = '') ORDER BY id",
            (owner, account_id, civil, amount, column),
        )):
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                continue
            if payload.get("source") != "extrato-bb-arquivo":
                continue
            statements.append({"text": _statement_text(payload), "order": index, "row": row, "payload": payload})
        remotes = [{"text": item["tx"].get("description") or "", "order": item["order"], "item": item} for item in items]
        pairs, _, leftover = assign_pairs(statements, remotes)
        for local, remote in pairs:
            _bind_statement(conn, owner, local, remote["item"])
        for remote in leftover:
            _create_pluggy(conn, owner, remote["item"])


def _bind_statement(conn, owner, local, item):
    payload = dict(local["payload"])
    tx = item["tx"]
    payload["pluggyCategory"] = item["category_name"]
    if tx.get("providerId"):
        payload["providerId"] = tx.get("providerId")
    payload["id"] = local["row"]["id"]
    payload["externalId"] = item["external"]
    payload["accountKind"] = item["local"].get("kind") or ""
    store.write_entry(conn, owner, payload, action="lancamento-vinculado-banco")


def _create_pluggy(conn, owner, item):
    tx = item["tx"]
    payload = {
        "accountId": item["local"]["id"],
        "accountKind": item["local"].get("kind") or "",
        "direction": item["direction"],
        "nature": "ganho" if item["direction"] == "ganho" else "consumo",
        "merchant": str(tx.get("description") or "Movimento")[:180],
        "noteDate": item["civil"],
        "statusDate": item["civil"],
        "dueDate": "",
        "amountMinor": item["amount"],
        "currency": item["currency"],
        "category": item["suggested"],
        "categorizationStatus": "sugerida" if item["suggested"] else "a_categorizar",
        "status": item["status"],
        "source": "pluggy",
        "pluggyCategory": item["category_name"],
        "providerId": tx.get("providerId") or "",
        "simulated": False,
        "archived": False,
        "externalId": item["external"],
    }
    store.write_entry(conn, owner, payload)


def plan_import_links(conn, owner, movements):
    """Extrato importado depois da Pluggy. Devolve o índice do movimento e o lançamento já gravado."""
    groups = {}
    prepared = []
    for index, row in enumerate(movements or []):
        item = {
            "index": index,
            "text": (row.get("label") or "") + " " + (row.get("signature") or ""),
            "order": index,
            "account": row.get("accountId") or "",
            "civil": str(row.get("date") or "")[:10],
            "amount": abs(int(row.get("cents") or 0)),
            "column": row.get("direction") or "saida",
        }
        prepared.append(item)
        groups.setdefault((item["account"], item["civil"], item["amount"], item["column"]), []).append(item)
    chosen = {}
    for (account_id, civil, amount, column), items in groups.items():
        if not account_id or not civil or not amount:
            continue
        remotes = []
        for index, row in enumerate(store.rows(
            conn,
            "SELECT * FROM ledger_entry WHERE owner_id = ? AND account_id = ? AND booked_on = ? AND amount_cents = ? AND direction = ? AND external_id IS NOT NULL AND external_id != '' ORDER BY id",
            (owner, account_id, civil, amount, column),
        )):
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                continue
            if payload.get("lineSignature") or payload.get("source") == "extrato-bb-arquivo":
                continue
            remotes.append({"text": payload.get("merchant") or "", "order": index, "row": row})
        pairs, _, _ = assign_pairs(items, remotes)
        for local, remote in pairs:
            chosen[local["index"]] = remote["row"]
    return chosen


def absorb_statement(conn, owner, linked, row, occurrence_id):
    payload = json.loads(linked["payload_json"])
    payload["id"] = linked["id"]
    payload["lineSignature"] = row.get("signature") or ""
    payload["occurrenceId"] = occurrence_id
    payload["externalId"] = linked.get("external_id") or payload.get("externalId") or ""
    store.write_entry(conn, owner, payload, action="lancamento-vinculado-banco")


def _days_apart(left, right):
    try:
        return abs((date.fromisoformat(left) - date.fromisoformat(right)).days)
    except ValueError:
        return 99


def _settle_payments(conn, owner):
    accounts = {item["id"]: item for item in store.rows(conn, "SELECT * FROM account WHERE owner_id = ?", (owner,))}
    credits = []
    debits = []
    for row in store.rows(conn, "SELECT * FROM ledger_entry WHERE owner_id = ? AND COALESCE(archived, 0) = 0", (owner,)):
        account = accounts.get(row.get("account_id") or "")
        if not account:
            continue
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            continue
        if payload.get("originRemoved") or (row.get("nature") or "") == "transferencia":
            continue
        item = {"row": row, "payload": payload, "account": account, "day": row.get("booked_on") or "", "amount": int(row["amount_cents"] or 0)}
        if account.get("kind") == "cartao" and row.get("direction") == "entrada":
            credits.append(item)
        elif account.get("kind") in ("corrente", "poupanca") and row.get("direction") == "saida":
            debits.append(item)
    ranked = []
    for i, credit in enumerate(credits):
        for j, debit in enumerate(debits):
            if credit["amount"] != debit["amount"] or _days_apart(credit["day"], debit["day"]) > 3:
                continue
            ranked.append((_days_apart(credit["day"], debit["day"]), credit["row"]["id"], debit["row"]["id"], i, j))
    ranked.sort()
    used_credit, used_debit = set(), set()
    for _, _, _, i, j in ranked:
        if i in used_credit or j in used_debit:
            continue
        used_credit.add(i)
        used_debit.add(j)
        _mark_transfer(conn, owner, credits[i], debits[j])
        _pay_bill(conn, owner, credits[i]["account"]["id"], credits[i]["amount"], credits[i]["row"]["id"])
    for i, credit in enumerate(credits):
        if i in used_credit or credit["payload"].get("billPaymentApplied"):
            continue
        _mark_bill_payment(conn, owner, credit)
        _pay_bill(conn, owner, credit["account"]["id"], credit["amount"], credit["row"]["id"])


def _mark_transfer(conn, owner, credit, debit):
    for item, other in ((credit, debit), (debit, credit)):
        payload = dict(item["payload"])
        payload["id"] = item["row"]["id"]
        payload["nature"] = "transferencia"
        payload["transferPair"] = other["row"]["id"]
        payload["externalId"] = item["row"].get("external_id") or payload.get("externalId") or ""
        payload["billPaymentApplied"] = True
        store.write_entry(conn, owner, payload, action="transferencia-fatura")


def _mark_bill_payment(conn, owner, credit):
    payload = dict(credit["payload"])
    payload["id"] = credit["row"]["id"]
    payload["nature"] = "pagamento_fatura"
    payload["externalId"] = credit["row"].get("external_id") or payload.get("externalId") or ""
    payload["billPaymentApplied"] = True
    store.write_entry(conn, owner, payload, action="pagamento-fatura")


def _pay_bill(conn, owner, account_id, paid, entry_id):
    chosen = None
    for row in store.rows(conn, "SELECT * FROM commitment WHERE owner_id = ? AND account_id = ? AND origin = ?", (owner, account_id, "banco")):
        try:
            body = json.loads(row["conditions_json"] or "{}")
        except json.JSONDecodeError:
            body = {}
        applied = body.get("appliedPayments") or []
        if entry_id in applied:
            return
        if chosen is None or int(row["remaining_cents"] or 0) > int(chosen[0]["remaining_cents"] or 0):
            chosen = (row, body, applied)
    if not chosen:
        return
    row, body, applied = chosen
    remaining = max(0, int(row["remaining_cents"] or 0) - int(paid))
    applied = list(applied) + [entry_id]
    body["appliedPayments"] = applied
    body["settledCents"] = int(body.get("settledCents") or 0) + int(paid)
    conn.execute(
        "UPDATE commitment SET remaining_cents = ?, conditions_json = ? WHERE id = ? AND owner_id = ?",
        (remaining, json.dumps(body), row["id"], owner),
    )


def _mark_removed(conn, owner, identifiers):
    for external in identifiers:
        row = store.one(conn, "SELECT * FROM ledger_entry WHERE owner_id = ? AND external_id = ?", (owner, external))
        if not row:
            continue
        payload = json.loads(row["payload_json"])
        payload["id"] = row["id"]
        payload["originRemoved"] = True
        store.write_entry(conn, owner, payload, action="removido-na-origem")


def _position(conn, link, position):
    external = str(position.get("id") or "")
    if not external:
        return
    balance = position.get("balance")
    amount = None if balance is None else int((Decimal(str(balance)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    kept = {
        "id": external,
        "name": position.get("name") or "",
        "type": position.get("type") or "",
        "subtype": position.get("subtype") or "",
        "balance": balance,
        "currencyCode": position.get("currencyCode") or "",
        "date": position.get("date") or "",
        "status": position.get("status") or "",
    }
    now = store.now()
    current = store.one(conn, "SELECT id FROM investment_position WHERE owner_id = ? AND external_id = ?", (link["owner_id"], external))
    values = (
        position.get("name") or "Investimento",
        position.get("type") or position.get("subtype") or "OTHER",
        amount,
        str(position.get("currencyCode") or "BRL").upper(),
        _civil(position.get("date")) or None,
        json.dumps(kept),
        now,
    )
    if current:
        conn.execute(
            "UPDATE investment_position SET name = ?, kind = ?, amount_cents = ?, currency = ?, as_of = ?, liquidity_note = NULL, raw_json = ?, updated_at = ? WHERE id = ?",
            values + (current["id"],),
        )
        return
    conn.execute(
        "INSERT INTO investment_position (id, owner_id, bank_link_id, external_id, name, kind, amount_cents, currency, as_of, liquidity_note, raw_json, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (uuid.uuid4().hex, link["owner_id"], link["id"], external, values[0], values[1], values[2], values[3], values[4], None, values[5], values[6]),
    )


def worker_turn(state, database, transport=None, clock=None):
    conn = state.get("conn")
    try:
        if conn is None:
            conn = store.connect(database, bootstrap=False)
            state["conn"] = conn
        return work_once(conn, transport=transport, clock=clock)
    except Exception as exc:
        print("ISA bank worker " + type(exc).__name__, flush=True)
        if conn is not None:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                state["conn"] = None
        return False


def start_worker(database):
    if os.environ.get("ISA_PLUGGY_ENABLED") != "1":
        return

    def run():
        state = {"conn": None}
        while True:
            active = worker_turn(state, database)
            time.sleep(1 if active else 5)

    threading.Thread(target=run, name="isa-bank", daemon=True).start()
