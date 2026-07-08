"""Modelos de dados do inove4us (SQLAlchemy + SQLite).

Define as tabelas usadas para armazenar o progresso das sessões de inovação
e o histórico das interações com o agente de IA.
"""

from __future__ import annotations

import os
from datetime import datetime
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Carrega o .env do backend, independentemente do diretório de execução
# (ex.: `python database/init_db.py` rodado a partir da raiz do projeto).
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
load_dotenv(_ENV_PATH)

# Credenciais do PostgreSQL lidas do .env.
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "inove4us")

# quote_plus garante que senhas com caracteres especiais (ex.: "!@/")
# não quebrem a montagem da URI de conexão.
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASS)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

Base = declarative_base()

# pool_pre_ping evita erros de "connection closed" em conexões ociosas com o Postgres.
engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


class Project(Base):
    """Sessão de inovação atual."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)

    steps = relationship(
        "StepProgress",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    interactions = relationship(
        "InteractionHistory",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} nome={self.nome!r}>"


class StepProgress(Base):
    """Rastreia em qual passo do Design Thinking o projeto está."""

    __tablename__ = "step_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    step_name = Column(String(50), nullable=False)
    # status: "pendente" | "em_andamento" | "concluido"
    status = Column(String(20), default="pendente", nullable=False)

    project = relationship("Project", back_populates="steps")

    def __repr__(self) -> str:
        return (
            f"<StepProgress project_id={self.project_id} "
            f"step={self.step_name!r} status={self.status!r}>"
        )


class InteractionHistory(Base):
    """Histórico de chat entre o usuário e o agente de IA."""

    __tablename__ = "interaction_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # role: "user" | "agent"
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="interactions")

    def __repr__(self) -> str:
        return (
            f"<InteractionHistory project_id={self.project_id} "
            f"role={self.role!r}>"
        )
