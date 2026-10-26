"""Lançamento em colunas. A foto compara o cálculo antigo com o novo, nos mesmos dados."""

import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import ai
import store
import workbatches

ROOT = Path(__file__).resolve().parents[1]
META = {"provider": "aws-bedrock", "model": "test-only", "request_id": "synthetic", "usage": {"inputTokens": 10, "outputTokens": 10}}
LEDGER_COLUMNS = (
    "direction", "amount_cents", "currency", "booked_on", "due_on", "status",
    "nature", "category", "source", "occurrence_id", "archived", "simulated",
)


def legacy_month_picture(conn, owner, month, reference, account_id=None):
    """Cálculo do mês como estava antes deste recorte. Serve de foto, não de leitura nova."""
    month = store.calendar_month(month)
    start = month + "-01"
    year, mon = [int(part) for part in month.split("-")]
    end = f"{year + 1}-01-01" if mon == 12 else f"{year}-{mon + 1:02d}-01"
    phase = "atual" if month == reference[:7] else ("passado" if month < reference[:7] else "futuro")
    accounts = {}
    for item in store.rows(conn, "SELECT id, payload_json FROM occurrence WHERE owner_id = ?", (owner,)):
        payload = store._payload(item["payload_json"])
        accounts[item["id"]] = payload.get("accountId") or ""
    seen = set()
    realized_in = realized_out = 0
    forecast_in = forecast_out = 0
    pending_nature = 0
    records = []
    for row in store.rows(conn, "SELECT * FROM movement WHERE owner_id = ? AND booked_on >= ? AND booked_on < ?", (owner, start, end)):
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
            "id": row["id"], "on": booked, "label": row["label"], "cents": amount,
            "direction": direction, "state": state, "nature": nature,
        })
        seen.add(row["occurrence_id"])
    for item in store.rows(conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ?", (owner,)):
        payload = store._payload(item["payload_json"])
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
        records.append({
            "id": payload.get("id") or "", "on": when, "label": payload.get("merchant") or "Lançamento",
            "cents": amount, "direction": direction, "state": state, "nature": nature,
        })
    open_items = []
    for item in store.rows(conn, "SELECT * FROM commitment WHERE owner_id = ?", (owner,)):
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
    for item in store.rows(conn, "SELECT * FROM inflow WHERE owner_id = ?", (owner,)):
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
        "month": month, "phase": phase, "realizedIn": realized_in, "realizedOut": realized_out,
        "forecastIn": forecast_in, "forecastOut": forecast_out, "pendingNatureCents": pending_nature,
        "records": records, "emptyForecast": phase == "futuro" and not open_items,
    }


def rewind_ledger(conn):
    for name in (
        "ledger_entry_owner_booked_idx", "ledger_entry_owner_account_booked_idx", "ledger_entry_occurrence_uidx",
        "ledger_entry_owner_amount_idx",
    ):
        conn.execute("DROP INDEX IF EXISTS " + name)
    for column in LEDGER_COLUMNS:
        conn.execute("ALTER TABLE ledger_entry DROP COLUMN " + column)
    conn.execute("DELETE FROM schema_migration WHERE version IN (10, 11, 12)")


def snapshot(conn):
    return store.rows(conn, "SELECT * FROM ledger_entry ORDER BY id")


