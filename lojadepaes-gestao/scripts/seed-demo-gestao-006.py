"""Dados de demonstração para as capturas do GESTAO-006 (SÓ ambiente local, banco descartável).

    GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... python scripts/seed-demo-gestao-006.py

Cria, pela API, ingredientes e uma entrada com:
  - "Trigo Sarraceno" ligado ao ingrediente ERRADO ("Farinha de trigo especial"), para a ação "Trocar ingrediente";
  - lotes com custo pelo valor pago e um lote antigo no modo "preço por unidade".
Nada disto vai para a produção.
"""

import os
import re
import sys
import uuid
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


def ingrediente(nome: str, categoria: str, base_un: str = "g") -> str:
    for i in cliente.get("/api/v1/ingredientes").json()["ingredientes"]:
        if i["nome"].lower() == nome.lower():
            return i["id"]
    r = post(
        "/ingredientes",
        {"nome": nome, "unidade_base": base_un, "categoria": categoria, "confirmado_inexistente": True},
    )
    return r["id"]


especial = ingrediente("Farinha de trigo especial", "Farinhas")
tipo0 = ingrediente("Farinha de trigo tipo 0", "Farinhas")
ingrediente("Farinha de trigo sarraceno", "Farinhas")
fermento = ingrediente("Fermento biológico seco", "Fermentos")
acucar = ingrediente("Açúcar refinado", "Açúcares e mel")

local = cliente.get("/api/v1/locais").json()[0]["id"]
validade = (date.today() + timedelta(days=120)).isoformat()
ontem = (date.today() - timedelta(days=1)).isoformat()

linhas = [
    # ligado ao ingrediente errado: o caso do "Trigo Sarraceno"
    {
        "item_nome": "Trigo Sarraceno",
        "marca": "",
        "unidade_controle": "massa",
        "ingrediente_id": especial,
        "quantidade": 0.5,
        "unidade": "kg",
        "validade": validade,
        "valor_pago": 22.99,
    },
    {
        "item_nome": "Farinha de trigo tipo 0 25 kg",
        "marca": "Nuvola",
        "unidade_controle": "massa",
        "ingrediente_id": tipo0,
        "quantidade": 25,
        "unidade": "kg",
        "validade": validade,
        "valor_pago": 112.5,
    },
    {
        "item_nome": "Fermento biológico seco 500 g",
        "marca": "Fleischmann",
        "unidade_controle": "embalagem",
        "conteudo_embalagem": 500,
        "ingrediente_id": fermento,
        "quantidade": 2,
        "unidade": "emb",
        "validade": validade,
        "valor_pago": 45.98,
    },
    # lote no modo antigo (preço por unidade), como as entradas de antes
    {
        "item_nome": "Açúcar refinado 5 kg",
        "marca": "União",
        "unidade_controle": "massa",
        "ingrediente_id": acucar,
        "quantidade": 5,
        "unidade": "kg",
        "validade": validade,
        "custo": 4.5,
    },
]
entrada = post(
    "/entradas",
    {
        "chave": uuid.uuid4().hex,
        "data": ontem,
        "local_id": local,
        "tipo": "sem_nota",
        "motivo": "compra_sem_nota",
        "fornecedor": "Atacadão",
        "linhas": linhas,
    },
)
print("entrada", entrada["id"], "valor", entrada["valor"])
