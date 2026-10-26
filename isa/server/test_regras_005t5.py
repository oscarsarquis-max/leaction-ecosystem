"""Regras únicas do lançamento. Pessoa sintética de 26/10/2026, sem saldo."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import store
import test_lancamento_005t3 as photo

ROOT = Path(__file__).resolve().parents[1]
WHEN = "2026-10-26"


def cases():
    return json.loads((ROOT / "prototype" / "regras-mes.json").read_text(encoding="utf-8"))["cases"]


def cut(month, archived=False):
    query = {"month": [month]}
    if archived:
        query["archived"] = ["1"]
    return store.parse_cut(query, "")


class RegrasTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get("ISA_ENV")
        os.environ["ISA_ENV"] = "lab"
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-regras"

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()
        if self.prev is None:
            os.environ.pop("ISA_ENV", None)
        else:
            os.environ["ISA_ENV"] = self.prev

    def test_month_cases_match_the_shared_table(self):
        for row in cases():
            self.assertEqual(store.list_when(row["entry"]), row["when"], row["name"])
            self.assertEqual(store.list_month(row["entry"]), row["month"], row["name"])

    def test_signed_outflow_used_to_shrink_the_month_and_now_adds(self):
        account = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        store.import_batch(self.conn, self.owner, {
            "batchKey": "sinal",
            "origin": "extrato-bb-arquivo",
            "movements": [{
                "signature": "sinal-1", "date": "2026-10-12", "cents": -1800, "direction": "saida",
                "label": "Tarifa", "nature": "consumo", "accountId": account["id"],
            }],
        })
        movement = store.one(self.conn, "SELECT amount_cents FROM movement WHERE owner_id = ?", (self.owner,))
        ledger = store.one(self.conn, "SELECT amount_cents, payload_json FROM ledger_entry WHERE owner_id = ?", (self.owner,))
        self.assertEqual(movement["amount_cents"], -1800)
        self.assertEqual(ledger["amount_cents"], 1800)
        self.assertEqual(json.loads(ledger["payload_json"])["amountMinor"], 1800)
        picture = store.month_picture(self.conn, self.owner, "2026-10", WHEN)
        self.assertEqual(picture["realizedOut"], 1800)
        self.assertNotEqual(picture["realizedOut"], movement["amount_cents"])

    def test_synthetic_person_matches_on_home_and_on_the_list(self):
        account = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        manuals = [
            {"id": "a", "merchant": "Mercado", "direction": "gasto", "status": "pago", "noteDate": "2026-10-05", "statusDate": "2026-10-05", "amountMinor": 10000, "nature": "consumo"},
            {"id": "b", "merchant": "Luz", "direction": "gasto", "status": "a_pagar", "noteDate": "2026-10-10", "dueDate": "2026-10-30", "amountMinor": 20000, "nature": "consumo"},
            {"id": "c", "merchant": "Internet", "direction": "gasto", "status": "a_pagar", "noteDate": "2026-10-01", "dueDate": "2026-11-15", "amountMinor": 9000, "nature": "consumo"},
            {"id": "f", "merchant": "Freela", "direction": "ganho", "status": "a_receber", "noteDate": "2026-10-02", "dueDate": "2026-10-28", "amountMinor": 50000, "nature": "consumo"},
            {"id": "g", "merchant": "Aluguel", "direction": "gasto", "status": "a_pagar", "dueDate": "2026-10-20", "amountMinor": 100000, "nature": "consumo"},
        ]
        for item in manuals:
            item["accountId"] = account["id"]
            store.save_entry(self.conn, self.owner, item)
        store.import_batch(self.conn, self.owner, {
            "batchKey": "extrato",
            "origin": "extrato-bb-arquivo",
            "movements": [
                {"signature": "farm", "date": "2026-10-12", "cents": -5000, "direction": "saida", "label": "Farmácia", "nature": "a_conferir", "accountId": account["id"]},
                {"signature": "pad", "date": "2026-10-14", "cents": -3000, "direction": "saida", "label": "Padaria", "nature": "a_conferir", "accountId": account["id"]},
            ],
        })
        padaria = store.one(self.conn, "SELECT id, payload_json FROM ledger_entry WHERE owner_id = ? AND payload_json LIKE ?", (self.owner, '%"merchant": "Padaria"%'))
        body = json.loads(padaria["payload_json"])
        body["archived"] = True
        store.save_entry(self.conn, self.owner, body)
        commitment = store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 100000, "dueOn": "2026-10-20", "accountId": account["id"]})
        self.conn.execute(
            "INSERT INTO link_row (id, owner_id, movement_id, commitment_id, amount_cents, created_at) VALUES (?,?,?,?,?,?)",
            ("vinculo-g", self.owner, "g", commitment["id"], 100000, store.now()),
        )
        self.assertEqual(store.one(self.conn, "SELECT remaining_cents FROM commitment WHERE id = ?", (commitment["id"],))["remaining_cents"], 100000)
        self.assertEqual(store.one(self.conn, "SELECT amount_cents FROM movement WHERE label = ?", ("Farmácia",))["amount_cents"], -5000)
        self.assertEqual(store.one(self.conn, "SELECT amount_cents FROM ledger_entry WHERE id = ?", (store.one(self.conn, "SELECT id FROM movement WHERE label = ?", ("Farmácia",))["id"],))["amount_cents"], 5000)

        picture = store.month_picture(self.conn, self.owner, "2026-10", WHEN)
        self.assertEqual(picture["realizedOut"], 15000)
        self.assertEqual(picture["realizedIn"], 0)
        self.assertEqual(picture["forecastOut"], 120000)
        self.assertEqual(picture["forecastIn"], 50000)
        by_label = {}
        for item in picture["records"]:
            by_label.setdefault(item["label"], []).append(item)
        self.assertEqual(by_label["Mercado"][0]["state"], "realizado")
        self.assertEqual(by_label["Luz"][0]["state"], "previsto")
        self.assertEqual(by_label["Farmácia"][0]["state"], "realizado")
        self.assertEqual(by_label["Freela"][0]["state"], "previsto")
        self.assertEqual(by_label["Freela"][0]["cents"], 50000)
        launch = next(item for item in by_label["Aluguel"] if item["id"] == "g")
        bill = next(item for item in by_label["Aluguel"] if item["id"] != "g")
        self.assertEqual(launch["state"], "em aberto")
        self.assertEqual(launch["cents"], 100000)
        self.assertEqual(bill["cents"], 100000)
        self.assertNotIn("Internet", by_label)
        self.assertNotIn("Padaria", by_label)

        november = store.month_picture(self.conn, self.owner, "2026-11", WHEN)
        self.assertEqual([item["label"] for item in november["records"]], ["Internet"])
        self.assertEqual(november["records"][0]["state"], "previsto")
        self.assertEqual(november["forecastOut"], 9000)
        self.assertEqual(november["realizedOut"], 0)

        listed = [item for item in store.workspace(self.conn, self.owner, cut=cut("2026-10"))["entries"] if not item.get("outsideSlice")]
        self.assertEqual(sorted(item["merchant"] for item in listed), ["Aluguel", "Farmácia", "Freela", "Luz", "Mercado"])
        self.assertEqual(store.workspace(self.conn, self.owner, cut=cut("2026-11"))["entries"][0]["merchant"], "Internet")
        archived = store.workspace(self.conn, self.owner, cut=cut("2026-10", archived=True))["entries"]
        self.assertIn("Padaria", [item["merchant"] for item in archived])
        for month in ("2026-10", "2026-11"):
            labels = [item["label"] for item in store.month_picture(self.conn, self.owner, month, WHEN)["records"]]
            self.assertNotIn("Padaria", labels)

        events = [item["label"] for item in store._events(self.conn, self.owner)]
        self.assertIn("Aluguel", events)
        for label in ("Luz", "Internet", "Freela", "Mercado", "Farmácia", "Padaria"):
            self.assertNotIn(label, events)

    def test_backfill_is_idempotent_and_keeps_the_payload(self):
        raw = '{"id":"velho","merchant":"Internet","amountMinor":9000,"direction":"gasto","status":"a_pagar","noteDate":"2026-10-01","dueDate":"2026-11-15","nature":"consumo"}'
        self.conn.execute(
            "INSERT INTO ledger_entry (id, owner_id, account_id, payload_json, updated_at, amount_cents, booked_on, direction) VALUES (?,?,?,?,?,?,?,?)",
            ("velho", self.owner, "", raw, "2026-10-01T00:00:00Z", -9000, "2026-10-01", "saida"),
        )
        store.backfill_entry_columns(self.conn)
        row = store.one(self.conn, "SELECT amount_cents, booked_on, payload_json, updated_at FROM ledger_entry WHERE id = ?", ("velho",))
        self.assertEqual(row["amount_cents"], 9000)
        self.assertEqual(row["booked_on"], "2026-11-15")
        self.assertEqual(row["payload_json"], raw)
        self.assertEqual(row["updated_at"], "2026-10-01T00:00:00Z")
        first = (row["amount_cents"], row["booked_on"], row["payload_json"], row["updated_at"])
        store.backfill_entry_columns(self.conn)
        again = store.one(self.conn, "SELECT amount_cents, booked_on, payload_json, updated_at FROM ledger_entry WHERE id = ?", ("velho",))
        self.assertEqual((again["amount_cents"], again["booked_on"], again["payload_json"], again["updated_at"]), first)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM schema_migration WHERE version = 12")["n"], 1)
        store._migrate_body(self.conn)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM schema_migration WHERE version = 12")["n"], 1)

    def test_paying_an_open_bill_moves_the_month(self):
        saved = store.save_entry(self.conn, self.owner, {
            "merchant": "Internet", "direction": "gasto", "status": "a_pagar",
            "noteDate": "2026-10-01", "dueDate": "2026-11-15", "amountMinor": 9000, "nature": "consumo",
        })
        self.assertEqual(store.one(self.conn, "SELECT booked_on FROM ledger_entry WHERE id = ?", (saved["id"],))["booked_on"], "2026-11-15")
        saved["status"] = "pago"
        saved["statusDate"] = "2026-10-26"
        store.save_entry(self.conn, self.owner, saved)
        self.assertEqual(store.one(self.conn, "SELECT booked_on FROM ledger_entry WHERE id = ?", (saved["id"],))["booked_on"], "2026-10-26")
        self.assertEqual(store.month_picture(self.conn, self.owner, "2026-10", WHEN)["realizedOut"], 9000)
        self.assertEqual(store.month_picture(self.conn, self.owner, "2026-11", WHEN)["records"], [])

    def test_people_stay_apart(self):
        self.test_synthetic_person_matches_on_home_and_on_the_list()
        other = "pessoa-outra"
        account = store.save_account(self.conn, other, {"name": "Caixa", "currency": "BRL", "kind": "corrente", "institution": "CAIXA ECONOMICA FEDERAL"})
        store.save_entry(self.conn, other, {
            "merchant": "Outro", "direction": "gasto", "status": "pago", "statusDate": "2026-10-08",
            "amountMinor": 99900, "nature": "consumo", "accountId": account["id"],
        })
        own = store.month_picture(self.conn, self.owner, "2026-10", WHEN)
        theirs = store.month_picture(self.conn, other, "2026-10", WHEN)
        self.assertEqual(own["realizedOut"], 15000)
        self.assertEqual(theirs["realizedOut"], 99900)
        self.assertNotIn("Outro", [item["label"] for item in own["records"]])
        self.assertEqual([item["label"] for item in theirs["records"]], ["Outro"])

    def test_october_scene_keeps_the_same_numbers(self):
        bb, _poup = photo.plant_october(self.conn, self.owner)
        page = store.home(self.conn, self.owner, WHEN)
        self.assertEqual(page["balance"]["cents"], 120000)
        self.assertEqual(page["month"]["forecastOut"], 135000)
        self.assertEqual(page["month"]["realizedIn"], 400000)
        self.assertEqual(page["month"]["realizedOut"], 310000)
        self.assertEqual(page["projection"]["first_insufficiency"], "2026-10-28")
        day = next(item for item in page["projection"]["days"] if item["date"] == "2026-10-28")
        self.assertEqual(day["cents"], -15000)
        close = next(item for item in page["projection"]["days"] if item["date"] == "2026-10-30")
        self.assertEqual(close["cents"], 135000)
        self.assertEqual(page["balance"]["protectedCents"], 20000)
        self.assertEqual(page["projection"]["margin"]["capacity_cents"], 0)
        one = store.home(self.conn, self.owner, WHEN, account=bb["id"])
        self.assertEqual(one["balance"]["cents"], 100000)


class PostgresRegrasTests(unittest.TestCase):
    def setUp(self):
        import test_pg
        self.prev = os.environ.get("ISA_ENV")
        os.environ["ISA_ENV"] = "lab"
        self.name = "isa_regras_" + store._id()[:12]
        self.url = test_pg.prepare(self.name)
        self.conn = store.connect(self.url)
        self.owner = "pessoa-regras"

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

    def test_synthetic_person_on_postgres(self):
        RegrasTests.test_synthetic_person_matches_on_home_and_on_the_list(self)

    def test_october_scene_on_postgres(self):
        RegrasTests.test_october_scene_keeps_the_same_numbers(self)
