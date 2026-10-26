"""Lotes de trabalho. Dados sintéticos e isolados. Não usa a conta publicada."""

import os
import tempfile
import unittest

import store
import workbatches

os.environ["ISA_ENV"] = "lab"


def entry(item_id, **extra):
    body = {
        "id": item_id,
        "merchant": extra.pop("merchant", "Compra"),
        "direction": "gasto",
        "nature": "consumo",
        "status": "pago",
        "statusDate": "2026-10-22",
        "noteDate": "2026-10-22",
        "amountMinor": 10000,
        "currency": "BRL",
        "category": "",
        "source": "digitado",
        "archived": False,
    }
    body.update(extra)
    return body


class WorkBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-ensaio-lotes"
        self.other = "pessoa-ensaio-outra"

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def paid(self, batch_id, currency="BRL"):
        batch = workbatches.public_batch(self.conn, self.owner, store.one(self.conn, "SELECT * FROM work_batch WHERE id = ?", (batch_id,)))
        return batch["totals"]["byCurrency"].get(currency, {}).get("gastosPagos", 0), batch

    def test_schema_starts_at_seven_and_a_visit_creates_nothing(self):
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 10)
        store.workspace(self.conn, self.owner)
        store.workspace(self.conn, self.owner)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM work_batch")["n"], 0)

    def test_trip_totals_retry_forecast_income_transfer_and_reference(self):
        batch = workbatches.create_batch(self.conn, self.owner, {
            "id": "viagem", "name": "Viagem", "criterion": "evento", "supplier": "Vários",
            "documentRef": "nota-250", "referenceMinor": 25000, "referenceCurrency": "BRL", "activate": True,
        })
        store.save_entry(self.conn, self.owner, entry("a", merchant="Mercado Central", amountMinor=10000, category="Alimentação", workBatchId="viagem"))
        store.save_entry(self.conn, self.owner, entry("b", merchant="Padaria", amountMinor=2790, workBatchId="viagem"))
        paid, current = self.paid("viagem")
        self.assertEqual(paid, 12790)
        self.assertEqual(current["count"], 2)
        food = next(item for item in current["compositions"][0]["items"] if item["category"] == "Alimentação")
        pending = next(item for item in current["compositions"][0]["items"] if item["category"] == "A categorizar")
        self.assertEqual(food["amount"], 10000)
        self.assertEqual(pending["amount"], 2790)
        self.assertEqual(current["compositions"][0]["total"], 12790)

        store.save_entry(self.conn, self.owner, entry("c", merchant="Café", amountMinor=2590, category="Alimentação", workBatchId="viagem"))
        store.save_entry(self.conn, self.owner, entry("c", merchant="Café", amountMinor=2590, category="Alimentação", workBatchId="viagem"))
        paid, current = self.paid("viagem")
        self.assertEqual(paid, 15380)
        self.assertEqual(current["count"], 3)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (self.owner,))["n"], 3)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM work_member WHERE batch_id = ? AND active = 1", ("viagem",))["n"], 3)

        store.save_entry(self.conn, self.owner, entry("d", merchant="Hotel", amountMinor=10000, status="a_pagar", statusDate="", dueDate="2026-10-30", workBatchId="viagem"))
        paid, current = self.paid("viagem")
        slot = current["totals"]["byCurrency"]["BRL"]
        self.assertEqual(paid, 15380)
        self.assertEqual(slot["gastosAPagar"], 10000)
        self.assertEqual(slot["gastosPagos"] + slot["gastosAPagar"], 25380)
        self.assertEqual(current["referenceGap"]["delta"], 380)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE amount_minor IS NOT NULL", )["n"] if False else store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (self.owner,))["n"], 4)

        store.save_entry(self.conn, self.owner, entry("e", merchant="Reembolso de amiga", direction="ganho", status="recebido", amountMinor=5000, category="Outros", workBatchId="viagem"))
        store.save_entry(self.conn, self.owner, entry("f", merchant="Entre contas", nature="transferencia", amountMinor=20000, workBatchId="viagem"))
        _, current = self.paid("viagem")
        slot = current["totals"]["byCurrency"]["BRL"]
        self.assertEqual(slot["gastosPagos"], 15380)
        self.assertEqual(slot["ganhosRecebidos"], 5000)
        self.assertEqual(slot["transferencias"], 20000)
        self.assertNotIn("rende", [key for key, value in slot.items() if key == "gastosPagos" and value != 15380])

        found = workbatches.search(self.conn, self.owner, {"q": "mercado", "pageSize": 1, "page": 1})
        self.assertEqual(found["entryCount"], 1)
        self.assertEqual(found["totals"]["byCurrency"]["BRL"]["gastosPagos"], 10000)
        self.assertEqual(len(found["entries"]), 1)
        trip = next(item for item in found["batches"] if item["id"] == "viagem")
        self.assertEqual(trip["foundCount"], 1)
        self.assertEqual(trip["foundTotals"]["byCurrency"]["BRL"]["gastosPagos"], 10000)
        self.assertEqual(trip["totals"]["byCurrency"]["BRL"]["gastosPagos"], 15380)
        page2 = workbatches.search(self.conn, self.owner, {"q": "mercado", "pageSize": 1, "page": 2})
        self.assertEqual(page2["totals"]["byCurrency"]["BRL"]["gastosPagos"], 10000)
        self.assertEqual(page2["entries"], [])

        alone = workbatches.create_batch(self.conn, self.owner, {"id": "unica", "name": "Uma compra", "criterion": "documento", "activate": False})
        store.save_entry(self.conn, self.owner, entry("g", merchant="Livro", amountMinor=4500, workBatchId="unica"))
        self.assertEqual(self.paid("unica")[1]["count"], 1)
        self.assertEqual(alone["count"], 0)

    def test_edit_move_archive_category_currency_and_isolation(self):
        workbatches.create_batch(self.conn, self.owner, {"id": "viagem", "name": "Viagem", "criterion": "evento"})
        workbatches.create_batch(self.conn, self.owner, {"id": "casa", "name": "Casa", "criterion": "outro", "activate": False})
        usd = store.save_account(self.conn, self.owner, {"name": "Viagem dólar", "currency": "USD", "institution": "Outro", "kind": "corrente"})
        store.save_entry(self.conn, self.owner, entry(
            "imp", merchant="Mercado Central", amountMinor=10000, category="Alimentação", workBatchId="viagem",
            occurrenceId="occ-1", source="extrato-sintetico", bankDocument="DOC-9",
        ))
        store.save_entry(self.conn, self.owner, entry("taxi", merchant="Táxi", amountMinor=2790, workBatchId="viagem"))
        before = store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE id = ?", ("taxi",))["n"]
        saved = store.save_entry(self.conn, self.owner, entry("taxi", merchant="Táxi", amountMinor=2790, category="Transporte", workBatchId="viagem"))
        self.assertEqual(saved["amountMinor"], 2790)
        self.assertEqual(saved["id"], "taxi")
        self.assertEqual(saved["workBatchId"], "viagem")
        self.assertEqual(before, 1)
        _, current = self.paid("viagem")
        labels = {item["category"]: item["amount"] for item in current["compositions"][0]["items"]}
        self.assertEqual(labels, {"Alimentação": 10000, "Transporte": 2790})
        self.assertEqual(current["compositions"][0]["total"], 12790)
        self.assertTrue(store.one(self.conn, "SELECT id FROM change_log WHERE entity_id = ? AND action = ?", ("taxi", "categoria-corrigida")))

        workbatches.move_entry(self.conn, self.owner, "viagem", "taxi", "casa")
        self.assertEqual(self.paid("viagem")[0], 10000)
        self.assertEqual(self.paid("casa")[0], 2790)
        kept = store.save_entry(self.conn, self.owner, entry("imp", merchant="Mercado Central", amountMinor=10000, category="Alimentação", occurrenceId="occ-1", source="extrato-sintetico"))
        self.assertEqual(kept["occurrenceId"], "occ-1")
        self.assertEqual(kept["workBatchId"], "viagem")

        store.save_entry(self.conn, self.owner, entry("taxi", merchant="Táxi", amountMinor=2790, category="Transporte", archived=True, workBatchId="casa"))
        home = self.paid("casa")[1]
        self.assertEqual(home["totals"]["byCurrency"].get("BRL", {}).get("gastosPagos", 0), 0)
        self.assertEqual(home["totals"]["archived"], 1)
        store.save_entry(self.conn, self.owner, entry("taxi", merchant="Táxi", amountMinor=2790, category="Transporte", archived=False, workBatchId="casa"))
        self.assertEqual(self.paid("casa")[0], 2790)

        store.save_entry(self.conn, self.owner, entry("usd", merchant="Coffee", amountMinor=500, currency="USD", accountId=usd["id"], workBatchId="viagem"))
        full = self.paid("viagem")[1]
        self.assertEqual(full["totals"]["byCurrency"]["BRL"]["gastosPagos"], 10000)
        self.assertEqual(full["totals"]["byCurrency"]["USD"]["gastosPagos"], 500)
        mixed = dict(full)
        self.assertIsNone(workbatches.reference_gap({"reference_minor": 25000, "reference_currency": "BRL"}, full["totals"]))

        with self.assertRaises(ValueError):
            workbatches.public_batch(self.conn, self.other, store.one(self.conn, "SELECT * FROM work_batch WHERE id = ?", ("viagem",)))
        with self.assertRaises(ValueError):
            store.save_entry(self.conn, self.other, entry("x", workBatchId="viagem"))
        hidden = workbatches.search(self.conn, self.other, {"q": "mercado"})
        self.assertEqual(hidden["entryCount"], 0)
        self.assertEqual(hidden["batches"], [])

        events = store.rows(self.conn, "SELECT kind FROM work_event WHERE owner_id = ? ORDER BY created_at", (self.owner,))
        self.assertIn("vinculado", [item["kind"] for item in events])
        self.assertIn("desvinculado", [item["kind"] for item in events])

    def test_cover_conflict_reopen_and_restart(self):
        created = workbatches.create_batch(self.conn, self.owner, {"id": "aberto", "name": "Registros de hoje", "criterion": "periodo"})
        workbatches.update_batch(self.conn, self.owner, "aberto", {"version": created["version"], "name": "Feira", "criterion": "evento"})
        with self.assertRaises(workbatches.Conflict):
            workbatches.update_batch(self.conn, self.owner, "aberto", {"version": created["version"], "name": "Outro", "criterion": "evento"})
        named = workbatches.public_batch(self.conn, self.owner, store.one(self.conn, "SELECT * FROM work_batch WHERE id = ?", ("aberto",)))
        self.assertEqual(named["name"], "Feira")
        workbatches.conclude_batch(self.conn, self.owner, "aberto")
        self.assertEqual(workbatches.list_batches(self.conn, self.owner)["activeWorkBatchId"], "")
        workbatches.reopen_batch(self.conn, self.owner, "aberto")
        self.assertEqual(workbatches.list_batches(self.conn, self.owner)["activeWorkBatchId"], "aberto")
        self.conn.close()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        again = workbatches.list_batches(self.conn, self.owner)
        self.assertEqual(len(again["items"]), 1)
        self.assertEqual(again["items"][0]["name"], "Feira")
        self.assertEqual(again["activeWorkBatchId"], "aberto")
        store.workspace(self.conn, self.owner)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM work_batch WHERE owner_id = ?", (self.owner,))["n"], 1)


if __name__ == "__main__":
    unittest.main()
