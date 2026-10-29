"""Conexão bancária com respostas gravadas. Nenhum teste chama a Pluggy."""

import io
import json
import os
import tempfile
import time
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path

import banksync
import pluggy
import store

ITEM = "item-sigiloso-abcdef"
SECRET = "segredo-teste"
OWNER = "pessoa-teste"
ROOT = Path(__file__).resolve().parents[1]


def _item(owner=OWNER):
    return {
        "id": ITEM,
        "clientUserId": banksync.client_user_id(owner),
        "status": "UPDATED",
        "executionStatus": "SUCCESS",
        "lastUpdatedAt": "2026-10-26T10:40:00.000Z",
        "consentExpiresAt": "2027-10-27T00:00:00.000Z",
        "connector": {"name": "MeuPluggy"},
        "owner": "NOMESECRETO",
    }


def _accounts():
    return {"results": [
        {
            "id": "conta-corrente-1",
            "type": "BANK",
            "subtype": "CHECKING_ACCOUNT",
            "number": "0001/12345-0",
            "name": "Conta corrente",
            "balance": 9876.54,
            "currencyCode": "BRL",
            "owner": "NOMESECRETO",
            "taxNumber": "000.000.000-00",
            "bankData": {"transferNumber": "123/0001/12345-0", "closingBalance": 9876.54},
        },
        {
            "id": "cartao-1",
            "type": "CREDIT",
            "subtype": "CREDIT_CARD",
            "number": "4242",
            "name": "Cartão",
            "balance": 500,
            "currencyCode": "BRL",
            "creditData": {"balanceCloseDate": "2026-10-28", "balanceDueDate": "2026-11-05", "minimumPayment": 100},
        },
    ], "page": 1, "totalPages": 1}


def _transactions(account_id):
    if account_id == "cartao-1":
        rows = [{
            "id": "tx-cartao-1",
            "description": "COMPRA MERCADO",
            "amount": 80,
            "date": "2026-10-18T03:00:00.000Z",
            "currencyCode": "BRL",
            "category": "Groceries",
            "status": "POSTED",
            "type": "DEBIT",
            "accountId": "cartao-1",
        }]
    else:
        rows = [
            {
                "id": "tx-extrato-1",
                "description": "COMPRA MERCADO CENTRAL",
                "amount": -25.90,
                "date": "2026-10-20T03:00:00.000Z",
                "currencyCode": "BRL",
                "category": "Groceries",
                "status": "POSTED",
                "type": "DEBIT",
                "accountId": "conta-corrente-1",
            },
            {
                "id": "tx-nova-1",
                "description": "PAGAMENTO ALUGUEL",
                "amount": -100,
                "date": "2026-10-21T03:00:00.000Z",
                "currencyCode": "BRL",
                "category": "Rent",
                "status": "POSTED",
                "type": "DEBIT",
                "accountId": "conta-corrente-1",
            },
            {
                "id": "tx-pendente-1",
                "description": "COMPRA FUTURA",
                "amount": -10,
                "date": "2026-10-22T03:00:00.000Z",
                "currencyCode": "BRL",
                "status": "PENDING",
                "type": "DEBIT",
                "accountId": "conta-corrente-1",
            },
        ]
    return {"results": rows, "page": 1, "totalPages": 1}


def _investments():
    return {"results": [{
        "id": "posicao-1",
        "name": "Fundo de teste",
        "balance": 1359.39,
        "currencyCode": "BRL",
        "type": "MUTUAL_FUND",
        "subtype": "MULTIMARKET_FUND",
        "date": "2026-10-19T18:27:41.802Z",
        "owner": "NOMESECRETO",
        "status": "ACTIVE",
    }], "page": 1, "totalPages": 1}


