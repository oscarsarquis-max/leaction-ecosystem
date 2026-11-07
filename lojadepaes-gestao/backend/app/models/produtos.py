"""Produto nasce na Gestão. A Loja de Pães só recebe o que o Oscar mandar, num ciclo futuro.

Produto produzido tem uma receita técnica (ainda sem linhas). Produto comprado aponta um item de
estoque. Componente vira um ingrediente de "Preparos da casa", para entrar na receita de outro.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.escopo import OrgScoped

MODALIDADES = ("produzido", "comprado")
UNIDADES_VENDA = ("un", "kg")
UNIDADES_LINHA = ("g", "kg", "ml", "l", "un")
SITUACOES_RECEITA = ("rascunho", "publicada")


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def _agora() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Familia(OrgScoped, Base):
    __tablename__ = "familias"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_familias_org_nome"),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(80), nullable=False)
    criado_em: Mapped[datetime] = _agora()


class Produto(OrgScoped, Base):
    __tablename__ = "produtos"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_produtos_org_nome"),
        CheckConstraint("modalidade IN ('produzido','comprado')", name="ck_produtos_modalidade"),
        CheckConstraint("unidade_venda IN ('un','kg')", name="ck_produtos_unidade_venda"),
        CheckConstraint("uso_venda OR uso_componente", name="ck_produtos_uso"),
        CheckConstraint(
            "peso_unidade_g IS NULL OR peso_unidade_g > 0", name="ck_produtos_peso"
        ),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(40))
    modalidade: Mapped[str] = mapped_column(String(12), nullable=False)
    uso_venda: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uso_componente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    familia_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("familias.id"))
    unidade_venda: Mapped[str] = mapped_column(String(2), nullable=False)
    peso_unidade_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacao: Mapped[str | None] = mapped_column(Text)
    item_estoque_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("itens_estoque.id")
    )
    foto_url: Mapped[str | None] = mapped_column(String(500))
    origem_loja_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ProdutoFoto(OrgScoped, Base):
    """Foto enviada na Gestão. Uma por produto. A miniatura fica na mesma linha."""

    __tablename__ = "produto_fotos"
    __table_args__ = (
        UniqueConstraint("produto_id", name="uq_produto_fotos_produto"),
        CheckConstraint("tipo = 'image/webp'", name="ck_produto_fotos_tipo"),
        CheckConstraint("largura > 0 AND altura > 0", name="ck_produto_fotos_medida"),
        CheckConstraint("largura <= 1200 AND altura <= 1200", name="ck_produto_fotos_teto"),
        CheckConstraint("bytes > 0", name="ck_produto_fotos_bytes"),
        CheckConstraint("mini_largura > 0 AND mini_altura > 0", name="ck_produto_fotos_mini"),
        CheckConstraint("mini_largura <= 96 AND mini_altura <= 96", name="ck_produto_fotos_mini_teto"),
    )

    id: Mapped[UUID] = _pk()
    produto_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="image/webp")
    largura: Mapped[int] = mapped_column(Integer, nullable=False)
    altura: Mapped[int] = mapped_column(Integer, nullable=False)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    conteudo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, deferred=True)
    mini_largura: Mapped[int] = mapped_column(Integer, nullable=False)
    mini_altura: Mapped[int] = mapped_column(Integer, nullable=False)
    mini_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mini_conteudo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, deferred=True)
    enviado_por: Mapped[str] = mapped_column(String(120), nullable=False)
    enviado_em: Mapped[datetime] = _agora()


class Receita(OrgScoped, Base):
    """Uma receita técnica por produto produzido. A versão publicada fica em receita_versoes."""

    __tablename__ = "receitas"
    __table_args__ = (
        UniqueConstraint("produto_id", name="uq_receitas_produto"),
        CheckConstraint("situacao IN ('rascunho', 'publicada')", name="ck_receitas_situacao"),
        CheckConstraint(
            "rendimento_quantidade IS NULL OR rendimento_quantidade > 0",
            name="ck_receitas_rendimento",
        ),
        CheckConstraint(
            "rendimento_unidade IS NULL OR rendimento_unidade IN ('g','kg','ml','l','un')",
            name="ck_receitas_unidade_rendimento",
        ),
        CheckConstraint(
            "peso_unidade_g IS NULL OR peso_unidade_g > 0",
            name="ck_receitas_peso",
        ),
        CheckConstraint(
            "perda_percentual >= 0 AND perda_percentual < 100",
            name="ck_receitas_perda",
        ),
        CheckConstraint(
            "formato IS NULL OR formato IN ('forma', 'forma_enriquecida', 'livre', 'assadeira', 'pequeno')",
            name="ck_receitas_formato",
        ),
        CheckConstraint(
            "unidades_desejadas IS NULL OR unidades_desejadas > 0",
            name="ck_receitas_unidades",
        ),
        CheckConstraint(
            "perda_processo_origem IS NULL OR perda_processo_origem IN ('medido', 'padrao', 'referencia', 'manual')",
            name="ck_receitas_origem_processo",
        ),
        CheckConstraint(
            "perda_coccao_origem IS NULL OR perda_coccao_origem IN ('medido', 'padrao', 'referencia', 'manual')",
            name="ck_receitas_origem_coccao",
        ),
        CheckConstraint("versao >= 1", name="ck_receitas_versao"),
    )

    id: Mapped[UUID] = _pk()
    produto_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False
    )
    situacao: Mapped[str] = mapped_column(String(12), nullable=False, default="rascunho")
    rendimento_quantidade: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    rendimento_unidade: Mapped[str | None] = mapped_column(String(2))
    peso_unidade_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    perda_percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal(0))
    formato: Mapped[str | None] = mapped_column(String(20))
    unidades_desejadas: Mapped[int | None] = mapped_column(Integer)
    perda_processo_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    perda_processo_origem: Mapped[str | None] = mapped_column(String(12))
    perda_processo_referencia_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("perda_referencia.id")
    )
    perda_processo_motivo: Mapped[str | None] = mapped_column(Text)
    perda_coccao_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    perda_coccao_origem: Mapped[str | None] = mapped_column(String(12))
    perda_coccao_referencia_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("perda_referencia.id")
    )
    perda_coccao_motivo: Mapped[str | None] = mapped_column(Text)
    modo_fazer: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    criado_em: Mapped[datetime] = _agora()


class ReceitaLinha(OrgScoped, Base):
    """Uma linha da receita em edição. Ingrediente vazio é linha ainda “a decidir”."""

    __tablename__ = "receita_linhas"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_receita_linhas_quantidade"),
        CheckConstraint("unidade IN ('g','kg','ml','l','un')", name="ck_receita_linhas_unidade"),
        CheckConstraint("ordem >= 1", name="ck_receita_linhas_ordem"),
        CheckConstraint(
            "origem IN ('manual', 'estimado', 'conferido')",
            name="ck_receita_linhas_origem",
        ),
        CheckConstraint(
            "funcao IN ('massa', 'recheio', 'cobertura', 'finalizacao')",
            name="ck_receita_linhas_funcao",
        ),
    )

    id: Mapped[UUID] = _pk()
    receita_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    ingrediente_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id")
    )
    texto: Mapped[str | None] = mapped_column(String(120))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unidade: Mapped[str] = mapped_column(String(2), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(String(12), nullable=False, default="manual", server_default="manual")
    faixa_min: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    faixa_max: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    funcao: Mapped[str] = mapped_column(String(12), nullable=False, default="massa", server_default="massa")


class ReceitaVersao(OrgScoped, Base):
    """Cópia imutável gravada ao publicar. O rascunho seguinte não altera esta linha."""

    __tablename__ = "receita_versoes"
    __table_args__ = (
        UniqueConstraint("receita_id", "versao", name="uq_receita_versoes_numero"),
        CheckConstraint("versao >= 1", name="ck_receita_versoes_versao"),
    )

    id: Mapped[UUID] = _pk()
    receita_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    publicada_em: Mapped[datetime] = _agora()
    rendimento_quantidade: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    rendimento_unidade: Mapped[str | None] = mapped_column(String(2))
    peso_unidade_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    perda_percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal(0))
    modo_fazer: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linhas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
