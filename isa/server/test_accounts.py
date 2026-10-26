"""Contas, moeda e isolamento. Usa SQLite temporário e, se existir, o PostgreSQL local de ensaio."""

import json
import os
import tempfile
import unittest

import store

os.environ["ISA_ENV"] = "lab"


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))
        self.owner = "pessoa-contas"
        self.other = "pessoa-outra"

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_schema_and_legacy_records_stay_unassigned(self):
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 11)
        store.save_availability(self.conn, self.owner, {"amountCents": 150000, "asOf": "2026-10-16", "protectedCents": 0, "source": "declarada"})
        commitment = store.add_commitment(self.conn, self.owner, {"label": "Luz", "totalCents": 8000, "dueOn": "2026-10-20"})
        page = store.home(self.conn, self.owner)
        self.assertEqual(page["context"]["scope"], "all")
        self.assertIsNone(store.one(self.conn, "SELECT account_id FROM availability WHERE owner_id = ?", (self.owner,))["account_id"])
        self.assertIsNone(commitment["account_id"])
        self.assertEqual(page["context"]["unassignedCommitments"], 1)
        self.assertEqual(page["overview"]["informed"]["cents"], 150000)

    def test_create_edit_inactivate_and_lock_currency(self):
        first = store.save_account(self.conn, self.owner, {"name": "Corrente", "institution": "Banco do Brasil", "kind": "corrente", "currency": "BRL"})
        second = store.save_account(self.conn, self.owner, {"name": "Poupança", "institution": "Caixa", "kind": "poupanca", "currency": "BRL"})
        foreign = store.save_account(self.conn, self.owner, {"name": "Viagem", "institution": "Outro", "kind": "corrente", "currency": "USD"})
        self.assertEqual(foreign["currency"], "USD")
        store.add_commitment(self.conn, self.owner, {"label": "Hotel", "totalCents": 10000, "dueOn": "2026-10-22", "accountId": foreign["id"]})
        with self.assertRaises(ValueError):
            store.save_account(self.conn, self.owner, {"id": foreign["id"], "edit": True, "name": "Viagem", "currency": "EUR", "kind": "corrente"})
        edited = store.save_account(self.conn, self.owner, {"id": second["id"], "edit": True, "name": "Reserva", "institution": "Caixa", "kind": "poupanca", "currency": "BRL", "status": "inactive"})
        self.assertEqual(edited["status"], "inactive")
        self.assertEqual(first["id"], store.owned(self.conn, "account", self.owner, first["id"])["id"])

    def test_context_does_not_copy_personal_balance_or_mix_currency(self):
        brl = store.save_account(self.conn, self.owner, {"name": "Corrente", "currency": "BRL", "kind": "corrente"})
        usd = store.save_account(self.conn, self.owner, {"name": "Dólar", "currency": "USD", "kind": "corrente"})
        store.save_availability(self.conn, self.owner, {"amountCents": 50000, "asOf": "2026-10-16", "source": "declarada"})
        store.add_commitment(self.conn, self.owner, {"label": "Aluguel", "totalCents": 20000, "dueOn": "2026-10-18", "accountId": brl["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Hotel", "totalCents": 3000, "dueOn": "2026-10-19", "accountId": usd["id"]})
        store.add_commitment(self.conn, self.owner, {"label": "Solto", "totalCents": 1000, "dueOn": "2026-10-21"})
        everything = store.home(self.conn, self.owner, account="all")
        self.assertEqual(everything["overview"]["kind"], "moedas")
        one = store.home(self.conn, self.owner, account=brl["id"])
        self.assertIsNone(one["overview"].get("informed"))
        self.assertGreater(one["overview"].get("outsideCommitments") or 0, 0)
        self.assertNotIn("Hotel", [item["label"] for item in one["commitments"]])
        again = store.home(self.conn, self.owner, account=brl["id"])
        self.assertEqual(again["context"]["accountId"], brl["id"])
        with self.assertRaises(ValueError):
            store.import_statement(self.conn, self.owner, {"account": {"id": usd["id"]}, "batchKey": "lote", "origin": "extrato-bb-arquivo", "movements": []})

    def test_investment_is_not_spendable_margin(self):
        item = store.save_account(self.conn, self.owner, {"name": "Aplicação", "kind": "investimento", "currency": "BRL", "liquid": False})
        store.save_availability(self.conn, self.owner, {"amountCents": 90000, "asOf": "2026-10-16", "accountId": item["id"], "source": "declarada"})
        page = store.home(self.conn, self.owner, account=item["id"])
        self.assertFalse(page["projection"]["complete"])
        self.assertEqual(page["overview"]["position"]["amount_cents"], 90000)
        self.assertEqual(page["overview"]["situation"]["kind"], "partial")

    def test_other_person_cannot_use_the_account(self):
        item = store.save_account(self.conn, self.owner, {"name": "Corrente", "currency": "BRL"})
        with self.assertRaises(ValueError):
            store.save_availability(self.conn, self.other, {"amountCents": 100, "asOf": "2026-10-16", "accountId": item["id"]})
        self.assertIsNone(store.owned(self.conn, "account", self.other, item["id"]))
        foreign = store.account_context(self.conn, self.other, item["id"], persist=True)
        self.assertEqual(foreign["scope"], "all")
        self.assertIn("não está disponível", foreign["notice"])

    def test_assign_keeps_amount_and_preference_is_per_person(self):
        item = store.save_account(self.conn, self.owner, {"name": "Corrente", "currency": "BRL"})
        commitment = store.add_commitment(self.conn, self.owner, {"label": "Luz", "totalCents": 8000, "dueOn": "2026-10-20"})
        preview = store.assign_records(self.conn, self.owner, {"kind": "commitment", "ids": [commitment["id"]], "accountId": item["id"]})
        self.assertFalse(preview["saved"])
        saved = store.assign_records(self.conn, self.owner, {"kind": "commitment", "ids": [commitment["id"]], "accountId": item["id"], "confirm": True})
        self.assertTrue(saved["saved"])
        again = store.assign_records(self.conn, self.owner, {"kind": "commitment", "ids": [commitment["id"]], "accountId": item["id"], "confirm": True})
        self.assertEqual(again["changed"], 1)
        row = store.owned(self.conn, "commitment", self.owner, commitment["id"])
        self.assertEqual(row["total_cents"], 8000)
        self.assertEqual(row["account_id"], item["id"])
        store.select_account(self.conn, self.owner, {"context": item["id"]})
        store.select_account(self.conn, self.other, {"context": "all"})
        self.assertEqual(store.account_context(self.conn, self.owner, None)["accountId"], item["id"])
        self.assertEqual(store.account_context(self.conn, self.other, None)["scope"], "all")

    def test_registration_requires_three_fields_and_keeps_number(self):
        with self.assertRaises(ValueError):
            store.save_account(self.conn, self.owner, {"registration": True, "institution": "Banco do Brasil", "kind": "corrente"})
        created = store.save_account(self.conn, self.owner, {
            "id": "conta-prova",
            "registration": True,
            "institution": "Banco do Brasil S.A.",
            "bankCode": "001",
            "accountNumber": "0012345-6",
            "kind": "corrente",
        })
        self.assertEqual(created["account_number"], "0012345-6")
        self.assertEqual(created["currency"], "BRL")
        self.assertNotEqual(created["name"], "")
        again = store.save_account(self.conn, self.owner, {
            "id": "conta-prova",
            "registration": True,
            "institution": "Outro banco",
            "accountNumber": "999",
            "kind": "poupanca",
        })
        self.assertEqual(again["account_number"], "0012345-6")
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM account WHERE owner_id = ?", (self.owner,))["n"], 1)
        legacy = store.save_account(self.conn, self.owner, {"name": "Antiga", "currency": "BRL"})
        self.assertEqual(legacy["account_number"], "")
        self.assertIsNotNone(store.owned(self.conn, "account", self.owner, legacy["id"]))

    def test_contacts_and_profile_stay_with_the_owner(self):
        import ai
        with self.assertRaises(ValueError):
            store.save_account(self.conn, self.owner, {
                "registration": True,
                "institution": "Caixa Econômica Federal",
                "bankCode": "104",
                "accountNumber": "000123",
                "kind": "poupanca",
                "bankEmail": "ruim",
            })
        account = store.save_account(self.conn, self.owner, {
            "registration": True,
            "institution": "Caixa Econômica Federal",
            "bankCode": "104",
            "accountNumber": "000123",
            "kind": "poupanca",
            "contacts": [
                {"name": "Ana", "role": "gerente_conta", "email": "ana@caixa.example", "scope": "conta", "primary": True},
                {"name": "Bruno", "role": "gerente_agencia", "email": "bruno@caixa.example", "scope": "agencia"},
            ],
        })
        public = store._public_account(self.conn, self.owner, account)
        self.assertEqual(public["contactCount"], 2)
        self.assertEqual(public["numberMasked"].endswith("23"), True)
        self.assertNotIn("ana@caixa.example", json.dumps(ai.context(self.conn, self.owner)))
        hidden = store.account_detail(self.conn, self.other, account["id"])
        self.assertIsNone(hidden)
        store.save_profile(self.conn, self.owner, {"displayName": "Pessoa da prova"})
        self.assertEqual(store.profile_public(self.conn, self.owner)["displayName"], "Pessoa da prova")
        self.assertEqual(store.profile_public(self.conn, self.other)["displayName"], "")
        store.remember_verified_profile(self.conn, self.other, {"name": "outro@email.com", "email": "outro@email.com"})
        self.assertEqual(store.profile_public(self.conn, self.other)["displayName"], "")
        self.assertEqual(store.profile_public(self.conn, self.other)["accessLabel"], "outro@email.com")

    def test_backup_includes_new_metadata(self):
        self.assertIn("account_preference", store.DATA_TABLES)
        self.assertIn("account_preference", store.OWNER_TABLES)
        self.assertIn("account_contact", store.DATA_TABLES)
        self.assertIn("person_profile", store.OWNER_TABLES)
        store.save_account(self.conn, self.owner, {"name": "Corrente", "currency": "EUR", "institution": "Informada"})
        store.select_account(self.conn, self.owner, {"context": "all"})
        dest = os.path.join(tempfile.gettempdir(), "isa-copia-" + store._id())
        copied = store.backup_dir(self.tmp.name, dest)
        self.assertTrue(copied["createdAt"])
        restored = store.connect(os.path.join(dest, "isa.sqlite"))
        self.assertEqual(restored.execute("SELECT currency FROM account").fetchone()["currency"], "EUR")
        restored.close()
        import shutil
        shutil.rmtree(dest, ignore_errors=True)

    def test_continuous_registration_keeps_legacy_fields_and_agency_name(self):
        created = store.save_account(self.conn, self.owner, {
            "id": "conta-continua",
            "registration": True,
            "institution": "Banco do Brasil S.A.",
            "bankCode": "001",
            "accountNumber": "0012345-6",
            "kind": "corrente",
            "currency": "BRL",
            "agency": "0123-4",
            "agencyName": "Agência Centro",
            "contacts": [{"name": "", "role": "", "email": "", "phone": ""}],
        })
        public = store._public_account(self.conn, self.owner, created)
        self.assertEqual(public["accountNumber"], "0012345-6")
        self.assertEqual(public["agency"], "0123-4")
        self.assertEqual(public["agencyName"], "Agência Centro")
        self.assertEqual(public["bankCode"], "001")
        self.assertEqual(public["institution"], "Banco do Brasil S.A.")
        self.assertEqual(public["contacts"], [])
        again = store.save_account(self.conn, self.owner, {
            "id": "conta-continua",
            "registration": True,
            "institution": "Banco do Brasil S.A.",
            "bankCode": "001",
            "accountNumber": "0012345-6",
            "kind": "corrente",
        })
        self.assertEqual(again["id"], created["id"])
        self.assertEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM account WHERE owner_id = ?", (self.owner,))["n"], 1)
        legacy = store.save_account(self.conn, self.owner, {
            "name": "Antiga",
            "institution": "Banco da Família",
            "currency": "BRL",
            "kind": "corrente",
            "accountNumber": "999",
            "accountDigit": "7",
            "country": "Brasil",
            "nickname": "Casa",
            "agencyEmail": "agencia@exemplo.com",
        })
        kept = store.save_account(self.conn, self.owner, {
            "id": legacy["id"],
            "edit": True,
            "registration": True,
            "institution": "Banco da Família",
            "bankCode": "",
            "accountNumber": "999",
            "kind": "corrente",
            "agencyName": "Centro",
        })
        self.assertEqual(kept["account_digit"], "7")
        self.assertEqual(kept["nickname"], "Casa")
        self.assertEqual(kept["country"], "Brasil")
        self.assertEqual(kept["agency_email"], "agencia@exemplo.com")
        self.assertEqual(kept["agency_name"], "Centro")
        with self.assertRaises(ValueError):
            store.save_account(self.conn, self.owner, {
                "registration": True,
                "institution": "Santander",
                "bankCode": "001",
                "accountNumber": "1",
                "kind": "corrente",
            })
        self.assertIsNone(store.owned(self.conn, "account", self.other, created["id"]))

    def test_str_catalog_accepts_code_ispb_and_keeps_old_name(self):
        import catalog_str
        summary = catalog_str.summary()
        self.assertGreater(summary["selectable"], 400)
        self.assertGreater(summary["withCode"], 400)
        self.assertEqual(summary["obtainedOn"], "2026-10-26")
        nu = catalog_str.BY_CODE["260"][0]
        created = store.save_account(self.conn, self.owner, {
            "registration": True,
            "institution": nu["name"],
            "bankCode": "260",
            "accountNumber": "2601",
            "kind": "corrente",
        })
        self.assertEqual(created["institution"], nu["name"])
        self.assertEqual(created["bank_ispb"], nu["ispb"])
        self.assertNotIn("Nubank", created["institution"])
        bare = next(item for item in catalog_str.CATALOG if item["selectable"] and not item["code"])
        without = store.save_account(self.conn, self.owner, {
            "registration": True,
            "institution": bare["name"],
            "bankCode": "",
            "bankIspb": bare["ispb"],
            "accountNumber": "sem-codigo",
            "kind": "investimento",
        })
        self.assertEqual(without["bank_code"], "")
        self.assertEqual(without["bank_ispb"], bare["ispb"])
        with self.assertRaises(ValueError):
            store.save_account(self.conn, self.owner, {
                "registration": True,
                "institution": bare["name"],
                "bankCode": "001",
                "bankIspb": bare["ispb"],
                "accountNumber": "inventado",
                "kind": "corrente",
            })
        old = store.save_account(self.conn, self.owner, {
            "name": "Antiga Nubank",
            "institution": "Nubank",
            "bankCode": "260",
            "currency": "BRL",
            "kind": "corrente",
            "accountNumber": "antiga",
        })
        kept = store.save_account(self.conn, self.owner, {
            "id": old["id"],
            "edit": True,
            "registration": True,
            "institution": "Nubank",
            "bankCode": "260",
            "accountNumber": "antiga",
            "kind": "corrente",
            "agencyName": "Agência antiga",
        })
        self.assertEqual(kept["institution"], "Nubank")
        self.assertEqual(kept["agency_name"], "Agência antiga")
        asked = store.save_catalog_request(self.conn, self.owner, {"query": "Banco que não está na lista"})
        self.assertTrue(asked["ok"])
        self.assertEqual(store.one(self.conn, "SELECT query FROM catalog_request WHERE owner_id = ?", (self.owner,))["query"], "Banco que não está na lista")


class PostgresAccountTests(unittest.TestCase):
    def setUp(self):
        import test_pg
        self.name = "isa_contas_" + store._id()[:12]
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

    def test_postgres_keeps_ids_and_separates_people(self):
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 11)
        owner = "pessoa-pg"
        other = "pessoa-pg-2"
        legacy = store.add_commitment(self.conn, owner, {"label": "Antigo", "totalCents": 4000, "dueOn": "2026-10-18"})
        account = store.save_account(self.conn, owner, {"name": "Corrente", "currency": "BRL", "institution": "Banco informado"})
        usd = store.save_account(self.conn, owner, {"name": "Dólar", "currency": "USD"})
        self.assertEqual(store.owned(self.conn, "commitment", owner, legacy["id"])["total_cents"], 4000)
        self.assertIsNone(store.owned(self.conn, "commitment", owner, legacy["id"])["account_id"])
        page = store.home(self.conn, owner, account=usd["id"])
        self.assertNotIn("Antigo", [item["label"] for item in page["commitments"]])
        self.assertEqual(store.account_context(self.conn, other, account["id"], persist=True)["scope"], "all")
        with self.assertRaises(ValueError):
            store.import_statement(self.conn, owner, {"account": {"id": usd["id"]}, "batchKey": "nao", "origin": "extrato-bb-arquivo", "movements": []})

    def test_postgres_migrates_from_schema_7_and_keeps_catalog_account(self):
        import catalog_str
        import psycopg
        import shutil
        import tempfile
        import test_pg
        self.conn.close()
        raw = psycopg.connect(self.url, autocommit=True)
        raw.execute("DROP TABLE IF EXISTS account")
        raw.execute("DELETE FROM schema_migration")
        raw.execute(
            """CREATE TABLE account (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              name TEXT NOT NULL,
              currency TEXT NOT NULL,
              created_at TEXT NOT NULL,
              institution TEXT NOT NULL DEFAULT '',
              kind TEXT NOT NULL DEFAULT 'corrente',
              intake TEXT NOT NULL DEFAULT 'arquivo',
              status TEXT NOT NULL DEFAULT 'active',
              liquid INTEGER NOT NULL DEFAULT 1,
              updated_at TEXT,
              account_number TEXT NOT NULL DEFAULT '',
              country TEXT NOT NULL DEFAULT '',
              bank_code TEXT NOT NULL DEFAULT '',
              agency TEXT NOT NULL DEFAULT '',
              account_digit TEXT NOT NULL DEFAULT '',
              nickname TEXT NOT NULL DEFAULT '',
              bank_email TEXT NOT NULL DEFAULT '',
              agency_email TEXT NOT NULL DEFAULT '',
              agency_phone TEXT NOT NULL DEFAULT ''
            )"""
        )
        raw.execute(
            """INSERT INTO account (id, owner_id, name, currency, created_at, institution, account_number, bank_code)
               VALUES ('conta-sete', 'pessoa-sete', 'Antiga', 'BRL', '2026-10-01T00:00:00Z', 'Banco da Família', '0012345-6', '')"""
        )
        raw.execute("INSERT INTO schema_migration (version) VALUES (7)")
        raw.close()
        self.conn = store.connect(self.url)
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 11)
        kept = store.one(self.conn, "SELECT * FROM account WHERE id = ?", ("conta-sete",))
        self.assertEqual(kept["owner_id"], "pessoa-sete")
        self.assertEqual(kept["account_number"], "0012345-6")
        self.assertEqual(kept["agency_name"], "")
        self.assertEqual(kept["bank_ispb"], "")
        nu = catalog_str.BY_CODE["077"][0]
        created = store.save_account(self.conn, "pessoa-sete", {
            "registration": True,
            "institution": nu["name"],
            "bankCode": "077",
            "accountNumber": "0771",
            "kind": "poupanca",
            "agency": "0123-4",
            "agencyName": "Agência Centro",
        })
        self.conn.close()
        reread = store.connect(self.url)
        row = store.one(reread, "SELECT institution, agency, agency_name, bank_code, bank_ispb FROM account WHERE id = ?", (created["id"],))
        self.assertEqual(row["institution"], nu["name"])
        self.assertEqual(row["agency"], "0123-4")
        self.assertEqual(row["agency_name"], "Agência Centro")
        self.assertNotEqual(nu["name"], "Inter")
        reread.execute("UPDATE account SET nickname = %s WHERE id = %s", ("Casa", created["id"]))
        still = store.one(reread, "SELECT agency_name, institution, nickname FROM account WHERE id = ?", (created["id"],))
        self.assertEqual(still["agency_name"], "Agência Centro")
        self.assertEqual(still["institution"], nu["name"])
        self.assertEqual(still["nickname"], "Casa")
        folder = tempfile.mkdtemp(prefix="isa-contas-pg-")
        try:
            store.logical_dump(reread, folder)
            restored = store.connect(test_pg.prepare("isa_contas_restore_" + store._id()[:8]))
            store.logical_restore(restored, folder)
            back = store.one(restored, "SELECT agency_name, institution, bank_code FROM account WHERE id = ?", (created["id"],))
            self.assertEqual(back["agency_name"], "Agência Centro")
            self.assertEqual(back["institution"], nu["name"])
            self.assertEqual(back["bank_code"], "077")
            restored.close()
        finally:
            reread.close()
            shutil.rmtree(folder, ignore_errors=True)
            self.conn = store.connect(self.url)


if __name__ == "__main__":
    unittest.main()
