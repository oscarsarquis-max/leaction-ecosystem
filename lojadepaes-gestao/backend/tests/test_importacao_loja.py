"""GESTAO-011: importação única da vitrine, idempotente, sem escrever na Loja."""

from uuid import uuid4

import psycopg
import pytest
from app.cli import main
from app.db.escopo import ativar_escopo
from app.db.session import get_engine, get_loja_engine
from app.domain.auth import Principal
from app.domain.contexto import Contexto
from app.domain.importacao_loja import (
    _SQL_PUBLICADOS,
    CAMINHO_FAMILIAS,
    carregar_mapa,
    importar_vitrine,
)
from app.models.organizacao import Organizacao
from app.models.produtos import Familia, Produto, Receita, ReceitaLinha
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from tests.conftest import ADMIN_URL, criar_org

NOMES = list(carregar_mapa(CAMINHO_FAMILIAS))


def _admin_loja():
    url = ADMIN_URL.rsplit("/", 1)[0] + "/lojadepaes_test"
    return psycopg.connect(url, autocommit=True)


def _limpar_loja():
    with _admin_loja() as conn:
        conn.execute("DELETE FROM products WHERE slug LIKE 'g011-%'")
        conn.execute("DELETE FROM media_assets WHERE stored_name LIKE 'g011-%'")


def _semear(nomes: list[str] | None = None, *, com_foto: bool = True) -> None:
    _limpar_loja()
    with _admin_loja() as conn:
        for ordem, nome in enumerate(nomes or NOMES):
            produto_id = uuid4()
            foto_id = uuid4() if com_foto else None
            if foto_id is not None:
                conn.execute(
                    """
                    INSERT INTO media_assets
                      (id, stored_name, object_key, content_type, byte_size, width, height)
                    VALUES (%s, %s, %s, 'image/jpeg', 12, 4, 3)
                    """,
                    (foto_id, f"g011-{produto_id.hex[:12]}", f"g011/{produto_id.hex}"),
                )
            conn.execute(
                """
                INSERT INTO products (
                  id, name, slug, editorial_status, featured_image_id,
                  featured_image_caption, short_description, featured_image_alt,
                  is_available, sort_order, fidelity_eligible
                ) VALUES (
                  %s, %s, %s, 'published', %s, '', '', '', true, %s, false
                )
                """,
                (produto_id, nome, f"g011-{produto_id.hex[:12]}", foto_id, ordem),
            )


def _ctx(db: Session, nome_curto: str) -> Contexto:
    org_id = criar_org(nome_curto)
    ativar_escopo(db, org_id)
    org = db.get(Organizacao, org_id)
    assert org is not None
    return Contexto(
        principal=Principal(None, "cli", "cli", False, None, org_id, ""),
        organizacao=org,
        papel="dono",
        db=db,
    )


@pytest.fixture()
def vitrine():
    _semear()
    yield
    _limpar_loja()


def test_a_consulta_nao_pede_vitrine_nem_preco_nem_arquivo():
    sql = str(_SQL_PUBLICADOS)
    assert "showcase_slots" not in sql
    assert "media_assets" not in sql
    assert "price_cents" not in sql
    assert "featured_image_id" in sql


def test_dry_run_nao_grava(vitrine):
    with Session(get_engine()) as db, Session(get_loja_engine()) as loja:
        ctx = _ctx(db, "boulangerie-dry")
        plano = importar_vitrine(ctx, loja, executar=False)
        db.commit()
        assert len(plano.linhas) == 10
        assert plano.produtos_criados == 0
        assert {linha.familia for linha in plano.linhas} == {"Focaccia", "Pão Rústico", "Pão Sovado"}
        assert all(linha.tem_foto and not linha.ja_existe for linha in plano.linhas)
        assert db.scalar(select(func.count()).select_from(Produto)) == 0


def test_executa_dez_e_a_segunda_vez_nao_cria_nem_sobrescreve(vitrine):
    with Session(get_engine()) as db, Session(get_loja_engine()) as loja:
        ctx = _ctx(db, "boulangerie")
        primeiro = importar_vitrine(ctx, loja, executar=True)
        db.commit()
        assert primeiro.familias_criadas == 3
        assert primeiro.produtos_criados == 10
        assert primeiro.nao_criados == []
        focaccia = db.scalar(select(Produto).where(Produto.nome.like("Focaccia%")))
        assert focaccia is not None
        assert focaccia.modalidade == "produzido"
        assert focaccia.uso_venda is True
        assert focaccia.uso_componente is False
        assert focaccia.foto_url == f"https://lojadepaes.com.br/api/v1/catalog/media/{_foto(focaccia)}"
        receita = db.scalar(select(Receita).where(Receita.produto_id == focaccia.id))
        assert receita is not None and receita.situacao == "rascunho"
        assert db.scalar(select(func.count()).select_from(ReceitaLinha).where(ReceitaLinha.receita_id == receita.id)) == 0
        focaccia.nome = "Focaccia da casa"
        db.commit()

        segundo = importar_vitrine(ctx, loja, executar=True)
        db.commit()
        assert segundo.produtos_criados == 0
        assert segundo.familias_criadas == 0
        assert segundo.ja_existiam == 10
        db.refresh(focaccia)
        assert focaccia.nome == "Focaccia da casa"
        assert db.scalar(select(func.count()).select_from(Familia)) == 3
        assert db.scalar(select(func.count()).select_from(Produto)) == 10


def _foto(produto: Produto) -> str:
    assert produto.foto_url is not None
    return produto.foto_url.rsplit("/", 1)[-1]


def test_nome_igual_ou_parecido_nao_cria(vitrine):
    with Session(get_engine()) as db, Session(get_loja_engine()) as loja:
        ctx = _ctx(db, "boulangerie-choque")
        from app.domain.produtos import criar_produto

        criar_produto(
            ctx,
            nome="Pão de Café (Marroquinus)",
            modalidade="produzido",
            uso_venda=True,
            uso_componente=False,
            familia_id=None,
            unidade_venda="un",
        )
        db.commit()
        resultado = importar_vitrine(ctx, loja, executar=True)
        db.commit()
        assert resultado.produtos_criados == 9
        assert any("Pão de Café" in linha.nome and linha.ja_existe for linha in resultado.nao_criados)
        assert db.scalar(select(func.count()).select_from(Produto)) == 10


def test_outra_organizacao_nao_ve(vitrine):
    with Session(get_engine()) as db, Session(get_loja_engine()) as loja:
        nossa = _ctx(db, "boulangerie-a")
        importar_vitrine(nossa, loja, executar=True)
        db.commit()
        outra = _ctx(db, "boulangerie-b")
        assert db.scalar(select(func.count()).select_from(Produto)) == 0
        ativar_escopo(db, nossa.organizacao.id)
        assert db.scalar(select(func.count()).select_from(Produto)) == 10
        assert outra.organizacao.id != nossa.organizacao.id


def test_confirmacao_errada_nao_grava():
    with pytest.raises(SystemExit):
        main(["importar-produtos-loja", "--organizacao", "boulangerie", "--executar", "--confirm", "outra"])


def test_loja_continua_so_leitura(vitrine):
    with Session(get_loja_engine()) as loja:
        with pytest.raises(Exception):
            loja.execute(text("UPDATE products SET name = name"))
            loja.commit()
