"""Ensaio do PostgreSQL, do login e da exclusão. A senha abaixo é só deste container local."""

import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psycopg

import oidc
import rehearsal_idp
import store
import wsgi_app

ROOT = Path(__file__).resolve().parent
ADMIN = "postgresql://isa:isa_local_only@127.0.0.1:5442/postgres"


def prepare(name):
    if not name.isidentifier():
        raise ValueError(name)
    admin = psycopg.connect(ADMIN, autocommit=True)
    admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (name,))
    admin.execute("DROP DATABASE IF EXISTS " + name)
    admin.execute("CREATE DATABASE " + name)
    admin.close()
    return "postgresql://isa:isa_local_only@127.0.0.1:5442/" + name


def call(app, method, path, body=None, headers=None, query=""):
    captured = {}

    def start(status, header_list):
        captured["status"] = int(status.split()[0])
        cookies = [value for key, value in header_list if key.lower() == "set-cookie"]
        mapped = dict(header_list)
        if cookies:
            mapped["Set-Cookie"] = next((item for item in cookies if item.startswith("isa_session=")), cookies[0])
        mapped["cookies"] = cookies
        captured["headers"] = mapped

    raw = json.dumps(body).encode("utf-8") if body is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8099",
        "wsgi.input": io.BytesIO(raw),
        "CONTENT_LENGTH": str(len(raw)),
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_ORIGIN": "http://127.0.0.1:8099",
    }
    if headers:
        environ.update(headers)
    payload = b"".join(app(environ, start))
    parsed = json.loads(payload) if payload[:1] in (b"{", b"[") else payload
    return captured["status"], parsed, captured["headers"]