def plant_october(conn, owner):
    bb = store.save_account(conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
    poup = store.save_account(conn, owner, {"name": "Poupança", "currency": "BRL", "kind": "poupanca", "institution": "CAIXA ECONOMICA FEDERAL"})
    store.save_availability(conn, owner, {"accountId": bb["id"], "amountCents": 100000, "asOf": "2026-10-26", "protectedCents": 0, "source": "declarada"})
    store.save_availability(conn, owner, {"accountId": poup["id"], "amountCents": 20000, "asOf": "2026-10-26", "protectedCents": 20000, "source": "declarada"})
    lines = [
        ("2026-10-05", 400000, "entrada", "Salário", "ganho"),
        ("2026-10-10", 180000, "saida", "Moradia", "consumo"),
        ("2026-10-15", 90000, "saida", "Mercado", "consumo"),
        ("2026-10-23", 40000, "saida", "Contas", "consumo"),
    ]
    store.import_batch(conn, owner, {
        "batchKey": "cena-26",
        "origin": "extrato-bb-arquivo",
        "movements": [{
            "signature": "cena-" + label, "date": day, "cents": cents, "direction": direction,
            "label": label, "nature": nature, "accountId": bb["id"],
        } for day, cents, direction, label, nature in lines],
    })
    store.add_commitment(conn, owner, {"label": "Conta do dia 27", "totalCents": 45000, "dueOn": "2026-10-27", "accountId": bb["id"]})
    store.add_commitment(conn, owner, {"label": "Conta do dia 28", "totalCents": 90000, "dueOn": "2026-10-28", "accountId": bb["id"]})
    store.add_inflow(conn, owner, {"label": "Recebimento", "amountCents": 150000, "dueOn": "2026-10-30", "state": "confirmada", "accountId": bb["id"]})
    store.add_commitment(conn, owner, {"label": "Novembro 3", "totalCents": 70000, "dueOn": "2026-11-03", "accountId": bb["id"]})
    store.add_inflow(conn, owner, {"label": "Salário de novembro", "amountCents": 400000, "dueOn": "2026-11-05", "state": "confirmada", "accountId": bb["id"]})
    store.add_commitment(conn, owner, {"label": "Novembro 10", "totalCents": 180000, "dueOn": "2026-11-10", "accountId": bb["id"]})
    store.add_commitment(conn, owner, {"label": "Novembro 20", "totalCents": 100000, "dueOn": "2026-11-20", "accountId": bb["id"]})
    return bb, poup


def plant_synthetic(conn, owner, count=1800):
    bb = store.save_account(conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
    caixa = store.save_account(conn, owner, {"name": "Caixa", "currency": "BRL", "kind": "corrente", "institution": "CAIXA ECONOMICA FEDERAL"})
    natures = ["consumo", "transferencia", "reembolso", "emprestimo", "bb_rende_facil", "a_conferir"]
    months = ["2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01"]
    movements = []
    for i in range(count):
        month = months[i % len(months)]
        direction = "entrada" if i % 3 == 0 else "saida"
        cents = 100 + (i % 4000)
        if direction == "saida" and i % 5:
            cents = -cents
        movements.append({
            "signature": f"sint-{owner}-{i}",
            "date": f"{month}-{(i % 27) + 1:02d}",
            "cents": cents,
            "direction": direction,
            "label": f"Linha {i} {owner}",
            "nature": natures[i % len(natures)],
            "accountId": bb["id"] if i % 4 else caixa["id"],
        })
    store.import_batch(conn, owner, {"batchKey": "lote-" + owner, "origin": "extrato-bb-arquivo", "movements": movements})
    batch = workbatches.create_batch(conn, owner, {"name": "Obra", "criterion": "outro"})
    other = workbatches.create_batch(conn, owner, {"name": "Outro", "criterion": "evento", "activate": False})
    for i in range(220):
        month = months[i % len(months)]
        payload = {
            "id": f"manual-{owner}-{i}",
            "merchant": f"Manual {i} {owner}",
            "amountMinor": 50 + i,
            "direction": "ganho" if i % 2 == 0 else "gasto",
            "status": "recebido" if i % 2 == 0 else "pago",
            "statusDate": f"{month}-{(i % 27) + 1:02d}",
            "noteDate": f"{month}-01",
            "dueDate": "2026-11-20" if i % 2 else "",
            "nature": "" if i % 19 == 0 else natures[i % len(natures)],
            "category": "",
            "archived": i % 17 == 0,
            "accountId": "" if i % 6 == 0 else bb["id"],
        }
        if i % 2 == 0:
            payload["workBatchId"] = batch["id"]
        store.save_entry(conn, owner, payload)
    store.save_entry(conn, owner, {"id": f"manual-{owner}-0", "workBatchId": other["id"], "merchant": f"Manual 0 {owner}", "amountMinor": 50, "direction": "ganho", "status": "recebido", "statusDate": "2026-08-01", "nature": "consumo"})
    store.add_commitment(conn, owner, {"label": "Boleto " + owner, "totalCents": 8000, "dueOn": "2026-10-28", "accountId": bb["id"]})
    store.add_commitment(conn, owner, {"label": "Vencido " + owner, "totalCents": 1500, "dueOn": "2026-07-02", "accountId": bb["id"]})
    store.add_inflow(conn, owner, {"label": "A receber " + owner, "amountCents": 6400, "dueOn": "2026-10-30", "state": "confirmada", "accountId": bb["id"]})
    return bb


def months_of(conn, owner):
    found = set()
    for sql in (
        "SELECT booked_on AS d FROM ledger_entry WHERE owner_id = ?",
        "SELECT booked_on AS d FROM movement WHERE owner_id = ?",
        "SELECT due_on AS d FROM commitment WHERE owner_id = ?",
        "SELECT due_on AS d FROM inflow WHERE owner_id = ?",
    ):
        for row in store.rows(conn, sql, (owner,)):
            text = row["d"] or ""
            if len(text) >= 7:
                found.add(text[:7])
    return sorted(found)


def assert_rules_not_the_old_photo(test, conn, owner):
    """A foto antiga somava o sinal da movimentação e tratava aberto como realizado. Não é mais o contrato."""
    negatives = store.rows(
        conn,
        "SELECT id, amount_cents FROM movement WHERE owner_id = ? AND amount_cents < 0",
        (owner,),
    )
    test.assertTrue(negatives)
    for movement in negatives:
        ledger = store.one(conn, "SELECT amount_cents FROM ledger_entry WHERE id = ?", (movement["id"],))
        test.assertEqual(ledger["amount_cents"], abs(int(movement["amount_cents"])))
    for row in store.rows(conn, "SELECT id, amount_cents, archived, booked_on, payload_json FROM ledger_entry WHERE owner_id = ?", (owner,)):
        test.assertGreaterEqual(int(row["amount_cents"] or 0), 0)
        payload = json.loads(row["payload_json"])
        test.assertEqual(row["booked_on"] or "", store.fact_date(payload))
    shown = set()
    for month in ("2026-10", "2026-11"):
        shown.update(item["id"] for item in store.month_picture(conn, owner, month, "2026-10-16")["records"])
    archived = store.rows(conn, "SELECT id FROM ledger_entry WHERE owner_id = ? AND COALESCE(archived, 0) = 1", (owner,))
    test.assertTrue(archived)
    for row in archived:
        test.assertNotIn(row["id"], shown)


def assert_same_picture(test, conn, owner, reference="2026-10-16"):
    page = store.home(conn, owner, reference)
    legacy = legacy_month_picture(conn, owner, reference[:7], reference, page["context"].get("accountId") or None)
    test.assertEqual(page["month"], legacy)
    for month in months_of(conn, owner):
        test.assertEqual(
            store.month_picture(conn, owner, month, reference),
            legacy_month_picture(conn, owner, month, reference),
            month,
        )
        account_id = page["context"].get("accountId")
        if account_id:
            test.assertEqual(
                store.month_picture(conn, owner, month, reference, account_id),
                legacy_month_picture(conn, owner, month, reference, account_id),
                month,
            )
    for account in store.rows(conn, "SELECT id FROM account WHERE owner_id = ?", (owner,)):
        test.assertEqual(
            store.month_picture(conn, owner, reference[:7], reference, account["id"]),
            legacy_month_picture(conn, owner, reference[:7], reference, account["id"]),
        )


def calc_summary(entries):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "entries.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle)
    script = (
        "const calc = require(process.argv[1]);"
        "const entries = require(process.argv[2]);"
        "const months = new Set();"
        "for (const entry of entries) {"
        "  for (const key of ['statusDate', 'noteDate', 'dueDate']) {"
        "    const value = String(entry[key] || '');"
        "    if (value.length >= 7) months.add(value.slice(0, 7));"
        "  }"
        "}"
        "const out = {};"
        "for (const month of [...months].sort()) out[month] = calc.summarize(entries, month);"
        "process.stdout.write(JSON.stringify(out));"
    )
    completed = subprocess.run(
        ["node", "-e", script, str(ROOT / "prototype" / "calc.js"), path],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


class QueryProxy:
    def __init__(self, conn):
        self.__dict__["_conn"] = conn
        self.__dict__["n"] = 0

    def execute(self, sql, *args, **kwargs):
        if str(sql).lstrip().upper().startswith("SELECT"):
            self.__dict__["n"] += 1
        return self._conn.execute(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def selects(conn, fn):
    proxy = QueryProxy(conn)
    started = time.perf_counter()
    fn(proxy)
    return proxy.n, (time.perf_counter() - started) * 1000


class LancamentoTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get("ISA_ENV")
        os.environ["ISA_ENV"] = "lab"
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-teste"

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()
        if self.prev is None:
            os.environ.pop("ISA_ENV", None)
        else:
            os.environ["ISA_ENV"] = self.prev

    def test_migration_from_schema_9_fills_columns_and_keeps_rows(self):
        rewind_ledger(self.conn)
        account = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        manual = {
            "id": "manual-ganho", "merchant": "Salário", "amountMinor": 250000, "direction": "ganho",
            "status": "recebido", "statusDate": "2026-10-05", "nature": "consumo", "accountId": account["id"], "archived": False,
        }
        gasto = {
            "id": "manual-gasto", "merchant": "Feira", "amountMinor": 3200, "direction": "gasto",
            "status": "pago", "statusDate": "2026-10-06", "noteDate": "2026-10-01", "nature": "consumo", "archived": True,
        }
        for payload in (manual, gasto):
            self.conn.execute(
                "INSERT INTO ledger_entry (id, owner_id, account_id, payload_json, updated_at) VALUES (?,?,?,?,?)",
                (payload["id"], self.owner, payload.get("accountId") or "", json.dumps(payload), "2026-10-01T00:00:00Z"),
            )
        self.conn.execute(
            "INSERT INTO occurrence (id, owner_id, batch_id, signature, state, movement_id, payload_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            ("occ-1", self.owner, "", "mov-1", "incorporada", "mov-1", json.dumps({"accountId": account["id"], "cents": -1800, "direction": "saida", "date": "2026-10-11", "label": "Importado", "nature": "a_conferir", "signature": "occ-1", "source": "extrato-bb-arquivo"}), store.now()),
        )
        self.conn.execute(
            "INSERT INTO movement (id, owner_id, occurrence_id, amount_cents, direction, nature, booked_on, label, source, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("mov-1", self.owner, "occ-1", -1800, "saida", "a_conferir", "2026-10-11", "Importado", "extrato-bb-arquivo", store.now()),
        )
        before_ids = [row["id"] for row in store.rows(self.conn, "SELECT id FROM ledger_entry ORDER BY id")]
        store._migrate_body(self.conn)
        store.backfill_entry_columns(self.conn)
        rows = store.rows(self.conn, "SELECT * FROM ledger_entry ORDER BY id")
        self.assertEqual(sorted(row["id"] for row in rows), sorted(before_ids + ["mov-1"]))
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(by_id["manual-ganho"]["direction"], "entrada")
        self.assertEqual(by_id["manual-ganho"]["amount_cents"], 250000)
        self.assertEqual(by_id["manual-ganho"]["booked_on"], "2026-10-05")
        self.assertEqual(by_id["manual-ganho"]["account_id"], account["id"])
        self.assertEqual(by_id["manual-gasto"]["direction"], "saida")
        self.assertEqual(by_id["manual-gasto"]["amount_cents"], 3200)
        self.assertEqual(by_id["manual-gasto"]["archived"], 1)
        self.assertEqual(by_id["manual-gasto"]["account_id"], "")
        self.assertEqual(by_id["mov-1"]["id"], "mov-1")
        self.assertEqual(by_id["mov-1"]["amount_cents"], 1800)
        self.assertEqual(store.one(self.conn, "SELECT amount_cents FROM movement WHERE id = ?", ("mov-1",))["amount_cents"], -1800)
        self.assertEqual(by_id["mov-1"]["direction"], "saida")
        self.assertEqual(by_id["mov-1"]["booked_on"], "2026-10-11")
        self.assertEqual(by_id["mov-1"]["occurrence_id"], "occ-1")
        self.assertEqual(json.loads(by_id["mov-1"]["payload_json"])["direction"], "gasto")
        self.assertEqual(json.loads(by_id["mov-1"]["payload_json"])["amountMinor"], 1800)
        first = snapshot(self.conn)
        store._migrate_body(self.conn)
        store.backfill_entry_columns(self.conn)
        self.assertEqual(snapshot(self.conn), first)
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 12)

    def test_empty_migration_and_repeat_change_nothing(self):
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 12)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry")["n"], 0)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM movement")["n"], 0)
        first = snapshot(self.conn)
        store._migrate_body(self.conn)
        store.backfill_entry_columns(self.conn)
        self.assertEqual(snapshot(self.conn), first)
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 12)

    def test_old_insert_is_filled_on_bootstrap_without_rewriting_the_payload(self):
        raw = '{"merchant":"Antigo","amountMinor":2500,"direction":"gasto","status":"pago","statusDate":"2026-10-12","nature":"consumo"}'
        self.conn.execute(
            "INSERT INTO ledger_entry (id, owner_id, account_id, payload_json, updated_at) VALUES (?,?,?,?,?)",
            ("velho", self.owner, "", raw, "2026-10-01T00:00:00Z"),
        )
        found = store.workspace(self.conn, self.owner, cut={"kind": "all", "archived": True})["entries"]
        self.assertEqual(found[0]["merchant"], "Antigo")
        self.conn.close()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        row = store.one(self.conn, "SELECT * FROM ledger_entry WHERE id = ?", ("velho",))
        self.assertEqual(row["payload_json"], raw)
        self.assertEqual(row["updated_at"], "2026-10-01T00:00:00Z")
        self.assertEqual(row["amount_cents"], 2500)
        self.assertEqual(row["direction"], "saida")
        self.assertEqual(row["booked_on"], "2026-10-12")
        again = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        try:
            self.assertEqual(store.one(again, "SELECT * FROM ledger_entry WHERE id = ?", ("velho",)), row)
        finally:
            again.close()

    def test_each_writer_keeps_column_and_payload_together(self):
        account = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        saved = store.save_entry(self.conn, self.owner, {
            "merchant": "Padaria", "amountMinor": 2790, "direction": "gasto", "status": "pago",
            "statusDate": "2026-10-12", "nature": "consumo", "category": "", "accountId": account["id"],
        })
        self.assert_coherent(saved["id"])
        job = {"id": "job-1", "owner_id": self.owner, "kind": "categorize"}
        with patch.object(ai, "invoke", return_value=({"items": [{"id": saved["id"], "category": "Alimentação", "clear": True, "reason": "Compra na padaria."}]}, META)):
            ai.categorize(self.conn, job, {"entries": [ai.entry_context(saved)]})
        self.assertEqual(store.one(self.conn, "SELECT category FROM ledger_entry WHERE id = ?", (saved["id"],))["category"], "Alimentação")
        self.assert_coherent(saved["id"])
        saved = [item for item in store.workspace(self.conn, self.owner)["entries"] if item["id"] == saved["id"]][0]
        corrected = store.save_entry(self.conn, self.owner, {**saved, "category": "Moradia"})
        self.assertEqual(corrected["userLocked"], True)
        self.assertEqual(store.one(self.conn, "SELECT category FROM ledger_entry WHERE id = ?", (saved["id"],))["category"], "Moradia")
        self.assert_coherent(saved["id"])
        store.assign_records(self.conn, self.owner, {"kind": "entry", "ids": [saved["id"]], "accountId": account["id"], "confirm": True})
        self.assertEqual(store.one(self.conn, "SELECT account_id FROM ledger_entry WHERE id = ?", (saved["id"],))["account_id"], account["id"])
        batch = workbatches.create_batch(self.conn, self.owner, {"name": "Obra", "criterion": "outro"})
        other = workbatches.create_batch(self.conn, self.owner, {"name": "Outro", "criterion": "evento", "activate": False})
        moved = store.save_entry(self.conn, self.owner, {**store.workspace(self.conn, self.owner)["entries"][0], "workBatchId": batch["id"]})
        self.assertEqual(moved["workBatchId"], batch["id"])
        moved = store.save_entry(self.conn, self.owner, {**moved, "workBatchId": other["id"]})
        self.assertEqual(moved["workBatchId"], other["id"])
        self.assert_coherent(saved["id"])
        store.import_batch(self.conn, self.owner, {
            "batchKey": "lote-escrita",
            "origin": "extrato-bb-arquivo",
            "movements": [{
                "signature": "esc-1", "date": "2026-10-02", "cents": -900, "direction": "saida",
                "label": "Tarifa", "nature": "a_conferir", "accountId": account["id"],
            }],
        })
        imported = store.one(self.conn, "SELECT id FROM movement WHERE label = ?", ("Tarifa",))
        self.assert_coherent(imported["id"])
        body = json.loads(store.one(self.conn, "SELECT payload_json FROM ledger_entry WHERE id = ?", (imported["id"],))["payload_json"])
        self.assertEqual(body["direction"], "gasto")
        self.assertEqual(body["amountMinor"], 900)

    def assert_coherent(self, entry_id):
        row = store.one(self.conn, "SELECT * FROM ledger_entry WHERE id = ? AND owner_id = ?", (entry_id, self.owner))
        payload = json.loads(row["payload_json"])
        movement = store.one(self.conn, "SELECT * FROM movement WHERE id = ? AND owner_id = ?", (entry_id, self.owner))
        if movement:
            self.assertEqual(row["amount_cents"], abs(int(movement["amount_cents"])))
            self.assertEqual(row["direction"], movement["direction"])
            self.assertEqual(row["booked_on"], movement["booked_on"])
            self.assertEqual(row["nature"], movement["nature"])
        else:
            expected = store.entry_columns(payload)
            for key in ("direction", "amount_cents", "booked_on", "nature", "category", "archived", "simulated", "currency"):
                self.assertEqual(row[key], expected[key], key)
        self.assertEqual(row["account_id"] or "", payload.get("accountId") or "")

    def test_release_013_still_reads_and_inserts_on_schema_10(self):
        source = subprocess.check_output(
            ["git", "-C", str(ROOT.parent), "show", "35ac85c0:isa/server/store.py"],
            text=True, encoding="utf-8",
        )
        self.assertIn("if version < 9:", source)
        self.assertNotIn("version < 10", source)
        self.conn.execute(
            "INSERT INTO ledger_entry (id, owner_id, account_id, payload_json, updated_at) VALUES (?,?,?,?,?)",
            ("velho-13", self.owner, "", '{"merchant":"Antigo","amountMinor":100,"direction":"ganho","status":"recebido","statusDate":"2026-10-08"}', "2026-10-08T00:00:00Z"),
        )
        loaded = store.rows(self.conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ? ORDER BY updated_at", (self.owner,))
        self.assertIn("Antigo", loaded[0]["payload_json"])
        movement = store.rows(
            self.conn,
            "SELECT * FROM movement WHERE owner_id = ? AND booked_on >= ? AND booked_on < ?",
            (self.owner, "2026-10-01", "2026-11-01"),
        )
        self.assertEqual(movement, [])
        self.conn.close()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        row = store.one(self.conn, "SELECT direction, amount_cents, booked_on, payload_json FROM ledger_entry WHERE id = ?", ("velho-13",))
        self.assertEqual(row["direction"], "entrada")
        self.assertEqual(row["amount_cents"], 100)
        self.assertEqual(row["booked_on"], "2026-10-08")
        self.assertIn("Antigo", row["payload_json"])

    def test_only_write_entry_writes_the_ledger(self):
        pattern = re.compile(r"\b(INSERT INTO|UPDATE)\s+ledger_entry\b", re.I)
        offenders = []
        for path in (ROOT / "server").glob("*.py"):
            if path.name.startswith("test_"):
                continue
            current = ""
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("def "):
                    current = line.split("(")[0][4:]
                if pattern.search(line) and current != "write_entry":
                    offenders.append(f"{path.name}:{current}:{line.strip()}")
        self.assertEqual(offenders, [])
        self.assertNotIn("FROM movement", store.month_picture.__doc__ and "")
        source = Path(store.__file__).read_text(encoding="utf-8")
        body = source.split("def month_picture", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("FROM movement", body)
        self.assertNotIn("FROM occurrence", body)

    def test_same_signature_does_not_duplicate_and_people_stay_apart(self):
        account = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        other = "pessoa-outra"
        other_account = store.save_account(self.conn, other, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        line = {"signature": "igual", "date": "2026-10-04", "cents": 1500, "direction": "saida", "label": "Repetida", "nature": "consumo", "accountId": account["id"]}
        store.import_batch(self.conn, self.owner, {"batchKey": "lote-a", "origin": "extrato-bb-arquivo", "movements": [line]})
        again = store.import_batch(self.conn, self.owner, {"batchKey": "lote-b", "origin": "extrato-bb-arquivo", "movements": [dict(line)]})
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (self.owner,))["n"], 1)
        self.assertGreater(again["pending"] + again["reused"], 0)
        line["accountId"] = other_account["id"]
        store.import_batch(self.conn, other, {"batchKey": "lote-c", "origin": "extrato-bb-arquivo", "movements": [line]})
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (other,))["n"], 1)
        own = store.month_picture(self.conn, self.owner, "2026-10", "2026-10-26")
        theirs = store.month_picture(self.conn, other, "2026-10", "2026-10-26")
        self.assertEqual([item["label"] for item in own["records"]], ["Repetida"])
        self.assertEqual([item["label"] for item in theirs["records"]], ["Repetida"])
        self.assertNotEqual(own["records"][0]["id"], theirs["records"][0]["id"])

    def test_payment_link_uses_the_launch_id(self):
        account = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        commitment = store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 5000, "dueOn": "2026-10-20", "accountId": account["id"]})
        saved = store.save_entry(self.conn, self.owner, {
            "merchant": "Aluguel", "amountMinor": 2000, "direction": "gasto", "status": "pago",
            "statusDate": "2026-10-20", "nature": "consumo", "accountId": account["id"],
        })
        linked = store.link_movement(self.conn, self.owner, {"movementId": saved["id"], "commitmentId": commitment["id"], "confirmed": True})
        self.assertEqual(linked["commitment"]["remaining_cents"], 3000)
        row = store.one(self.conn, "SELECT movement_id FROM link_row WHERE owner_id = ?", (self.owner,))
        self.assertEqual(row["movement_id"], saved["id"])

    def test_october_scene_keeps_the_same_numbers(self):
        bb, _poup = plant_october(self.conn, self.owner)
        page = store.home(self.conn, self.owner, "2026-10-26")
        self.assertEqual(page["balance"]["cents"], 120000)
        self.assertEqual(page["month"]["forecastOut"], 135000)
        self.assertEqual(page["projection"]["first_insufficiency"], "2026-10-28")
        day = next(item for item in page["projection"]["days"] if item["date"] == "2026-10-28")
        self.assertEqual(day["cents"], -15000)
        close = next(item for item in page["projection"]["days"] if item["date"] == "2026-10-30")
        self.assertEqual(close["cents"], 135000)
        self.assertEqual(page["balance"]["protectedCents"], 20000)
        self.assertEqual(page["projection"]["margin"]["capacity_cents"], 0)
        one = store.home(self.conn, self.owner, "2026-10-26", account=bb["id"])
        self.assertEqual(one["balance"]["cents"], 100000)
        assert_same_picture(self, self.conn, self.owner, "2026-10-26")

    def test_photo_matches_on_demo_people_and_a_large_synthetic_set(self):
        owners = []
        for owner in ("pessoa-marina", "pessoa-paulo", "pessoa-eveline-demo"):
            store.load_october(self.conn, owner)
            owners.append(owner)
        plant_synthetic(self.conn, "pessoa-sintetica")
        owners.append("pessoa-sintetica")
        self.assertGreaterEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", ("pessoa-sintetica",))["n"], 2000)
        for owner in owners:
            if owner == "pessoa-sintetica":
                assert_rules_not_the_old_photo(self, self.conn, owner)
            else:
                assert_same_picture(self, self.conn, owner)
            entries = store.workspace(self.conn, owner, cut={"kind": "all", "archived": True})["entries"]
            ordered = [json.loads(row["payload_json"]) for row in store.rows(self.conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ? ORDER BY updated_at, id", (owner,))]
            self.assertEqual(sorted(entries, key=lambda item: item["id"]), sorted(ordered, key=lambda item: item["id"]))
            dates = []
            for item in entries:
                row = store.one(self.conn, "SELECT booked_on FROM ledger_entry WHERE id = ?", (item["id"],))
                dates.append(row["booked_on"] or "")
            self.assertEqual(dates, sorted(dates))
            self.assertEqual(calc_summary(entries), calc_summary(ordered))

    def test_local_measurement(self):
        table = []
        for count in (0, 2000, 5000):
            folder = tempfile.TemporaryDirectory()
            conn = store.connect(os.path.join(folder.name, "isa.sqlite"))
            owner = "pessoa-medida"
            try:
                if count:
                    account = store.save_account(conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
                    months = ["2026-08", "2026-09", "2026-10", "2026-11"]
                    movements = [{
                        "signature": f"med-{i}",
                        "date": f"{months[i % 4]}-{(i % 27) + 1:02d}",
                        "cents": 100 + i if i % 2 == 0 else -(100 + i),
                        "direction": "entrada" if i % 2 == 0 else "saida",
                        "label": f"Medida {i}",
                        "nature": "consumo",
                        "accountId": account["id"],
                    } for i in range(count)]
                    store.import_batch(conn, owner, {"batchKey": "medida", "origin": "extrato-bb-arquivo", "movements": movements})
                def legacy_workspace(db, person):
                    real_rows = store.rows

                    def rows(conn, sql, args=()):
                        if "ORDER BY booked_on" in str(sql):
                            sql = "SELECT payload_json FROM ledger_entry WHERE owner_id = ? ORDER BY updated_at"
                            args = (args[0],)
                        return real_rows(conn, sql, args)

                    store.rows = rows
                    try:
                        return store.workspace(db, person)
                    finally:
                        store.rows = real_rows

                original = store.month_picture
                store.month_picture = legacy_month_picture
                try:
                    before_home = selects(conn, lambda db: store.home(db, owner, "2026-10-26"))
                    before_space = selects(conn, lambda db: legacy_workspace(db, owner))
                finally:
                    store.month_picture = original
                after_home = selects(conn, lambda db: store.home(db, owner, "2026-10-26"))
                after_space = selects(conn, lambda db: store.workspace(db, owner))
                table.append({
                    "lancamentos": count,
                    "home_antes_consultas": before_home[0], "home_depois_consultas": after_home[0],
                    "home_antes_ms": round(before_home[1], 1), "home_depois_ms": round(after_home[1], 1),
                    "workspace_antes_consultas": before_space[0], "workspace_depois_consultas": after_space[0],
                    "workspace_antes_ms": round(before_space[1], 1), "workspace_depois_ms": round(after_space[1], 1),
                })
            finally:
                conn.close()
                folder.cleanup()
        print("MEDICAO " + json.dumps(table, ensure_ascii=False))
        self.assertLess(table[-1]["home_depois_consultas"], table[-1]["home_antes_consultas"])


class PostgresLancamentoTests(unittest.TestCase):
    def setUp(self):
        import test_pg
        self.prev = os.environ.get("ISA_ENV")
        os.environ["ISA_ENV"] = "lab"
        self.name = "isa_lanc_" + store._id()[:12]
        self.url = test_pg.prepare(self.name)
        self.conn = store.connect(self.url)

    def tearDown(self):
        self.conn.close()
        import psycopg
        import test_pg
        admin = psycopg.connect(test_pg.ADMIN, autocommit=True)
        admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (self.name,))
        admin.execute("DROP DATABASE IF EXISTS " + self.name)
        admin.close()
        if self.prev is None:
            os.environ.pop("ISA_ENV", None)
        else:
            os.environ["ISA_ENV"] = self.prev

    def test_photo_matches_on_postgres(self):
        for owner in ("pessoa-marina", "pessoa-paulo", "pessoa-eveline-demo"):
            store.load_october(self.conn, owner)
            assert_same_picture(self, self.conn, owner)
        plant_synthetic(self.conn, "pessoa-sintetica")
        self.assertGreaterEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", ("pessoa-sintetica",))["n"], 2000)
        assert_rules_not_the_old_photo(self, self.conn, "pessoa-sintetica")
        entries = store.workspace(self.conn, "pessoa-sintetica")["entries"]
        self.assertEqual(calc_summary(entries), calc_summary(list(reversed(entries))))
