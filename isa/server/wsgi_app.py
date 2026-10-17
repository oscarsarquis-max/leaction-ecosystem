"""Aplicação de produção. Não usa http.server e não aceita identidade de laboratório."""

import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import jwt

import access
import oidc
import store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOTYPE = os.path.join(ROOT, "prototype")
PUBLIC = {"index.html", "styles.css", "app.js", "plan.js", "calc.js", "bb-statement.js"}
LAB_HEADER = "HTTP_X_ISA_LAB_PERSON"
LAB_PATHS = {"/api/fixtures/october", "/api/forget", "/api/backup"}
REJECTED_QUERY = {"access_token", "id_token", "owner", "ownerId", "owner_id", "token"}


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
        for name in ("ownerId", "owner_id", "email", "access_token", "id_token", "sub"):
            data.pop(name, None)
    return data


def _json(start, code, payload, extra=None):
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ]
    if extra:
        headers.extend(extra)
    start(str(code) + " " + {200: "OK", 302: "Found", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 503: "Unavailable"}.get(code, "Error"), headers)
    return [body]


def _redirect(start, location, cookie=None):
    headers = [("Location", location), ("Content-Length", "0"), ("Cache-Control", "no-store")]
    cookies = cookie if isinstance(cookie, (list, tuple)) else ([cookie] if cookie else [])
    for item in cookies:
        headers.append(("Set-Cookie", item))
    start("302 Found", headers)
    return [b""]


def _cookie(session_id=None):
    origin = os.environ.get("ISA_ORIGIN") or ""
    secure = "; Secure" if origin.startswith("https://") else ""
    if not session_id:
        return "isa_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax" + secure
    return "isa_session=%s; HttpOnly; Path=/; Max-Age=43200; SameSite=Lax%s" % (session_id, secure)


def _client(environ):
    remote = environ.get("REMOTE_ADDR") or "local"
    if os.environ.get("ISA_TRUST_PROXY") != "1":
        return remote
    parts = [item.strip() for item in (environ.get("HTTP_X_FORWARDED_FOR") or "").split(",") if item.strip()]
    return parts[-1] if parts else remote


