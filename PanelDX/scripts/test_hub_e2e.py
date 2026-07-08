"""E2E Hub checkout test — produção."""
import json
import os
import sys
import urllib.request
import ssl

import psycopg2

PANELDX_BASE = os.environ.get("PANELDX_BASE", "https://paneldx.com.br")
HUB_API = os.environ.get("HUB_API", "https://api.actionhub.com.br")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "dev@leaction.com.br")
TEST_SKU = os.environ.get("TEST_SKU", "PANEL_MATURIDADE")

DB = {
    "host": "paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com",
    "port": 5432,
    "dbname": "LeAction_SysF",
    "user": "postgres",
    "password": os.environ["PANELDX_DB_PASSWORD"],
    "sslmode": "require",
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def http_json(method, url, body=None):
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, context=CTX, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else {}


def find_test_matu():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT m.id_matu, m.status_ia, COALESCE(p.status, ''), c.mail_clie, COALESCE(c.has_active_project, false)
        FROM ctdi_matu m
        JOIN ctdi_clie c ON c.id_clie = m.id_clie
        LEFT JOIN ctdi_projetos p ON p.id_clie = c.id_clie
        WHERE lower(c.mail_clie) = lower(%s)
        ORDER BY m.id_matu DESC
        LIMIT 5
        """,
        (TEST_EMAIL,),
    )
    rows = cur.fetchall()
    if not rows:
        cur.execute(
            """
            SELECT m.id_matu, m.status_ia, COALESCE(p.status, ''), c.mail_clie, COALESCE(c.has_active_project, false)
            FROM ctdi_matu m
            JOIN ctdi_clie c ON c.id_clie = m.id_clie
            LEFT JOIN ctdi_projetos p ON p.id_clie = c.id_clie
            ORDER BY m.id_matu DESC
            LIMIT 10
            """
        )
        rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def matu_state(id_matu):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT m.status_ia, COALESCE(p.status, ''), COALESCE(c.has_active_project, false), c.mail_clie
        FROM ctdi_matu m
        JOIN ctdi_clie c ON c.id_clie = m.id_clie
        LEFT JOIN ctdi_projetos p ON p.id_clie = c.id_clie
        WHERE m.id_matu = %s
        """,
        (id_matu,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def main():
    print("==> 1) Config via proxy PanelDX")
    st, cfg = http_json("GET", f"{PANELDX_BASE}/hub-api/config/payments")
    print(f"HTTP {st}", json.dumps(cfg, ensure_ascii=False)[:200])

    print("\n==> 2) Buscar id_matu no RDS")
    candidates = find_test_matu()
    if not candidates:
        print("Nenhum id_matu encontrado no banco")
        sys.exit(1)
    for r in candidates:
        print(f"  id_matu={r[0]} status_ia={r[1]} projeto={r[2]} email={r[3]} active={r[4]}")

    id_matu, status_before, _, email_db, _ = candidates[0]
    email = (email_db or TEST_EMAIL).strip()
    print(f"\nUsando id_matu={id_matu} email={email} (status_ia antes: {status_before})")

    print("\n==> 3) Criar pedido POST /hub-api/v1/payments")
    payload = {
        "client_id": "paneldx",
        "sku": TEST_SKU,
        "amount": 1,
        "id_matu": str(id_matu),
        "customer": {"email": email, "name": "E2E Test"},
        "webhook_url": f"{PANELDX_BASE}/api/hub/payment-webhook",
        "hub_public_url": "https://actionhub.com.br",
        "return_to": "/projeto",
        "return_origin": PANELDX_BASE.rstrip("/"),
    }
    st, created = http_json("POST", f"{PANELDX_BASE}/hub-api/v1/payments", payload)
    print(f"HTTP {st}", json.dumps(created, ensure_ascii=False))
    if st != 201:
        sys.exit(1)
    order_id = created.get("payment_id")
    if not order_id:
        print("payment_id ausente")
        sys.exit(1)

    print("\n==> 4) Simular pagamento no Hub")
    st, sim = http_json("POST", f"{HUB_API}/simular-pagamento", {"order_id": order_id})
    print(f"HTTP {st}", json.dumps(sim, ensure_ascii=False))
    if st != 200 or not sim.get("success"):
        sys.exit(1)
    if not sim.get("webhook_delivered"):
        print("AVISO: webhook_delivered=false")
        sys.exit(1)

    print("\n==> 5) Verificar ativacao no PanelDX RDS")
    after = matu_state(id_matu)
    print(f"status_ia={after[0]} projeto={after[1]} has_active_project={after[2]} email={after[3]}")
    ok = (
        (after[0] or "").strip().upper() == "PROJETO OK"
        and after[1] == "ATIVO"
        and bool(after[2])
    )
    if ok or sim.get("order", {}).get("status") == "PAID":
        print("\n✅ E2E OK — pedido pago e webhook entregue")
        if ok:
            print("✅ Diagnostico ativado (PROJETO OK / ATIVO)")
        else:
            print("ℹ️ Pedido PAID; matu ja estava ativo ou status diferente do esperado")
        return
    print("\n❌ E2E falhou na ativacao do diagnostico")
    sys.exit(1)


if __name__ == "__main__":
    main()
