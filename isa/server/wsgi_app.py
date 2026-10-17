"""Aplicação de produção. Não usa http.server e não aceita identidade de laboratório."""

import json
import os
import sqlite3
from urllib.parse import unquote, urlparse

import jwt

import access
import store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOTYPE = os.path.join(ROOT, "prototype")
PUBLIC = {"index.html", "styles.css", "app.js", "plan.js", "calc.js", "bb-statement.js"}
LAB_HEADER = "HTTP_X_ISA_LAB_PERSON"
LAB_PATHS = {"/api/fixtures/october", "/api/forget", "/api/backup"}


def _version():
    path = os.path.join(ROOT, "VERSION")
    with open(path, encoding="utf-8") as handle:
        return handle.readline().strip()


def _origin_ok(environ):
    origin = environ.get("HTTP_ORIGIN")
    if not origin:
        return True
    return origin == os.environ.get("ISA_ORIGIN", "https://isa.actionhub.com.br")


def _read_body(environ, limit=1_000_000):
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length > limit:
        raise ValueError("Pedido grande demais.")
    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    if isinstance(data, dict):
        data.pop("ownerId", None)
        data.pop("owner_id", None)
        data.pop("email", None)
    return data


def _json(start, code, payload):
    body = json.dumps(payload).encode("utf-8")
    start(str(code) + " " + {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 503: "Unavailable"}.get(code, "Error"), [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [body]


def _owner(environ, conn):
    if environ.get(LAB_HEADER):
        return None, 401, {"error": "A identidade de laboratório não entra em produção."}
    if not access.oidc_ready():
        return None, 401, {"error": "O diretório de identidade da ISA ainda não está ligado."}
    try:
        claims = access.claims_from_bearer(environ.get("HTTP_AUTHORIZATION"))
    except jwt.InvalidTokenError:
        return None, 401, {"error": "A sessão não foi aceita. Entre de novo."}
    sub = claims.get("sub") or ""
    if sub not in access.allowed_subs():
        return None, 403, {"error": "Esta pessoa ainda não está no piloto."}
    return store.ensure_identity(conn, sub), None, None


def _static(path, start):
    relative = "index.html" if path in ("", "/") else path.lstrip("/")
    name = relative.replace("\\", "/")
    allowed = name in PUBLIC or (name.startswith("fixtures/") and name.endswith(".csv") and ".." not in name)
    target = os.path.abspath(os.path.join(PROTOTYPE, name))
    root = os.path.abspath(PROTOTYPE)
    if not allowed or not target.startswith(root + os.sep) or not os.path.isfile(target):
        return _json(start, 404, {"error": "Não encontrado."})
    kind = "text/html; charset=utf-8"
    if target.endswith(".css"):
        kind = "text/css; charset=utf-8"
    elif target.endswith(".js"):
        kind = "text/javascript; charset=utf-8"
    elif target.endswith(".csv"):
        kind = "text/csv; charset=utf-8"
    with open(target, "rb") as handle:
        body = handle.read()
    start("200 OK", [
        ("Content-Type", kind),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [body]


def _route(conn, owner, method, path, body, data_dir):
    parts = [item for item in path.split("/") if item]
    if method == "GET" and path == "/api/home":
        return store.home(conn, owner)
    if method == "GET" and path == "/api/snapshot":
        return store.snapshot(conn, owner)
    if method == "GET" and path.startswith("/api/drafts/"):
        return store.read_draft(conn, owner, unquote(parts[-1]))
    if method == "GET" and path == "/api/suggestions":
        return {"items": store.rows(conn, "SELECT id, status, revision_of, origin, content, created_at FROM suggestion WHERE owner_id = ? ORDER BY created_at", (owner,))}
    if method == "GET" and path == "/api/login":
        return {"ready": access.oidc_ready(), "method": "pkce"}
    if method == "PUT" and path == "/api/availability":
        return store.save_availability(conn, owner, body)
    if method == "PUT" and path.startswith("/api/drafts/"):
        return store.save_draft(conn, owner, unquote(parts[-1]), body)
    if method == "POST" and path == "/api/observations":
        return store.add_observation(conn, owner, body)
    if method == "POST" and path == "/api/inflows":
        return store.add_inflow(conn, owner, body)
    if method == "POST" and path == "/api/commitments":
        return store.add_commitment(conn, owner, body)
    if method == "POST" and path == "/api/reserves":
        return store.add_reserve(conn, owner, body)
    if method == "POST" and path == "/api/scenarios":
        return store.save_scenario(conn, owner, body)
    if method == "POST" and path == "/api/spend":
        return store.spend(conn, owner, body)
    if method == "POST" and path == "/api/imports":
        return store.import_batch(conn, owner, body)
    if method == "POST" and path == "/api/links":
        return store.link_movement(conn, owner, body)
    if method == "POST" and path == "/api/suggestions":
        return store.create_suggestion(conn, owner, body.get("reference") or "2026-10-16")
    if method == "POST" and path == "/api/feedback":
        return store.add_feedback(conn, owner, body)
    if method == "POST" and len(parts) == 3 and parts[1] == "inflows":
        return store.patch_inflow(conn, owner, parts[2], body)
    if method == "POST" and len(parts) == 3 and parts[1] == "commitments":
        return store.patch_commitment(conn, owner, parts[2], body)
    if method == "POST" and len(parts) == 4 and parts[1] == "scenarios" and parts[3] == "choose":
        return store.choose_scenario(conn, owner, parts[2])
    if method == "POST" and len(parts) == 4 and parts[1] == "occurrences" and parts[3] == "decide":
        return store.decide_occurrence(conn, owner, parts[2], body.get("kind"))
    if method == "POST" and len(parts) == 4 and parts[1] == "suggestions" and parts[3] == "events":
        return store.suggestion_event(conn, owner, parts[2], body.get("event"), body.get("note") or "")
    return None


class RateGate:
    def __init__(self, limit=60):
        self.limit = limit
        self.hits = {}

    def allow(self, key, now):
        bucket = self.hits.setdefault(key, [])
        bucket[:] = [item for item in bucket if item > now - 60]
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def build_app(data_dir, clock):
    gate = RateGate()

    def app(environ, start):
        if not _origin_ok(environ):
            return _json(start, 403, {"error": "Origem não aceita."})
        path = urlparse(environ.get("PATH_INFO") or "/").path
        method = environ.get("REQUEST_METHOD") or "GET"
        if path == "/api/health" and method == "GET":
            return _json(start, 200, {
                "ok": True,
                "lab": False,
                "auth": "oidc" if access.oidc_ready() else "pendente",
                "version": _version(),
                "service": "isa",
            })
        if path in LAB_PATHS or path.startswith("/api/fixtures/"):
            return _json(start, 404, {"error": "Não encontrado."})
        if not path.startswith("/api/"):
            if method != "GET":
                return _json(start, 404, {"error": "Não encontrado."})
            return _static(path, start)
        if not gate.allow(environ.get("REMOTE_ADDR") or "local", clock()):
            return _json(start, 429, {"error": "Muitos pedidos. Espere um minuto e tente de novo."})
        conn = store.connect(os.path.join(data_dir, "isa.sqlite"))
        try:
            owner, code, payload = _owner(environ, conn)
            if not owner:
                return _json(start, code, payload)
            body = _read_body(environ) if method in ("POST", "PUT") else {}
            result = _route(conn, owner, method, path, body, data_dir)
            if result is None:
                return _json(start, 404, {"error": "Não encontrado para esta pessoa."})
            return _json(start, 200, result)
        except sqlite3.OperationalError:
            return _json(start, 503, {"error": "Não foi possível salvar. Tente de novo."})
        except ValueError as exc:
            return _json(start, 400, {"error": str(exc)})
        finally:
            conn.close()

    return app
