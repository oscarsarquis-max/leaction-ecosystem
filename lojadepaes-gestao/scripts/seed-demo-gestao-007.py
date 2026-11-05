"""Dados de demonstração para as capturas do GESTAO-007 (SÓ ambiente local).

    GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... python scripts/seed-demo-gestao-007.py

Cria uma entrada com Fubá Orgânico, Trigo Sarraceno e Sal, lotes E20261103-12 a -14,
e corrige o custo do -12 para o selo aparecer. Nada disto vai para a produção.
"""

import os
import re
import sys
from datetime import date, timedelta

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


fuba = ingrediente("Fubá Orgânico", "Farinhas")
sarraceno = ingrediente("Trigo Sarraceno", "Farinhas")
sal = ingrediente("Sal", "Sal e temperos")
local = cliente.get("/api/v1/locais").json()[0]["id"]
validade = (date.today() + timedelta(days=90)).isoformat()

entrada = post(
    "/entradas",
    {
        "chave": "demo-007-contagem",
        "data": "2026-11-03",
        "local_id": local,
        "motivo": "contagem",
        "linhas": [
            {
                "item_nome": nome,
                "marca": "",
                "unidade_controle": "massa",
                "ingrediente_id": ing,
                "quantidade": 1,
                "unidade": "kg",
                "lote_codigo": codigo,
                "validade": validade,
                "valor_pago": 10,
            }
            for nome, ing, codigo in (
                ("Fubá Orgânico", fuba, "E20261103-12"),
                ("Trigo Sarraceno", sarraceno, "E20261103-13"),
                ("Sal", sal, "E20261103-14"),
            )
        ],
    },
)
lote = next(linha["lote_id"] for linha in entrada["linhas"] if linha["lote"] == "E20261103-12")
if not entrada["linhas"][0].get("custo_corrigido"):
    post(f"/lotes/{lote}/custo", {"valor_pago": 18, "motivo": "O pacote custou 18, não 10"})
print("demo 007 pronta", entrada["id"])
