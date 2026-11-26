"""Semeia um lote vencido com saldo no Gestão de teste (captura GESTAO-022)."""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import httpx

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

from tests.conftest import SENHA, criar_usuario  # noqa: E402


def main() -> None:
    try:
        criar_usuario("captura022", SENHA, "dono", nome="Captura 022", org="loja")
    except Exception:
        pass

    c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=60)
    r = c.post("/api/v1/auth/entrar", json={"usuario": "captura022", "senha": SENHA})
    print("login", r.status_code)
    assert r.status_code == 200, r.text
    csrf = r.json()["csrf"]
    h = {"X-CSRF-Token": csrf}

    nome = "Farinha de semolina"
    farinha = c.post(
        "/api/v1/ingredientes",
        json={
            "nome": nome,
            "unidade_base": "g",
            "categoria": "Farinhas",
            "confirmado_inexistente": True,
        },
        headers=h,
    )
    print("farinha", farinha.status_code)
    if farinha.status_code == 201:
        fid = farinha.json()["id"]
    else:
        fid = next(
            i["id"]
            for i in c.get("/api/v1/ingredientes").json()["ingredientes"]
            if i["nome"].lower() == nome.lower()
        )

    local_id = c.get("/api/v1/locais").json()[0]["id"]
    ontem = (date.today() - timedelta(days=1)).isoformat()
    vencido = (date.today() - timedelta(days=7)).isoformat()
    ent = c.post(
        "/api/v1/entradas",
        json={
            "chave": f"cap022-{uuid.uuid4().hex[:8]}",
            "data": ontem,
            "local_id": local_id,
            "motivo": "compra_sem_nota",
            "linhas": [
                {
                    "item_nome": "Semolina",
                    "marca": "Casa",
                    "unidade_controle": "massa",
                    "ingrediente_id": fid,
                    "quantidade": 2,
                    "unidade": "kg",
                    "validade": vencido,
                    "custo": 8,
                }
            ],
        },
        headers=h,
    )
    print("entrada", ent.status_code, ent.text[:200] if ent.status_code >= 400 else "")
    assert ent.status_code == 201, ent.text

    hoje = c.get("/api/v1/hoje").json()
    vencidos = [v for v in hoje["vence_em_7_dias"] if v["dias"] < 0]
    print("vencidos", [(v["ingrediente"], v["dias"], v["codigo"]) for v in vencidos])
    fluxo = c.get("/api/v1/fluxo").json()
    ing = next(e for e in fluxo["etapas"] if e["id"] == "ingredientes")
    print("ingredientes", ing["estado"], ing["frase"])


if __name__ == "__main__":
    main()
