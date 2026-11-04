"""Uma entrada pendente para as capturas do GESTAO-007A (SÓ ambiente local).

    GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... python scripts/seed-demo-gestao-007a.py

A entrada fica sem validade, então a lista mostra o selo Pendente. Nada disto vai para a produção.
"""

import os
import re
import sys

import httpx

base = os.environ.get("GESTAO_BASE_URL", "http://127.0.0.1:8090")
if not re.match(r"^http://(127\.0\.0\.1|localhost)(:|/|$)", base):
    sys.exit("só em ambiente local")

cliente = httpx.Client(base_url=base, timeout=20)
sessao = cliente.post(
    "/api/v1/auth/entrar",
    json={"usuario": os.environ["GESTAO_USER"], "senha": os.environ["GESTAO_PASS"]},
)
sessao.raise_for_status()
cab = {"X-CSRF-Token": sessao.json()["csrf"]}


def post(rota: str, corpo: dict) -> dict:
    r = cliente.post(f"/api/v1{rota}", json=corpo, headers=cab)
    if r.status_code >= 300:
        sys.exit(f"{rota}: {r.status_code} {r.text}")
    return r.json()


def ingrediente(nome: str, categoria: str) -> str:
    for i in cliente.get("/api/v1/ingredientes").json()["ingredientes"]:
        if i["nome"].lower() == nome.lower():
            return i["id"]
    return post(
        "/ingredientes",
        {"nome": nome, "unidade_base": "g", "categoria": categoria, "confirmado_inexistente": True},
    )["id"]


melhorador = ingrediente("Melhorador", "Outros")
local = cliente.get("/api/v1/locais").json()[0]["id"]
entrada = post(
    "/entradas",
    {
        "chave": "demo-007a-pendente",
        "data": "2026-11-04",
        "local_id": local,
        "motivo": "compra_sem_nota",
        "fornecedor": "Atacadão",
        "linhas": [
            {
                "item_nome": "Melhorador 500 g",
                "marca": "",
                "unidade_controle": "massa",
                "ingrediente_id": melhorador,
                "quantidade": 500,
                "unidade": "g",
                "lote_codigo": "E20261104-01",
                "valor_pago": 12.5,
            }
        ],
    },
)
print("demo 007a", entrada.get("situacao"), entrada.get("id"))
