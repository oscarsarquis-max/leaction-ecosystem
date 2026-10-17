import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

import oidc
import store
import wsgi_app

ROOT = Path(__file__).resolve().parent
PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = json.loads(RSAAlgorithm.to_jwk(PRIVATE.public_key()))
PUBLIC_JWK.update({"kid": "teste", "alg": "RS256", "use": "sig"})
ISSUER = "https://cognito-idp.us-east-2.amazonaws.com/us-east-2_isaexemplo"
CLIENT = "cliente-publico"


class Discovery(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        base = "http://127.0.0.1:%s" % self.server.server_address[1]
        if self.path.startswith("/.well-known/openid-configuration"):
            payload = {
                "issuer": ISSUER,
                "authorization_endpoint": base + "/authorize",
                "token_endpoint": base + "/token",
                "jwks_uri": base + "/jwks",
                "recovery_endpoint": base + "/recover",
            }
        elif self.path.startswith("/jwks"):
            keys = [PUBLIC_JWK]
            if getattr(self.server, "jwks_calls", None) is not None:
                self.server.jwks_calls += 1
                if self.server.jwks_calls == 1:
                    keys = []
            payload = {"keys": keys}
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def token(sub, hours=1, issuer=ISSUER, use="access"):
    now = datetime.now(timezone.utc)
    claims = {"sub": sub, "iss": issuer, "exp": now + timedelta(hours=hours), "iat": now, "token_use": use}
    if use == "access":
        claims["client_id"] = CLIENT
    else:
        claims["aud"] = "isa-piloto"
    return jwt.encode(claims, PRIVATE, algorithm="RS256", headers={"kid": "teste"})


def call(app, method, path, body=None, headers=None, query=""):
    captured = {}

    def start(status, header_list):
        captured["status"] = int(status.split()[0])
        captured["headers"] = header_list

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
    chunks = app(environ, start)
    payload = b"".join(chunks)
    parsed = json.loads(payload) if payload[:1] in (b"{", b"[") else payload
    return captured["status"], parsed, captured.get("headers") or []


class ProductionGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="isa-prod-")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Discovery)
        self.httpd.jwks_calls = None
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        discovery = "http://127.0.0.1:%s/.well-known/openid-configuration" % self.httpd.server_address[1]
        self.env = {
            "ISA_OIDC_ISSUER": ISSUER,
            "ISA_OIDC_CLIENT_ID": CLIENT,
            "ISA_OIDC_DISCOVERY": discovery,
            "ISA_OIDC_ALLOWED_SUBS": "teste-uma,teste-duas",
            "ISA_ORIGIN": "http://127.0.0.1:8099",
        }
        self.cleared = ["ISA_DATABASE_URL", "ISA_OIDC_JWKS", "ISA_OIDC_REHEARSAL", "ISA_OIDC_AUDIENCE", "ISA_ENV"]
        self.old = {key: os.environ.get(key) for key in list(self.env) + self.cleared}
        os.environ.update(self.env)
        for key in self.cleared:
            os.environ.pop(key, None)
        oidc.reset()
        self.app = wsgi_app.build_app(self.tmp, time.time)

    def tearDown(self):
        self.httpd.shutdown()
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        oidc.reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def auth(self, sub, use="access"):
        return {"HTTP_AUTHORIZATION": "Bearer " + token(sub, use=use)}

    def test_pkce_does_not_use_a_secret(self):
        import access
        url = access.authorize_url("estado", "verifier-verifier-verifier")
        self.assertIn("code_challenge_method=S256", url)
        self.assertNotIn("client_secret", url)
        self.assertNotIn(ISSUER + "/oauth2/authorize", url)

    def test_lab_header_fixture_and_two_people(self):
        code, health, _headers = call(self.app, "GET", "/api/health")
        self.assertEqual(code, 200)
        self.assertFalse(health["lab"])
        self.assertEqual(health["auth"], "oidc")
        self.assertEqual(health["database"], "sqlite")
        code, denied, _headers = call(self.app, "GET", "/api/home", headers={"HTTP_X_ISA_LAB_PERSON": "eveline", "HTTP_AUTHORIZATION": "Bearer " + token("teste-uma")})
        self.assertEqual(code, 401)
        code, missing, _headers = call(self.app, "GET", "/api/home")
        self.assertEqual(code, 401)
        code, outsider, _headers = call(self.app, "GET", "/api/home", headers=self.auth("outra-pessoa"))
        self.assertEqual(code, 403)
        code, expired, _headers = call(self.app, "GET", "/api/home", headers={"HTTP_AUTHORIZATION": "Bearer " + token("teste-uma", hours=-1)})
        self.assertEqual(code, 401)
        code, identity, _headers = call(self.app, "GET", "/api/home", headers=self.auth("teste-uma", use="id"))
        self.assertEqual(code, 401)
        code, planted, _headers = call(self.app, "GET", "/api/home", query="access_token=abc&ownerId=pessoa-marina", headers=self.auth("teste-uma"))
        self.assertEqual(code, 400)
        code, fixture, _headers = call(self.app, "POST", "/api/fixtures/october", {}, self.auth("teste-uma"))
        self.assertEqual(code, 404)
        code, forget, _headers = call(self.app, "POST", "/api/forget", {}, self.auth("teste-uma"))
        self.assertEqual(code, 404)
        code, created, _headers = call(self.app, "POST", "/api/commitments", {"label": "Aluguel", "totalCents": 50000, "dueOn": "2026-10-20"}, self.auth("teste-uma"))
        self.assertEqual(code, 200)
        code, foreign, _headers = call(self.app, "POST", "/api/commitments/" + created["id"], {"dueOn": "2026-10-26"}, self.auth("teste-duas"))
        self.assertEqual(code, 404)
        code, home, _headers = call(self.app, "GET", "/api/home", headers=self.auth("teste-duas"))
        self.assertFalse(home["projection"]["complete"])
        self.assertEqual(home["commitments"], [])
        code, hidden, _headers = call(self.app, "GET", "/server/store.py")
        self.assertEqual(code, 404)
        code, page, _headers = call(self.app, "GET", "/")
        self.assertIsInstance(page, bytes)
        self.assertIn(b"ISA", page)

    def test_unknown_kid_reloads_keys(self):
        self.httpd.jwks_calls = 0
        oidc.reset()
        code, home, _headers = call(self.app, "GET", "/api/home", headers=self.auth("teste-uma"))
        self.assertEqual(code, 200)
        self.assertGreaterEqual(self.httpd.jwks_calls, 2)
        self.assertIn("commitments", home)

    def test_process_replacement_keeps_the_commitment(self):
        from test_pg import prepare
        env = os.environ.copy()
        env.update(self.env)
        env["ISA_ENV"] = "production"
        env["ISA_DATABASE_URL"] = prepare("isa_proc")
        env["ISA_PORT"] = "8132"
        env["ISA_ORIGIN"] = "http://127.0.0.1:8132"
        env.pop("ISA_OIDC_REHEARSAL", None)
        env.pop("ISA_OIDC_JWKS", None)
        proc = subprocess.Popen([sys.executable, str(ROOT / "prod_serve.py")], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            self.assertIn(b"ISA produ", proc.stdout.readline())
            import urllib.request
            body = json.dumps({"label": "Luz", "totalCents": 20000, "dueOn": "2026-10-18"}).encode()
            request = urllib.request.Request(
                "http://127.0.0.1:8132/api/commitments",
                data=body,
                method="POST",
                headers={"Authorization": "Bearer " + token("teste-uma"), "Content-Type": "application/json", "Origin": "http://127.0.0.1:8132"},
            )
            saved = json.load(urllib.request.urlopen(request))
            proc.kill()
            proc.wait(timeout=5)
            proc = subprocess.Popen([sys.executable, str(ROOT / "prod_serve.py")], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertIn(b"ISA produ", proc.stdout.readline())
            again = urllib.request.Request("http://127.0.0.1:8132/api/home", headers={"Authorization": "Bearer " + token("teste-uma"), "Origin": "http://127.0.0.1:8132"})
            home = json.load(urllib.request.urlopen(again))
            health = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8132/api/health")))
            self.assertEqual(health["database"], "postgres")
            self.assertEqual(health["auth"], "oidc")
            labels = [item["label"] for item in home["commitments"]]
            self.assertEqual(labels, ["Luz"])
            self.assertEqual(saved["due_on"], "2026-10-18")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


class IdentityStoreTest(unittest.TestCase):
    def test_same_subject_keeps_owner(self):
        tmp = tempfile.mkdtemp(prefix="isa-id-")
        try:
            conn = store.connect(os.path.join(tmp, "isa.sqlite"))
            first = store.ensure_identity(conn, "sujeito-a")
            second = store.ensure_identity(conn, "sujeito-a")
            other = store.ensure_identity(conn, "sujeito-b")
            self.assertEqual(first, second)
            self.assertNotEqual(first, other)
            self.assertFalse(first.startswith("sujeito"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
