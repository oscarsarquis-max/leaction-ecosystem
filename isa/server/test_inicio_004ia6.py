"""Cenário do Início integrado. Data fixa 26/10/2026. Dados sintéticos."""

import os
import tempfile
import unittest

import store

os.environ["ISA_ENV"] = "lab"
REF = "2026-10-26"


class IntegratedHomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-inicio"
        self.bb = store.save_account(self.conn, self.owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
        self.poup = store.save_account(self.conn, self.owner, {"name": "Poupança", "currency": "BRL", "kind": "poupanca", "institution": "CAIXA ECONOMICA FEDERAL"})

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def _money(self, account_id, day, cents, direction, label, nature="consumo"):
        movement = "mov-" + label
        occurrence = "occ-" + label
        self.conn.execute(
            "INSERT INTO occurrence (id, owner_id, batch_id, signature, state, movement_id, payload_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (occurrence, self.owner, "", movement, "incorporada", movement, '{"accountId":"%s"}' % account_id, store.now()),
        )
        self.conn.execute(
            "INSERT INTO movement (id, owner_id, occurrence_id, amount_cents, direction, nature, booked_on, label, source, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (movement, self.owner, occurrence, cents, direction, nature, day, label, "sintetico", store.now()),
        )
        store.backfill_entry_columns(self.conn)

    def _scene(self):
        store.save_availability(self.conn, self.owner, {"accountId": self.bb["id"], "amountCents": 100000, "asOf": REF, "protectedCents": 0, "source": "declarada"})
        store.save_availability(self.conn, self.owner, {"accountId": self.poup["id"], "amountCents": 20000, "asOf": REF, "protectedCents": 20000, "source": "declarada"})
        self._money(self.bb["id"], "2026-10-05", 400000, "entrada", "Salário", "ganho")
        self._money(self.bb["id"], "2026-10-10", 180000, "saida", "Moradia")
        self._money(self.bb["id"], "2026-10-15", 90000, "saida", "Mercado")
        self._money(self.bb["id"], "2026-10-23", 40000, "saida", "Contas")
        store.add_commitment(self.conn, self.owner, {"label": "Conta do dia 27", "totalCents": 45000, "dueOn": "2026-10-27", "accountId": self.bb["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Conta do dia 28", "totalCents": 90000, "dueOn": "2026-10-28", "accountId": self.bb["id"]})
        store.add_inflow(self.conn, self.owner, {"label": "Recebimento", "amountCents": 150000, "dueOn": "2026-10-30", "state": "confirmada", "accountId": self.bb["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Novembro 3", "totalCents": 70000, "dueOn": "2026-11-03", "accountId": self.bb["id"]})
        store.add_inflow(self.conn, self.owner, {"label": "Salário de novembro", "amountCents": 400000, "dueOn": "2026-11-05", "state": "confirmada", "accountId": self.bb["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Novembro 10", "totalCents": 180000, "dueOn": "2026-11-10", "accountId": self.bb["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Novembro 20", "totalCents": 100000, "dueOn": "2026-11-20", "accountId": self.bb["id"]})

    def test_october_keeps_balance_apart_from_history_and_finds_the_gap(self):
        self._scene()
        page = store.home(self.conn, self.owner, REF)
        balance = page["balance"]
        self.assertEqual(balance["label"], "Disponível hoje")
        self.assertEqual(balance["cents"], 120000)
        self.assertEqual(balance["origin"], "Soma das contas com referência")
        self.assertTrue(balance["usableToday"])
        self.assertEqual(balance["protectedCents"], 20000)
        month = page["month"]
        self.assertEqual(month["realizedIn"], 400000)
        self.assertEqual(month["realizedOut"], 310000)
        self.assertEqual(month["forecastOut"], 135000)
        self.assertEqual(month["forecastIn"], 150000)
        result = page["projection"]
        self.assertEqual(result["base_cents"], 120000)
        self.assertEqual(result["first_insufficiency"], "2026-10-28")
        day = next(item for item in result["days"] if item["date"] == "2026-10-28")
        self.assertEqual(day["cents"], -15000)
        self.assertEqual(result["days"][-1]["cents"] if False else next(item for item in result["days"] if item["date"] == "2026-10-30")["cents"], 135000)
        self.assertEqual(result["margin"]["capacity_cents"], 0)
        self.assertEqual(result["floor_gap_cents"], 35000)
        november = [item for item in result["days"] if item["date"].startswith("2026-11")]
        self.assertEqual(min(item["cents"] for item in november), 65000)
        self.assertEqual(next(item["cents"] for item in november if item["date"] == "2026-11-20"), 185000)
        self.assertNotEqual(result["margin"]["capacity_cents"], 45000)

    def test_one_account_does_not_reuse_the_global_balance(self):
        self._scene()
        page = store.home(self.conn, self.owner, REF, account=self.bb["id"])
        self.assertEqual(page["balance"]["cents"], 100000)
        self.assertNotIn(120000, [line["cents"] for line in page["balance"]["lines"]])
        self.assertTrue(page["projection"]["complete"])
        self.assertNotEqual(page["projection"]["base_cents"], 120000)

    def test_partial_and_stale_balances_do_not_become_today(self):
        store.save_availability(self.conn, self.owner, {"accountId": self.bb["id"], "amountCents": 100000, "asOf": REF, "source": "declarada"})
        page = store.home(self.conn, self.owner, REF)
        self.assertEqual(page["balance"]["label"], "Total conhecido")
        self.assertEqual(page["balance"]["cents"], 100000)
        self.assertFalse(page["balance"]["usableToday"])
        self.assertTrue(page["balance"]["missing"])
        store.save_availability(self.conn, self.owner, {"accountId": self.bb["id"], "amountCents": 80000, "asOf": "2026-10-14", "source": "declarada"})
        store.save_availability(self.conn, self.owner, {"accountId": self.poup["id"], "amountCents": 0, "asOf": "2026-10-14", "source": "declarada"})
        stale = store.home(self.conn, self.owner, REF)
        self.assertEqual(stale["balance"]["label"], "Último saldo conhecido")
        self.assertFalse(stale["balance"]["usableToday"])
        self.assertNotEqual(stale["balance"]["label"], "Disponível hoje")

    def test_future_month_is_forecast_and_a_future_settlement_is_not_realized_today(self):
        self._scene()
        self._money(self.bb["id"], "2026-11-02", 1000, "saida", "Futuro liquidado")
        picture = store.month_picture(self.conn, self.owner, "2026-11", REF, self.bb["id"])
        self.assertEqual(picture["phase"], "futuro")
        self.assertEqual(picture["realizedOut"], 0)
        self.assertTrue(any(item["state"] == "data futura" for item in picture["records"]))
        empty = store.month_picture(self.conn, self.owner, "2026-12", REF, self.bb["id"])
        self.assertTrue(empty["emptyForecast"])

    def test_an_empty_month_is_not_a_new_person(self):
        self._money(self.bb["id"], "2026-09-02", 1000, "saida", "Setembro")
        page = store.home(self.conn, self.owner, REF)
        self.assertFalse(page["presence"]["emptyPerson"])
        self.assertGreater(page["presence"]["movements"], 0)
        december = store.month_picture(self.conn, self.owner, "2026-12", REF, self.bb["id"])
        self.assertEqual(december["records"], [])
        bare = store.connect(os.path.join(self.tmp.name, "vazio.sqlite"))
        try:
            empty = store.home(bare, "pessoa-vazia", REF)
            self.assertTrue(empty["presence"]["emptyPerson"])
            self.assertEqual(empty["presence"]["accounts"], 0)
        finally:
            bare.close()


if __name__ == "__main__":
    unittest.main()
