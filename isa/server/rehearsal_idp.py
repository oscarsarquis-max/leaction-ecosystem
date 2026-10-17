"""Provedor local de ensaio. Não é o Cognito e não sobe em produção."""

import base64
import hashlib
import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = json.loads(RSAAlgorithm.to_jwk(PRIVATE.public_key()))
PUBLIC_JWK.update({"kid": "ensaio", "alg": "RS256", "use": "sig"})
CODES = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sub(self):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "rehearsal_sub" and value:
                return urllib.parse.unquote(value)
        return ""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        base = self.server.base
        if parsed.path == "/.well-known/openid-configuration":
            self._json(200, {
                "issuer": base,
                "authorization_endpoint": base + "/authorize",
                "token_endpoint": base + "/token",
                "jwks_uri": base + "/jwks",
                "recovery_endpoint": base + "/recover",
            })
            return
        if parsed.path == "/jwks":
            self._json(200, {"keys": [PUBLIC_JWK]})
            return
        if parsed.path == "/choose":
            sub = (query.get("sub") or [""])[0]
            body = "Pessoa do ensaio escolhida. Isto não é o Cognito.".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Set-Cookie", "rehearsal_sub=" + urllib.parse.quote(sub) + "; Path=/; SameSite=Lax")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/recover":
            body = "Recuperação no provedor de ensaio. A ISA não pediu senha.".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/authorize":
            sub = self._sub()
            challenge = (query.get("code_challenge") or [""])[0]
            state = (query.get("state") or [""])[0]
            redirect = (query.get("redirect_uri") or [""])[0]
            if not sub or not challenge or not redirect:
                self._json(400, {"error": "autorização incompleta"})
                return
            code = base64.urlsafe_b64encode(os.urandom(18)).decode("ascii").rstrip("=")
            CODES[code] = {"challenge": challenge, "sub": sub}
            target = redirect + ("&" if "?" in redirect else "?") + urllib.parse.urlencode({"code": code, "state": state})
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return
        self._json(404, {"error": "não encontrado"})

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/token":
            self._json(404, {"error": "não encontrado"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        code = (form.get("code") or [""])[0]
        verifier = (form.get("code_verifier") or [""])[0]
        stored = CODES.pop(code, None)
        digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
        if not stored or digest != stored["challenge"]:
            self._json(400, {"error": "troca recusada"})
            return
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": stored["sub"],
                "iss": self.server.base,
                "client_id": "isa-ensaio",
                "token_use": "access",
                "exp": now + timedelta(minutes=30),
                "iat": now,
            },
            PRIVATE,
            algorithm="RS256",
            headers={"kid": "ensaio"},
        )
        self._json(200, {"access_token": token, "token_type": "Bearer"})


def serve(port):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.base = "http://127.0.0.1:%s" % httpd.server_address[1]
    return httpd
