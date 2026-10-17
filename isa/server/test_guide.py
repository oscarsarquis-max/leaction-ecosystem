import os
import tempfile
import unittest

import store


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-guia"

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def guide(self):
        home = store.home(self.conn, self.owner)
        return home["guide"], home

    def test_empty_account_asks_for_availability_without_reading_the_sentence(self):
        guide, _home = self.guide()
        self.assertEqual(guide["step"], "availability")
        self.assertEqual(guide["gaps"], ["availability", "inflow", "commitments"])
        self.assertFalse(guide["availabilityKnown"])

    def test_zero_is_saved_and_unknown_is_not_zero(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 0, "asOf": "2026-10-17", "protectedCents": 0, "source": "declarada"})
        guide, _home = self.guide()
        self.assertTrue(guide["availabilityKnown"])
        self.assertEqual(guide["availability"]["amountCents"], 0)
        self.assertEqual(guide["availability"]["protectedCents"], 0)
        self.assertNotIn("availability", guide["gaps"])

    def test_unknown_availability_can_continue_without_inventing_a_value(self):
        store.save_draft(self.conn, self.owner, "planejar", {"availabilityUnknown": True})
        guide, _home = self.guide()
        self.assertEqual(guide["step"], "availability-pending")
        self.assertIn("availability", guide["gaps"])
        store.save_draft(self.conn, self.owner, "planejar", {"availabilityUnknown": True, "continuePastAvailability": True})
        guide, _home = self.guide()
        self.assertEqual(guide["step"], "inflow")
        self.assertIsNone(guide["availability"])

    def test_repeat_click_does_not_duplicate(self):
        first = store.add_inflow(self.conn, self.owner, {"label": "Pagamento", "amountCents": 120050, "dueOn": "2026-10-25", "state": "confirmada"})
        second = store.add_inflow(self.conn, self.owner, {"label": "Pagamento", "amountCents": 120050, "dueOn": "2026-10-25", "state": "confirmada"})
        self.assertTrue(second["repeated"])
        self.assertEqual(first["id"], second["id"])
        bill = store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 50000, "dueOn": "2026-10-20"})
        again = store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 50000, "dueOn": "2026-10-20"})
        self.assertTrue(again["repeated"])
        self.assertEqual(bill["id"], again["id"])
        rows = store.rows(self.conn, "SELECT id FROM commitment WHERE owner_id = ?", (self.owner,))
        self.assertEqual(len(rows), 1)

    def test_declared_none_is_not_an_empty_list(self):
        store.save_availability(self.conn, self.owner, {"amountCents": 100000, "asOf": "2026-10-17", "protectedCents": 0})
        store.add_inflow(self.conn, self.owner, {"label": "Pagamento", "amountCents": 50000, "dueOn": "2026-10-25", "state": "confirmada"})
        guide, _home = self.guide()
        self.assertEqual(guide["step"], "commitments")
        store.save_draft(self.conn, self.owner, "planejar", {"commitmentsDeclaredNone": True, "continuePastCommitments": True})
        guide, _home = self.guide()
        self.assertEqual(guide["step"], "summary")
        self.assertTrue(guide["commitmentsDeclaredNone"])
        self.assertNotIn("commitments", guide["gaps"])


if __name__ == "__main__":
    unittest.main()
