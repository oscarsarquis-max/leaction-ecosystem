"""Semeia demanda sintética na Loja de teste e dados no Gestão para capturas GESTAO-020."""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import httpx
from sqlalchemy import text

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

from app.db.session import get_engine  # noqa: E402
from tests.conftest import Loja, SENHA, criar_usuario  # noqa: E402


def main() -> None:
    try:
        criar_usuario("captura020", SENHA, "dono", nome="Captura 020", org="loja")
    except Exception:
        pass

    c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=60)
    r = c.post("/api/v1/auth/entrar", json={"usuario": "captura020", "senha": SENHA})
    print("login", r.status_code)
    assert r.status_code == 200, r.text
    csrf = r.json()["csrf"]
    h = {"X-CSRF-Token": csrf}

    loja = Loja()
    loja.limpar()
    base = loja.base("CAP020")
    produto_loja, variantes = loja.produto("Pão captura 020", base, [("Unidade", 1)])
    variante = variantes[0]
    dia = date.today() + timedelta(days=1)
    pedido = loja.pedido("CAP-1", "confirmed", dia)
    loja.item(pedido, produto=produto_loja, variante=variante, quantidade=4, unidades=4, base=base)
    print("loja demanda ok")

    farinha = c.post(
        "/api/v1/ingredientes",
        json={
            "nome": "Farinha captura 020",
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
            if "Farinha captura 020" in i["nome"]
        )
    local_id = c.get("/api/v1/locais").json()[0]["id"]
    ontem = (date.today() - timedelta(days=1)).isoformat()
    val = (date.today() + timedelta(days=90)).isoformat()
    ent = c.post(
        "/api/v1/entradas",
        json={
            "chave": f"cap020-{uuid.uuid4().hex[:8]}",
            "data": ontem,
            "local_id": local_id,
            "motivo": "compra_sem_nota",
            "linhas": [
                {
                    "item_nome": "Farinha cap",
                    "marca": "Casa",
                    "unidade_controle": "massa",
                    "ingrediente_id": fid,
                    "quantidade": 5,
                    "unidade": "kg",
                    "validade": val,
                    "custo": 12,
                }
            ],
        },
        headers=h,
    )
    print("entrada", ent.status_code)

    pao = c.post(
        "/api/v1/produtos",
        json={
            "nome": "Pão captura 020",
            "modalidade": "produzido",
            "uso_venda": True,
            "uso_componente": False,
            "unidade_venda": "un",
            "confirmado_inexistente": True,
        },
        headers=h,
    )
    print("produto", pao.status_code)
    pid = pao.json()["id"]
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE produtos SET origem_loja_id = :o WHERE id = :id"),
            {"o": str(variante), "id": pid},
        )

    put = c.put(
        f"/api/v1/receitas/{pid}",
        json={
            "linhas": [{"ingrediente_id": fid, "quantidade": 500, "unidade": "g"}],
            "rendimento_quantidade": 1,
            "rendimento_unidade": "un",
            "perda_percentual": 0,
            "peso_unidade_g": 500,
            "formato": "livre",
            "modo_fazer": [],
        },
        headers=h,
    )
    print("receita", put.status_code)
    pub = c.post(f"/api/v1/receitas/{pid}/publicar", json={"confirmar_sem_fermento": True}, headers=h)
    print("pub", pub.status_code)
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE receitas SET
                  perda_processo_pct=0, perda_processo_origem='manual', perda_processo_motivo='cap',
                  perda_coccao_pct=0, perda_coccao_origem='manual', perda_coccao_motivo='cap'
                WHERE produto_id = :id
                """
            ),
            {"id": pid},
        )

    c.post("/api/v1/custos/fixos", json={"nome": "Aluguel", "valor_mensal": 3000}, headers=h)
    c.put(
        "/api/v1/custos/parametros",
        json={"massa_mensal_kg": 600, "regra": {"tipo": "margem", "valor": 60}},
        headers=h,
    )
    outro = c.post(
        "/api/v1/produtos",
        json={
            "nome": "Pão preço informado 020",
            "modalidade": "produzido",
            "uso_venda": True,
            "uso_componente": False,
            "unidade_venda": "un",
            "confirmado_inexistente": True,
        },
        headers=h,
    )
    oid = outro.json()["id"]
    c.put(
        f"/api/v1/receitas/{oid}",
        json={
            "linhas": [{"ingrediente_id": fid, "quantidade": 1000, "unidade": "g"}],
            "rendimento_quantidade": 1,
            "rendimento_unidade": "un",
            "perda_percentual": 0,
            "peso_unidade_g": 1000,
            "formato": "livre",
            "modo_fazer": [],
        },
        headers=h,
    )
    c.post(f"/api/v1/receitas/{oid}/publicar", json={"confirmar_sem_fermento": True}, headers=h)
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE receitas SET
                  perda_processo_pct=0, perda_processo_origem='manual', perda_processo_motivo='cap',
                  perda_coccao_pct=0, perda_coccao_origem='manual', perda_coccao_motivo='cap'
                WHERE produto_id = :id
                """
            ),
            {"id": oid},
        )
    preco = c.put(f"/api/v1/custos/produtos/{oid}/preco", json={"preco": 20}, headers=h)
    print("preco", preco.status_code)

    hoje = c.get("/api/v1/hoje", headers=h).json()
    print("hoje fornadas", len(hoje.get("fornadas", [])), "total", hoje.get("total_paes_fisicos"))
    loja.fechar()
    print("SEED_OK")


if __name__ == "__main__":
    main()
