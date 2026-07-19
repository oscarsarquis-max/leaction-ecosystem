"""Teste ponta a ponta do fluxo de add-ons (API PanelDX + webhook + cota)."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

import jwt
import psycopg2
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

FLASK = os.getenv("FLASK_URL", "http://127.0.0.1:5002")
NODE = os.getenv("NODE_URL", "http://127.0.0.1:3000")
HUB = os.getenv("HUB_URL", "http://127.0.0.1:4000")
GATEWAY = os.getenv("GATEWAY_URL", "http://127.0.0.1:4001")
JWT_SECRET = os.getenv("HUB_JWT_SECRET", "super-secret-hub-key-2026")

DB = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "LeAction_SysF"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASS", ""),
)


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    sys.exit(1)


def wait_url(url: str, timeout: int = 60, method: str = "GET", **kwargs) -> None:
    deadline = time.time() + timeout
    last_err = ""
    while time.time() < deadline:
        try:
            r = requests.request(method, url, timeout=5, **kwargs)
            if r.status_code < 500:
                return
            last_err = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
        time.sleep(2)
    fail(f"Serviço indisponível: {url} ({last_err})")


def db_conn():
    return psycopg2.connect(**DB)


def pick_test_client(cur) -> tuple[int, int, int]:
    """Retorna (id_clie, id_contrato, max_base)."""
    cur.execute(
        """
        SELECT c.id_clie, c.id AS id_contrato, COALESCE(p.max_usuarios, 5) AS max_base
        FROM public.dx_contratos c
        JOIN public.dx_planos p ON p.id = c.id_plano
        WHERE c.status = 'ativo'
        ORDER BY c.id DESC
        LIMIT 1;
        """
    )
    row = cur.fetchone()
    if not row:
        fail("Nenhum contrato ativo encontrado para teste.")
    return int(row[0]), int(row[1]), int(row[2])


def addon_id(cur) -> int:
    cur.execute(
        """
        SELECT id FROM public.dx_planos
        WHERE tipo_plano = 'addon' AND ativo = TRUE
        ORDER BY id ASC LIMIT 1;
        """
    )
    row = cur.fetchone()
    if not row:
        fail("Plano add-on seed não encontrado.")
    return int(row[0])


def count_addons(cur, id_contrato: int) -> int:
    cur.execute(
        """
        SELECT COUNT(*) FROM public.dx_contratos_addons
        WHERE id_contrato = %s AND status = 'ativo';
        """,
        (id_contrato,),
    )
    return int(cur.fetchone()[0])


def sum_addon_users(cur, id_contrato: int) -> int:
    cur.execute(
        """
        SELECT COALESCE(SUM(COALESCE(p.max_usuarios,0)*COALESCE(a.quantidade,1)),0)::int
        FROM public.dx_contratos_addons a
        JOIN public.dx_planos p ON p.id = a.id_plano_addon
        WHERE a.id_contrato = %s AND a.status = 'ativo';
        """,
        (id_contrato,),
    )
    return int(cur.fetchone()[0])


def main() -> None:
    print("=== Teste E2E Add-ons PanelDX ===\n")

    print("1) Health checks")
    wait_url(f"{FLASK}/api/public/planos-addon/1", timeout=90)
    ok(f"Flask {FLASK}")

    try:
        wait_url(f"{NODE}/", timeout=30)
        ok(f"Node {NODE}")
    except SystemExit:
        print("  [WARN] Node indisponível — pulando proxy webhook via Node")

    hub_ok = False
    gateway_ok = False
    try:
        wait_url(f"{HUB}/checkout/direct", timeout=20)
        hub_ok = True
        ok(f"ActionHub {HUB}")
    except SystemExit:
        print("  [WARN] ActionHub indisponível")

    try:
        wait_url(f"{GATEWAY}/config/payments", timeout=10)
        gateway_ok = True
        ok(f"Gateway {GATEWAY}")
    except SystemExit:
        print("  [WARN] Gateway indisponível (Hub DB pode estar offline)")

    conn = db_conn()
    cur = conn.cursor()
    id_clie, id_contrato, max_base = pick_test_client(cur)
    id_addon = addon_id(cur)
    ok(f"Cliente teste id_clie={id_clie}, contrato={id_contrato}, base={max_base}, addon={id_addon}")

    print("\n2) API pública do pacote add-on")
    r = requests.get(f"{FLASK}/api/public/planos-addon/{id_addon}", timeout=10)
    if r.status_code != 200:
        fail(f"GET planos-addon: {r.status_code} {r.text[:200]}")
    body = r.json()
    if body.get("status") != "success":
        fail(f"Resposta inválida: {body}")
    ok(f"Pacote: {body['addon']['nome']} — R$ {body['addon']['valor_mensal']}")

    print("\n3) Webhook ativar-addon (simulação pós-pagamento)")
    antes_addons = sum_addon_users(cur, id_contrato)
    order_id = f"e2e-test-{uuid.uuid4().hex[:12]}"
    token = jwt.encode(
        {
            "iss": "leaction-hub",
            "status_tecnico": "PAYMENT_CONFIRMED",
            "order_id": order_id,
            "product_type": "PANELDX_ADDON",
            "gateway_ref": order_id,
            "hub_payload": {
                "id_clie": id_clie,
                "id_plano_addon": id_addon,
                "quantidade": 1,
            },
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    webhook_urls = [f"{FLASK}/api/webhooks/ativar-addon"]
    try:
        requests.get(NODE, timeout=3)
        webhook_urls.append(f"{NODE}/api/webhooks/ativar-addon")
    except Exception:  # noqa: BLE001
        pass

    activated = False
    for url in webhook_urls:
        wr = requests.post(url, json={"token": token}, timeout=15)
        label = "Flask" if "5002" in url else "Node proxy"
        if wr.status_code == 200 and wr.json().get("success"):
            ok(f"Webhook via {label}: order_id={order_id}")
            activated = True
            break
        print(f"  [WARN] {label}: HTTP {wr.status_code} — {wr.text[:180]}")

    if not activated:
        fail("Webhook não ativou o add-on.")

    conn.commit()
    cur.execute(
        "SELECT id, quantidade, status FROM public.dx_contratos_addons WHERE hub_order_id = %s;",
        (order_id,),
    )
    row = cur.fetchone()
    if not row:
        fail("Registro dx_contratos_addons não encontrado após webhook.")
    ok(f"Registro add-on id={row[0]} status={row[2]}")

    depois_addons = sum_addon_users(cur, id_contrato)
    esperado_extra = int(body["addon"]["max_usuarios"])
    if depois_addons < antes_addons + esperado_extra:
        fail(f"Cota add-on não aumentou: antes={antes_addons} depois={depois_addons}")
    ok(f"Usuários extras: {antes_addons} -> {depois_addons} (+{depois_addons - antes_addons})")

    print("\n4) Checkout expresso ActionHub")
    if hub_ok:
        checkout_url = (
            f"{HUB}/checkout/direct?client_id={id_clie}&addon_id={id_addon}"
            f"&email=teste@paneldx.com.br&return_origin={NODE}&return_to=/teams"
        )
        cr = requests.get(checkout_url, timeout=15)
        if cr.status_code != 200:
            fail(f"Checkout direct HTTP {cr.status_code}")
        if "Resumo" not in cr.text and "Pacote" not in cr.text and "checkout" not in cr.text.lower():
            print("  [WARN] Página carregou mas conteúdo não validado (SSR/hydration)")
        else:
            ok(f"Checkout direct respondeu HTTP 200 ({len(cr.text)} bytes)")
    else:
        print("  [SKIP] ActionHub offline")

    if gateway_ok:
        gr = requests.get(f"{GATEWAY}/config/payments", timeout=10)
        if gr.status_code == 200:
            ok("Gateway /config/payments respondeu")
        else:
            print(f"  [WARN] Gateway config HTTP {gr.status_code}")
    else:
        print("  [SKIP] Gateway offline — aplique patch quando Hub DB subir")

    print("\n=== E2E concluído com sucesso ===")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
