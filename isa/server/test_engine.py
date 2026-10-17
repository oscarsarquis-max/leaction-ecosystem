import unittest

from engine import project

BASE = {
    "known": True,
    "as_of": "2026-10-16",
    "amount_cents": 60000,
    "protected_cents": 10000,
    "convention": "encerramento_do_dia",
}

EVENTS = [
    {"id": "luz", "kind": "saida", "label": "Luz", "on": "2026-10-18", "cents": 20000, "included": True},
    {"id": "aluguel", "kind": "saida", "label": "Aluguel", "on": "2026-10-20", "cents": 50000, "included": True},
    {"id": "mercado", "kind": "saida", "label": "Mercado", "on": "2026-10-28", "cents": 30000, "included": True},
    {"id": "pagto", "kind": "entrada", "label": "Pagamento", "on": "2026-10-25", "cents": 120000, "included": True},
]


def day(result, iso):
    return next(item for item in result["days"] if item["date"] == iso)


class ProjectTest(unittest.TestCase):
    def test_canonical_gap_before_income(self):
        result = project(BASE, EVENTS, "2026-10-16")
        self.assertTrue(result["complete"])
        self.assertEqual(day(result, "2026-10-16")["cents"], 60000)
        self.assertEqual(day(result, "2026-10-18")["cents"], 40000)
        self.assertEqual(day(result, "2026-10-20")["cents"], -10000)
        self.assertEqual(day(result, "2026-10-25")["cents"], 110000)
        self.assertEqual(day(result, "2026-10-28")["cents"], 80000)
        self.assertEqual(result["october_end_cents"], 80000)
        self.assertEqual(result["minimum"], {"date": "2026-10-20", "cents": -10000})
        self.assertEqual(result["first_insufficiency"], "2026-10-20")
        self.assertEqual(result["floor_gap_cents"], 20000)
        self.assertEqual(result["margin"]["capacity_cents"], 0)
        self.assertEqual(result["margin"]["deficit_cents"], 20000)
        self.assertEqual(result["horizon_end"], "2026-11-30")

    def test_delay_keeps_month_end_and_lifts_minimum(self):
        moved = [dict(item) for item in EVENTS]
        moved[1] = dict(moved[1], on="2026-10-26")
        result = project(BASE, moved, "2026-10-16")
        self.assertEqual(result["minimum"]["cents"], 40000)
        self.assertEqual(result["october_end_cents"], 80000)
        self.assertIsNone(result["first_insufficiency"])
        self.assertEqual(day(result, "2026-10-26")["cents"], 110000)

    def test_delay_into_november_stays_visible(self):
        moved = [dict(item) for item in EVENTS]
        moved[1] = dict(moved[1], on="2026-11-02")
        moved.append({"id": "nov", "kind": "saida", "label": "Condomínio", "on": "2026-11-05", "cents": 10000, "included": True})
        result = project(BASE, moved, "2026-10-16")
        labels = {item["label"] for item in result["next_month_events"]}
        self.assertEqual(labels, {"Aluguel", "Condomínio"})
        self.assertEqual(result["carried_to_next_month_cents"], 130000)

    def test_uncertain_income_stays_out(self):
        noisy = EVENTS + [{"id": "talvez", "kind": "entrada", "label": "Talvez", "on": "2026-10-21", "cents": 99900, "included": False}]
        result = project(BASE, noisy, "2026-10-16")
        self.assertEqual(day(result, "2026-10-21")["cents"], -10000)

    def test_missing_base_is_not_zero(self):
        result = project({"known": False}, EVENTS, "2026-10-16")
        self.assertFalse(result["complete"])
        self.assertIn("Quanto você tem disponível e em qual data?", result["missing"])
        self.assertIsNone(result["margin"]["capacity_cents"])

    def test_same_day_order_is_reported(self):
        base = dict(BASE, amount_cents=10000, protected_cents=0)
        events = [
            {"id": "sai", "kind": "saida", "label": "Conta", "on": "2026-10-17", "cents": 15000, "included": True},
            {"id": "entra", "kind": "entrada", "label": "Crédito", "on": "2026-10-17", "cents": 20000, "included": True},
        ]
        result = project(base, events, "2026-10-16")
        self.assertEqual(day(result, "2026-10-17")["cents"], 15000)
        self.assertEqual(result["dependencies"][0]["date"], "2026-10-17")
        self.assertTrue(result["dependencies"][0]["sem_horario"])

    def test_reserve_already_in_base_is_not_added(self):
        events = EVENTS + [{"id": "poup", "kind": "reserva", "label": "Poupança", "on": "2026-10-19", "cents": 20000, "included_in_base": True, "usable": True}]
        result = project(BASE, events, "2026-10-16")
        self.assertEqual(day(result, "2026-10-19")["cents"], 40000)

    def test_credit_limit_is_not_money(self):
        events = EVENTS + [{"id": "lim", "kind": "reserva", "kind_detail": "limite", "label": "Limite", "on": "2026-10-19", "cents": 900000, "included_in_base": False, "usable": True}]
        result = project(BASE, events, "2026-10-16")
        self.assertEqual(result["minimum"]["cents"], -10000)

    def test_negative_balance_is_kept(self):
        result = project(dict(BASE, amount_cents=-5000, protected_cents=0), [], "2026-10-16", horizon="2026-10-18")
        self.assertEqual(day(result, "2026-10-18")["cents"], -5000)

    def test_movement_already_in_closing_balance_is_skipped(self):
        events = EVENTS + [{"id": "velho", "kind": "saida", "label": "Já saiu", "on": "2026-10-16", "cents": 40000, "included": True, "already_in_base": True}]
        result = project(BASE, events, "2026-10-16")
        self.assertEqual(day(result, "2026-10-16")["cents"], 60000)

    def test_extra_spend_on_reference_day_reduces_capacity(self):
        plain = project(BASE, EVENTS, "2026-10-16")
        spent = project(BASE, EVENTS, "2026-10-16", extra={"on": "2026-10-16", "cents": 1000, "label": "Café"})
        self.assertEqual(plain["margin"]["capacity_cents"], 0)
        self.assertEqual(spent["days"][0]["cents"], 59000)
        self.assertEqual(spent["margin"]["capacity_cents"], 0)
        self.assertGreater(spent["margin"]["deficit_cents"], plain["margin"]["deficit_cents"])

    def test_category_budget_does_not_stack(self):
        result = project(BASE, EVENTS, "2026-10-16", budgets=[{"category": "Lazer", "remaining_cents": 80000}])
        self.assertEqual(result["budgets"]["categories"][0]["offered_cents"], 0)
        self.assertIn("não se somam", result["budgets"]["categories"][0]["note"].lower())


if __name__ == "__main__":
    unittest.main()
