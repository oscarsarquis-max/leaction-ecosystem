"""Semeia um pão para capturas GESTAO-024 (N=1 e depois N=8)."""

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

from tests.conftest import SENHA, criar_usuario

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1


def main() -> None:
    try:
        criar_usuario("captura024", SENHA, "dono", nome="Captura 024", org="loja")
    except Exception:
        pass
    c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=60)
    r = c.post("/api/v1/auth/entrar", json={"usuario": "captura024", "senha": SENHA})
    assert r.status_code == 200, r.text
    h = {"X-CSRF-Token": r.json()["csrf"]}
    farinha = c.post(
        "/api/v1/ingredientes",
        json={"nome": "Farinha captura 024", "unidade_base": "g", "categoria": "Farinhas", "confirmado_inexistente": True},
        headers=h,
    )
    fid = farinha.json()["id"] if farinha.status_code == 201 else next(
        i["id"] for i in c.get("/api/v1/ingredientes").json()["ingredientes"] if "Farinha captura 024" in i["nome"]
    )
    produtos = c.get("/api/v1/produtos").json()["produtos"]
    pao = next((p for p in produtos if p["nome"] == "Pão captura 024"), None)
    if pao is None:
        criado = c.post(
            "/api/v1/produtos",
            json={
                "nome": "Pão captura 024",
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
    pid = pao["id"]
    massa = 720 if N == 1 else 720
    put = c.put(
        f"/api/v1/receitas/{pid}",
        json={
            "linhas": [{"ingrediente_id": fid, "quantidade": massa, "unidade": "g"}],
            "rendimento_quantidade": N,
            "rendimento_unidade": "un",
            "peso_unidade_g": None,
            "perda_percentual": 0,
            "modo_fazer": [],
            "formato": "forma",
            "unidades_desejadas": N,
            "processo": {"percentual": 5, "origem": "manual", "motivo": "captura 024"},
            "coccao": {"percentual": 14, "origem": "manual", "motivo": "captura 024"},
        },
        headers=h,
    )
    assert put.status_code == 200, put.text
    corpo = put.json()
    print("produto", pid)
    print("N", N, "cru", corpo["perdas"]["peso_cru_g"], "final", corpo["perdas"]["peso_final_g"])


if __name__ == "__main__":
    main()