class Fixture:
    def __init__(self, owner=OWNER, foreign=False):
        self.owner = owner
        self.foreign = foreign
        self.calls = []
        self.fail = {}
        self.balance = 500
        self.drop_updated = False
        self.checking_balance = None

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, body, headers.get("X-API-KEY", "")))
        if self.fail.get("timeout"):
            self.fail["timeout"] -= 1
            raise pluggy.PluggyError("O banco demorou para responder. Tente de novo em alguns minutos.", "timeout")
        if self.fail.get("status"):
            status = self.fail["status"]
            if status < 500:
                self.fail["status"] = 0
            return status, {}
        if url.endswith("/auth"):
            return 200, {"apiKey": "chave-teste"}
        if url.endswith("/connect_token"):
            return 200, {"accessToken": "token-teste"}
        if "/items/" in url and method == "DELETE":
            return 200, {}
        if "/items/" in url and method == "GET":
            payload = _item(self.owner)
            if self.foreign:
                payload["clientUserId"] = "outra-pessoa"
            if self.drop_updated:
                payload.pop("lastUpdatedAt", None)
            return 200, payload
        if url.split("?")[0].endswith("/accounts"):
            payload = _accounts()
            if self.checking_balance is not None:
                payload["results"][0]["balance"] = self.checking_balance
            return 200, payload
        if "/transactions" in url or "/v2/transactions" in url:
            account = "cartao-1" if "cartao-1" in url else "conta-corrente-1"
            return 200, _transactions(account)
        if url.split("?")[0].endswith("/investments"):
            return 200, _investments()
        if url.endswith("/webhooks"):
            return 201, {"id": "hook-1"}
        return 404, {}


class ClientTests(unittest.TestCase):
    def test_cache_expiry_error_and_timeout(self):
        clock = {"now": 1_000.0}
        fixture = Fixture()
        remote = pluggy.Client({"clientId": "id-teste", "clientSecret": SECRET, "webhookSecret": "cabecalho-teste"}, transport=fixture, clock=lambda: clock["now"])
        remote.item(ITEM)
        remote.item(ITEM)
        self.assertEqual(sum(1 for call in fixture.calls if call[0] == "POST" and call[1].endswith("/auth")), 1)
        clock["now"] = 1_000 + pluggy.KEY_LIFETIME
        remote.item(ITEM)
        self.assertEqual(sum(1 for call in fixture.calls if call[1].endswith("/auth")), 2)
        refused = Fixture()
        refused.fail["status"] = 401
        broken = pluggy.Client({"clientId": "id-teste", "clientSecret": SECRET}, transport=refused, clock=lambda: 0)
        with self.assertRaises(pluggy.PluggyError) as caught:
            broken.item(ITEM)
        self.assertEqual(caught.exception.code, "unauthorized")
        self.assertEqual(sum(1 for call in refused.calls if call[1].endswith("/auth")), 1)
        slow = Fixture()
        slow.fail["timeout"] = 1
        delayed = pluggy.Client({"clientId": "id-teste", "clientSecret": SECRET}, transport=slow, clock=lambda: 0)
        self.assertEqual(delayed.item(ITEM)["status"], "UPDATED")
        self.assertEqual(sum(1 for call in slow.calls if call[1].endswith("/auth")), 2)
        down = Fixture()
        down.fail["status"] = 500
        failed = pluggy.Client({"clientId": "id-teste", "clientSecret": SECRET}, transport=down, clock=lambda: 0)
        with self.assertRaises(pluggy.PluggyError):
            failed.connect_token("pessoa", "https://isa.actionhub.com.br/api/bank/webhook")


