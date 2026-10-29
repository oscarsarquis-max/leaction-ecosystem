"""Conexão por pool e bootstrap único. PostgreSQL só no container local."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import psycopg
from psycopg.pq import TransactionStatus
from psycopg_pool import PoolTimeout

import ai
import pgconn
import prod_serve
import store
import wsgi_app
from test_pg import call, prepare


class BootstrapTests(unittest.TestCase):
    def tearDown(self):
        pgconn.close_pool()

    def test_request_does_not_migrate_or_reread_erasures(self):
        url = prepare("isa_conn_req")
        store.connect(url, bootstrap=True).close()
        store.bootstrap_counts["migrate"] = 0
        store.bootstrap_counts["erasure"] = 0
        reads = {"n": 0}
        real = store.erased_owners

        def counting():
            reads["n"] += 1
            return real()

        old_url = os.environ.get("ISA_DATABASE_URL")
        old_env = os.environ.get("ISA_ENV")
        old_origin = os.environ.get("ISA_ORIGIN")
        os.environ["ISA_DATABASE_URL"] = url
        os.environ["ISA_ENV"] = "production"
        os.environ["ISA_ORIGIN"] = "http://127.0.0.1:8099"
        try:
            with patch.object(store, "erased_owners", counting):
                app = wsgi_app.build_app(tempfile.mkdtemp(prefix="isa-conn-"), lambda: 0)
                code, body, headers = call(app, "GET", "/api/ready")
            self.assertEqual(code, 200)
            self.assertEqual(body["schema"], 14)
            self.assertEqual(store.bootstrap_counts["migrate"], 0)
            self.assertEqual(store.bootstrap_counts["erasure"], 0)
            self.assertEqual(reads["n"], 0)
            mapped = dict(headers)
            self.assertIn("Server-Timing", mapped)
            self.assertTrue(mapped["Server-Timing"].startswith("app;dur="))
        finally:
            if old_url is None:
                os.environ.pop("ISA_DATABASE_URL", None)
            else:
                os.environ["ISA_DATABASE_URL"] = old_url
            if old_env is None:
                os.environ.pop("ISA_ENV", None)
            else:
                os.environ["ISA_ENV"] = old_env
            if old_origin is None:
                os.environ.pop("ISA_ORIGIN", None)
            else:
                os.environ["ISA_ORIGIN"] = old_origin

    def test_unreadable_ledger_stops_the_process(self):
        folder = tempfile.mkdtemp(prefix="isa-ledger-")
        old_url = os.environ.pop("ISA_DATABASE_URL", None)
        old_env = os.environ.pop("ISA_ENV", None)
        try:
            with patch.object(store, "erased_owners", side_effect=store.LedgerError("Não foi possível ler o livro de exclusões.")):
                with self.assertRaises(store.LedgerError):
                    store.connect(os.path.join(folder, "isa.sqlite"), bootstrap=True)
                with self.assertRaises(SystemExit):
                    prod_serve.bootstrap_or_exit(folder)
        finally:
            if old_url is not None:
                os.environ["ISA_DATABASE_URL"] = old_url
            if old_env is not None:
                os.environ["ISA_ENV"] = old_env

    def test_restore_keeps_a_forgotten_person_out(self):
        url = prepare("isa_conn_live")
        restore = prepare("isa_conn_back")
        ledger = tempfile.mktemp(prefix="isa-conn-ledger-", suffix=".jsonl")
        old = os.environ.get("ISA_ERASURE_LEDGER")
        os.environ["ISA_ERASURE_LEDGER"] = ledger
        conn = store.connect(url, bootstrap=True)
        try:
            kept = store.ensure_identity(conn, "fica-005")
            gone = store.ensure_identity(conn, "sai-005")
            store.add_commitment(conn, kept, {"label": "Luz", "totalCents": 1000, "dueOn": "2026-10-18", "origin": "ensaio"})
            store.add_commitment(conn, gone, {"label": "Segredo", "totalCents": 900, "dueOn": "2026-10-19", "origin": "ensaio"})
            folder = tempfile.mkdtemp(prefix="isa-conn-dump-")
            store.logical_dump(conn, folder)
            store.forget_owner(conn, None, gone)
            self.assertEqual(store.one(conn, "SELECT COUNT(*) AS n FROM identity WHERE owner_id = ?", (gone,))["n"], 0)
            self.assertIsNone(store.read_session(conn, "sessao-que-nao-existe"))
            later = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0).isoformat()
            conn.execute(
                "INSERT INTO app_session (id, owner_id, sub, expires_at, created_at) VALUES (?,?,?,?,?)",
                ("sessao-plantada", gone, "sai-005", later, store.now()),
            )
            self.assertIsNone(store.read_session(conn, "sessao-plantada"))
            restored = store.connect(restore, bootstrap=True)
            result = store.logical_restore(restored, folder)
            self.assertTrue(result["erasuresReapplied"])
            self.assertEqual(store.one(restored, "SELECT COUNT(*) AS n FROM identity WHERE owner_id = ?", (gone,))["n"], 0)
            self.assertEqual(store.one(restored, "SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ?", (kept,))["n"], 1)
            home = store.home(restored, gone)
            self.assertEqual(home["commitments"], [])
            restored.close()
        finally:
            conn.close()
            if old is None:
                os.environ.pop("ISA_ERASURE_LEDGER", None)
            else:
                os.environ["ISA_ERASURE_LEDGER"] = old

    def test_returned_connection_is_clean_and_pool_timeout_is_503(self):
        url = prepare("isa_conn_pool")
        pgconn.enable_pool(url, min_size=1, max_size=1, timeout=0.4)
        try:
            first = store.connect(url, bootstrap=True)
            owner = store.ensure_identity(first, "pool-005")
            try:
                first.execute("BEGIN IMMEDIATE")
                first.execute(
                    "INSERT INTO feedback (id, owner_id, body, created_at) VALUES (?,?,?,?)",
                    ("fb-sujo", owner, "nao pode ficar", store.now()),
                )
                raise RuntimeError("meio do pedido")
            except RuntimeError:
                first.close()
            second = store.connect(url, bootstrap=False)
            self.assertTrue(second.raw.autocommit)
            self.assertEqual(second.raw.info.transaction_status, TransactionStatus.IDLE)
            self.assertEqual(store.one(second, "SELECT COUNT(*) AS n FROM feedback WHERE id = ?", ("fb-sujo",))["n"], 0)
            held = second
            with self.assertRaises(PoolTimeout):
                store.connect(url, bootstrap=False)
            held.close()
            old_url = os.environ.get("ISA_DATABASE_URL")
            old_env = os.environ.get("ISA_ENV")
            old_origin = os.environ.get("ISA_ORIGIN")
            os.environ["ISA_DATABASE_URL"] = url
            os.environ["ISA_ENV"] = "production"
            os.environ["ISA_ORIGIN"] = "http://127.0.0.1:8099"
            try:
                app = wsgi_app.build_app(tempfile.mkdtemp(prefix="isa-pool-"), lambda: 0)
                with patch.object(store, "connect", side_effect=PoolTimeout("couldn't get a connection after 0.40 sec")):
                    code, body, _headers = call(app, "GET", "/api/ready")
                self.assertEqual(code, 503)
                self.assertEqual(body, {"ready": False})
                with patch.object(store, "connect", side_effect=psycopg.OperationalError("db")):
                    code, body, _headers = call(app, "POST", "/api/commitments", {"label": "x"})
                self.assertEqual(code, 503)
                self.assertEqual(body["error"], "A base não está disponível.")
                with patch.object(wsgi_app, "_owner", return_value=("pessoa-005", None, None)):
                    with patch.object(wsgi_app, "_route", side_effect=psycopg.OperationalError("write")):
                        code, body, _headers = call(app, "POST", "/api/commitments", {"label": "x"})
                self.assertEqual(code, 503)
                self.assertEqual(body["error"], "Não foi possível salvar. Tente de novo.")
            finally:
                if old_url is None:
                    os.environ.pop("ISA_DATABASE_URL", None)
                else:
                    os.environ["ISA_DATABASE_URL"] = old_url
                if old_env is None:
                    os.environ.pop("ISA_ENV", None)
                else:
                    os.environ["ISA_ENV"] = old_env
                if old_origin is None:
                    os.environ.pop("ISA_ORIGIN", None)
                else:
                    os.environ["ISA_ORIGIN"] = old_origin
        finally:
            pgconn.close_pool()

    def test_worker_reuses_the_pool_connection_when_idle(self):
        url = prepare("isa_conn_worker")
        pgconn.enable_pool(url, min_size=1, max_size=2, timeout=5)
        store.connect(url, bootstrap=True).close()
        owner = None
        conn = store.connect(url, bootstrap=False)
        try:
            owner = store.ensure_identity(conn, "worker-005")
            payload = '{"day":"2026-10-16","facts":[{"id":"f","title":"aviso"}],"source_hash":"outro","prompt_version":"t"}'
            conn.execute(
                "INSERT INTO ai_job (id, owner_id, kind, context_hash, payload_json, status, result_json, error_code, created_at, started_at, finished_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                ("job-005", owner, "insight", "h", payload, "queued", None, None, store.now(), None, None),
            )
        finally:
            conn.close()
        opens = {"n": 0}
        real = store.connect

        def counting(db, bootstrap=None):
            opens["n"] += 1
            return real(db, bootstrap=bootstrap)

        state = {"conn": None}
        old_ai = os.environ.get("ISA_AI_ENABLED")
        os.environ["ISA_AI_ENABLED"] = "1"
        try:
            with patch.object(store, "connect", counting):
                with patch.object(ai, "invoke", return_value=({"explanation": "Cabe no período informado."}, {"provider": "aws-bedrock", "model": "teste", "request_id": "t", "usage": {}})):
                    self.assertTrue(ai.worker_turn(state, url))
                self.assertEqual(opens["n"], 1)
                self.assertIs(state["conn"]._pool, pgconn._pool)
                self.assertFalse(ai.worker_turn(state, url))
                self.assertEqual(opens["n"], 1)
            done = store.connect(url, bootstrap=False)
            try:
                self.assertEqual(store.one(done, "SELECT status FROM ai_job WHERE id = ?", ("job-005",))["status"], "done")
            finally:
                done.close()
        finally:
            if state.get("conn") is not None:
                state["conn"].close()
            if old_ai is None:
                os.environ.pop("ISA_AI_ENABLED", None)
            else:
                os.environ["ISA_AI_ENABLED"] = old_ai
            pgconn.close_pool()


if __name__ == "__main__":
    unittest.main()
