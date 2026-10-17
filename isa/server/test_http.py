import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import store


def call(port, method, path, body=None, person="marina", raw=None, headers=None, env_header=True):
    data = None if body is None else json.dumps(body).encode("utf-8")
    if raw is not None:
        data = raw
    request = urllib.request.Request("http://127.0.0.1:%s%s" % (port, path), data=data, method=method)
    if env_header and person:
        request.add_header("X-ISA-Lab-Person", person)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read()
            content = response.headers.get("Content-Type") or ""
            parsed = json.loads(payload.decode("utf-8")) if "json" in content else payload
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        exc.close()
        return exc.code, payload


class Server:
    def __init__(self, env="lab", port=8124):
        self.tmp = tempfile.mkdtemp(prefix="isa-lab-")
        self.data = os.path.join(self.tmp, "active")
        self.backup = os.path.join(self.tmp, "backups")
        self.port = port
        self.ledger = os.path.join(self.tmp, "erasure-ledger.jsonl")
        os.makedirs(self.data)
        os.makedirs(self.backup)
        os.environ["ISA_ERASURE_LEDGER"] = self.ledger
        environment = os.environ.copy()
        environment["ISA_ENV"] = env
        environment["ISA_DATA"] = self.data
        environment["ISA_BACKUP_ROOT"] = self.backup
        environment["ISA_PORT"] = str(self.port)
        environment["ISA_ERASURE_LEDGER"] = self.ledger
        self.proc = subprocess.Popen([sys.executable, str(ROOT / "serve.py")], cwd=str(ROOT), env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                code, payload = call(self.port, "GET", "/api/health", person=None, env_header=False)
                if code == 200:
                    self.health = payload
                    return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError(self.proc.stdout.read().decode("utf-8", "replace"))

    def stop(self):
        self.proc.kill()
        self.proc.wait(timeout=5)

    def restart(self):
        self.stop()
        environment = os.environ.copy()
        environment["ISA_ENV"] = "lab"
        environment["ISA_DATA"] = self.data
        environment["ISA_BACKUP_ROOT"] = self.backup
        environment["ISA_PORT"] = str(self.port)
        environment["ISA_ERASURE_LEDGER"] = self.ledger
        self.proc = subprocess.Popen([sys.executable, str(ROOT / "serve.py")], cwd=str(ROOT), env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                if call(self.port, "GET", "/api/health", person=None, env_header=False)[0] == 200:
                    return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("não voltou")


class HttpTest(unittest.TestCase):
    def test_lab_round_restart_restore_and_isolation(self):
        server = Server()
        try:
            self.assertTrue(server.health["lab"])
            code, denied = call(server.port, "GET", "/api/home", person="visitante")
            self.assertEqual(code, 401)
            code, home = call(server.port, "POST", "/api/fixtures/october")
            self.assertEqual(code, 200)
            projection = home["projection"]
            self.assertEqual(projection["minimum"]["cents"], -10000)
            self.assertEqual(projection["october_end_cents"], 80000)
            self.assertEqual(projection["margin"]["capacity_cents"], 0)
            self.assertIn("margem para um gasto adicional", home["explanation"]["text"])
            self.assertIn("projeção calculada", home["explanation"]["text"].lower())
            code, again = call(server.port, "POST", "/api/fixtures/october")
            self.assertEqual(len(again["projection"]["days"]), len(projection["days"]))
            code, saved = call(server.port, "PUT", "/api/drafts/conferencia", {"step": "conta", "open": True})
            self.assertEqual(saved["saved"], True)
            code, imported = call(server.port, "POST", "/api/imports", {
                "batchKey": "lote-sintetico",
                "origin": "exemplo-sintetico",
                "movements": [
                    {"signature": "a", "date": "2026-10-03", "cents": 4000, "direction": "saida", "label": "Compra", "nature": "a_conferir"},
                    {"signature": "a", "date": "2026-10-03", "cents": 4000, "direction": "saida", "label": "Compra", "nature": "a_conferir"},
                    {"signature": "b", "date": "2026-10-06", "cents": 2000, "direction": "entrada", "label": "Pix", "nature": "a_conferir"},
                ],
            })
            self.assertEqual(imported["imported"], 3)
            code, repeated = call(server.port, "POST", "/api/imports", {"batchKey": "lote-sintetico", "origin": "exemplo-sintetico", "movements": []})
            self.assertTrue(repeated["repeated"])
            self.assertEqual(repeated["imported"], 3)
            code, overlap = call(server.port, "POST", "/api/imports", {
                "batchKey": "lote-sobreposto",
                "origin": "exemplo-sintetico",
                "movements": [
                    {"signature": "a", "date": "2026-10-03", "cents": 4000, "direction": "saida", "label": "Compra", "nature": "a_conferir"},
                    {"signature": "c", "date": "2026-10-07", "cents": 500, "direction": "saida", "label": "Nova", "nature": "a_conferir"},
                ],
            })
            self.assertEqual(overlap["imported"], 1)
            self.assertEqual(overlap["pending"], 1)
            pending = [item for item in call(server.port, "GET", "/api/snapshot")[1]["occurrences"] if item["state"] == "pendente"]
            self.assertEqual(len(pending), 1)

            def decide():
                return call(server.port, "POST", "/api/occurrences/%s/decide" % pending[0]["id"], {"kind": "mesma"})

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: decide(), (1, 2)))
            states = [item[1]["state"] for item in results]
            self.assertEqual(states, ["mesma", "mesma"])
            movements = call(server.port, "GET", "/api/snapshot")[1]["movements"]
            self.assertEqual(len(movements), 4)
            code, foreign = call(server.port, "POST", "/api/occurrences/%s/decide" % pending[0]["id"], {"kind": "outra"}, person="paulo")
            self.assertEqual(code, 404)
            code, paulo = call(server.port, "GET", "/api/home", person="paulo")
            self.assertFalse(paulo["projection"]["complete"])
            code, suggestion = call(server.port, "POST", "/api/suggestions", {"reference": "2026-10-16"})
            self.assertEqual(suggestion["status"], "gerada")
            self.assertNotIn("aceita", suggestion["status"])
            code, shown = call(server.port, "POST", "/api/suggestions/%s/events" % suggestion["id"], {"event": "apresentada"})
            self.assertEqual(shown["status"], "apresentada")
            code, refused = call(server.port, "POST", "/api/suggestions/%s/events" % suggestion["id"], {"event": "recusada", "note": "Não quero adiar."})
            self.assertEqual(refused["status"], "recusada")
            code, second = call(server.port, "POST", "/api/suggestions", {"reference": "2026-10-16"})
            call(server.port, "POST", "/api/suggestions/%s/events" % second["id"], {"event": "apresentada"})
            commitments = call(server.port, "GET", "/api/snapshot")[1]["commitments"]
            aluguel = next(item for item in commitments if item["label"] == "Aluguel")
            self.assertEqual(aluguel["due_on"], "2026-10-20")
            code, changed = call(server.port, "POST", "/api/inflows", {"label": "Outra data", "amountCents": 100, "dueOn": "2026-11-01", "state": "confirmada"})
            self.assertEqual(code, 200)
            items = call(server.port, "GET", "/api/suggestions")[1]["items"]
            by_id = {item["id"]: item["status"] for item in items}
            self.assertEqual(by_id[suggestion["id"]], "recusada")
            self.assertEqual(by_id[second["id"]], "desatualizada")
            code, revised = call(server.port, "POST", "/api/suggestions/%s/events" % suggestion["id"], {"event": "corrigida"})
            self.assertEqual(revised["revision_of"], suggestion["id"])
            code, accepted = call(server.port, "POST", "/api/suggestions/%s/events" % revised["id"], {"event": "aceita"})
            self.assertEqual(accepted["status"], "aceita")
            code, accepted_again = call(server.port, "POST", "/api/suggestions/%s/events" % revised["id"], {"event": "aceita"})
            self.assertTrue(accepted_again["repeated"])
            aluguel_after = next(item for item in call(server.port, "GET", "/api/snapshot")[1]["commitments"] if item["label"] == "Aluguel")
            self.assertEqual(aluguel_after["due_on"], aluguel["due_on"])
            self.assertEqual(aluguel_after["original_due_on"], "2026-10-20")
            chosen = [item for item in call(server.port, "GET", "/api/snapshot")[1]["scenarios"] if item["chosen"]]
            self.assertEqual(len(chosen), 1)
            self.assertIn("Custo do adiamento ainda não informado", chosen[0]["note"])
            code, stored = call(server.port, "POST", "/api/files", raw=b"sintetico,apenas\n", headers={"X-ISA-File-Label": "sintetico-anexo", "Content-Type": "text/plain"})
            self.assertEqual(stored["byteLength"], len(b"sintetico,apenas\n"))
            before = call(server.port, "GET", "/api/snapshot")[1]
            server.restart()
            after = call(server.port, "GET", "/api/snapshot")[1]
            self.assertEqual(len(after["commitments"]), len(before["commitments"]))
            self.assertEqual(after["suggestions"][0]["status"], before["suggestions"][0]["status"])
            draft = call(server.port, "GET", "/api/drafts/conferencia")[1]
            self.assertEqual(draft["body"]["step"], "conta")
            code, copied = call(server.port, "POST", "/api/backup", {"name": "prova"})
            self.assertTrue(copied["sameDiskLimitation"])
            isolated = os.path.join(server.tmp, "isolated")
            store.restore_dir(os.path.join(server.backup, "prova"), isolated)
            restored = store.connect(os.path.join(isolated, "isa.sqlite"))
            snap = store.snapshot(restored, "pessoa-marina")
            restored.close()
            self.assertEqual(len(snap["commitments"]), len(before["commitments"]))
            self.assertEqual(len(snap["links"]), len(before["links"]))
            statuses = {item["status"] for item in snap["suggestions"]}
            self.assertIn("recusada", statuses)
            self.assertTrue(any(item["revision_of"] for item in snap["suggestions"]))
            self.assertEqual(snap["files"][0]["sha256"], stored["sha256"])
            self.assertTrue(os.path.isfile(os.path.join(isolated, "files", "pessoa-marina", stored["id"])))
            self.assertEqual(json.loads(snap["drafts"][0]["body_json"])["open"], True)
            code, gone = call(server.port, "POST", "/api/forget")
            self.assertEqual(gone["forgotten"], True)
            self.assertEqual(call(server.port, "GET", "/api/snapshot")[1]["commitments"], [])
            self.assertTrue(os.path.isdir(os.path.join(server.backup, "prova")))
            old = os.path.join(server.backup, "antiga")
            os.makedirs(old)
            with open(os.path.join(old, "manifest.json"), "w", encoding="utf-8") as handle:
                json.dump({"createdAt": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(), "retention": "laboratorio-7-dias"}, handle)
            removed = store.expire_backups(server.backup, days=7)
            self.assertIn("antiga", removed)
            self.assertTrue(os.path.isdir(os.path.join(server.backup, "prova")))
        finally:
            server.stop()
            shutil.rmtree(server.tmp, ignore_errors=True)

    def test_production_refuses_lab_identity(self):
        server = Server(env="production", port=8125)
        try:
            self.assertFalse(server.health["lab"])
            code, payload = call(server.port, "GET", "/api/home")
            self.assertEqual(code, 403)
            self.assertIn("laboratório", payload["error"])
        finally:
            server.stop()
            shutil.rmtree(server.tmp, ignore_errors=True)


