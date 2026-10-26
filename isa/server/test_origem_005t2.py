"""Origem verdadeira da importação. A suíte usa PostgreSQL isolado no discover e SQLite aqui."""

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

import store
import workbatches
from test_http import Server, call

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "reclassify_import_origin_005t2",
    ROOT / "scripts" / "ops" / "reclassify-import-origin-005t2.py",
)
reclass = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reclass)

MESSAGE = "A origem do arquivo não foi reconhecida. Nada foi importado."


def movement(signature, label, cents=2500):
    return {
        "signature": signature,
        "date": "2026-10-03",
        "cents": cents,
        "direction": "saida",
        "label": label,
        "history": label,
    }


def backup_dir(folder, created_at=None):
    folder.mkdir()
    raw = b"{}"
    (folder / "dump.json").write_bytes(raw)
    manifest = {"createdAt": created_at or store.now(), "sha256": hashlib.sha256(raw).hexdigest()}
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


class OriginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ledger = os.environ.get("ISA_ERASURE_LEDGER")
        cls.server = Server(port=8139)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        if cls._ledger is None:
            os.environ.pop("ISA_ERASURE_LEDGER", None)
        else:
            os.environ["ISA_ERASURE_LEDGER"] = cls._ledger

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "isa.sqlite")
        self.conn = store.connect(self.path)
        self.owner = "pessoa-origem"
        self.other = "pessoa-outra-origem"
        self._env = os.environ.get("ISA_ENV")

    def tearDown(self):
        if self.conn is not None:
            self.conn.close()
        self.tmp.cleanup()
        if self._env is None:
            os.environ.pop("ISA_ENV", None)
        else:
            os.environ["ISA_ENV"] = self._env
        os.environ.pop("ISA_DATABASE_URL", None)

    def account(self, owner=None):
        return store.save_account(self.conn, owner or self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente"})

    def test_real_file_is_stored_everywhere_and_is_not_simulated(self):
        account = self.account()
        result = store.import_statement(self.conn, self.owner, {
            "account": {"id": account["id"]},
            "batchKey": "lote-real",
            "origin": "extrato-bb-arquivo",
            "movements": [movement("sig-real", "Padaria", 2500)],
            "notes": [{"signature": "nota-real", "date": "2026-10-03", "cents": 100000, "class": "final"}],
        })
        self.assertFalse(result["repeated"])
        self.assertEqual(store.one(self.conn, "SELECT origin FROM batch")["origin"], "extrato-bb-arquivo")
        self.assertEqual(store.one(self.conn, "SELECT source FROM movement")["source"], "extrato-bb-arquivo")
        occurrence = json.loads(store.one(self.conn, "SELECT payload_json FROM occurrence")["payload_json"])
        self.assertEqual(occurrence["source"], "extrato-bb-arquivo")
        entry = json.loads(store.one(self.conn, "SELECT payload_json FROM ledger_entry")["payload_json"])
        self.assertEqual(entry["source"], "extrato-bb-arquivo")
        self.assertFalse(entry["simulated"])
        note = json.loads(store.one(self.conn, "SELECT payload_json FROM statement_note")["payload_json"])
        self.assertEqual(note["origin"], "extrato-bb-arquivo")
        page = store.workspace(self.conn, self.owner)
        self.assertEqual(page["entries"][0]["source"], "extrato-bb-arquivo")
        self.assertFalse(page["entries"][0]["simulated"])
        self.assertFalse(page["occurrences"][0]["simulated"])
        store.home(self.conn, self.owner)
        again = store.import_statement(self.conn, self.owner, {
            "account": {"id": account["id"]},
            "batchKey": "lote-repetido",
            "origin": "extrato-bb-arquivo",
            "movements": [movement("sig-real", "Padaria", 2500)],
        })
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM movement")["n"], 1)
        self.assertEqual(again["pending"], 1)
        self.assertEqual(workbatches.bucket({"nature": "a_conferir", "source": "extrato-bb-arquivo"}), workbatches.bucket({"nature": "a_conferir", "source": "arquivo-teste"}))

    def test_missing_or_unknown_origin_stores_nothing(self):
        before = store.one(self.conn, "SELECT COUNT(*) AS n FROM batch")["n"]
        for body in (
            {"batchKey": "sem", "movements": [movement("s", "Nada")]},
            {"batchKey": "ruim", "origin": "desconhecida", "movements": [movement("s2", "Nada")]},
            {"batchKey": "legado", "origin": "arquivo-teste", "movements": []},
        ):
            with self.assertRaises(ValueError) as caught:
                store.import_batch(self.conn, self.owner, body)
            self.assertEqual(str(caught.exception), MESSAGE)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM batch")["n"], before)
        code, payload = call(self.server.port, "POST", "/api/imports", {"batchKey": "http-sem", "movements": []})
        self.assertEqual(code, 400)
        self.assertEqual(payload["error"], MESSAGE)
        code, payload = call(self.server.port, "POST", "/api/imports", {"batchKey": "http-ruim", "origin": "cenario-sintetico-004", "movements": []})
        self.assertEqual(code, 400)
        self.assertEqual(payload["error"], MESSAGE)
        code, payload = call(self.server.port, "POST", "/api/imports", {"batchKey": "http-ok", "origin": "extrato-bb-arquivo", "movements": []})
        self.assertEqual(code, 200)

    def test_production_rejects_example_and_legacy_origin(self):
        os.environ["ISA_ENV"] = "production"
        for origin in ("exemplo-sintetico", "arquivo-teste"):
            with self.assertRaises(ValueError) as caught:
                store.import_batch(self.conn, self.owner, {"batchKey": "prod-" + origin, "origin": origin, "movements": []})
            self.assertEqual(str(caught.exception), MESSAGE)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM batch")["n"], 0)
        created = store.import_batch(self.conn, self.owner, {"batchKey": "prod-real", "origin": "extrato-bb-arquivo", "movements": []})
        self.assertEqual(created["origin"], "extrato-bb-arquivo")

    def test_restored_preview_origin_is_what_gets_confirmed(self):
        account = self.account()
        store.save_draft(self.conn, self.owner, "import", {
            "batchId": "lote-previa",
            "origin": "extrato-bb-arquivo",
            "movements": [movement("sig-previa", "Mercado")],
        })
        store.import_statement(self.conn, self.owner, {
            "account": {"id": account["id"]},
            "batchKey": "lote-previa",
            "origin": "",
            "movements": [movement("sig-previa", "Mercado")],
        })
        self.assertEqual(store.one(self.conn, "SELECT origin FROM batch")["origin"], "extrato-bb-arquivo")
        self.assertEqual(store.one(self.conn, "SELECT source FROM movement")["source"], "extrato-bb-arquivo")

    def test_reclassification_is_dry_by_default_then_idempotent(self):
        self._plant_legacy()
        folder = backup_dir(Path(self.tmp.name) / "copia")
        ids = self._identity()
        sums = reclass.control_sums(self.conn)
        self.conn.close()
        self.conn = None
        os.environ["ISA_ENV"] = "production"
        os.environ["ISA_DATABASE_URL"] = self.path
        first = self._run(["--backup", str(folder)])
        self.assertEqual(first["modo"], "simulacao")
        self.assertGreater(first["wouldChange"], 0)
        self.assertEqual(first["changed"], 0)
        self.assertEqual(first["before"], first["after"])
        self.assertEqual(first["controleAntes"], first["controleDepois"])
        self.conn = store.connect(self.path, bootstrap=False)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM movement WHERE source = ?", ("arquivo-teste",))["n"], 2)
        self.conn.close()
        self.conn = None
        applied = self._run(["--backup", str(folder), "--apply"])
        self.assertEqual(applied["changed"], applied["wouldChange"])
        self.assertGreater(applied["changed"], 0)
        self.assertEqual(applied["controleAntes"], applied["controleDepois"])
        self.assertEqual(applied["iguais"], True)
        self.conn = store.connect(self.path, bootstrap=False)
        logged = store.one(self.conn, "SELECT COUNT(*) AS n FROM change_log WHERE action = ?", (reclass.ACTION,))["n"]
        self.assertGreater(logged, 0)
        self.conn.close()
        self.conn = None
        second = self._run(["--backup", str(folder), "--apply"])
        self.assertEqual(second["wouldChange"], 0)
        self.assertEqual(second["changed"], 0)
        self.conn = store.connect(self.path, bootstrap=False)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM change_log WHERE action = ?", (reclass.ACTION,))["n"], logged)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM batch WHERE origin IN ('arquivo-teste', 'exemplo-sintetico')")["n"], 0)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM movement WHERE source IN ('arquivo-teste', 'exemplo-sintetico')")["n"], 0)
        self.assertEqual(store.one(self.conn, "SELECT source FROM movement WHERE label = ?", ("Sintetico antigo",))["source"], "extrato-sintetico")
        self.assertEqual(store.one(self.conn, "SELECT source FROM availability")["source"], "cenario-sintetico-004")
        for row in store.rows(self.conn, "SELECT payload_json FROM occurrence"):
            payload = json.loads(row["payload_json"])
            if payload.get("source") == "extrato-bb-arquivo":
                self.assertIn(payload["originLegacy"], ("arquivo-teste", "exemplo-sintetico"))
        ledger = [json.loads(row["payload_json"]) for row in store.rows(self.conn, "SELECT payload_json FROM ledger_entry")]
        self.assertTrue(any(item.get("originLegacy") for item in ledger))
        self.assertTrue(all(item.get("source") != "exemplo-sintetico" or item.get("simulated") is False for item in ledger))
        self.assertTrue(all(item.get("simulated") is False for item in ledger if item.get("source") == "extrato-bb-arquivo"))
        logs = store.rows(self.conn, "SELECT * FROM change_log WHERE action = ?", (reclass.ACTION,))
        self.assertEqual(len(logs), logged)
        self.assertTrue(all(item["before_json"] and item["after_json"] for item in logs))
        self.assertEqual(self._identity(), ids)
        self.assertEqual(reclass.control_sums(self.conn), sums)
        again = store.one(self.conn, "SELECT COUNT(*) AS n FROM change_log WHERE action = ?", (reclass.ACTION,))["n"]
        self.assertEqual(again, len(logs))

    def test_script_refuses_lab_and_missing_backup(self):
        folder = backup_dir(Path(self.tmp.name) / "copia")
        os.environ["ISA_ENV"] = "lab"
        os.environ["ISA_DATABASE_URL"] = self.path
        with self.assertRaises(SystemExit):
            reclass.main(["--backup", str(folder), "--apply"])
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM change_log")["n"], 0)
        os.environ["ISA_ENV"] = "production"
        old = (datetime.now(timezone.utc) - timedelta(days=2)).replace(microsecond=0).isoformat()
        stale = backup_dir(Path(self.tmp.name) / "velha", old)
        with self.assertRaises(SystemExit):
            reclass.main(["--backup", str(stale)])
        with self.assertRaises(SystemExit):
            reclass.main(["--backup", str(Path(self.tmp.name) / "ausente")])

    def test_october_scene_isolation_and_month_totals_stay(self):
        os.environ["ISA_ENV"] = "production"
        self.assertEqual(store.reference_date(), "2026-10-26")
        bb = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente"})
        savings = store.save_account(self.conn, self.owner, {"name": "Poupança", "currency": "BRL", "kind": "poupanca"})
        store.save_availability(self.conn, self.owner, {"accountId": bb["id"], "amountCents": 100000, "asOf": "2026-10-26", "protectedCents": 0, "source": "declarada"})
        store.save_availability(self.conn, self.owner, {"accountId": savings["id"], "amountCents": 20000, "asOf": "2026-10-26", "protectedCents": 20000, "source": "declarada"})
        store.add_commitment(self.conn, self.owner, {"label": "Conta do dia 27", "totalCents": 45000, "dueOn": "2026-10-27", "accountId": bb["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Conta do dia 28", "totalCents": 90000, "dueOn": "2026-10-28", "accountId": bb["id"]})
        store.add_inflow(self.conn, self.owner, {"label": "Recebimento", "amountCents": 150000, "dueOn": "2026-10-30", "state": "confirmada", "accountId": bb["id"]})
        home = store.home(self.conn, self.owner)
        self.assertEqual(home["balance"]["cents"], 120000)
        self.assertEqual(home["projection"]["first_insufficiency"], "2026-10-28")
        day = next(item for item in home["projection"]["days"] if item["date"] == "2026-10-28")
        self.assertEqual(day["cents"], -15000)
        close = next(item for item in home["projection"]["days"] if item["date"] == "2026-10-30")
        self.assertEqual(close["cents"], 135000)
        self.assertEqual(home["projection"]["margin"]["capacity_cents"], 0)
        self.assertEqual(home["balance"]["protectedCents"], 20000)
        store.import_statement(self.conn, self.owner, {
            "account": {"id": bb["id"]},
            "batchKey": "lote-cena",
            "origin": "extrato-bb-arquivo",
            "movements": [movement("sig-cena", "Importado", 1800)],
        })
        other_account = self.account(self.other)
        store.import_statement(self.conn, self.other, {
            "account": {"id": other_account["id"]},
            "batchKey": "lote-alheia",
            "origin": "extrato-bb-arquivo",
            "movements": [movement("sig-alheia", "Alheio", 999)],
        })
        self._retarget("Importado", "arquivo-teste")
        before = self._month(self.owner)
        picture = store.month_picture(self.conn, self.owner, "2026-10", "2026-10-26")
        self.assertEqual(store.home(self.conn, self.owner, account=bb["id"])["balance"]["cents"], 100000)
        folder = backup_dir(Path(self.tmp.name) / "copia")
        self.conn.close()
        self.conn = None
        os.environ["ISA_DATABASE_URL"] = self.path
        self._run(["--backup", str(folder), "--apply"])
        self.conn = store.connect(self.path, bootstrap=False)
        after = store.home(self.conn, self.owner, account="all")
        self.assertEqual(after["balance"]["cents"], 120000)
        self.assertEqual(after["projection"]["first_insufficiency"], "2026-10-28")
        self.assertEqual(next(item for item in after["projection"]["days"] if item["date"] == "2026-10-28")["cents"], -15000)
        self.assertEqual(next(item for item in after["projection"]["days"] if item["date"] == "2026-10-30")["cents"], 135000)
        self.assertEqual(after["projection"]["margin"]["capacity_cents"], 0)
        self.assertEqual(store.home(self.conn, self.owner, account=bb["id"])["balance"]["cents"], 100000)
        self.assertEqual(self._month(self.owner, "all"), before)
        again = store.month_picture(self.conn, self.owner, "2026-10", "2026-10-26")
        for key in ("realizedIn", "realizedOut", "forecastIn", "forecastOut", "pendingNatureCents"):
            self.assertEqual(again[key], picture[key])
        labels = [item["merchant"] for item in store.workspace(self.conn, self.owner)["entries"]]
        self.assertIn("Importado", labels)
        self.assertNotIn("Alheio", labels)
        self.assertEqual(store.one(self.conn, "SELECT source FROM movement WHERE label = ?", ("Importado",))["source"], "extrato-bb-arquivo")
        self.assertEqual(store.one(self.conn, "SELECT amount_cents FROM movement WHERE label = ?", ("Alheio",))["amount_cents"], 999)

    def _plant_legacy(self):
        account = self.account()
        other = self.account(self.other)
        store.save_availability(self.conn, self.owner, {"amountCents": 1000, "asOf": "2026-10-26", "source": "cenario-sintetico-004", "accountId": account["id"]})
        for owner, account_id, key, label, source in (
            (self.owner, account["id"], "lote-arq", "Arquivo antigo", "arquivo-teste"),
            (self.owner, account["id"], "lote-ex", "Exemplo antigo", "exemplo-sintetico"),
            (self.owner, account["id"], "lote-ext", "Sintetico antigo", "extrato-sintetico"),
            (self.other, other["id"], "lote-outra", "Outra pessoa", "arquivo-teste"),
        ):
            store.import_statement(self.conn, owner, {
                "account": {"id": account_id},
                "batchKey": key,
                "origin": "extrato-bb-arquivo",
                "movements": [movement(key, label, 3200 if owner == self.owner else 1100)],
                "notes": [{"signature": "nota-" + key, "date": "2026-10-03", "cents": 5000, "class": "final"}],
            })
            self._retarget(label, source)

    def _retarget(self, label, source):
        row = store.one(self.conn, "SELECT id, occurrence_id, owner_id FROM movement WHERE label = ?", (label,))
        self.conn.execute("UPDATE movement SET source = ? WHERE id = ?", (source, row["id"]))
        occurrence = store.one(self.conn, "SELECT id, batch_id, payload_json FROM occurrence WHERE id = ?", (row["occurrence_id"],))
        payload = json.loads(occurrence["payload_json"])
        payload["source"] = source
        self.conn.execute("UPDATE occurrence SET payload_json = ? WHERE id = ?", (json.dumps(payload), occurrence["id"]))
        if source in ("arquivo-teste", "exemplo-sintetico"):
            self.conn.execute("UPDATE batch SET origin = ? WHERE id = ?", (source, occurrence["batch_id"]))
        for item in store.rows(self.conn, "SELECT id, payload_json FROM ledger_entry WHERE owner_id = ?", (row["owner_id"],)):
            body = json.loads(item["payload_json"])
            if body.get("occurrenceId") != occurrence["id"]:
                continue
            body["source"] = source
            body["simulated"] = source == "exemplo-sintetico"
            self.conn.execute("UPDATE ledger_entry SET payload_json = ? WHERE id = ?", (json.dumps(body), item["id"]))
        for item in store.rows(self.conn, "SELECT id, payload_json FROM statement_note WHERE owner_id = ?", (row["owner_id"],)):
            body = json.loads(item["payload_json"])
            if source in ("arquivo-teste", "exemplo-sintetico") and body.get("origin") == "extrato-bb-arquivo":
                body["origin"] = source
                self.conn.execute("UPDATE statement_note SET payload_json = ? WHERE id = ?", (json.dumps(body), item["id"]))
                break

    def _identity(self):
        return {
            "movement": store.rows(self.conn, "SELECT id, owner_id, occurrence_id, amount_cents, booked_on FROM movement ORDER BY id"),
            "occurrence": store.rows(self.conn, "SELECT id, owner_id, batch_id, signature, movement_id FROM occurrence ORDER BY id"),
        }

    def _month(self, owner, account=None):
        page = store.home(self.conn, owner, account=account)
        month = page["month"]
        return {key: month[key] for key in ("realizedIn", "realizedOut", "forecastIn", "forecastOut")}

    def _run(self, argv):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            reclass.main(argv)
        return json.loads(buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
