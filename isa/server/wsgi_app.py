"""Aplicação de produção. Não usa http.server e não aceita identidade de laboratório."""

import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import jwt

import access
import ai
import oidc
import pgconn
import store
import workbatches

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOTYPE = os.path.join(ROOT, "prototype")
PUBLIC = {"logoisantrans.png", "index.html", "styles.css", "app.js", "plan.js", "home.js", "calc.js", "bb-statement.js", "assistant.js", "lotes.js", "ui.js"}
FONTS = {
    "fonts/fonts.css",
    "fonts/Geist-Regular.woff2",
    "fonts/Geist-Medium.woff2",
    "fonts/Geist-SemiBold.woff2",
    "fonts/Geist-Bold.woff2",
    "fonts/LICENSE-Geist-OFL.txt",
}
VERSIONED = ["fonts/fonts.css", "styles.css", "ui.js", "calc.js", "lotes.js", "bb-statement.js", "plan.js", "home.js", "app.js", "assistant.js", "logoisantrans.png"]
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


_ROUTE_WORDS = {
    "api", "ai", "status", "analyze", "categorize", "suggestions", "events",
    "home", "insights", "today", "dismiss", "workspace", "accounts", "snapshot",
    "drafts", "login", "start", "recovery", "availability", "observations",
    "inflows", "commitments", "reserves", "scenarios", "spend", "profile",
    "catalog-requests", "select", "assign", "entries", "banks", "duplicate-check", "work-batches",
    "work-preference", "work-search", "conclude", "reopen", "members", "move",
    "unlink", "imports", "links", "feedback", "occurrences", "decide", "choose",
    "ready", "health", "logout",
}


def _route_name(path):
    parts = [item for item in (path or "/").split("/") if item]
    named = [item if item in _ROUTE_WORDS else "{id}" for item in parts]
    return "/" + "/".join(named) if named else "/"


def _connect(data_dir, bootstrap=False):
    url = os.environ.get("ISA_DATABASE_URL") or ""
    if os.environ.get("ISA_ENV") == "production" or url.startswith("postgres"):
        if not url.startswith("postgres"):
            raise RuntimeError("produção sem PostgreSQL")
        return store.connect(url, bootstrap=bootstrap)
    return store.connect(os.path.join(data_dir, "isa.sqlite"), bootstrap=True)


def _db_message(method):
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "Não foi possível salvar. Tente de novo."
    return "A base não está disponível."


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
        tokens = oidc.exchange(code, attempt["verifier"])
        claims = oidc.claims_from_access_token(tokens["access_token"])
    except (jwt.InvalidTokenError, OSError, ValueError):
        return _json(start, 401, {"error": "A troca do código não foi aceita."})
    sub = claims.get("sub") or ""
    if sub not in access.allowed_subs():
        return _json(start, 403, {"error": "Esta pessoa ainda não está no piloto."})
    owner = store.ensure_identity(conn, sub)
    if tokens.get("id_token"):
        try:
            store.remember_verified_profile(conn, owner, oidc.presentation_claims(tokens["id_token"]))
        except jwt.InvalidTokenError:
            pass
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


def _stamp_index(body):
    version = _version().split()[-1]
    text = body.decode("utf-8")
    for asset in VERSIONED:
        text = text.replace('href="' + asset + '"', 'href="' + asset + "?v=" + version + '"')
        text = text.replace('src="' + asset + '"', 'src="' + asset + "?v=" + version + '"')
    return text.encode("utf-8")


