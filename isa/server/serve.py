"""Servidor local da ISA. Identidade sintética só com ISA_ENV=lab."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ai
import store
import workbatches

PEOPLE = {"marina": "pessoa-marina", "paulo": "pessoa-paulo", "eveline": "pessoa-eveline-demo"}
PROTOTYPE = os.path.join(ROOT, "prototype")


class ReuseServer(ThreadingHTTPServer):
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "ISA-local"

    def log_message(self, fmt, *args):
        return

    def _send(self, code, payload=None, body=None, content_type="application/json; charset=utf-8"):
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body or b"")))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1_000_000:
            raise ValueError("Arquivo grande demais para esta etapa.")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            data.pop("ownerId", None)
            data.pop("owner_id", None)
        return data

    def _owner(self):
        if os.environ.get("ISA_ENV") != "lab":
            self._send(403, {"error": "O mecanismo de identidades sintéticas só existe no laboratório."})
            return None
        person = PEOPLE.get(self.headers.get("X-ISA-Lab-Person") or "")
        if not person:
            self._send(401, {"error": "Identidade de laboratório não reconhecida. Isto não é autenticação de produção."})
            return None
        return person

    def _account(self):
        return (self.headers.get("X-ISA-Account") or "").strip() or None

    def _db(self):
        return store.connect(os.path.join(self.server.data_dir, "isa.sqlite"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send(200, {"ok": True, "lab": os.environ.get("ISA_ENV") == "lab", "auth": "identidade-sintetica" if os.environ.get("ISA_ENV") == "lab" else "recusada"})
            return
        if not path.startswith("/api/"):
            self._static(path)
            return
        owner = self._owner()
        if not owner:
            return
        conn = self._db()
        try:
            if path == "/api/home":
                page = store.home(conn, owner, account=self._account())
                month = (parse_qs(urlparse(self.path).query).get("month") or [""])[0]
                if month:
                    chosen = store.calendar_month(month)
                    account_id = (page.get("context") or {}).get("accountId") or None
                    page["month"] = store.month_picture(conn, owner, chosen, (page.get("overview") or {}).get("reference") or store.reference_date(), account_id)
                self._send(200, page)
            elif path == "/api/accounts":
                self._send(200, store.list_accounts(conn, owner, self._account()))
            elif path.startswith("/api/accounts/"):
                detail = store.account_detail(conn, owner, path.rstrip("/").split("/")[-1])
                self._send(200 if detail else 404, detail or {"error": "Não encontrado para esta pessoa."})
            elif path == "/api/workspace":
                self._send(200, store.workspace(conn, owner, self._account()))
            elif path == "/api/snapshot":
                self._send(200, store.snapshot(conn, owner))
            elif path.startswith("/api/drafts/"):
                draft = store.read_draft(conn, owner, unquote(path.split("/")[-1]))
                self._send(200 if draft else 404, draft or {"error": "Não há rascunho."})
            elif path == "/api/suggestions":
                self._send(200, {"items": store.rows(conn, "SELECT id, status, revision_of, origin, content, created_at FROM suggestion WHERE owner_id = ? ORDER BY created_at", (owner,))})
            else:
                self._send(404, {"error": "Não encontrado."})
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        finally:
            conn.close()

    def do_POST(self):
        path = urlparse(self.path).path
        owner = self._owner()
        if not owner:
            return
        conn = self._db()
        key = self.headers.get("Idempotency-Key")
        try:
            if key:
                prior = store.one(conn, "SELECT response_json FROM idempotency WHERE owner_id = ? AND key = ?", (owner, key))
                if prior:
                    self._send(200, json.loads(prior["response_json"]))
                    return
            if path == "/api/files":
                length = int(self.headers.get("Content-Length") or 0)
                blob = self.rfile.read(length)
                payload = store.store_file(conn, self.server.data_dir, owner, self.headers.get("X-ISA-File-Label") or "", blob)
            else:
                body = self._read_json()
                payload = self._post(conn, owner, path, body)
            if payload is None:
                self._send(404, {"error": "Não encontrado para esta pessoa."})
                return
            if key:
                conn.execute(
                    "INSERT OR IGNORE INTO idempotency (owner_id, key, response_json, created_at) VALUES (?,?,?,?)",
                    (owner, key, json.dumps(payload), store.now()),
                )
            self._send(200, payload)
        except workbatches.Conflict as exc:
            self._send(409, {"error": str(exc)})
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        finally:
            conn.close()

    def _post(self, conn, owner, path, body):
        parts = [item for item in path.split("/") if item]
        if path == "/api/observations":
            return store.add_observation(conn, owner, body)
        if path == "/api/inflows":
            return store.add_inflow(conn, owner, body)
        if path == "/api/commitments":
            return store.add_commitment(conn, owner, body)
        if path == "/api/reserves":
            return store.add_reserve(conn, owner, body)
        if path == "/api/scenarios":
            return store.save_scenario(conn, owner, body)
        if path == "/api/spend":
            return store.spend(conn, owner, body)
        if path == "/api/fixtures/october":
            return store.load_october(conn, owner)
        if path == "/api/imports":
            return store.import_batch(conn, owner, body)
        if path == "/api/links":
            return store.link_movement(conn, owner, body)
        if path == "/api/suggestions":
            return store.create_suggestion(conn, owner, body.get("reference") or "2026-10-16")
        if path == "/api/insights/today":
            return ai.queue_insight(conn, owner, bool(body.get("manual")), self._account())
        if path == "/api/profile":
            return {"profile": store.save_profile(conn, owner, body or {}), "workspace": store.workspace(conn, owner, self._account())}
        if path == "/api/catalog-requests":
            return store.save_catalog_request(conn, owner, body or {})
        if path == "/api/accounts":
            payload = dict(body.get("account") or body or {})
            payload["registration"] = True
            created = store.save_account(conn, owner, payload)
            return {"account": store._public_account(conn, owner, dict(created)), "workspace": store.workspace(conn, owner, self._account())}
        if path == "/api/accounts/select":
            return store.select_account(conn, owner, body or {})
        if path == "/api/accounts/assign":
            return store.assign_records(conn, owner, body or {})
        if len(parts) == 3 and parts[1] == "accounts":
            payload = dict(body or {})
            payload["id"] = parts[2]
            payload["edit"] = True
            payload["registration"] = True
            edited = store.save_account(conn, owner, payload)
            return {"account": store._public_account(conn, owner, dict(edited))}
        if path == "/api/insights/dismiss":
            return store.dismiss_insight(conn, owner, body)
        if path == "/api/forget":
            return store.forget_owner(conn, self.server.data_dir, owner)
        if path == "/api/backup":
            dest = os.path.join(self.server.backup_root, os.path.basename(body.get("name") or "manual"))
            return store.backup_dir(self.server.data_dir, dest)
        if len(parts) == 3 and parts[1] == "inflows":
            return store.patch_inflow(conn, owner, parts[2], body)
        if len(parts) == 3 and parts[1] == "commitments":
            return store.patch_commitment(conn, owner, parts[2], body)
        if len(parts) == 4 and parts[1] == "scenarios" and parts[3] == "choose":
            return store.choose_scenario(conn, owner, parts[2])
        if len(parts) == 4 and parts[1] == "occurrences" and parts[3] == "decide":
            return store.decide_occurrence(conn, owner, parts[2], body.get("kind"))
        if len(parts) == 4 and parts[1] == "suggestions" and parts[3] == "events":
            return store.suggestion_event(conn, owner, parts[2], body.get("event"), body.get("note") or "")
        if path == "/api/entries":
            saved = store.save_entry(conn, owner, body.get("entry") or body)
            ai.queue_categories(conn, owner)
            return {"entry": saved, "workspace": store.workspace(conn, owner, self._account())}
        if path == "/api/work-batches":
            return {"batch": workbatches.create_batch(conn, owner, body or {}), "workspace": store.workspace(conn, owner, self._account())}
        if path == "/api/work-preference":
            return workbatches.set_preference(conn, owner, (body or {}).get("activeBatchId") or "")
        if path == "/api/work-search":
            return workbatches.search(conn, owner, body or {})
        if len(parts) >= 3 and parts[1] == "work-batches":
            batch_id = parts[2]
            if len(parts) == 3:
                return {"batch": workbatches.update_batch(conn, owner, batch_id, body or {}), "workspace": store.workspace(conn, owner, self._account())}
            if len(parts) == 4 and parts[3] == "conclude":
                return {"batch": workbatches.conclude_batch(conn, owner, batch_id), "workspace": store.workspace(conn, owner, self._account())}
            if len(parts) == 4 and parts[3] == "reopen":
                return {"batch": workbatches.reopen_batch(conn, owner, batch_id), "workspace": store.workspace(conn, owner, self._account())}
            if len(parts) == 4 and parts[3] == "members":
                return {"batch": workbatches.link_entry(conn, owner, batch_id, (body or {}).get("entryId") or ""), "workspace": store.workspace(conn, owner, self._account())}
            if len(parts) == 6 and parts[3] == "members" and parts[5] == "move":
                return {"batch": workbatches.move_entry(conn, owner, batch_id, parts[4], (body or {}).get("toBatchId") or ""), "workspace": store.workspace(conn, owner, self._account())}
            if len(parts) == 6 and parts[3] == "members" and parts[5] == "unlink":
                return {"batch": workbatches.unlink_entry(conn, owner, batch_id, parts[4]), "workspace": store.workspace(conn, owner, self._account())}
        return None

    def do_PUT(self):
        path = urlparse(self.path).path
        owner = self._owner()
        if not owner:
            return
        conn = self._db()
        try:
            body = self._read_json()
            if path == "/api/availability":
                self._send(200, store.save_availability(conn, owner, body))
                return
            if path.startswith("/api/drafts/"):
                self._send(200, store.save_draft(conn, owner, unquote(path.split("/")[-1]), body))
                return
            self._send(404, {"error": "Não encontrado."})
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        finally:
            conn.close()

    def _static(self, path):
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = os.path.abspath(os.path.join(PROTOTYPE, relative))
        if not target.startswith(os.path.abspath(PROTOTYPE) + os.sep) and target != os.path.abspath(os.path.join(PROTOTYPE, "index.html")):
            self._send(404, {"error": "Não encontrado."})
            return
        if not os.path.isfile(target):
            self._send(404, {"error": "Não encontrado."})
            return
        kind = "text/html; charset=utf-8"
        if target.endswith(".css"):
            kind = "text/css; charset=utf-8"
        elif target.endswith(".js"):
            kind = "text/javascript; charset=utf-8"
        elif target.endswith(".png"):
            kind = "image/png"
        elif target.endswith(".csv"):
            kind = "text/csv; charset=utf-8"
        with open(target, "rb") as handle:
            body = handle.read()
        self._send(200, body=body, content_type=kind)


def main():
    data = os.environ.get("ISA_DATA") or os.path.join(ROOT, "data", "lab")
    backup = os.environ.get("ISA_BACKUP_ROOT") or os.path.join(ROOT, "data", "backups")
    port = int(os.environ.get("ISA_PORT") or "8098")
    os.makedirs(data, exist_ok=True)
    os.makedirs(backup, exist_ok=True)
    httpd = ReuseServer(("127.0.0.1", port), Handler)
    httpd.data_dir = data
    httpd.backup_root = backup
    print("ISA local em http://127.0.0.1:%s" % port, flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
