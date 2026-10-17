import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

import store
import wsgi_app

ROOT = Path(__file__).resolve().parent
PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = json.loads(RSAAlgorithm.to_jwk(PRIVATE.public_key()))
PUBLIC_JWK.update({"kid": "teste", "alg": "RS256", "use": "sig"})
ISSUER = "https://cognito-idp.us-east-2.amazonaws.com/us-east-2_isaexemplo"
AUDIENCE = "isa-piloto"


def token(sub, hours=1, audience=AUDIENCE, issuer=ISSUER):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": sub, "iss": issuer, "aud": audience, "exp": now + timedelta(hours=hours), "iat": now},
        PRIVATE,
        algorithm="RS256",
        headers={"kid": "teste"},
    )


def call(app, method, path, body=None, headers=None):
    captured = {}

    def start(status, header_list):
        captured["status"] = int(status.split()[0])

    raw = json.dumps(body).encode("utf-8") if body is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
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
    return captured["status"], parsed


class ProductionGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="isa-prod-")
        self.env = {
            "ISA_OIDC_ISSUER": ISSUER,
            "ISA_OIDC_AUDIENCE": AUDIENCE,
            "ISA_OIDC_CLIENT_ID": "cliente-publico",
            "ISA_OIDC_JWKS": json.dumps({"keys": [PUBLIC_JWK]}),
            "ISA_OIDC_ALLOWED_SUBS": "teste-uma,teste-duas",
            "ISA_ORIGIN": "http://127.0.0.1:8099",
        }
        self.old = {key: os.environ.get(key) for key in self.env}
        os.environ.update(self.env)
        self.app = wsgi_app.build_app(self.tmp, time.time)

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.tmp, ignore_errors=True)

    def auth(self, sub):
        return {"HTTP_AUTHORIZATION": "Bearer " + token(sub)}

    def test_pkce_does_not_use_a_secret(self):
        import access
        url = access.authorize_url("estado", "verifier-verifier-verifier")
        self.assertIn("code_challenge_method=S256", url)
        self.assertNotIn("client_secret", url)

    def test_lab_header_fixture_and_two_people(self):
        code, health = call(self.app, "GET", "/api/health")
        self.assertEqual(code, 200)
        self.assertFalse(health["lab"])
        self.assertEqual(health["auth"], "oidc")
        code, denied = call(self.app, "GET", "/api/home", headers={"HTTP_X_ISA_LAB_PERSON": "eveline", "HTTP_AUTHORIZATION": "Bearer " + token("teste-uma")})
        self.assertEqual(code, 401)
        code, missing = call(self.app, "GET", "/api/home")
        self.assertEqual(code, 401)
        code, outsider = call(self.app, "GET", "/api/home", headers=self.auth("outra-pessoa"))
        self.assertEqual(code, 403)
        code, expired = call(self.app, "GET", "/api/home", headers={"HTTP_AUTHORIZATION": "Bearer " + token("teste-uma", hours=-1)})
        self.assertEqual(code, 401)
        code, fixture = call(self.app, "POST", "/api/fixtures/october", {}, self.auth("teste-uma"))
        self.assertEqual(code, 404)
        code, forget = call(self.app, "POST", "/api/forget", {}, self.auth("teste-uma"))
        self.assertEqual(code, 404)
        code, created = call(self.app, "POST", "/api/commitments", {"label": "Aluguel", "totalCents": 50000, "dueOn": "2026-10-20"}, self.auth("teste-uma"))
        self.assertEqual(code, 200)
        code, foreign = call(self.app, "POST", "/api/commitments/" + created["id"], {"dueOn": "2026-10-26"}, self.auth("teste-duas"))
        self.assertEqual(code, 404)
        code, home = call(self.app, "GET", "/api/home", headers=self.auth("teste-duas"))
        self.assertFalse(home["projection"]["complete"])
        self.assertEqual(home["commitments"], [])
        code, hidden = call(self.app, "GET", "/server/store.py")
        self.assertEqual(code, 404)
        code, page = call(self.app, "GET", "/")
        self.assertIsInstance(page, bytes)
        self.assertIn(b"ISA", page)

    def test_process_replacement_keeps_the_commitment(self):
        env = os.environ.copy()
        env.update(self.env)
        env["ISA_ENV"] = "production"
        env["ISA_DATA"] = self.tmp
        env["ISA_PORT"] = "8132"
        env["ISA_ORIGIN"] = "http://127.0.0.1:8132"
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
