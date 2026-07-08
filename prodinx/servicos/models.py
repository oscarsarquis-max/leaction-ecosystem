from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Indicadores(Base):
    __tablename__ = "indicadores"
    __table_args__ = (
        UniqueConstraint(
            "cod_indicador",
            "nome_grupo",
            name="uq_indicadores_cod_grupo",
        ),
        Index("ix_indicadores_cod_indicador", "cod_indicador"),
        Index("ix_indicadores_nome_grupo", "nome_grupo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cod_indicador: Mapped[str] = mapped_column(String(10), nullable=False)
    nome_indicador: Mapped[str] = mapped_column(String(150), nullable=False)
    nome_grupo: Mapped[str] = mapped_column(String(50), nullable=False)
    dimensao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nivel_avaliacao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    formula_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula_normalizada: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parametros_configuraveis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    subpapeis_aplicaveis: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
    )

    medicoes: Mapped[list["Medicoes"]] = relationship(
        "Medicoes",
        back_populates="indicador",
        passive_deletes=True,
    )
    descricao: Mapped["DescricaoIndicador | None"] = relationship(
        "DescricaoIndicador",
        back_populates="indicadores",
        primaryjoin="foreign(Indicadores.cod_indicador) == DescricaoIndicador.cod_indicador",
        uselist=False,
    )


class Colaboradores(Base):
    __tablename__ = "colaboradores"
    __table_args__ = (
        Index("ix_colaboradores_matricula", "matricula"),
    )

    id_colaborador: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    matricula: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    funcao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codsetor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    papel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subpapel: Mapped[str | None] = mapped_column(String(50), nullable=True)

    medicoes: Mapped[list["Medicoes"]] = relationship(
        "Medicoes",
        back_populates="colaborador",
        passive_deletes=True,
    )


class DescricaoIndicador(Base):
    __tablename__ = "descricao_indicador"
    __table_args__ = (
        Index("ix_descricao_indicador_cod_indicador", "cod_indicador"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cod_indicador: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
    )
    subpapel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    normalizacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    explicacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    importancia: Mapped[str | None] = mapped_column(Text, nullable=True)

    indicadores: Mapped[list["Indicadores"]] = relationship(
        "Indicadores",
        back_populates="descricao",
        primaryjoin="DescricaoIndicador.cod_indicador == foreign(Indicadores.cod_indicador)",
    )


class Medicoes(Base):
    __tablename__ = "medicoes"
    __table_args__ = (
        Index("ix_medicoes_indicador_id", "indicador_id"),
        Index("ix_medicoes_id_colaborador", "id_colaborador"),
        Index("ix_medicoes_status_import", "status_import"),
        Index("ix_medicoes_data_importacao", "data_importacao"),
        Index("ix_medicoes_data_referencia", "data_referencia"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicador_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("indicadores.id", ondelete="CASCADE"),
        nullable=True,
    )
    id_colaborador: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("colaboradores.id_colaborador", ondelete="SET NULL"),
        nullable=True,
    )
    nome_arquivo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data_importacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    data_referencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    status_import: Mapped[str] = mapped_column(String(20), nullable=False)
    detalhe_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    indicador: Mapped[Indicadores | None] = relationship(
        "Indicadores",
        back_populates="medicoes",
    )
    colaborador: Mapped["Colaboradores | None"] = relationship(
        "Colaboradores",
        back_populates="medicoes",
    )


class AnalisesInteligentes(Base):
    __tablename__ = "analises_inteligentes"
    __table_args__ = (
        UniqueConstraint("id_colaborador", name="uq_analises_inteligentes_colaborador"),
        Index("ix_analises_inteligentes_colaborador", "id_colaborador"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_colaborador: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("colaboradores.id_colaborador", ondelete="CASCADE"),
        nullable=False,
    )
    hash_contexto: Mapped[str] = mapped_column(String(64), nullable=False)
    resultado: Mapped[dict] = mapped_column(JSONB, nullable=False)
    modelo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gerado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    colaborador: Mapped["Colaboradores"] = relationship("Colaboradores")


class ConfiguracaoPesos(Base):
    __tablename__ = "configuracao_pesos"
    __table_args__ = (
        UniqueConstraint("papel", "subpapel", name="uq_configuracao_pesos_papel_subpapel"),
        Index("ix_configuracao_pesos_papel", "papel"),
        Index("ix_configuracao_pesos_subpapel", "subpapel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    papel: Mapped[str] = mapped_column(String(50), nullable=False)
    subpapel: Mapped[str] = mapped_column(String(50), nullable=False)
    peso_ind: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.4)
    peso_eq: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.6)
    peso_satisfacao: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    peso_performance: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    peso_atividade: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    peso_comunicacao: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    peso_eficiencia: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
