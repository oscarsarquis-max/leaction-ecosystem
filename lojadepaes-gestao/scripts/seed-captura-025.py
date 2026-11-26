"""Semeia um ingrediente duplicado sem movimento para capturas GESTAO-025."""

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

NOME = "Farinha de Trigo Especial Nuvola"


def main() -> None:
    try:
        criar_usuario("captura025", SENHA, "dono", nome="Captura 025", org="loja")
    except Exception:
        pass
    c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=60)
    r = c.post("/api/v1/auth/entrar", json={"usuario": "captura025", "senha": SENHA})
    assert r.status_code == 200, r.text
    h = {"X-CSRF-Token": r.json()["csrf"]}
    existentes = c.get("/api/v1/ingredientes").json()["ingredientes"]
    achou = next((i for i in existentes if i["nome"] == NOME), None)
    if achou is None:
        criado = c.post(
            "/api/v1/ingredientes",
            json={
                "nome": NOME,
                "unidade_base": "g",
                "categoria": "Farinhas",
                "confirmado_inexistente": True,
            },
            headers=h,
        )
        assert criado.status_code == 201, criado.text
        achou = criado.json()
    print(achou["id"])


if __name__ == "__main__":
    main()