class PostgresPilotTest(unittest.TestCase):
    def setUp(self):
        self.ledger = tempfile.mktemp(prefix="isa-ledger-", suffix=".jsonl")
        self.old_ledger = os.environ.get("ISA_ERASURE_LEDGER")
        os.environ["ISA_ERASURE_LEDGER"] = self.ledger
        self.url = prepare("isa_flow")
        self.restore_url = prepare("isa_restore")

    def tearDown(self):
        if self.old_ledger is None:
            os.environ.pop("ISA_ERASURE_LEDGER", None)
        else:
            os.environ["ISA_ERASURE_LEDGER"] = self.old_ledger
        if os.path.isfile(self.ledger):
            os.remove(self.ledger)

    def test_migration_transaction_idempotency_and_concurrency(self):
        conn = store.connect(self.url)
        version = store.one(conn, "SELECT MAX(version) AS v FROM schema_migration")["v"]
        self.assertEqual(version, 4)
        owner = store.ensure_identity(conn, "sujeito-flow")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO account (id, owner_id, name, currency, created_at) VALUES (?,?,?,?,?)",
            ("conta-vai-voltar", owner, "Temporária", "BRL", store.now()),
        )
        conn.execute("ROLLBACK")
        self.assertIsNone(store.one(conn, "SELECT id FROM account WHERE id = ?", ("conta-vai-voltar",)))
        body = {"batchKey": "lote-1", "origin": "exemplo-sintetico", "movements": [
            {"signature": "a", "date": "2026-10-02", "cents": -1000, "direction": "saida", "label": "Padaria"},
            {"signature": "b", "date": "2026-10-03", "cents": 5000, "direction": "entrada", "label": "Pix"},
        ]}
        first = store.import_batch(conn, owner, body)
        second = store.import_batch(conn, owner, body)
        self.assertFalse(first["repeated"])
        self.assertTrue(second["repeated"])
        self.assertEqual(store.one(conn, "SELECT COUNT(*) AS n FROM occurrence WHERE owner_id = ?", (owner,))["n"], 2)
        conn.close()

        def once(_item):
            other = store.connect(self.url)
            try:
                return store.import_batch(other, owner, {"batchKey": "lote-concorrente", "origin": "exemplo-sintetico", "movements": [
                    {"signature": "c", "date": "2026-10-04", "cents": -200, "direction": "saida", "label": "Ônibus"},
                ]})
            finally:
                other.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(once, (1, 2)))
        self.assertEqual(sum(1 for item in results if item["repeated"]), 1)
        check = store.connect(self.url)
        self.assertEqual(store.one(check, "SELECT COUNT(*) AS n FROM batch WHERE batch_key = ?", ("lote-concorrente",))["n"], 1)
        check.close()

    def test_restore_hides_forgotten_person(self):
        conn = store.connect(self.url)
        kept = store.ensure_identity(conn, "fica")
        gone = store.ensure_identity(conn, "esquece")
        store.add_commitment(conn, kept, {"label": "Luz", "totalCents": 20000, "dueOn": "2026-10-18", "origin": "ensaio"})
        store.add_commitment(conn, gone, {"label": "Segredo", "totalCents": 900, "dueOn": "2026-10-19", "origin": "ensaio"})
        folder = tempfile.mkdtemp(prefix="isa-dump-")
        try:
            manifest = store.logical_dump(conn, folder)
            self.assertFalse(manifest["schedule"])
            self.assertFalse(manifest["externalDestination"])
            store.forget_owner(conn, None, gone)
            self.assertEqual(store.one(conn, "SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ?", (gone,))["n"], 0)
            restored = store.connect(self.restore_url)
            result = store.logical_restore(restored, folder)
            self.assertTrue(result["erasuresReapplied"])
            self.assertEqual(store.one(restored, "SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ?", (gone,))["n"], 0)
            self.assertEqual(store.one(restored, "SELECT COUNT(*) AS n FROM identity WHERE owner_id = ?", (gone,))["n"], 0)
            self.assertEqual(store.one(restored, "SELECT COUNT(*) AS n FROM commitment WHERE owner_id = ?", (kept,))["n"], 1)
            home = store.home(restored, gone)
            self.assertEqual(home["commitments"], [])
            restored.close()
        finally:
            conn.close()
            shutil.rmtree(folder, ignore_errors=True)

    def test_login_redirect_session_and_logout(self):
        idp = rehearsal_idp.serve(0)
        thread = threading.Thread(target=idp.serve_forever, daemon=True)
        thread.start()
        base = idp.base
        keys = [
            "ISA_ENV", "ISA_OIDC_REHEARSAL", "ISA_OIDC_ISSUER", "ISA_OIDC_DISCOVERY",
            "ISA_OIDC_CLIENT_ID", "ISA_OIDC_REDIRECT", "ISA_OIDC_ALLOWED_SUBS", "ISA_ORIGIN", "ISA_DATABASE_URL",
        ]
        old = {key: os.environ.get(key) for key in keys}
        os.environ.update({
            "ISA_OIDC_REHEARSAL": "1",
            "ISA_OIDC_ISSUER": base,
            "ISA_OIDC_DISCOVERY": base + "/.well-known/openid-configuration",
            "ISA_OIDC_CLIENT_ID": "isa-ensaio",
            "ISA_OIDC_REDIRECT": "http://127.0.0.1:8099/callback",
            "ISA_OIDC_ALLOWED_SUBS": "teste-uma,teste-duas",
            "ISA_ORIGIN": "http://127.0.0.1:8099",
            "ISA_DATABASE_URL": self.url,
        })
        os.environ.pop("ISA_ENV", None)
        oidc.reset()
        app = wsgi_app.build_app(tempfile.mkdtemp(prefix="isa-login-"), lambda: 0)
        try:
            code, _body, headers = call(app, "GET", "/api/login/start")
            self.assertEqual(code, 302)
            self.assertIn("/authorize?", headers["Location"])
            self.assertNotIn("client_secret", headers["Location"])
            state_cookie = [item for item in headers["cookies"] if item.startswith("isa_login_state=")][0].split(";", 1)[0]
            import urllib.request
            request = urllib.request.Request(headers["Location"], headers={"Cookie": "rehearsal_sub=teste-uma"})
            class Stop(Exception):
                def __init__(self, location):
                    self.location = location
            class RedirectStop(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                    raise Stop(newurl)
            opener = urllib.request.build_opener(RedirectStop)
            try:
                opener.open(request, timeout=5)
                self.fail("o ensaio deveria redirecionar")
            except Stop as exc:
                returned = urlparse(exc.location)
            query = parse_qs(returned.query)
            code, _body, headers = call(app, "GET", "/callback", query=returned.query, headers={"HTTP_COOKIE": state_cookie})
            self.assertEqual(code, 302)
            session_cookie = [item for item in headers["cookies"] if item.startswith("isa_session=")][0]
            self.assertIn("isa_session=", session_cookie)
            session = session_cookie.split(";", 1)[0].split("=", 1)[1]
            code, workspace, _headers = call(app, "GET", "/api/workspace", headers={"HTTP_COOKIE": "isa_session=" + session})
            self.assertEqual(code, 200)
            self.assertTrue(workspace["ownerId"].startswith("pessoa-"))
            code, foreign, _headers = call(app, "GET", "/api/workspace", headers={"HTTP_COOKIE": "isa_session=" + session, "HTTP_X_ISA_LAB_PERSON": "marina"})
            self.assertEqual(code, 401)
            again, _body, _headers = call(app, "GET", "/callback", query=returned.query)
            self.assertEqual(again, 400)
            planted, _body, _headers = call(app, "GET", "/callback", query="access_token=abc&state=" + query["state"][0])
            self.assertEqual(planted, 400)
            code, left, done = call(app, "POST", "/api/logout", {}, headers={"HTTP_COOKIE": "isa_session=" + session})
            self.assertEqual(code, 200)
            self.assertTrue(left["left"])
            self.assertIn("Max-Age=0", done["Set-Cookie"])
            code, _body, _headers = call(app, "GET", "/api/workspace", headers={"HTTP_COOKIE": "isa_session=" + session})
            self.assertEqual(code, 401)
        finally:
            idp.shutdown()
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            oidc.reset()


if __name__ == "__main__":
    unittest.main()
