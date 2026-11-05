"""Estoque simplificado, no desenho da Panne (ledger imutável), sempre dentro de uma organização.

ingrediente 1 ── N item_estoque ── N lote ── N movimento
                                   entrada ── N entrada_linha (cada linha gera lote + movimento)

O saldo nunca é gravado: é a soma dos movimentos (por lote, item e ingrediente). O movimento é
imutável (trigger no banco); corrige-se com um movimento contrário.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.escopo import OrgScoped

UNIDADES_BASE = ("g", "ml", "un")
CONTROLES = ("massa", "volume", "embalagem")
MOTIVOS_ENTRADA = ("contagem", "compra_sem_nota", "bonificacao", "outro")
TIPOS_MOVIMENTO = ("entrada", "ajuste", "juncao")
CATEGORIAS_INGREDIENTE = (
    "Farinhas",
    "Fermentos",
    "Açúcares e mel",
    "Gorduras",
    "Laticínios",
    "Ovos",
    "Sal e temperos",
    "Sementes e grãos",
    "Frutas secas e oleaginosas",
    "Chocolates e cacau",
    "Frios e embutidos",
    "Líquidos",
    "Outros",
)
CATEGORIA_PADRAO = "Outros"


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def _agora() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Local(OrgScoped, Base):
    __tablename__ = "locais"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_locais_org_nome"),
        Index(
            "uq_locais_um_padrao_por_org",
            "organizacao_id",
            unique=True,
            postgresql_where=text("padrao"),
        ),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(80), nullable=False)
    padrao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = _agora()


class Ingrediente(OrgScoped, Base):
    __tablename__ = "ingredientes"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_ingredientes_org_nome"),
        CheckConstraint("unidade_base IN ('g','ml','un')", name="ck_ingredientes_unidade_base"),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(120), nullable=False)
    unidade_base: Mapped[str] = mapped_column(String(2), nullable=False)
    categoria: Mapped[str] = mapped_column(
        String(40), nullable=False, default=CATEGORIA_PADRAO, server_default=CATEGORIA_PADRAO
    )
    # Outros nomes pelos quais a padaria chama o ingrediente ("farinha 00", "tipo 00").
    apelidos: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    # Quem disse "confirmo que não existe" ao cadastrar um ingrediente parecido com outro.
    confirmado_inexistente_por: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id")
    )
    confirmado_inexistente_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Preenchido quando este ingrediente foi juntado em outro (nada é apagado).
    juntado_em_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id")
    )
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = _agora()


class CatalogoIngrediente(Base):
    """Catálogo de referência, GLOBAL (sem organização): só sugere; não é dado de ninguém.

    Carregado do YAML versionado pelo comando `carregar-catalogo`; nunca editado pela tela.
    """

    __tablename__ = "catalogo_ingrediente"
    __table_args__ = (
        UniqueConstraint("nome_normalizado", name="uq_catalogo_ingrediente_nome"),
        CheckConstraint("unidade_base IN ('g','ml','un')", name="ck_catalogo_unidade_base"),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria: Mapped[str] = mapped_column(String(40), nullable=False)
    unidade_base: Mapped[str] = mapped_column(String(2), nullable=False)
    apelidos: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = _agora()


class ItemEstoque(OrgScoped, Base):
    __tablename__ = "itens_estoque"
    __table_args__ = (
        UniqueConstraint(
            "organizacao_id",
            "nome_normalizado",
            "marca_normalizada",
            name="uq_itens_org_nome_marca",
        ),
        CheckConstraint(
            "unidade_controle IN ('massa','volume','embalagem')", name="ck_itens_controle"
        ),
        CheckConstraint(
            "(unidade_controle = 'embalagem' AND conteudo_embalagem > 0)"
            " OR (unidade_controle <> 'embalagem' AND conteudo_embalagem IS NULL)",
            name="ck_itens_conteudo",
        ),
    )

    id: Mapped[UUID] = _pk()
    ingrediente_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(160), nullable=False)
    marca: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    marca_normalizada: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    unidade_controle: Mapped[str] = mapped_column(String(12), nullable=False)
    # Conteúdo de UMA embalagem, na unidade base do ingrediente (g, ml ou un).
    conteudo_embalagem: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = _agora()


class Lote(OrgScoped, Base):
    __tablename__ = "lotes"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "item_id", "codigo", name="uq_lotes_org_item_codigo"),
        CheckConstraint("NOT (validade IS NOT NULL AND sem_validade)", name="ck_lotes_validade"),
    )

    id: Mapped[UUID] = _pk()
    item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("itens_estoque.id"), nullable=False, index=True
    )
    local_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("locais.id"), nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    validade: Mapped[date | None] = mapped_column(Date)
    sem_validade: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # R$ por unidade base (g, ml ou un). Vazio = custo desconhecido (nunca zero).
    custo_unidade_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    criado_em: Mapped[datetime] = _agora()


class Entrada(OrgScoped, Base):
    __tablename__ = "entradas"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "chave_idempotencia", name="uq_entradas_org_chave"),
        CheckConstraint("tipo IN ('sem_nota','com_nota')", name="ck_entradas_tipo"),
        CheckConstraint(
            "motivo IN ('contagem','compra_sem_nota','bonificacao','outro')",
            name="ck_entradas_motivo",
        ),
    )

    id: Mapped[UUID] = _pk()
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    local_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("locais.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    motivo: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo_detalhe: Mapped[str | None] = mapped_column(String(200))
    fornecedor: Mapped[str | None] = mapped_column(String(160))
    observacao: Mapped[str | None] = mapped_column(Text)
    lancada_por: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    chave_idempotencia: Mapped[str] = mapped_column(String(64), nullable=False)
    criada_em: Mapped[datetime] = _agora()


class Movimento(OrgScoped, Base):
    """Linha do ledger. Imutável: o banco recusa UPDATE e DELETE."""

    __tablename__ = "movimentos"
    __table_args__ = (
        CheckConstraint("tipo IN ('entrada','ajuste','juncao')", name="ck_movimentos_tipo"),
        CheckConstraint(
            "(tipo = 'juncao' AND quantidade_base = 0"
            " AND ingrediente_origem_id IS NOT NULL AND ingrediente_destino_id IS NOT NULL)"
            " OR (tipo <> 'juncao' AND quantidade_base <> 0 AND lote_id IS NOT NULL AND item_id IS NOT NULL)",
            name="ck_movimentos_forma",
        ),
        Index("ix_movimentos_lote", "lote_id"),
        Index("ix_movimentos_item", "item_id"),
    )

    id: Mapped[UUID] = _pk()
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    item_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("itens_estoque.id"))
    lote_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("lotes.id"))
    # Na unidade base do ingrediente (g, ml ou un). Positivo entra, negativo sai.
    quantidade_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text)
    entrada_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("entradas.id"))
    ingrediente_origem_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id")
    )
    ingrediente_destino_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id")
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    criado_em: Mapped[datetime] = _agora()


class EntradaLinha(OrgScoped, Base):
    __tablename__ = "entrada_linhas"
    __table_args__ = (UniqueConstraint("entrada_id", "posicao", name="uq_entrada_linhas_posicao"),)

    id: Mapped[UUID] = _pk()
    entrada_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("entradas.id"), nullable=False, index=True
    )
    posicao: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("itens_estoque.id"), nullable=False
    )
    lote_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lotes.id"), nullable=False
    )
    movimento_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("movimentos.id"), nullable=False
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unidade: Mapped[str] = mapped_column(String(12), nullable=False)
    quantidade_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    # Modo "preço por unidade" (o legado): o que foi digitado e por quê (kg, L ou emb).
    custo_informado: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    custo_por: Mapped[str | None] = mapped_column(String(12))
    # Modo "valor pago" (o padrão desde a 006): o TOTAL pago pela linha, como foi digitado.
    valor_pago: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    # 'valor_pago' | 'preco_unidade'. Vazio nas linhas anteriores à 006 (que eram sempre preço por unidade).
    modo_custo: Mapped[str | None] = mapped_column(String(14))
    # Valor da linha (arredondado a centavos): o valor pago, ou quantidade x preço por unidade.
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class CorrecaoCusto(OrgScoped, Base):
    """Histórico de correção do custo de um lote. O custo não é saldo: nunca mexe na quantidade."""

    __tablename__ = "correcoes_custo"
    __table_args__ = (
        CheckConstraint("modo IN ('valor_pago','preco_unidade')", name="ck_correcoes_custo_modo"),
    )

    id: Mapped[UUID] = _pk()
    lote_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lotes.id"), nullable=False, index=True
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    # Quanto foi comprado (unidade base) quando o custo foi corrigido: a base do valor pago.
    quantidade_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    modo: Mapped[str] = mapped_column(String(14), nullable=False)
    valor_pago: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    preco_informado: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    # R$ por unidade base (g, ml ou un), antes e depois. Antes vazio = custo era desconhecido.
    custo_antes: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    custo_depois: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = _agora()


class TrocaIngrediente(OrgScoped, Base):
    """Histórico de "Trocar ingrediente": o item passou de um ingrediente para outro (com os lotes)."""

    __tablename__ = "trocas_ingrediente"

    id: Mapped[UUID] = _pk()
    item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("itens_estoque.id"), nullable=False, index=True
    )
    de_ingrediente_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id"), nullable=False
    )
    para_ingrediente_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredientes.id"), nullable=False
    )
    # O movimento de junção (quantidade 0) que leva o saldo de um ingrediente ao outro no histórico.
    movimento_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("movimentos.id")
    )
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = _agora()


class ParecidoDistinto(OrgScoped, Base):
    """Decisão "não são o mesmo": o par deixa de ser apontado como parecido."""

    __tablename__ = "parecidos_distintos"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "tipo", "id_menor", "id_maior", name="uq_parecidos_par"),
        CheckConstraint("tipo IN ('ingrediente','item')", name="ck_parecidos_tipo"),
    )

    id: Mapped[UUID] = _pk()
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    id_menor: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    id_maior: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    criado_em: Mapped[datetime] = _agora()