class StoreRuleTest(unittest.TestCase):
    def test_series_link_and_old_balance(self):
        tmp = tempfile.mkdtemp(prefix="isa-store-")
        try:
            conn = store.connect(os.path.join(tmp, "isa.sqlite"))
            series = "serie-curso"
            first = store.add_commitment(conn, "pessoa-marina", {"label": "Curso", "totalCents": 10000, "dueOn": "2026-10-10", "seriesId": series, "recurrence": "mensal", "origin": "declarada"})
            second = store.add_commitment(conn, "pessoa-marina", {"label": "Curso", "totalCents": 10000, "dueOn": "2026-11-10", "seriesId": series, "recurrence": "mensal", "origin": "declarada"})
            store.patch_commitment(conn, "pessoa-marina", first["id"], {"dueOn": "2026-10-12"})
            self.assertEqual(store.owned(conn, "commitment", "pessoa-marina", second["id"])["due_on"], "2026-11-10")
            self.assertEqual(store.owned(conn, "commitment", "pessoa-marina", first["id"])["due_on"], "2026-10-12")
            bill = store.add_commitment(conn, "pessoa-marina", {"label": "Parcial", "totalCents": 50000, "dueOn": "2026-10-20", "origin": "declarada"})
            imported = store.import_batch(conn, "pessoa-marina", {"batchKey": "pago", "origin": "exemplo-sintetico", "movements": [{"signature": "p", "date": "2026-10-19", "cents": 20000, "direction": "saida", "label": "Parte", "nature": "a_conferir"}]})
            movement = store.one(conn, "SELECT id FROM movement WHERE owner_id = ?", ("pessoa-marina",))
            linked = store.link_movement(conn, "pessoa-marina", {"movementId": movement["id"], "commitmentId": bill["id"], "amountCents": 20000, "confirmed": True})
            self.assertEqual(linked["commitment"]["remaining_cents"], 30000)
            again = store.link_movement(conn, "pessoa-marina", {"movementId": movement["id"], "commitmentId": bill["id"], "confirmed": True})
            self.assertTrue(again["repeated"])
            self.assertEqual(store.owned(conn, "commitment", "pessoa-marina", bill["id"])["remaining_cents"], 30000)
            store.add_observation(conn, "pessoa-marina", {"amountCents": 99900, "asOf": "2026-09-30", "kind": "saldo_informado", "source": "extrato-antigo"})
            self.assertFalse(store.home(conn, "pessoa-marina")["projection"]["complete"])
            self.assertEqual(imported["imported"], 1)
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