class BankTests(unittest.TestCase):
    def setUp(self):
        self.old = {name: os.environ.get(name) for name in ("ISA_ENV", "ISA_PLUGGY_ENABLED", "ISA_PLUGGY_ALLOWED_SUBS", "ISA_REFERENCE_DATE", "ISA_DATABASE_URL", "ISA_ERASURE_LEDGER")}
        os.environ["ISA_ENV"] = "lab"
        os.environ["ISA_PLUGGY_ENABLED"] = "1"
        os.environ["ISA_PLUGGY_ALLOWED_SUBS"] = OWNER
        os.environ["ISA_REFERENCE_DATE"] = "2026-10-26"
        os.environ.pop("ISA_DATABASE_URL", None)
        self.ledger = tempfile.NamedTemporaryFile(prefix="isa-erasure-", delete=False)
        self.ledger.close()
        os.environ["ISA_ERASURE_LEDGER"] = self.ledger.name
        pluggy.set_credentials({"clientId": "id-teste", "clientSecret": SECRET, "webhookSecret": "cabecalho-teste"})
        self.original_client = pluggy.client
        self.dir = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.dir.name, "isa.sqlite"))
        self.fixture = Fixture()
        pluggy.client = lambda transport=None, clock=None: pluggy.Client(pluggy.load_credentials(), transport=transport or self.fixture, clock=clock)

    def tearDown(self):
        self.conn.close()
        self.dir.cleanup()
        if os.path.isfile(self.ledger.name):
            os.remove(self.ledger.name)
        pluggy.client = self.original_client
        pluggy.set_credentials(None)
        for name, value in self.old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_schema_keeps_prior_writers(self):
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 14)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM schema_migration WHERE version = 12")["n"], 1)
        before = store.one(self.conn, "SELECT COUNT(*) AS n FROM account")["n"]
        account = store.save_account(self.conn, OWNER, {"name": "Manual", "currency": "BRL", "institution": "Banco"})
        store.write_entry(self.conn, OWNER, {"accountId": account["id"], "direction": "gasto", "amountMinor": 100, "status": "pago", "statusDate": "2026-10-10", "source": "manual"})
        self.assertIsNone(store.one(self.conn, "SELECT external_id FROM account WHERE id = ?", (account["id"],))["external_id"])
        self.assertIsNone(store.one(self.conn, "SELECT external_id FROM ledger_entry WHERE owner_id = ?", (OWNER,))["external_id"])
        store._migrate_body(self.conn)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM account")["n"], before + 1)

    def test_lock_hides_the_action(self):
        code, payload = banksync.route(self.conn, "outra-pessoa", "outra-pessoa", "GET", "/api/bank/connect-token", {})
        self.assertEqual(code, 403)
        self.assertEqual(payload["error"], banksync.DENIED)
        page = banksync.present(self.conn, "outra-pessoa", "outra-pessoa", store.list_accounts(self.conn, "outra-pessoa"))
        self.assertFalse(page["bankConnect"])
        self.assertEqual(page["bankLinks"], [])
        source = (ROOT / "prototype" / "app.js").read_text(encoding="utf-8")
        self.assertIn("state.bankConnect === true", source)
        self.assertIn("Conectar banco", source)
        self.assertLess(source.index("state.bankConnect === true"), source.index('id="connect-bank"'))

    def test_rejects_a_foreign_item(self):
        self.fixture.foreign = True
        code, payload = banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
        self.assertEqual(code, 403)
        self.assertIsNone(store.one(self.conn, "SELECT id FROM bank_link"))
        self.assertNotIn(ITEM, json.dumps(payload))

    def test_sync_links_and_does_not_duplicate(self):
        manual = store.save_account(self.conn, OWNER, {
            "name": "Conta já cadastrada",
            "institution": "Banco",
            "kind": "corrente",
            "currency": "BRL",
            "accountNumber": "12345-0",
            "bankCode": "123",
            "agency": "0001",
            "registration": False,
        })
        store.write_entry(self.conn, OWNER, {
            "accountId": manual["id"],
            "merchant": "COMPRA MERCADO CENTRAL",
            "direction": "gasto",
            "amountMinor": 2590,
            "status": "pago",
            "statusDate": "2026-10-20",
            "noteDate": "2026-10-20",
            "source": "extrato-bb-arquivo",
            "lineSignature": "2026-10-20\u001fCOMPRA MERCADO CENTRAL\u001f\u001f\u001f-2590\u001f",
        })
        output = io.StringIO()
        with redirect_stdout(output):
            code, payload = banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
            self.assertEqual(code, 200)
            self.assertEqual(payload["notice"], banksync.CONNECTING)
            self.assertNotIn("itemId", payload)
            self.assertTrue(banksync.work_once(self.conn, transport=self.fixture))
        text = output.getvalue()
        for hidden in (SECRET, "chave-teste", "NOMESECRETO", "9876.54", ITEM, "000.000.000-00"):
            self.assertNotIn(hidden, text)
        accounts = store.rows(self.conn, "SELECT * FROM account WHERE owner_id = ?", (OWNER,))
        self.assertEqual(len(accounts), 2)
        linked = store.one(self.conn, "SELECT * FROM account WHERE id = ?", (manual["id"],))
        self.assertEqual(linked["external_id"], "conta-corrente-1")
        self.assertEqual(linked["currency"], "BRL")
        balance = store.one(self.conn, "SELECT * FROM availability WHERE owner_id = ? AND source = ? AND active = 1", (OWNER, "banco"))
        self.assertEqual(balance["amount_cents"], 987654)
        self.assertEqual(balance["as_of"], "2026-10-26")
        self.assertEqual(store.freshness_label(balance["observed_at"], "2026-10-26"), "atualizado às 07:40")
        entries = store.rows(self.conn, "SELECT * FROM ledger_entry WHERE owner_id = ?", (OWNER,))
        self.assertEqual(len(entries), 3)
        kept = [json.loads(row["payload_json"]) for row in entries if row["external_id"] == "tx-extrato-1"][0]
        self.assertEqual(kept["source"], "extrato-bb-arquivo")
        self.assertEqual(kept["pluggyCategory"], "Groceries")
        fresh = [json.loads(row["payload_json"]) for row in entries if row["external_id"] == "tx-nova-1"][0]
        self.assertEqual(fresh["source"], "pluggy")
        self.assertEqual(fresh["category"], "Moradia")
        self.assertEqual(fresh["categorizationStatus"], "sugerida")
        self.assertEqual(fresh["direction"], "gasto")
        self.assertEqual(store.one(self.conn, "SELECT amount_cents, direction FROM ledger_entry WHERE external_id = ?", ("tx-nova-1",))["amount_cents"], 10000)
        self.assertIsNone(store.one(self.conn, "SELECT id FROM ledger_entry WHERE external_id = ?", ("tx-pendente-1",)))
        bills = store.rows(self.conn, "SELECT * FROM commitment WHERE owner_id = ? AND origin = ?", (OWNER, "banco"))
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0]["total_cents"], 50000)
        self.assertEqual(bills[0]["account_id"], store.one(self.conn, "SELECT id FROM account WHERE external_id = ?", ("cartao-1",))["id"])
        position = store.one(self.conn, "SELECT * FROM investment_position WHERE owner_id = ?", (OWNER,))
        self.assertEqual(position["amount_cents"], 135939)
        self.assertIsNone(position["liquidity_note"])
        self.assertNotIn("NOMESECRETO", position["raw_json"])
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (OWNER,))["n"], 3)
        self.fixture.calls.clear()
        link = store.one(self.conn, "SELECT * FROM bank_link WHERE owner_id = ?", (OWNER,))
        banksync.sync_link(self.conn, link, transport=self.fixture)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (OWNER,))["n"], 3)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ? AND origin = ?", (OWNER, "banco"))["n"], 1)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM account WHERE owner_id = ?", (OWNER,))["n"], 2)
        asked = [url for method, url, body, key in self.fixture.calls if "/v2/transactions" in url and "conta-corrente-1" in url]
        self.assertTrue(asked)
        self.assertIn("from=2026-10-14", asked[0])
        picture = store.describe_balance(self.conn, OWNER, "2026-10-26")
        self.assertNotIn(50000, [line.get("cents") for line in picture["lines"]])
        self.assertTrue(any(line.get("excluded") for line in picture["lines"]))

    def test_webhook_is_fast_idempotent_and_keeps_deleted_rows(self):
        banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
        banksync.work_once(self.conn, transport=self.fixture)
        body = {"event": "transactions/deleted", "eventId": "evt-1", "itemId": ITEM, "transactionIds": ["tx-nova-1"]}
        started = time.perf_counter()
        missing, _ = banksync.accept_webhook(self.conn, "", body)
        self.assertEqual(missing, 401)
        self.assertIsNone(store.one(self.conn, "SELECT event_id FROM bank_event WHERE event_id = ?", ("evt-1",)))
        code, _ = banksync.accept_webhook(self.conn, "cabecalho-teste", body)
        self.assertEqual(code, 200)
        self.assertLess(time.perf_counter() - started, 1)
        again, _ = banksync.accept_webhook(self.conn, "cabecalho-teste", body)
        self.assertEqual(again, 200)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM bank_event WHERE event_id = ?", ("evt-1",))["n"], 1)
        banksync.work_once(self.conn, transport=self.fixture)
        row = store.one(self.conn, "SELECT payload_json FROM ledger_entry WHERE external_id = ?", ("tx-nova-1",))
        self.assertTrue(json.loads(row["payload_json"])["originRemoved"])
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE external_id = ?", ("tx-nova-1",))["n"], 1)
        banksync.accept_webhook(self.conn, "cabecalho-teste", {"event": "item/error", "eventId": "evt-erro", "itemId": ITEM})
        banksync.work_once(self.conn, transport=self.fixture)
        link = store.one(self.conn, "SELECT * FROM bank_link WHERE owner_id = ?", (OWNER,))
        self.assertEqual(link["status"], "LOGIN_ERROR")
        self.assertEqual(banksync._notice(link), banksync.AUTHORIZE)

    def test_disconnect_keeps_history_and_forget_removes_the_item(self):
        banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
        banksync.work_once(self.conn, transport=self.fixture)
        link = store.one(self.conn, "SELECT id FROM bank_link WHERE owner_id = ?", (OWNER,))
        before = store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (OWNER,))["n"]
        code, payload = banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links/%s/disconnect" % link["id"], {})
        self.assertEqual(code, 200)
        self.assertIn("permanece", payload["notice"])
        self.assertEqual(store.one(self.conn, "SELECT status FROM bank_link WHERE id = ?", (link["id"],))["status"], "desligado")
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (OWNER,))["n"], before)
        self.assertTrue(any(method == "DELETE" and ITEM in url for method, url, body, key in self.fixture.calls))
        self.fixture.calls.clear()
        banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
        store.forget_owner(self.conn, self.dir.name, OWNER)
        self.assertTrue(any(method == "DELETE" for method, url, body, key in self.fixture.calls))
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (OWNER,))["n"], 0)

    def test_token_uses_an_opaque_person_and_the_webhook_header(self):
        code, payload = banksync.route(self.conn, OWNER, OWNER, "GET", "/api/bank/connect-token", {})
        self.assertEqual(code, 200)
        self.assertNotIn("@", payload["accessToken"])
        posted = [body for method, url, body, key in self.fixture.calls if url.endswith("/connect_token")][0]
        self.assertEqual(posted["options"]["clientUserId"], banksync.client_user_id(OWNER))
        self.assertNotIn(OWNER, posted["options"]["clientUserId"])
        self.assertTrue(posted["options"]["webhookUrl"].endswith("/api/bank/webhook"))
        remote = pluggy.Client(pluggy.load_credentials(), transport=self.fixture, clock=lambda: 0)
        remote.register_webhook("https://isa.actionhub.com.br/api/bank/webhook", banksync.HEADER, "cabecalho-teste")
        hook = [body for method, url, body, key in self.fixture.calls if url.endswith("/webhooks")][-1]
        self.assertEqual(hook["headers"][banksync.HEADER], "cabecalho-teste")
        self.assertEqual(hook["url"], "https://isa.actionhub.com.br/api/bank/webhook")

    def test_balance_without_documented_update_is_not_written(self):
        self.fixture.drop_updated = True
        banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
        banksync.work_once(self.conn, transport=self.fixture)
        self.assertIsNone(store.one(self.conn, "SELECT id FROM availability WHERE owner_id = ? AND source = ?", (OWNER, "banco")))

    def test_negative_balance_is_not_spendable(self):
        self.fixture.checking_balance = -50
        banksync.route(self.conn, OWNER, OWNER, "POST", "/api/bank/links", {"itemId": ITEM})
        banksync.work_once(self.conn, transport=self.fixture)
        row = store.one(self.conn, "SELECT * FROM availability WHERE owner_id = ? AND source = ? AND active = 1", (OWNER, "banco"))
        self.assertEqual(row["amount_cents"], -5000)
        picture = store.describe_balance(self.conn, OWNER, "2026-10-26")
        line = [item for item in picture["lines"] if item.get("cents") == -5000][0]
        self.assertFalse(line["coversToday"])
        self.assertEqual(line["updatedLabel"], "atualizado às 07:40")
        self.assertEqual(store.freshness_label("2026-10-25T22:15:00.000Z", "2026-10-26"), "atualizado ontem às 19:15")
        self.assertEqual(store.freshness_label("2026-10-20T15:00:00.000Z", "2026-10-26"), "atualizado em 20/10")

    def test_card_spend_counts_once_and_the_week_sees_the_purchases(self):
        card = store.save_account(self.conn, OWNER, {"name": "Cartão", "kind": "cartao", "currency": "BRL", "institution": "Banco", "registration": False})
        for day, cents in (("2026-10-12", 10000), ("2026-10-13", 12000), ("2026-10-14", 8000)):
            store.write_entry(self.conn, OWNER, {
                "accountId": card["id"], "accountKind": "cartao", "direction": "gasto", "nature": "consumo",
                "merchant": "MERCADO", "category": "Alimentação", "amountMinor": cents,
                "status": "pago", "statusDate": day, "noteDate": day, "source": "pluggy",
            })
        store.add_commitment(self.conn, OWNER, {"label": "Fatura do cartão", "totalCents": 30000, "dueOn": "2026-10-20", "origin": "banco", "accountId": card["id"]})
        picture = store.month_picture(self.conn, OWNER, "2026-10", "2026-10-26")
        self.assertEqual(picture["realizedOut"] + picture["forecastOut"], 30000)
        self.assertEqual(store.spending_cents(self.conn, OWNER, "2026-10-12", "2026-10-18"), 30000)
        self.assertNotEqual(picture["realizedOut"] + picture["forecastOut"], 60000)

    def test_bill_payment_pair_partial_and_unpaired(self):
        bank = store.save_account(self.conn, OWNER, {"name": "Corrente", "kind": "corrente", "currency": "BRL", "institution": "Banco", "registration": False})
        card = store.save_account(self.conn, OWNER, {"name": "Cartão", "kind": "cartao", "currency": "BRL", "institution": "Banco", "registration": False})
        bill = store.add_commitment(self.conn, OWNER, {"label": "Fatura do cartão", "totalCents": 30000, "dueOn": "2026-10-20", "origin": "banco", "accountId": card["id"]})
        self.conn.execute("UPDATE commitment SET origin = ? WHERE id = ?", ("banco", bill["id"]))
        out = store.write_entry(self.conn, OWNER, {
            "accountId": bank["id"], "direction": "gasto", "nature": "consumo", "merchant": "PAGAMENTO FATURA",
            "amountMinor": 30000, "status": "pago", "statusDate": "2026-10-18", "noteDate": "2026-10-18", "source": "pluggy", "externalId": "pag-1",
        })
        inn = store.write_entry(self.conn, OWNER, {
            "accountId": card["id"], "accountKind": "cartao", "direction": "ganho", "nature": "ganho", "merchant": "PAGAMENTO RECEBIDO",
            "amountMinor": 30000, "status": "recebido", "statusDate": "2026-10-19", "noteDate": "2026-10-19", "source": "pluggy", "externalId": "cred-1",
        })
        banksync._settle_payments(self.conn, OWNER)
        pair_out = json.loads(store.one(self.conn, "SELECT payload_json FROM ledger_entry WHERE id = ?", (out["id"],))["payload_json"])
        pair_in = json.loads(store.one(self.conn, "SELECT payload_json FROM ledger_entry WHERE id = ?", (inn["id"],))["payload_json"])
        self.assertEqual(pair_out["nature"], "transferencia")
        self.assertEqual(pair_in["nature"], "transferencia")
        self.assertEqual(pair_out["transferPair"], inn["id"])
        paid = store.one(self.conn, "SELECT remaining_cents FROM commitment WHERE id = ?", (bill["id"],))
        self.assertEqual(paid["remaining_cents"], 0)
        picture = store.month_picture(self.conn, OWNER, "2026-10", "2026-10-26")
        self.assertEqual(picture["realizedOut"] + picture["forecastOut"], 0)

        other = store.save_account(self.conn, "pessoa-parcial", {"name": "Cartão", "kind": "cartao", "currency": "BRL", "institution": "Banco", "registration": False})
        partial_bill = store.add_commitment(self.conn, "pessoa-parcial", {"label": "Fatura do cartão", "totalCents": 30000, "dueOn": "2026-10-20", "origin": "banco", "accountId": other["id"]})
        self.conn.execute("UPDATE commitment SET origin = ? WHERE id = ?", ("banco", partial_bill["id"]))
        store.write_entry(self.conn, "pessoa-parcial", {
            "accountId": other["id"], "direction": "ganho", "nature": "ganho", "merchant": "PAGAMENTO",
            "amountMinor": 10000, "status": "recebido", "statusDate": "2026-10-18", "noteDate": "2026-10-18", "source": "pluggy", "externalId": "parcial-1",
        })
        banksync._settle_payments(self.conn, "pessoa-parcial")
        left = store.one(self.conn, "SELECT remaining_cents FROM commitment WHERE id = ?", (partial_bill["id"],))
        self.assertEqual(left["remaining_cents"], 20000)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ?", ("pessoa-parcial",))["n"], 1)
        marked = json.loads(store.one(self.conn, "SELECT payload_json FROM ledger_entry WHERE external_id = ?", ("parcial-1",))["payload_json"])
        self.assertEqual(marked["nature"], "pagamento_fatura")
        month = store.month_picture(self.conn, "pessoa-parcial", "2026-10", "2026-10-26")
        self.assertEqual(month["realizedOut"] + month["forecastOut"], 30000)
        self.assertEqual(store.spending_cents(self.conn, "pessoa-parcial", "2026-10-01", "2026-10-31"), 0)

    def test_same_day_amounts_link_both_ways_by_quantity(self):
        account = store.save_account(self.conn, OWNER, {"name": "Corrente", "kind": "corrente", "currency": "BRL", "institution": "Banco", "bankCode": "001", "registration": False})
        for index in (1, 2):
            store.write_entry(self.conn, OWNER, {
                "accountId": account["id"], "direction": "gasto", "nature": "consumo", "merchant": "UBER VIAGEM " + str(index),
                "amountMinor": 500, "status": "pago", "statusDate": "2026-10-20", "noteDate": "2026-10-20",
                "source": "extrato-bb-arquivo", "lineSignature": "2026-10-20 UBER VIAGEM " + str(index),
            })
        rows = [
            {"id": "p1", "description": "UBER VIAGEM 1", "amount": -5, "date": "2026-10-20T03:00:00.000Z", "currencyCode": "BRL", "status": "POSTED", "type": "DEBIT", "accountId": "ext-conta"},
            {"id": "p2", "description": "UBER VIAGEM 2", "amount": -5, "date": "2026-10-20T03:00:00.000Z", "currencyCode": "BRL", "status": "POSTED", "type": "DEBIT", "accountId": "ext-conta"},
            {"id": "p3", "description": "UBER VIAGEM 3", "amount": -5, "date": "2026-10-20T03:00:00.000Z", "currencyCode": "BRL", "status": "POSTED", "type": "DEBIT", "accountId": "ext-conta"},
        ]
        self.conn.execute("UPDATE account SET external_id = ? WHERE id = ?", ("ext-conta", account["id"]))
        banksync._apply_transactions(self.conn, {"owner_id": OWNER, "id": "link"}, rows, None, store.one(self.conn, "SELECT * FROM account WHERE id = ?", (account["id"],)), "2026-01-01")
        linked = store.rows(self.conn, "SELECT external_id FROM ledger_entry WHERE owner_id = ? AND external_id IS NOT NULL", (OWNER,))
        self.assertEqual(len(linked), 3)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (OWNER,))["n"], 3)
        kept = store.rows(self.conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ? AND source = ?", (OWNER, "extrato-bb-arquivo"))
        self.assertEqual(len(kept), 2)

        later = store.save_account(self.conn, "pessoa-depois", {"name": "Corrente", "kind": "corrente", "currency": "BRL", "institution": "Banco", "registration": False})
        for index, external in ((1, "ja-1"), (2, "ja-2")):
            store.write_entry(self.conn, "pessoa-depois", {
                "accountId": later["id"], "direction": "gasto", "nature": "consumo", "merchant": "PADARIA CENTRAL " + str(index),
                "amountMinor": 500, "status": "pago", "statusDate": "2026-10-21", "noteDate": "2026-10-21",
                "source": "pluggy", "externalId": external,
            })
        movements = []
        for index in (1, 2):
            movements.append({
                "signature": "2026-10-21 PADARIA CENTRAL " + str(index),
                "cents": -500,
                "direction": "saida",
                "date": "2026-10-21",
                "label": "PADARIA CENTRAL " + str(index),
                "nature": "a_conferir",
                "accountId": later["id"],
            })
        store.import_batch(self.conn, "pessoa-depois", {"batchKey": "lote-depois", "origin": "extrato-bb-arquivo", "movements": movements})
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", ("pessoa-depois",))["n"], 2)
        signed = store.rows(self.conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ?", ("pessoa-depois",))
        self.assertEqual(sum(1 for row in signed if json.loads(row["payload_json"]).get("lineSignature")), 2)


class PostgresBankTests(unittest.TestCase):
    def setUp(self):
        import test_pg
        self.name = "isa_banco_" + uuid.uuid4().hex[:12]
        self.url = test_pg.prepare(self.name)
        self.old = os.environ.get("ISA_REFERENCE_DATE")
        os.environ["ISA_REFERENCE_DATE"] = "2026-10-26"
        os.environ["ISA_ENV"] = "lab"
        self.conn = store.connect(self.url)

    def tearDown(self):
        self.conn.close()
        pluggy.set_credentials(None)
        os.environ.pop("ISA_PLUGGY_ENABLED", None)
        os.environ.pop("ISA_PLUGGY_ALLOWED_SUBS", None)
        import psycopg
        import test_pg
        admin = psycopg.connect(test_pg.ADMIN, autocommit=True)
        admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (self.name,))
        admin.execute("DROP DATABASE IF EXISTS " + self.name)
        admin.close()
        if self.old is None:
            os.environ.pop("ISA_REFERENCE_DATE", None)
        else:
            os.environ["ISA_REFERENCE_DATE"] = self.old

    def test_schema_and_webhook_unique(self):
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 14)
        os.environ["ISA_PLUGGY_ENABLED"] = "1"
        os.environ["ISA_PLUGGY_ALLOWED_SUBS"] = OWNER
        pluggy.set_credentials({"clientId": "id-teste", "clientSecret": SECRET, "webhookSecret": "cabecalho-teste"})
        self.conn.execute(
            "INSERT INTO bank_link (id, owner_id, provider, item_id, connector_name, status, status_detail, consent_expires_at, last_synced_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("link-1", OWNER, "pluggy", ITEM, "MeuPluggy", "UPDATED", "", None, None, store.now(), store.now()),
        )
        body = {"event": "item/updated", "eventId": "evt-pg", "itemId": ITEM}
        self.assertEqual(banksync.accept_webhook(self.conn, "cabecalho-teste", body)[0], 200)
        self.assertEqual(banksync.accept_webhook(self.conn, "cabecalho-teste", body)[0], 200)
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM bank_event")["n"], 1)
        self.assertEqual(banksync.accept_webhook(self.conn, "errado", body)[0], 401)


if __name__ == "__main__":
    unittest.main()
