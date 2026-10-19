import os
import tempfile
import unittest
from unittest.mock import patch

import overview
import store
import ai


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-visao"
        self.other = "pessoa-outra"

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def page(self, owner=None):
        return store.home(self.conn, owner or self.owner)["overview"]

    def test_empty_account_keeps_questions_without_a_fake_zero(self):
        page = self.page()
        self.assertIsNone(page["informed"])
        self.assertIsNone(page["nextInflow"])
        self.assertEqual(page["situation"]["kind"], "incomplete")
        self.assertIsNone(page["margin"]["cents"])
        self.assertIsNone(page["series"])
        self.assertEqual(page["payables"]["count"], 0)

    def test_partial_known_sum_does_not_hide_pending_items(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 100000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 40000, "dueOn": "2026-10-20"})
        store.add_commitment(self.conn, self.owner, {"label": "Luz", "totalCents": None, "dueOn": None})
        page = self.page()
        self.assertEqual(page["payables"]["cents"], 40000)
        self.assertEqual(page["payables"]["pendingCount"], 1)
        self.assertEqual(page["payables"]["coverage"], "Compromissos do planejamento")
        self.assertEqual(page["situation"]["kind"], "covers")

    def test_shortfall_date_is_not_the_minimum_date(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 100000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_inflow(self.conn, self.owner, {"label": "Pagamento", "amountCents": 200000, "dueOn": "2026-11-05", "state": "confirmada"})
        store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 120000, "dueOn": "2026-10-18"})
        store.add_commitment(self.conn, self.owner, {"label": "Escola", "totalCents": 10000, "dueOn": "2026-10-25"})
        page = self.page()
        self.assertEqual(page["situation"]["kind"], "shortfall")
        self.assertEqual(page["situation"]["on"], "2026-10-18")
        self.assertEqual(page["situation"]["cents"], 20000)
        self.assertEqual(page["situation"]["minimum"]["on"], "2026-10-25")
        self.assertEqual(page["period"]["basis"], "ate-entrada")
        self.assertEqual(page["period"]["until"], "2026-11-05")
        self.assertEqual(page["payables"]["cents"], 130000)

    def test_reserve_use_is_not_a_negative_balance(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 100000, "asOf": "2026-10-16", "protectedCents": 40000})
        store.add_inflow(self.conn, self.owner, {"label": "Pagamento", "amountCents": 50000, "dueOn": "2026-11-05", "state": "confirmada"})
        store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 70000, "dueOn": "2026-10-18"})
        page = self.page()
        self.assertEqual(page["situation"]["kind"], "reserve")
        self.assertGreater(page["situation"]["cents"], 0)
        self.assertEqual(page["informed"]["protectedCents"], 40000)

    def test_uncertain_inflow_does_not_support_the_conclusion(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 50000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_inflow(self.conn, self.owner, {"label": "Talvez", "amountCents": 80000, "dueOn": "2026-10-28", "state": "incerta"})
        store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 20000, "dueOn": "2026-10-20"})
        page = self.page()
        self.assertIsNone(page["nextInflow"])
        self.assertEqual(page["uncertainInflow"]["state"], "incerta")
        self.assertEqual(page["period"]["basis"], "30-dias")

    def test_partial_payment_counts_only_the_remainder(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 80000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 80000, "remainingCents": 30000, "dueOn": "2026-10-20"})
        page = self.page()
        self.assertEqual(page["payables"]["cents"], 30000)

    def test_known_charge_is_absolute_and_unknown_charge_is_not_zero(self):
        known = {"label": "Condomínio", "due_on": "2026-10-01", "remaining_cents": 100000, "conditions_json": '{"principalCents": 100000, "fineCents": 2000, "interest": {"regime": "simples", "period": "month", "rateBps": 100}}'}
        estimate = overview.charge_estimate(known, "2026-11-01")
        self.assertEqual(estimate["status"], "estimated")
        self.assertEqual(estimate["components"][0]["cents"], 2000)
        self.assertEqual(estimate["components"][1]["cents"], 1000)
        self.assertEqual(estimate["extraCents"], 3000)
        self.assertEqual(estimate["totalCents"], 103000)
        unknown = overview.charge_estimate({"label": "Cartão", "due_on": "2026-10-01", "remaining_cents": 50000, "conditions_json": '{"custo": "desconhecido", "aceite": "desconhecido"}'}, "2026-10-20")
        self.assertEqual(unknown["status"], "unknown")
        self.assertNotIn("cents", unknown)

    def test_overdue_charge_messages_and_owner_isolation(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 200000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_commitment(self.conn, self.owner, {"label": "Condomínio", "totalCents": 100000, "dueOn": "2026-10-01", "conditions": {"kind": "fatura", "principalCents": 100000, "fineCents": 2000, "interest": {"regime": "simples", "period": "month", "rateBps": 100}}})
        store.add_commitment(self.conn, self.owner, {"label": "Internet", "totalCents": 9000, "dueOn": "2026-10-10"})
        store.save_availability(self.conn, self.other, {"amountCents": 100, "asOf": "2026-10-16", "protectedCents": 0})
        page = self.page()
        other = self.page(self.other)
        self.assertEqual(page["payables"]["overdueCount"], 2)
        self.assertTrue(any(item["id"].startswith("charge:") and item.get("estimate", {}).get("extraCents") == 3000 for item in page["insightHistory"]))
        self.assertTrue(any(item.get("estimate", {}).get("status") == "unknown" for item in page["insightHistory"]))
        self.assertEqual(other["informed"]["cents"], 100)
        self.assertEqual(other["payables"]["count"], 0)

    def test_home_read_does_not_write_money_or_ai(self):
        before_jobs = store.one(self.conn, "SELECT COUNT(*) AS n FROM ai_job")["n"]
        before_bills = store.one(self.conn, "SELECT COUNT(*) AS n FROM commitment")["n"]
        self.page()
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ai_job")["n"], before_jobs)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM commitment")["n"], before_bills)

    def test_dismiss_hides_today_without_deleting_the_fact(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 1000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_commitment(self.conn, self.owner, {"label": "Luz", "totalCents": None, "dueOn": None})
        page = self.page()
        pending = next(item for item in page["insights"] if item["id"] == "pending")
        store.dismiss_insight(self.conn, self.owner, {"id": pending["id"]})
        again = self.page()
        self.assertNotIn("pending", [item["id"] for item in again["insights"]])
        self.assertIn("pending", [item["id"] for item in again["insightHistory"]])

    def test_daily_reading_is_idempotent_until_the_money_changes(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 100000, "asOf": "2026-10-16", "protectedCents": 0})
        bill = store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 40000, "dueOn": "2026-10-01"})
        with patch.dict(os.environ, {"ISA_AI_ENABLED": "1"}):
            first = ai.queue_insight(self.conn, self.owner)
            second = ai.queue_insight(self.conn, self.owner)
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ai_job WHERE owner_id = ?", (self.owner,))["n"], 1)
            store.patch_commitment(self.conn, self.owner, bill["id"], {"remainingCents": 10000})
            third = ai.queue_insight(self.conn, self.owner)
            self.assertNotEqual(third["id"], first["id"])
            page = self.page()
            self.assertTrue(page["reading"]["stale"] or page["reading"]["status"] == "queued")

    def test_empty_day_does_not_invent_a_reading(self):
        with patch.dict(os.environ, {"ISA_AI_ENABLED": "1"}):
            job = ai.queue_insight(self.conn, self.owner)
        self.assertEqual(job["status"], "idle")
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ai_job WHERE owner_id = ?", (self.owner,))["n"], 0)

    def test_failed_reading_waits_for_a_manual_retry(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 100000, "asOf": "2026-10-16", "protectedCents": 0})
        store.add_commitment(self.conn, self.owner, {"label": "Luz", "totalCents": None, "dueOn": None})
        with patch.dict(os.environ, {"ISA_AI_ENABLED": "1"}):
            first = ai.queue_insight(self.conn, self.owner)
            self.conn.execute("UPDATE ai_job SET status = 'failed' WHERE id = ?", (first["id"],))
            self.conn.commit()
            again = ai.queue_insight(self.conn, self.owner, False)
            self.assertEqual(again["status"], "failed")
            self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ai_job WHERE owner_id = ?", (self.owner,))["n"], 1)
            manual = ai.queue_insight(self.conn, self.owner, True)
            self.assertNotEqual(manual["id"], first["id"])


if __name__ == "__main__":
    unittest.main()
