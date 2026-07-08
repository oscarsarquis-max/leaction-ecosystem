"""Testa fluxo completo Hub: criar pedido addon -> simular pagamento -> webhook PanelDX."""

import os
import sys

import psycopg2
import requests
from dotenv import load_dotenv

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

GATEWAY = "http://127.0.0.1:4001"
NODE_WEBHOOK = "http://127.0.0.1:3000/api/webhooks/ativar-addon"

payload = {
    "client_id": "paneldx",
    "sku": "PANELDX_ADDON",
    "amount": 199.0,
    "id_clie": 3,
    "id_plano": 4,
    "plano_nome": "Pacote Extra: 5 Usuarios",
    "quantidade": 1,
    "customer": {"email": "teste@paneldx.com.br", "name": "Teste E2E Hub"},
    "webhook_url": NODE_WEBHOOK,
    "return_origin": "http://127.0.0.1:3000",
    "return_to": "/teams",
    "hub_public_url": "http://127.0.0.1:4000",
}

print("1) Criando pedido PANELDX_ADDON no Gateway...")
r = requests.post(f"{GATEWAY}/v1/payments", json=payload, timeout=15)
print(f"   HTTP {r.status_code}")
if r.status_code not in (200, 201):
    print(r.text[:500])
    sys.exit(1)

body = r.json()
order_id = body.get("payment_id") or body.get("order_id")
print(f"   Order ID: {order_id}")

print("2) Simulando pagamento...")
s = requests.post(f"{GATEWAY}/simular-pagamento", json={"order_id": order_id}, timeout=20)
print(f"   HTTP {s.status_code}")
sim = s.json()
print(f"   webhook_delivered: {sim.get('webhook_delivered')}")

if not sim.get("webhook_delivered"):
    print("   AVISO: webhook não confirmado pelo gateway")

print("3) Verificando PanelDX DB...")
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
)
cur = conn.cursor()
cur.execute(
    """
    SELECT id, status, hub_order_id
    FROM public.dx_contratos_addons
    WHERE hub_order_id = %s OR hub_order_id LIKE %s
    ORDER BY id DESC LIMIT 1;
    """,
    (str(order_id), f"{order_id}%"),
)
row = cur.fetchone()
if row:
    print(f"   Addon ativado: id={row[0]} status={row[1]} hub_order_id={row[2]}")
else:
    cur.execute(
        "SELECT id, status, hub_order_id FROM public.dx_contratos_addons ORDER BY id DESC LIMIT 3"
    )
    print(f"   Últimos addons: {cur.fetchall()}")
    sys.exit(1)

cur.execute(
    """
    SELECT COALESCE(SUM(COALESCE(p.max_usuarios, 0) * COALESCE(a.quantidade, 1)), 0)::int
    FROM public.dx_contratos_addons a
    JOIN public.dx_planos p ON p.id = a.id_plano_addon
    WHERE a.id_contrato = 1 AND a.status = 'ativo';
    """
)
extras = cur.fetchone()[0]
print(f"   Total usuários extras no contrato 1: {extras}")
cur.close()
conn.close()

print("\n=== Fluxo Hub + PanelDX OK ===")
