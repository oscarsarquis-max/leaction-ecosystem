"""Testa integrações PanelDX ↔ ActionHub em ambiente local."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

PANELDX_FLASK = os.environ.get("PANELDX_FLASK", "http://127.0.0.1:5002")
PANELDX_BFF = os.environ.get("PANELDX_BFF", "http://127.0.0.1:3000")
HUB_GATEWAY = os.environ.get("HUB_GATEWAY", "http://127.0.0.1:4001")
ACTION_HUB = os.environ.get("ACTION_HUB", "http://127.0.0.1:4000")

PASS = 0
FAIL = 0
WARN = 0


def discover_test_matu() -> tuple[str, str]:
    """Busca id_matu + email no Postgres local do PanelDX."""
    try:
        from dotenv import load_dotenv
        import psycopg2

        load_dotenv(ROOT / "LeAction_SysF" / ".env")
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            dbname=os.getenv("DB_NAME", "LeAction_SysF"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", ""),
        )
        cur = conn.cursor()
        email = os.environ.get("TEST_EMAIL", "").strip()
        if email:
            cur.execute(
                """
                SELECT m.id_matu, c.mail_clie
                FROM ctdi_matu m
                JOIN ctdi_clie c ON c.id_clie = m.id_clie
                WHERE lower(c.mail_clie) = lower(%s)
                ORDER BY m.id_matu DESC LIMIT 1
                """,
                (email,),
            )
        else:
            cur.execute(
                """
                SELECT m.id_matu, c.mail_clie
                FROM ctdi_matu m
                JOIN ctdi_clie c ON c.id_clie = m.id_clie
                ORDER BY m.id_matu DESC LIMIT 1
                """
            )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return str(row[0]), (row[1] or "").strip()
    except Exception as exc:
        warn("Descoberta id_matu no DB", str(exc))
    return os.environ.get("TEST_ID_MATU", "1"), os.environ.get("TEST_EMAIL", "dev@leaction.com.br")


def http(method: str, url: str, body: dict | None = None, headers: dict | None = None):
    data = None
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if body is not None:
        hdrs["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed, raw[:300]
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"_raw": raw[:300]}
        return exc.code, parsed, raw[:300]


def ok(name: str, detail: str = ""):
    global PASS
    PASS += 1
    print(f"  OK {name}" + (f" - {detail}" if detail else ""))


def bad(name: str, detail: str = ""):
    global FAIL
    FAIL += 1
    print(f"  FAIL {name}" + (f" - {detail}" if detail else ""))


def warn(name: str, detail: str = ""):
    global WARN
    WARN += 1
    print(f"  WARN {name}" + (f" - {detail}" if detail else ""))


def section(title: str):
    print(f"\n== {title} ==")


def expect_json_status(name: str, method: str, url: str, expected: int | tuple, body=None, headers=None):
    try:
        status, data, raw = http(method, url, body, headers)
    except URLError as exc:
        bad(name, f"sem conexão: {exc.reason}")
        return None, None
    exp = (expected,) if isinstance(expected, int) else expected
    if status in exp:
        ok(name, f"HTTP {status}")
    else:
        bad(name, f"HTTP {status} (esperado {exp}) — {raw}")
    return status, data


def main() -> int:
    print("PanelDX <-> ActionHub - teste local de integracoes")
    print(f"  Flask {PANELDX_FLASK} | BFF {PANELDX_BFF} | Gateway {HUB_GATEWAY} | ActionHub {ACTION_HUB}")

    section("1. Proxies e APIs públicas")
    expect_json_status(
        "PanelDX BFF → Hub /config/payments",
        "GET",
        f"{PANELDX_BFF}/hub-api/config/payments",
        200,
    )
    expect_json_status(
        "ActionHub → Hub /config/payments",
        "GET",
        f"{ACTION_HUB}/hub-api/config/payments",
        200,
    )
    st, data = expect_json_status(
        "PanelDX Flask vitrine pública",
        "GET",
        f"{PANELDX_FLASK}/api/public/vitrine/planos",
        200,
    )
    planos = (data or {}).get("planos") if data else []
    if st == 200 and isinstance(planos, list) and planos:
        ok("Vitrine Flask tem planos", str(len(planos)))
    elif st == 200:
        warn("Vitrine Flask vazia", "publique no /admin/crm")

    st, data = expect_json_status(
        "ActionHub proxy → PanelDX vitrine",
        "GET",
        f"{ACTION_HUB}/paneldx-api/api/public/vitrine/planos",
        200,
    )

    section("2. Vitrine sync PanelDX → Gateway")
    if not planos:
        warn("Sync vitrine", "pulado — sem planos no Flask")
    else:
        sync_id = str(uuid.uuid4())
        st, data = expect_json_status(
            "POST /v1/vitrine/paneldx/sync",
            "POST",
            f"{HUB_GATEWAY}/v1/vitrine/paneldx/sync",
            200,
            {
                "sync_id": sync_id,
                "source": "paneldx",
                "published_at": "2026-06-27T12:00:00Z",
                "planos": planos[:3],
            },
        )
        if data and data.get("received"):
            ok("Gateway confirmou recebimento", f"sync {str(data.get('sync_id', ''))[:8]}")

        st, snap = expect_json_status(
            "GET /v1/vitrine/paneldx snapshot",
            "GET",
            f"{HUB_GATEWAY}/v1/vitrine/paneldx",
            (200, 404),
        )
        if st == 200 and isinstance((snap or {}).get("planos"), list) and snap["planos"]:
            ok("Snapshot Hub com planos", str(len(snap["planos"])))
        elif st == 404:
            warn("Snapshot Hub", "tabela paneldx_vitrine_snapshots ausente?")

    section("3. Assessment checkout (PANEL_MATURIDADE)")
    id_matu, test_email = discover_test_matu()
    print(f"  Usando id_matu={id_matu} email={test_email}")
    webhook = f"{PANELDX_FLASK}/api/hub/payment-webhook"

    st, created = expect_json_status(
        "Criar pedido assessment via BFF proxy",
        "POST",
        f"{PANELDX_BFF}/hub-api/v1/payments",
        (201, 200),
        {
            "client_id": "paneldx",
            "sku": "PANEL_MATURIDADE",
            "amount": 1,
            "id_matu": str(id_matu),
            "customer": {"email": test_email, "name": "E2E Local"},
            "webhook_url": webhook,
            "hub_public_url": ACTION_HUB,
            "return_to": "/projeto",
            "return_origin": PANELDX_BFF,
        },
    )
    order_id = (created or {}).get("payment_id") if created else None
    if order_id:
        ok("payment_id gerado", str(order_id)[:8] + "…")
        st, sim = expect_json_status(
            "Simular pagamento + webhook assessment",
            "POST",
            f"{HUB_GATEWAY}/simular-pagamento",
            200,
            {"order_id": order_id},
        )
        if sim and sim.get("webhook_delivered"):
            ok("Webhook assessment entregue ao PanelDX")
        elif sim:
            bad("Webhook assessment", f"webhook_delivered={sim.get('webhook_delivered')}")

    section("4. Subscription checkout (PANELDX_SUBSCRIPTION)")
    if not planos:
        warn("Pedido subscription", "pulado — sem planos")
    else:
        plano = planos[0]
        st, sub = expect_json_status(
            "Criar pedido subscription no gateway",
            "POST",
            f"{HUB_GATEWAY}/v1/payments",
            (201, 200),
            {
                "client_id": "paneldx",
                "sku": "PANELDX_SUBSCRIPTION",
                "amount": plano.get("valor_mensal", 99),
                "id_clie": int(os.environ.get("TEST_ID_CLIE", "1")),
                "id_plano": plano.get("id", 1),
                "plano_nome": plano.get("nome", "Plano"),
                "customer": {"email": test_email, "name": "Cliente PanelDX"},
                "webhook_url": webhook,
                "hub_public_url": ACTION_HUB,
                "return_to": "/meu-plano",
                "return_origin": PANELDX_BFF,
            },
        )
        sub_order = (sub or {}).get("payment_id") if sub else None
        if sub_order:
            ok("payment_id subscription", str(sub_order)[:8] + "…")
            st, sim = expect_json_status(
                "Simular pagamento subscription",
                "POST",
                f"{HUB_GATEWAY}/simular-pagamento",
                200,
                {"order_id": sub_order},
            )
            if sim and sim.get("webhook_delivered"):
                warn(
                    "Webhook subscription entregue",
                    "PanelDX ainda exige id_matu numérico — contrato CRM pode não ativar",
                )
            elif sim:
                warn("Webhook subscription", f"webhook_delivered={sim.get('webhook_delivered')}")

    section("5. URLs de checkout ActionHub")
    for path in ("/checkout/paneldx?client_id=1&email=dev@leaction.com.br", "/"):
        try:
            req = Request(f"{ACTION_HUB}{path}", headers={"Accept": "text/html"})
            with urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    ok(f"ActionHub GET {path.split('?')[0]}", f"HTTP {resp.status}")
                else:
                    bad(f"ActionHub GET {path.split('?')[0]}", f"HTTP {resp.status}")
        except HTTPError as exc:
            if exc.code in (200, 307, 308):
                ok(f"ActionHub GET {path.split('?')[0]}", f"HTTP {exc.code}")
            else:
                bad(f"ActionHub GET {path.split('?')[0]}", f"HTTP {exc.code}")
        except URLError as exc:
            bad(f"ActionHub GET {path.split('?')[0]}", str(exc.reason))

    section("Resumo")
    print(f"  Passou: {PASS} | Falhou: {FAIL} | Avisos: {WARN}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
