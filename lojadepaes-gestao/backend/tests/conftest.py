"""Fixtures de teste.

Exigem um Postgres 16 descartável (nunca a Loja, nunca produção). Por padrão:
    GESTAO_TEST_ADMIN_URL=postgresql://postgres:pg_test_root@127.0.0.1:55440/postgres

Cada execução recria dois bancos de teste:
  gestao_test      banco do Gestão (migrado pelo Alembic do Gestão)
  lojadepaes_test  cópia só do esquema da Loja + os GRANTs reais de deploy/sql/02
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

ADMIN_URL = os.environ.get(
    "GESTAO_TEST_ADMIN_URL", "postgresql://postgres:pg_test_root@127.0.0.1:55440/postgres"
)
HOST_PORT = "127.0.0.1:55440"
APP_PW = "app_test_pw"
READER_PW = "reader_test_pw"
ROOT = Path(__file__).resolve().parents[2]

os.environ["GESTAO_DATABASE_URL"] = (
    f"postgresql+psycopg://gestao_app:{APP_PW}@{HOST_PORT}/gestao_test"
)
os.environ["GESTAO_LOJA_DATABASE_URL"] = (
    f"postgresql+psycopg://gestao_reader:{READER_PW}@{HOST_PORT}/lojadepaes_test"
)
os.environ["GESTAO_SESSION_SECRET"] = "s" * 48
os.environ["GESTAO_COOKIE_SECURE"] = "false"
os.environ["GESTAO_ENV"] = "test"
os.environ["GESTAO_SPA_DIR"] = ""


def _admin(dbname: str | None = None) -> psycopg.Connection:
    url = ADMIN_URL if dbname is None else re.sub(r"/[^/]*$", f"/{dbname}", ADMIN_URL)
    return psycopg.connect(url, autocommit=True)


def _script_sem_meta(path: Path) -> str:
    return "\n".join(
        linha
        for linha in path.read_text(encoding="utf-8").splitlines()
        if not linha.startswith("\\")
    )


@pytest.fixture(scope="session", autouse=True)
def bancos_de_teste():
    with _admin() as conn:
        for papel, senha in (("gestao_app", APP_PW), ("gestao_reader", READER_PW)):
            existe = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (papel,)).fetchone()
            comando = "ALTER" if existe else "CREATE"
            conn.execute(
                sql.SQL(f"{comando} ROLE {papel} LOGIN NOSUPERUSER PASSWORD {{}}").format(
                    sql.Literal(senha)
                )
            )
        conn.execute("ALTER ROLE gestao_reader SET default_transaction_read_only = on")
        conn.execute("ALTER ROLE gestao_reader SET statement_timeout = '15s'")
        for banco in ("gestao_test", "lojadepaes_test"):
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(banco))
            )
        conn.execute("CREATE DATABASE gestao_test OWNER gestao_app")
        conn.execute("REVOKE ALL ON DATABASE gestao_test FROM PUBLIC")
        conn.execute("GRANT CONNECT ON DATABASE gestao_test TO gestao_app")
        conn.execute("CREATE DATABASE lojadepaes_test")
        conn.execute("GRANT CONNECT ON DATABASE lojadepaes_test TO gestao_reader")

    with _admin("lojadepaes_test") as loja:
        loja.execute(
            _script_sem_meta(Path(__file__).parent / "fixtures" / "loja_schema_e7b3c9a41d06.sql")
        )
        loja.execute("SET search_path TO public")  # o dump zera o search_path
        loja.execute("INSERT INTO alembic_version (version_num) VALUES ('e7b3c9a41d06')")
        loja.execute(_script_sem_meta(ROOT / "deploy" / "sql" / "02-gestao-reader-grants.sql"))

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "database" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "database" / "migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(scope="session", autouse=True)
def catalogo_carregado(bancos_de_teste):
    """O catálogo de referência é global e fica no banco (o TRUNCATE de cada teste não o toca)."""
    from app.db.session import get_engine
    from app.domain.catalogo import carregar_catalogo
    from sqlalchemy.orm import Session

    with Session(get_engine()) as sessao:
        carregar_catalogo(sessao)
        sessao.commit()


@pytest.fixture()
def db():
    from app.db.session import get_engine
    from sqlalchemy.orm import Session

    with Session(get_engine(), expire_on_commit=False) as sessao:
        yield sessao


@pytest.fixture(autouse=True)
def limpar_gestao():
    yield
    with _admin("gestao_test") as conn:
        conn.execute("TRUNCATE tentativas_login, sessoes, membros, usuarios, organizacoes CASCADE")
    _CONTADOR_CNPJ[0] = 0


@pytest.fixture()
def client():
    from app.main import create_app
    from fastapi.testclient import TestClient

    with TestClient(create_app(), base_url="http://testserver") as c:
        yield c


_CONTADOR_CNPJ = [0]


def cnpj_de_teste() -> str:
    """CNPJ válido e único dentro de um teste (12 primeiros dígitos sequenciais)."""
    from app.domain.cnpj import digitos_verificadores

    _CONTADOR_CNPJ[0] += 1
    base = f"1000{_CONTADOR_CNPJ[0]:04d}0001"
    return base + digitos_verificadores(base)


def criar_org(nome_curto: str = "loja", *, fonte_loja: bool = True, cnpj: str | None = None):
    """Cria (ou devolve) uma organização com o local padrão "Despensa". Devolve o id."""
    from app.db.session import get_engine
    from app.domain.normalizacao import normalizar
    from app.models.estoque import Local
    from app.models.organizacao import Organizacao
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(get_engine()) as sessao:
        existente = sessao.scalar(select(Organizacao).where(Organizacao.nome_curto == nome_curto))
        if existente is not None:
            return existente.id
        org = Organizacao(
            nome=f"Org {nome_curto}",
            nome_curto=nome_curto,
            cnpj=cnpj or cnpj_de_teste(),
            fonte_loja=fonte_loja,
        )
        sessao.add(org)
        sessao.flush()
        from app.domain.gigio.padroes import semear

        semear(sessao, org.id)
        sessao.add(
            Local(
                organizacao_id=org.id,
                nome="Despensa",
                nome_normalizado=normalizar("Despensa"),
                padrao=True,
            )
        )
        sessao.commit()
        return org.id


def criar_usuario(
    usuario: str,
    senha: str,
    papel: str | None = "dono",
    *,
    ativo: bool = True,
    nome: str = "Pessoa",
    org: str | None = "loja",
    admin_plataforma: bool = False,
    fonte_loja: bool = True,
) -> None:
    from app.db.session import get_engine
    from app.domain.auth import gerar_hash_senha
    from app.models.organizacao import Membro
    from app.models.usuarios import Usuario
    from sqlalchemy.orm import Session

    org_id = criar_org(org, fonte_loja=fonte_loja) if (org and not admin_plataforma) else None
    with Session(get_engine()) as sessao:
        u = Usuario(
            usuario=usuario,
            nome=nome,
            senha_hash=gerar_hash_senha(senha),
            ativo=ativo,
            admin_plataforma=admin_plataforma,
        )
        sessao.add(u)
        sessao.flush()
        if org_id is not None:
            sessao.add(Membro(usuario_id=u.id, organizacao_id=org_id, papel=papel or "dono"))
        sessao.commit()


SENHA = "senha-de-teste-123"


def entrar(client, usuario: str, papel: str = "dono", senha: str = SENHA, **opcoes):
    """Cria o usuário (por padrão dono da org "loja", que lê a demanda da Loja) e faz login."""
    criar_usuario(usuario, senha, papel, **opcoes)
    resposta = client.post("/api/v1/auth/entrar", json={"usuario": usuario, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --- dados sintéticos da Loja -------------------------------------------------------------


class Loja:
    """Insere dados sintéticos (sem pessoas reais) no banco `lojadepaes_test` como superusuário."""

    def __init__(self) -> None:
        self.conn = _admin("lojadepaes_test")

    def fechar(self) -> None:
        self.conn.close()

    def limpar(self) -> None:
        self.conn.execute(
            "TRUNCATE managerial_exclusions, order_items, orders, production_batches, "
            "product_variants, products, dough_types, recipe_bases CASCADE"
        )

    def base(self, code: str) -> uuid.UUID:
        id_ = uuid.uuid4()
        self.conn.execute(
            "INSERT INTO recipe_bases (id, code, name, is_active) VALUES (%s, %s, %s, true)",
            (id_, code, f"Base {code}"),
        )
        return id_

    def produto(self, nome: str, base: uuid.UUID | None, variantes: list[tuple[str, int | None]]):
        produto_id = uuid.uuid4()
        self.conn.execute(
            "INSERT INTO products (id, name, slug, recipe_base_id, featured_image_caption, "
            "fidelity_eligible) VALUES (%s, %s, %s, %s, '', false)",
            (produto_id, nome, nome.lower().replace(" ", "-"), base),
        )
        ids = []
        for posicao, (rotulo, unidades) in enumerate(variantes, start=1):
            variante_id = uuid.uuid4()
            self.conn.execute(
                "INSERT INTO product_variants (id, product_id, display_name, presentation_type, "
                "units_per_pack, physical_units, price_cents, currency, is_active, sort_order) "
                "VALUES (%s, %s, %s, 'pack', %s, %s, 1000, 'BRL', true, 0)",
                (variante_id, produto_id, rotulo, posicao, unidades),
            )
            ids.append(variante_id)
        return produto_id, ids

    def massa(self, nome: str, base: uuid.UUID | None) -> uuid.UUID:
        id_ = uuid.uuid4()
        self.conn.execute(
            "INSERT INTO dough_types (id, name, slug, short_description, sort_order, is_active, "
            "recipe_base_id) VALUES (%s, %s, %s, '', 0, true, %s)",
            (id_, nome, nome.lower().replace(" ", "-"), base),
        )
        return id_

    def pedido(
        self,
        referencia: str,
        status: str,
        dia: date | None,
        *,
        reserva: bool = True,
        lote: uuid.UUID | None = None,
        nome_cliente: str = "NOME-SINTETICO",
    ) -> uuid.UUID:
        id_ = uuid.uuid4()
        self.conn.execute(
            "INSERT INTO orders (id, public_reference, status, customer_note, currency, "
            "holds_capacity, production_local_date, production_batch_id, customer_name, "
            "customer_email) VALUES (%s, %s, %s, '', 'BRL', %s, %s, %s, %s, 'sintetico@example.invalid')",
            (id_, referencia, status, reserva, dia, lote, nome_cliente),
        )
        return id_

    def item(
        self,
        pedido: uuid.UUID,
        *,
        produto: uuid.UUID | None = None,
        variante: uuid.UUID | None = None,
        quantidade: int = 1,
        unidades: int | None = None,
        massa: uuid.UUID | None = None,
        nome_massa: str | None = None,
        nome_forma: str | None = None,
        base: uuid.UUID | None = None,
    ) -> None:
        # Como na Loja, a receita-base é copiada para a linha no momento do pedido.
        if produto is not None:
            self.conn.execute(
                "INSERT INTO order_items (id, order_id, product_id, product_variant_id, quantity, "
                "physical_units, unit_price_cents, line_total_cents, recipe_base_id) VALUES "
                "(%s, %s, %s, %s, %s, %s, 1000, %s, %s)",
                (
                    uuid.uuid4(),
                    pedido,
                    produto,
                    variante,
                    quantidade,
                    unidades,
                    quantidade * 1000,
                    base,
                ),
            )
        else:
            forma = uuid.uuid4()
            self.conn.execute(
                "INSERT INTO bread_shapes (id, name, slug, description, crust_crumb_notes, "
                "image_ref, sort_order, is_active) VALUES (%s, %s, %s, '', '', '', 0, true)",
                (forma, nome_forma or "Forma", f"forma-{forma}"),
            )
            self.conn.execute(
                "INSERT INTO order_items (id, order_id, dough_type_id, bread_shape_id, quantity, "
                "physical_units, dough_name_snapshot, shape_name_snapshot, unit_price_cents, "
                "line_total_cents, recipe_base_id) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, 1000, %s, %s)",
                (
                    uuid.uuid4(),
                    pedido,
                    massa,
                    forma,
                    quantidade,
                    quantidade,
                    nome_massa,
                    nome_forma,
                    quantidade * 1000,
                    base,
                ),
            )

    def lote(self, codigo: str, disponivel_em: datetime) -> uuid.UUID:
        id_ = uuid.uuid4()
        self.conn.execute(
            "INSERT INTO production_batches (id, code, planned_start_at, breads_available_at, "
            "order_deadline_at, capacity_units, status) VALUES (%s, %s, %s, %s, %s, 20, 'open')",
            (
                id_,
                codigo,
                disponivel_em - timedelta(hours=8),
                disponivel_em,
                disponivel_em,
            ),
        )
        return id_

    def excluir(self, pedido: uuid.UUID, *, revertida: bool = False) -> None:
        self.conn.execute(
            "INSERT INTO managerial_exclusions (id, subject_type, subject_id, kind, reason, "
            "author_ref, reversed_at) VALUES (%s, 'order', %s, 'test', 'teste', 'admin:x', %s)",
            (uuid.uuid4(), pedido, datetime.now() if revertida else None),
        )


@pytest.fixture()
def loja():
    helper = Loja()
    helper.limpar()
    yield helper
    helper.limpar()
    helper.fechar()
