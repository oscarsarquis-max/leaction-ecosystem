"""Recorte da área de trabalho. A lista visível tem de coincidir com a área inteira filtrada."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import store
import test_http
import test_lancamento_005t3 as photo
import workbatches


MONTH_CASES = [
    ({"status": "pago", "statusDate": "2026-10-02", "dueDate": "2026-11-02", "noteDate": "2026-09-02"}, "2026-10"),
    ({"status": "a_pagar", "dueDate": "2026-11-20", "noteDate": "2026-10-02"}, "2026-11"),
    ({"status": "pago", "noteDate": "2026-08-01"}, "2026-08"),
    ({}, ""),
]


def node_compare(payload):
    folder = tempfile.TemporaryDirectory()
    path = os.path.join(folder.name, "payload.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    done = subprocess.run(
        ["node", "prototype/recorte.test.mjs", "--compare", path],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    folder.cleanup()
    if done.returncode != 0:
        raise AssertionError(done.stderr or done.stdout)
    return json.loads(done.stdout)


def plant_special(conn, owner, bulk=0):
    account = store.save_account(conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente", "institution": "Banco do Brasil S.A."})
    if bulk:
        months = ["2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01"]
        movements = [{
            "signature": "vol-%s-%s" % (owner, i),
            "date": "%s-%02d" % (months[i % 6], (i % 27) + 1),
            "cents": 100 + (i % 400) if i % 3 == 0 else -(100 + (i % 400)),
            "direction": "entrada" if i % 3 == 0 else "saida",
            "label": "Volume %s %s" % (i, owner),
            "nature": "consumo",
            "accountId": account["id"],
        } for i in range(bulk)]
        store.import_batch(conn, owner, {"batchKey": "vol-" + owner, "origin": "extrato-bb-arquivo", "movements": movements})
    batch = workbatches.create_batch(conn, owner, {"name": "Obra " + owner, "criterion": "outro", "documentRef": "DOC-" + owner, "supplier": "Fornecedor"})
    specs = [
        {"id": "ago-" + owner, "merchant": "Agosto " + owner, "amountMinor": 1500, "direction": "gasto", "status": "pago", "statusDate": "2026-08-10", "nature": "consumo", "category": "Moradia", "accountId": account["id"], "workBatchId": batch["id"]},
        {"id": "out-" + owner, "merchant": "Outubro " + owner, "amountMinor": 3200, "direction": "gasto", "status": "pago", "statusDate": "2026-10-10", "nature": "consumo", "category": "Alimentação", "accountId": account["id"], "workBatchId": batch["id"]},
        {"id": "par-out-" + owner, "merchant": "Extrato ligado", "amountMinor": 8800, "direction": "gasto", "status": "pago", "statusDate": "2026-10-08", "nature": "a_conferir", "source": "extrato-bb-arquivo", "accountId": account["id"], "linkId": "par-set-" + owner},
        {"id": "par-set-" + owner, "merchant": "Manual ligado", "amountMinor": 8800, "direction": "gasto", "status": "pago", "statusDate": "2026-09-08", "nature": "consumo", "category": "Moradia", "source": "digitado", "accountId": account["id"]},
        {"id": "arq-" + owner, "merchant": "Arquivado " + owner, "amountMinor": 400, "direction": "gasto", "status": "pago", "statusDate": "2026-10-11", "nature": "consumo", "category": "Outros", "archived": True, "accountId": account["id"]},
        {"id": "vence-" + owner, "merchant": "Vence em novembro", "amountMinor": 700, "direction": "gasto", "status": "a_pagar", "statusDate": "", "dueDate": "2026-11-03", "noteDate": "2026-10-02", "nature": "consumo", "accountId": account["id"]},
        {"id": "aberto-" + owner, "merchant": "Aberto deste mês", "amountMinor": 640, "direction": "ganho", "status": "a_receber", "statusDate": "", "dueDate": "2026-10-20", "noteDate": "2026-09-01", "nature": "consumo", "category": "Serviços", "accountId": account["id"]},
        {"id": "usd-" + owner, "merchant": "Dólar " + owner, "amountMinor": 300, "direction": "gasto", "status": "pago", "statusDate": "2026-10-12", "nature": "consumo", "currency": "USD", "category": "Compras"},
        {"id": "pad-" + owner, "merchant": "Padaria do teste", "amountMinor": 1250, "direction": "gasto", "status": "pago", "statusDate": "2026-10-06", "nature": "consumo", "category": "Alimentação", "accountId": account["id"], "documentId": "NF-" + owner},
    ]
    for spec in specs:
        store.save_entry(conn, owner, spec)
    return account, batch


def full_entries(conn, owner):
    page = store.workspace(conn, owner, cut={"kind": "all", "archived": True})
    return page


def view(name, page, filters, month="2026-10", whole=False):
    return {
        "name": name,
        "entries": page["entries"],
        "filters": filters,
        "month": month,
        "calcMonth": "2026-10",
        "wholeCalc": whole,
        "batches": (page.get("workBatches") or {}).get("items") or [],
    }


class RecorteTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get("ISA_ENV")
        os.environ["ISA_ENV"] = "lab"
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.connect(os.path.join(self.tmp.name, "isa.sqlite"))

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()
        if self.prev is None:
            os.environ.pop("ISA_ENV", None)
        else:
            os.environ["ISA_ENV"] = self.prev

    def test_list_month_matches_lotes(self):
        payload = {"full": [], "views": [], "months": [{"entry": entry, "expect": expect} for entry, expect in MONTH_CASES]}
        node_compare(payload)
        for entry, expect in MONTH_CASES:
            self.assertEqual(store.list_month(entry), expect)

    def test_equivalence_for_people_and_a_large_set(self):
        people = [
            ("pessoa-marina", 0),
            ("pessoa-paulo", 0),
            ("pessoa-eveline-demo", 0),
            ("pessoa-sintetica", 2100),
        ]
        for owner, bulk in people:
            account, batch = plant_special(self.conn, owner, bulk)
            whole = full_entries(self.conn, owner)
            month = store.workspace(self.conn, owner, cut=store.parse_cut({"month": ["2026-10"]}, ""))
            archived = store.workspace(self.conn, owner, cut=store.parse_cut({"month": ["2026-10"], "archived": ["1"]}, ""))
            lot = store.workspace(self.conn, owner, cut=store.parse_cut({"batch": [batch["id"]]}, ""))
            period = store.workspace(self.conn, owner, cut=store.parse_cut({"from": ["2026-09-01"], "to": ["2026-10-15"]}, ""))
            everything = store.workspace(self.conn, owner, cut=store.parse_cut({"scope": ["all"]}, ""))
            self.assertGreaterEqual(store.one(self.conn, "SELECT COUNT(*) AS n FROM ledger_entry WHERE owner_id = ?", (owner,))["n"], 9 if not bulk else 2100)
            self.assertNotIn("banks", month)
            self.assertNotIn("bankCatalog", month)
            self.assertEqual(month["slice"], "month=2026-10")
            partner = next(item for item in month["entries"] if item["id"] == "par-set-" + owner)
            self.assertTrue(partner.get("outsideSlice"))
            self.assertTrue(any(item["id"] == "ago-" + owner and item.get("outsideSlice") for item in month["entries"]))
            self.assertFalse(any(item["id"] == "vence-" + owner and not item.get("outsideSlice") for item in month["entries"]))
            self.assertTrue(any(item["id"] == "aberto-" + owner and not item.get("outsideSlice") for item in month["entries"]))
            shown = [item["id"] for item in lot["entries"] if not item.get("outsideSlice")]
            self.assertIn("ago-" + owner, shown)
            self.assertIn("out-" + owner, shown)
            card = next(item for item in month["workBatches"]["items"] if item["id"] == batch["id"])
            self.assertGreaterEqual(card["count"], 2)
            self.assertIn("totals", card)
            own_account = store.workspace(self.conn, owner, account["id"], store.parse_cut({"month": ["2026-10"]}, ""))
            self.assertTrue(all(item.get("accountId") in ("", account["id"]) or item.get("outsideSlice") for item in own_account["entries"]))
            payload = {
                "full": whole["entries"],
                "batches": whole["workBatches"]["items"],
                "monthEntries": month["entries"],
                "partnerId": "par-set-" + owner,
                "calcMonth": "2026-10",
                "views": [
                    view("mês " + owner, month, {}, whole=True),
                    view("lote " + owner, lot, {"batchId": batch["id"]}),
                    view("todos " + owner, everything, {"mode": "todos-meses"}),
                    view("período " + owner, period, {"mode": "todos-meses", "dateFrom": "2026-09-01", "dateTo": "2026-10-15"}),
                    view("arquivados " + owner, archived, {"archived": True}),
                    view("realizados " + owner, month, {"quick": "realizados"}),
                    view("previstos " + owner, month, {"quick": "previstos"}),
                    view("conferir " + owner, month, {"quick": "conferir"}),
                    view("direção " + owner, month, {"direction": "gasto"}),
                    view("categoria " + owner, month, {"category": "Alimentação"}),
                    view("situação " + owner, month, {"status": "pago"}),
                    view("moeda " + owner, month, {"currency": "USD"}),
                    view("busca " + owner, month, {"q": "padaria"}),
                    view("resultado " + owner, month, {"mode": "resultado"}),
                    view("consumo " + owner, month, {"consumption": True}),
                ],
            }
            node_compare(payload)
            other = "pessoa-outra"
            store.save_entry(self.conn, other, {"id": "alheio", "merchant": "Alheio", "amountMinor": 8800, "direction": "gasto", "status": "pago", "statusDate": "2026-10-08", "nature": "consumo", "documentId": "NF-" + owner})
            self.assertIsNone(store.read_entry(self.conn, owner, "alheio"))
            self.assertEqual(store.read_entry(self.conn, owner, "par-set-" + owner)["merchant"], "Manual ligado")
            leaked = store.duplicate_check(self.conn, other, {"merchant": "Novo", "noteDate": "2026-10-06", "amountMinor": 1250, "documentId": "NF-" + owner})
            self.assertEqual(leaked.get("kind"), "documento")
            hidden = store.duplicate_check(self.conn, owner, {"merchant": "Alheio", "noteDate": "2026-10-08", "amountMinor": 8800, "documentId": "alheio-doc"})
            self.assertNotEqual(hidden.get("entry", {}).get("id"), "alheio")

    def test_duplicate_matches_calc(self):
        owner = "pessoa-marina"
        account = store.save_account(self.conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente"})
        planted = [
            {"id": "d1", "merchant": "Padaria", "noteDate": "2026-10-03", "statusDate": "2026-10-03", "amountMinor": 2500, "direction": "gasto", "status": "pago", "nature": "consumo", "documentId": "NF-1", "accountId": account["id"]},
            {"id": "d2", "merchant": "Outro", "noteDate": "2026-10-04", "statusDate": "2026-10-04", "amountMinor": 2500, "direction": "gasto", "status": "pago", "nature": "consumo", "fingerprint": "abc", "accountId": account["id"]},
            {"id": "d3", "merchant": "Mercado", "noteDate": "2026-10-05", "statusDate": "2026-10-05", "amountMinor": 900, "direction": "gasto", "status": "pago", "nature": "consumo", "accountId": account["id"]},
        ]
        for spec in planted:
            store.save_entry(self.conn, owner, spec)
        entries = [json.loads(row["payload_json"]) for row in store.rows(self.conn, "SELECT payload_json FROM ledger_entry WHERE owner_id = ? ORDER BY booked_on, id", (owner,))]
        cases = [
            {"merchant": "X", "noteDate": "2026-01-01", "amountMinor": 1, "documentId": "NF-1"},
            {"merchant": "X", "noteDate": "2026-01-01", "amountMinor": 1, "fingerprint": "abc"},
            {"merchant": "padaria", "noteDate": "2026-10-03", "amountMinor": 2500},
            {"merchant": "Novo", "noteDate": "2026-10-05", "amountMinor": 900},
            {"id": "d3", "merchant": "Mercado", "noteDate": "2026-10-05", "amountMinor": 900},
            {"merchant": "Arquivado", "noteDate": "2026-10-03", "amountMinor": 2500, "documentId": "NF-9"},
        ]
        found = node_compare({"full": [], "views": [], "duplicates": cases, "dupEntries": entries})["duplicates"]
        for candidate, expected in zip(cases, found):
            got = store.duplicate_check(self.conn, owner, candidate)
            if expected.get("kind"):
                self.assertEqual(got.get("kind"), expected["kind"])
                self.assertEqual(got["entry"]["id"], expected["id"])
            else:
                self.assertFalse(got.get("kind"))
                self.assertEqual(bool(got.get("soft")), bool(expected.get("soft")))
        self.assertIsNone(store.read_entry(self.conn, "pessoa-paulo", "d1"))

    def test_write_returns_the_sent_slice(self):
        owner = "pessoa-paulo"
        account = store.save_account(self.conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente"})
        store.save_entry(self.conn, owner, {"id": "out", "merchant": "Outubro", "amountMinor": 100, "direction": "gasto", "status": "pago", "statusDate": "2026-10-02", "nature": "consumo", "accountId": account["id"]})
        store.save_entry(self.conn, owner, {"id": "set", "merchant": "Setembro", "amountMinor": 100, "direction": "gasto", "status": "pago", "statusDate": "2026-09-02", "nature": "consumo", "accountId": account["id"]})
        sent = store.parse_cut({}, "month=2026-09")
        page = store.workspace(self.conn, owner, cut=sent)
        self.assertEqual(page["slice"], "month=2026-09")
        self.assertIn("set", [item["id"] for item in page["entries"] if not item.get("outsideSlice")])
        self.assertNotIn("out", [item["id"] for item in page["entries"] if not item.get("outsideSlice")])
        current = store.workspace(self.conn, owner)
        self.assertEqual(current["slice"], "month=" + store.today()[:7])
        self.assertNotEqual(len(current["entries"]), len(full_entries(self.conn, owner)["entries"]))

    def test_banks_document_and_october_scene(self):
        body, tag = store.banks_document()
        again, tag_again = store.banks_document()
        self.assertEqual(tag, tag_again)
        self.assertGreater(len(body), 1000)
        parsed = json.loads(body)
        self.assertIn("banks", parsed)
        self.assertIn("bankCatalog", parsed)
        page = store.workspace(self.conn, "pessoa-marina")
        self.assertNotIn("banks", page)
        self.assertNotIn("bankCatalog", page)
        bb, _poup = photo.plant_october(self.conn, "pessoa-marina")
        home = store.home(self.conn, "pessoa-marina", "2026-10-26")
        self.assertEqual(home["balance"]["cents"], 120000)
        self.assertEqual(home["month"]["forecastOut"], 135000)
        self.assertEqual(home["projection"]["first_insufficiency"], "2026-10-28")
        day = next(item for item in home["projection"]["days"] if item["date"] == "2026-10-28")
        self.assertEqual(day["cents"], -15000)
        close = next(item for item in home["projection"]["days"] if item["date"] == "2026-10-30")
        self.assertEqual(close["cents"], 135000)
        self.assertEqual(home["balance"]["protectedCents"], 20000)
        self.assertEqual(home["projection"]["margin"]["capacity_cents"], 0)
        one = store.home(self.conn, "pessoa-marina", "2026-10-26", account=bb["id"])
        self.assertEqual(one["balance"]["cents"], 100000)
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 12)

    def test_http_slice_detail_and_banks(self):
        server = test_http.Server(port=8138)
        try:
            code, denied = request(server.port, "GET", "/api/banks")
            self.assertEqual(code, 401)
            code, catalog, headers = request(server.port, "GET", "/api/banks", person="marina", headers_out=True)
            self.assertEqual(code, 200)
            self.assertIn("banks", catalog)
            tag = header_value(headers, "ETag")
            self.assertTrue(tag)
            self.assertIn("max-age=86400", header_value(headers, "Cache-Control"))
            code, empty, _headers = request(server.port, "GET", "/api/banks", person="marina", extra={"If-None-Match": tag}, headers_out=True)
            self.assertEqual(code, 304)
            self.assertEqual(empty, b"")
            code, created = request(server.port, "POST", "/api/entries", person="marina", body={"entry": {
                "merchant": "Setembro", "amountMinor": 100, "direction": "gasto", "status": "pago",
                "statusDate": "2026-09-02", "noteDate": "2026-09-02", "nature": "consumo",
            }}, extra={"X-ISA-Slice": "month=2026-09"})
            self.assertEqual(code, 200)
            self.assertEqual(created["workspace"]["slice"], "month=2026-09")
            self.assertNotIn("banks", created["workspace"])
            self.assertTrue(any(item["id"] == created["entry"]["id"] for item in created["workspace"]["entries"]))
            code, current = request(server.port, "GET", "/api/workspace", person="marina")
            self.assertEqual(current["slice"], "month=" + store.today()[:7])
            self.assertFalse(any(item["id"] == created["entry"]["id"] and not item.get("outsideSlice") for item in current["entries"]))
            code, detail = request(server.port, "GET", "/api/entries/" + created["entry"]["id"], person="marina")
            self.assertEqual(code, 200)
            self.assertEqual(detail["merchant"], "Setembro")
            code, missing = request(server.port, "GET", "/api/entries/" + created["entry"]["id"], person="paulo")
            self.assertEqual(code, 404)
            code, dup = request(server.port, "POST", "/api/entries/duplicate-check", person="marina", body={"entry": {
                "merchant": "Outro", "noteDate": "2026-09-02", "statusDate": "2026-09-02", "amountMinor": 100, "direction": "gasto",
            }})
            self.assertEqual(code, 200)
            self.assertTrue(dup.get("kind") or dup.get("soft"))
        finally:
            server.stop()

    def test_measurement(self):
        table = []
        for count in (0, 2000, 5000):
            folder = tempfile.TemporaryDirectory()
            conn = store.connect(os.path.join(folder.name, "isa.sqlite"))
            owner = "pessoa-medida"
            try:
                batch_id = ""
                if count:
                    account = store.save_account(conn, owner, {"name": "Banco do Brasil", "currency": "BRL", "kind": "corrente"})
                    months = ["2026-08", "2026-09", "2026-10", "2026-11"]
                    movements = [{
                        "signature": "med-%s" % i,
                        "date": "%s-%02d" % (months[i % 4], (i % 27) + 1),
                        "cents": 100 + i if i % 2 == 0 else -(100 + i),
                        "direction": "entrada" if i % 2 == 0 else "saida",
                        "label": "Medida %s" % i,
                        "nature": "consumo",
                        "accountId": account["id"],
                    } for i in range(count)]
                    store.import_batch(conn, owner, {"batchKey": "medida", "origin": "extrato-bb-arquivo", "movements": movements})
                def take(cut):
                    proxy = CountConn(conn)
                    started = time.perf_counter()
                    page = store.workspace(proxy, owner, cut=cut)
                    elapsed = (time.perf_counter() - started) * 1000
                    raw = json.dumps(page).encode("utf-8")
                    return {"queries": proxy.n, "ms": round(elapsed, 1), "bytes": len(raw), "entries": len(page["entries"])}

                month_cut = store.parse_cut({"month": ["2026-10"]}, "")
                plain = take(month_cut)
                if count:
                    batch = workbatches.create_batch(conn, owner, {"name": "Lote medida", "criterion": "outro", "activate": False})
                    batch_id = batch["id"]
                    stamp = store.now()
                    conn.execute("BEGIN IMMEDIATE")
                    try:
                        for row in store.rows(conn, "SELECT id FROM ledger_entry WHERE owner_id = ?", (owner,)):
                            conn.execute(
                                "INSERT INTO work_member (batch_id, entry_id, owner_id, active, added_at) VALUES (?,?,?,?,?)",
                                (batch_id, row["id"], owner, 1, stamp),
                            )
                        conn.execute("COMMIT")
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                table.append({
                    "lancamentos": count,
                    "month": plain,
                    "batch": take(store.parse_cut({"batch": [batch_id or "nenhum"]}, "")),
                    "all": take({"kind": "all", "archived": False}),
                })
            finally:
                conn.close()
                folder.cleanup()
        banks = len(store.banks_document()[0])
        print("MEDICAO_RECORTE " + json.dumps({"table": table, "banks_bytes": banks}, ensure_ascii=False))
        self.assertLess(table[-1]["month"]["bytes"], table[-1]["all"]["bytes"])
        self.assertGreater(banks, 1000)


class CountConn:
    def __init__(self, conn):
        self._conn = conn
        self.n = 0

    def execute(self, sql, *args, **kwargs):
        if str(sql).lstrip().upper().startswith("SELECT"):
            self.n += 1
        return self._conn.execute(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def header_value(headers, name):
    for key, value in headers:
        if key.lower() == name.lower():
            return value
    return ""


def request(port, method, path, person="", body=None, extra=None, headers_out=False):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:%s%s" % (port, path), data=data, method=method)
    if person:
        req.add_header("X-ISA-Lab-Person", person)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (extra or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = response.read()
            content = response.headers.get("Content-Type") or ""
            parsed = json.loads(payload.decode("utf-8")) if payload[:1] in (b"{", b"[") else payload
            if headers_out:
                return response.status, parsed, list(response.headers.items())
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        parsed = json.loads(raw.decode("utf-8")) if raw[:1] in (b"{", b"[") else raw
        exc.close()
        if headers_out:
            return exc.code, parsed, list(exc.headers.items())
        return exc.code, parsed


class PostgresRecorteTests(unittest.TestCase):
    def setUp(self):
        import test_pg
        self.prev = os.environ.get("ISA_ENV")
        os.environ["ISA_ENV"] = "lab"
        self.name = "isa_rec_" + store._id()[:12]
        self.url = test_pg.prepare(self.name)
        self.conn = store.connect(self.url)

    def tearDown(self):
        self.conn.close()
        import psycopg
        import test_pg
        admin = psycopg.connect(test_pg.ADMIN, autocommit=True)
        admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (self.name,))
        admin.execute("DROP DATABASE IF EXISTS " + self.name)
        admin.close()
        if self.prev is None:
            os.environ.pop("ISA_ENV", None)
        else:
            os.environ["ISA_ENV"] = self.prev

    def test_slice_and_scene_on_postgres(self):
        account, batch = plant_special(self.conn, "pessoa-marina", 0)
        month = store.workspace(self.conn, "pessoa-marina", cut=store.parse_cut({"month": ["2026-10"]}, ""))
        self.assertEqual(month["slice"], "month=2026-10")
        self.assertTrue(any(item["id"] == "par-set-pessoa-marina" and item.get("outsideSlice") for item in month["entries"]))
        self.assertIsNone(store.read_entry(self.conn, "pessoa-paulo", "out-pessoa-marina"))
        self.assertEqual(store.one(self.conn, "SELECT MAX(version) AS v FROM schema_migration")["v"], 12)
        bb, _poup = photo.plant_october(self.conn, "pessoa-paulo")
        home = store.home(self.conn, "pessoa-paulo", "2026-10-26")
        self.assertEqual(home["balance"]["cents"], 120000)
        one = store.home(self.conn, "pessoa-paulo", "2026-10-26", account=bb["id"])
        self.assertEqual(one["balance"]["cents"], 100000)
        self.assertEqual(batch["id"][:1], batch["id"][:1])
        self.assertEqual(account["currency"], "BRL")
