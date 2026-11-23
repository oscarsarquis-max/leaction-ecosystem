"""Semeia Farinha tipo 0 com item Nuvola para captura GESTAO-026."""

from __future__ import annotations

import os
import sys

os.environ.setdefault(
    "GESTAO_DATABASE_URL",
    "postgresql+psycopg://gestao_app:app_test_pw@127.0.0.1:55540/gestao_test",
)
os.environ.setdefault(
    "GESTAO_LOJA_DATABASE_URL",
    "postgresql+psycopg://gestao_reader:reader_test_pw@127.0.0.1:55540/lojadepaes_test",
)
os.environ.setdefault("GESTAO_SESSION_SECRET", "s" * 48)
os.environ.setdefault("GESTAO_COOKIE_SECURE", "false")
os.environ.setdefault("GESTAO_ENV", "development")

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from tests.conftest import SENHA, criar_usuario
from datetime import date, timedelta

ONTEM = (date.today() - timedelta(days=1)).isoformat()


def main() -> None:
    try:
        criar_usuario("captura026", SENHA, "dono", nome="Captura 026", org="loja")
    except Exception:
        pass
    c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=60)
    r = c.post("/api/v1/auth/entrar", json={"usuario": "captura026", "senha": SENHA})
    assert r.status_code == 200, r.text
    h = {"X-CSRF-Token": r.json()["csrf"]}
    ings = c.get("/api/v1/ingredientes").json()["ingredientes"]
    tipo0 = next((i for i in ings if i["nome"] == "Farinha de trigo tipo 0"), None)
    if tipo0 is None:
        criado = c.post(
            "/api/v1/ingredientes",
            json={
                "nome": "Farinha de trigo tipo 0",
                "unidade_base": "g",
                "categoria": "Farinhas",
                "confirmado_inexistente": True,
            },
            headers=h,
        )
        assert criado.status_code == 201, criado.text
        tipo0 = criado.json()
    locais = c.get("/api/v1/locais").json()
    local_id = locais[0]["id"]
    # garante item Nuvola
    det = c.get(f"/api/v1/ingredientes/{tipo0['id']}").json()
    tem = any("Nuvola" in (it.get("nome") or "") for it in det.get("itens_detalhe") or [])
    if not tem:
        entrada = c.post(
            "/api/v1/entradas",
            json={
                "chave": "captura026-nuvola",
                "data": ONTEM,
                "local_id": local_id,
                "motivo": "compra_sem_nota",
                "linhas": [
                    {
                        "item_nome": "Farinha de Trigo Tipo Nuvola",
                        "marca": "Caputo",
                        "unidade_controle": "massa",
                        "ingrediente_id": tipo0["id"],
                        "quantidade": 1,
                        "unidade": "kg",
                        "validade": (date.today() + timedelta(days=120)).isoformat(),
                        "custo": 12,
                    }
                ],
            },
            headers=h,
        )
        assert entrada.status_code == 201, entrada.text
    # produto + receita para abrir o campo
    produtos = c.get("/api/v1/produtos").json()["produtos"]
    pao = next((p for p in produtos if p["nome"] == "Pão captura 026"), None)
    if pao is None:
        criado = c.post(
            "/api/v1/produtos",
            json={
                "nome": "Pão captura 026",
                "modalidade": "produzido",
                "uso_venda": True,
                "uso_componente": False,
                "unidade_venda": "un",
                "confirmado_inexistente": True,
            },
            headers=h,
        )
        assert criado.status_code == 201, criado.text
        pao = criado.json()
    print(pao["id"])


if __name__ == "__main__":
    main()