def _static(path, start, environ=None):
    if path == "/runtime.js":
        body = b"window.isaRuntime='public';window.isaPublic=true;"
        start("200 OK", [
            ("Content-Type", "text/javascript; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [body]
    relative = "index.html" if path in ("", "/") else path.lstrip("/")
    name = relative.replace("\\", "/")
    allowed = name in PUBLIC or name in FONTS
    target = os.path.abspath(os.path.join(PROTOTYPE, name))
    root = os.path.abspath(PROTOTYPE)
    if not allowed or not target.startswith(root + os.sep) or not os.path.isfile(target):
        return _json(start, 404, {"error": "Não encontrado."})
    kind = "text/html; charset=utf-8"
    if target.endswith(".css"):
        kind = "text/css; charset=utf-8"
    elif target.endswith(".js"):
        kind = "text/javascript; charset=utf-8"
    elif target.endswith(".png"):
        kind = "image/png"
    elif target.endswith(".csv"):
        kind = "text/csv; charset=utf-8"
    elif target.endswith(".woff2"):
        kind = "font/woff2"
    elif target.endswith(".txt"):
        kind = "text/plain; charset=utf-8"
    with open(target, "rb") as handle:
        body = handle.read()
    if name == "index.html":
        body = _stamp_index(body)
    cache = "no-store" if name in ("index.html", "runtime.js") else "public, max-age=31536000, immutable"
    headers = [
        ("Content-Type", kind),
        ("X-Content-Type-Options", "nosniff"),
        ("Cache-Control", cache),
    ]
    accept = ((environ or {}).get("HTTP_ACCEPT_ENCODING") or "")
    if "gzip" in accept and kind.startswith("text"):
        import gzip
        body = gzip.compress(body)
        headers.append(("Content-Encoding", "gzip"))
        headers.append(("Vary", "Accept-Encoding"))
    headers.append(("Content-Length", str(len(body))))
    start("200 OK", headers)
    return [body]


def _account_header(environ):
    value = (environ.get("HTTP_X_ISA_ACCOUNT") or "").strip()
    return value or None


def _route(conn, owner, method, path, body, data_dir, account=None, month="", cut=None):
    parts = [item for item in path.split("/") if item]
    if method == "GET" and path == "/api/ai/status":
        return ai.status(conn, owner)
    if method == "POST" and path == "/api/ai/analyze":
        return ai.queue_plan(conn, owner, body)
    if method == "POST" and path == "/api/ai/categorize":
        ai.queue_categories(conn, owner)
        return ai.status(conn, owner)
    if method == "POST" and len(parts) == 5 and parts[1:3] == ["ai", "suggestions"] and parts[4] == "events":
        return ai.decision(conn, owner, parts[3], body)
    if method == "GET" and path == "/api/home":
        page = store.home(conn, owner, account=account)
        if month:
            chosen = store.calendar_month(month)
            account_id = (page.get("context") or {}).get("accountId") or None
            page["month"] = store.month_picture(conn, owner, chosen, (page.get("overview") or {}).get("reference") or store.reference_date(), account_id)
        return page
    if method == "POST" and path == "/api/insights/today":
        return ai.queue_insight(conn, owner, bool((body or {}).get("manual")), account)
    if method == "POST" and path == "/api/insights/dismiss":
        return store.dismiss_insight(conn, owner, body)
    if method == "GET" and path == "/api/workspace":
        return store.workspace(conn, owner, account, cut)
    if method == "POST" and path == "/api/entries/duplicate-check":
        return store.duplicate_check(conn, owner, (body or {}).get("entry") or body or {})
    if method == "GET" and len(parts) == 3 and parts[1] == "entries":
        return store.read_entry(conn, owner, unquote(parts[2]))
    if method == "GET" and path == "/api/accounts":
        return store.list_accounts(conn, owner, account)
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
    if method == "POST" and path == "/api/profile":
        return {"profile": store.save_profile(conn, owner, body or {}), "workspace": store.workspace(conn, owner, account, cut)}
    if method == "GET" and len(parts) == 3 and parts[1] == "accounts":
        detail = store.account_detail(conn, owner, parts[2])
        return detail
    if method == "POST" and path == "/api/catalog-requests":
        return store.save_catalog_request(conn, owner, body or {})
    if method == "POST" and path == "/api/accounts":
        payload = dict(body.get("account") or body or {})
        payload["registration"] = True
        created = store.save_account(conn, owner, payload)
        return {"account": store._public_account(conn, owner, dict(created)), "workspace": store.workspace(conn, owner, account, cut)}
    if method == "POST" and path == "/api/accounts/select":
        return store.select_account(conn, owner, body or {})
    if method == "POST" and path == "/api/accounts/assign":
        return store.assign_records(conn, owner, body or {})
    if method == "POST" and len(parts) == 3 and parts[1] == "accounts":
        payload = dict(body or {})
        payload["id"] = parts[2]
        payload["edit"] = True
        payload["registration"] = True
        edited = store.save_account(conn, owner, payload)
        return {"account": store._public_account(conn, owner, dict(edited)), "workspace": store.workspace(conn, owner, account, cut)}
    if method == "POST" and path == "/api/entries":
        saved = store.save_entry(conn, owner, body.get("entry") or body)
        ai.queue_categories(conn, owner)
        return {"entry": saved, "workspace": store.workspace(conn, owner, account, cut)}
    if method == "POST" and path == "/api/work-batches":
        created = workbatches.create_batch(conn, owner, body or {})
        return {"batch": created, "workspace": store.workspace(conn, owner, account, cut)}
    if method == "POST" and path == "/api/work-preference":
        return workbatches.set_preference(conn, owner, (body or {}).get("activeBatchId") or "")
    if method == "POST" and path == "/api/work-search":
        return workbatches.search(conn, owner, body or {})
    if method == "POST" and len(parts) >= 3 and parts[1] == "work-batches":
        batch_id = parts[2]
        if len(parts) == 3:
            return {"batch": workbatches.update_batch(conn, owner, batch_id, body or {}), "workspace": store.workspace(conn, owner, account, cut)}
        if len(parts) == 4 and parts[3] == "conclude":
            return {"batch": workbatches.conclude_batch(conn, owner, batch_id), "workspace": store.workspace(conn, owner, account, cut)}
        if len(parts) == 4 and parts[3] == "reopen":
            return {"batch": workbatches.reopen_batch(conn, owner, batch_id), "workspace": store.workspace(conn, owner, account, cut)}
        if len(parts) == 4 and parts[3] == "members":
            return {"batch": workbatches.link_entry(conn, owner, batch_id, (body or {}).get("entryId") or ""), "workspace": store.workspace(conn, owner, account, cut)}
        if len(parts) == 6 and parts[3] == "members" and parts[5] == "move":
            moved = workbatches.move_entry(conn, owner, batch_id, parts[4], (body or {}).get("toBatchId") or "")
            return {"batch": moved, "workspace": store.workspace(conn, owner, account, cut)}
        if len(parts) == 6 and parts[3] == "members" and parts[5] == "unlink":
            return {"batch": workbatches.unlink_entry(conn, owner, batch_id, parts[4]), "workspace": store.workspace(conn, owner, account, cut)}
    if method == "POST" and path == "/api/imports":
        if body.get("account") or body.get("notes") is not None:
            result = store.import_statement(conn, owner, body, account, cut)
            ai.queue_categories(conn, owner)
            return result
        return store.import_batch(conn, owner, body)
    if method == "POST" and path == "/api/links":
        linked = store.link_movement(conn, owner, body)
        if linked is None:
            return None
        linked["workspace"] = store.workspace(conn, owner, account, cut)
        return linked
    if method == "POST" and path == "/api/suggestions":
        return ai.queue_plan(conn, owner, body)
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
        item["workspace"] = store.workspace(conn, owner, account, cut)
        ai.queue_categories(conn, owner)
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

    def app(environ, start_response):
        begun = time.perf_counter()
        path = urlparse(environ.get("PATH_INFO") or "/").path
        method = environ.get("REQUEST_METHOD") or "GET"
        touched = {"conn": None}

        def start(status, headers, exc_info=None):
            headers = list(headers)
            if path.startswith("/api/"):
                dur = (time.perf_counter() - begun) * 1000.0
                code = int(str(status).split()[0])
                queries = getattr(touched["conn"], "queries", 0)
                headers.append(("Server-Timing", "app;dur=%.1f" % dur))
                print("ISA api %s %s %s %.1fms queries=%s" % (method, _route_name(path), code, dur, queries), flush=True)
            if exc_info is not None:
                return start_response(status, headers, exc_info)
            return start_response(status, headers)

        if not _origin_ok(environ):
            return _json(start, 403, {"error": "Origem não aceita."})
        if set(_query(environ)) & REJECTED_QUERY:
            return _json(start, 400, {"error": "O acesso não aceita token nem proprietário na URL."})
        if path == "/api/ready" and method == "GET":
            try:
                conn = _connect(data_dir, bootstrap=False)
                touched["conn"] = conn
                try:
                    version = store.one(conn, "SELECT MAX(version) AS v FROM schema_migration")
                    if not version or (version["v"] or 0) < 4:
                        return _json(start, 503, {"ready": False})
                    return _json(start, 200, {"ready": True, "schema": version["v"]})
                finally:
                    conn.close()
            except Exception as exc:
                if pgconn.is_db_failure(exc):
                    print("ISA db " + type(exc).__name__, flush=True)
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
                "ai": "claude-bedrock" if ai.enabled() else "unavailable",
                "database": "postgres" if (os.environ.get("ISA_DATABASE_URL") or "").startswith("postgres") else "sqlite",
            })
        if path in LAB_PATHS or path.startswith("/api/fixtures/"):
            return _json(start, 404, {"error": "Não encontrado."})
        guarded = path.startswith("/api/") or path == "/callback"
        if guarded and not gate.allow(_client(environ), clock()):
            return _json(start, 429, {"error": "Muitos pedidos. Espere um minuto e tente de novo."})
        if path == "/callback" or path.startswith("/api/"):
            try:
                conn = _connect(data_dir, bootstrap=False)
                touched["conn"] = conn
            except Exception as exc:
                if pgconn.is_db_failure(exc):
                    print("ISA db " + type(exc).__name__, flush=True)
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
                    return _json(start, 200, {"left": True, "logoutUrl": oidc.logout_url()}, [("Set-Cookie", _cookie())])
                owner, code, payload = _owner(environ, conn)
                if not owner:
                    return _json(start, code, payload)
                if method == "GET" and path == "/api/banks":
                    catalog, tag = store.banks_document()
                    if (environ.get("HTTP_IF_NONE_MATCH") or "") == tag:
                        start("304 Not Modified", [
                            ("ETag", tag),
                            ("Cache-Control", "private, max-age=86400"),
                            ("Content-Length", "0"),
                            ("X-Content-Type-Options", "nosniff"),
                        ])
                        return [b""]
                    start("200 OK", [
                        ("Content-Type", "application/json; charset=utf-8"),
                        ("Content-Length", str(len(catalog))),
                        ("ETag", tag),
                        ("Cache-Control", "private, max-age=86400"),
                        ("X-Content-Type-Options", "nosniff"),
                    ])
                    return [catalog]
                body = _read_body(environ) if method in ("POST", "PUT") else {}
                idem = (environ.get("HTTP_IDEMPOTENCY_KEY") or "").strip()
                if method == "POST" and idem:
                    prior = store.one(conn, "SELECT response_json FROM idempotency WHERE owner_id = ? AND key = ?", (owner, idem))
                    if prior:
                        return _json(start, 200, json.loads(prior["response_json"]))
                month = (_query(environ).get("month") or [""])[0]
                cut = store.parse_cut(_query(environ), environ.get("HTTP_X_ISA_SLICE") or "")
                result = _route(conn, owner, method, path, body, data_dir, _account_header(environ), month, cut)
                if result is None:
                    return _json(start, 404, {"error": "Não encontrado para esta pessoa."})
                if method == "POST" and idem:
                    try:
                        conn.execute(
                            "INSERT INTO idempotency (owner_id, key, response_json, created_at) VALUES (?,?,?,?)",
                            (owner, idem, json.dumps(result), store.now()),
                        )
                    except sqlite3.IntegrityError:
                        prior = store.one(conn, "SELECT response_json FROM idempotency WHERE owner_id = ? AND key = ?", (owner, idem))
                        if prior:
                            return _json(start, 200, json.loads(prior["response_json"]))
                return _json(start, 200, result)
            except workbatches.Conflict as exc:
                return _json(start, 409, {"error": str(exc)})
            except ValueError as exc:
                return _json(start, 400, {"error": str(exc)})
            except Exception as exc:
                if not pgconn.is_db_failure(exc):
                    raise
                print("ISA db " + type(exc).__name__, flush=True)
                return _json(start, 503, {"error": _db_message(method)})
            finally:
                conn.close()
        if method != "GET":
            return _json(start, 404, {"error": "Não encontrado."})
        return _static(path, start, environ)

    return app