def _cookie_map(environ):
    found = {}
    for part in (environ.get("HTTP_COOKIE") or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name and name not in found:
            found[name] = value
    return found


def _same(left, right):
    if not left or not right or len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def _session_id(environ):
    return _cookie_map(environ).get("isa_session") or ""


def _query(environ):
    return parse_qs(environ.get("QUERY_STRING") or "")


def _connect(data_dir):
    url = os.environ.get("ISA_DATABASE_URL") or ""
    if os.environ.get("ISA_ENV") == "production" or url.startswith("postgres"):
        if not url.startswith("postgres"):
            raise RuntimeError("produção sem PostgreSQL")
        return store.connect(url)
    return store.connect(os.path.join(data_dir, "isa.sqlite"))


def _owner(environ, conn):
    if environ.get(LAB_HEADER):
        return None, 401, {"error": "A identidade de laboratório não entra em produção."}
    session = store.read_session(conn, _session_id(environ)) if _session_id(environ) else None
    if session:
        if session["sub"] not in access.allowed_subs():
            return None, 403, {"error": "Esta pessoa ainda não está no piloto."}
        return session["owner_id"], None, None
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


def _start_login(conn, start):
    if not access.oidc_ready():
        return _json(start, 503, {"error": "O diretório de identidade da ISA ainda não está ligado."})
    verifier = secrets.token_urlsafe(48)
    state = store.start_attempt(conn, verifier)
    try:
        url = access.authorize_url(state, verifier)
    except (jwt.InvalidTokenError, OSError):
        return _json(start, 503, {"error": "O diretório de identidade da ISA ainda não está ligado."})
    if not url:
        return _json(start, 503, {"error": "O diretório de identidade da ISA ainda não está ligado."})
    return _redirect(start, url, _login_cookie(state))


def _login_cookie(state=None):
    origin = os.environ.get("ISA_ORIGIN") or ""
    secure = "; Secure" if origin.startswith("https://") else ""
    if not state:
        return "isa_login_state=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax" + secure
    return "isa_login_state=%s; HttpOnly; Path=/; Max-Age=600; SameSite=Lax%s" % (state, secure)


def _finish_login(conn, environ, start):
    query = _query(environ)
    code = (query.get("code") or [""])[0]
    state = (query.get("state") or [""])[0]
    if not _same(_cookie_map(environ).get("isa_login_state"), state):
        return _json(start, 400, {"error": "O retorno não pertence a este navegador. Entre novamente."}, [("Set-Cookie", _login_cookie())])
    attempt = store.take_attempt(conn, state) if state else None
    if not attempt or not code:
        return _json(start, 400, {"error": "O retorno não confere com o início do acesso."})
    try:
        token = oidc.exchange(code, attempt["verifier"])
        claims = oidc.claims_from_access_token(token)
    except (jwt.InvalidTokenError, OSError, ValueError):
        return _json(start, 401, {"error": "A troca do código não foi aceita."})
    sub = claims.get("sub") or ""
    if sub not in access.allowed_subs():
        return _json(start, 403, {"error": "Esta pessoa ainda não está no piloto."})
    owner = store.ensure_identity(conn, sub)
    expires = (datetime.now(timezone.utc) + timedelta(hours=12)).replace(microsecond=0).isoformat()
    session_id = store.save_session(conn, owner, sub, expires)
    return _redirect(start, "/#inicio", [_cookie(session_id), _login_cookie()])


def _recovery(start):
    try:
        url = access.recovery_url()
    except (jwt.InvalidTokenError, OSError):
        url = None
    if not url:
        return _json(start, 503, {"error": "A recuperação no provedor ainda não está ligada."})
    return _redirect(start, url)


def _static(path, start):
    if path == "/runtime.js":
        body = b"window.isaRuntime='public';window.isaPublic=true;"
        start("200 OK", [
            ("Content-Type", "text/javascript; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ])
        return [body]
    relative = "index.html" if path in ("", "/") else path.lstrip("/")
    name = relative.replace("\\", "/")
    allowed = name in PUBLIC
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
    if method == "GET" and path == "/api/workspace":
        return store.workspace(conn, owner)
    if method == "GET" and path == "/api/snapshot":
        return store.snapshot(conn, owner)
    if method == "GET" and path.startswith("/api/drafts/"):
        return store.read_draft(conn, owner, unquote(parts[-1]))
    if method == "GET" and path == "/api/suggestions":
        return {"items": store.rows(conn, "SELECT id, status, revision_of, origin, content, created_at FROM suggestion WHERE owner_id = ? ORDER BY created_at", (owner,))}
    if method == "GET" and path == "/api/login":
        return {"ready": access.oidc_ready(), "method": "pkce", "rehearsal": os.environ.get("ISA_OIDC_REHEARSAL") == "1"}
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
    if method == "POST" and path == "/api/accounts":
        account = store.save_account(conn, owner, body.get("account") or body)
        return {"account": dict(account), "workspace": store.workspace(conn, owner)}
    if method == "POST" and path == "/api/entries":
        saved = store.save_entry(conn, owner, body.get("entry") or body)
        return {"entry": saved, "workspace": store.workspace(conn, owner)}
    if method == "POST" and path == "/api/imports":
        if body.get("account") or body.get("notes") is not None:
            return store.import_statement(conn, owner, body)
        return store.import_batch(conn, owner, body)
    if method == "POST" and path == "/api/links":
        linked = store.link_movement(conn, owner, body)
        if linked is None:
            return None
        linked["workspace"] = store.workspace(conn, owner)
        return linked
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
        item = store.decide_occurrence(conn, owner, parts[2], body.get("kind"))
        if item is None:
            return None
        item["workspace"] = store.workspace(conn, owner)
        return item
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
        if set(_query(environ)) & REJECTED_QUERY:
            return _json(start, 400, {"error": "O acesso não aceita token nem proprietário na URL."})
        path = urlparse(environ.get("PATH_INFO") or "/").path
        method = environ.get("REQUEST_METHOD") or "GET"
        if path == "/api/ready" and method == "GET":
            try:
                conn = _connect(data_dir)
                try:
                    version = store.one(conn, "SELECT MAX(version) AS v FROM schema_migration")
                    if not version or (version["v"] or 0) < 3:
                        return _json(start, 503, {"ready": False})
                    return _json(start, 200, {"ready": True, "schema": version["v"]})
                finally:
                    conn.close()
            except Exception:
                return _json(start, 503, {"ready": False})
        if path == "/api/health" and method == "GET":
            rehearsal = os.environ.get("ISA_OIDC_REHEARSAL") == "1"
            return _json(start, 200, {
                "ok": True,
                "lab": False,
                "auth": "ensaio" if rehearsal and access.oidc_ready() else "oidc" if access.oidc_ready() else "pendente",
                "rehearsal": rehearsal,
                "version": _version(),
                "service": "isa",
                "database": "postgres" if (os.environ.get("ISA_DATABASE_URL") or "").startswith("postgres") else "sqlite",
            })
        if path in LAB_PATHS or path.startswith("/api/fixtures/"):
            return _json(start, 404, {"error": "Não encontrado."})
        guarded = path.startswith("/api/") or path == "/callback"
        if guarded and not gate.allow(_client(environ), clock()):
            return _json(start, 429, {"error": "Muitos pedidos. Espere um minuto e tente de novo."})
        if path == "/callback" or path.startswith("/api/"):
            try:
                conn = _connect(data_dir)
            except Exception:
                return _json(start, 503, {"error": "A base não está disponível."})
            try:
                if path == "/api/login/start" and method == "GET":
                    return _start_login(conn, start)
                if path == "/api/login/recovery" and method == "GET":
                    return _recovery(start)
                if path == "/callback" and method == "GET":
                    return _finish_login(conn, environ, start)
                if path == "/api/logout" and method == "POST":
                    store.drop_session(conn, _session_id(environ))
                    return _json(start, 200, {"left": True}, [("Set-Cookie", _cookie())])
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
        if method != "GET":
            return _json(start, 404, {"error": "Não encontrado."})
        return _static(path, start)

    return app
