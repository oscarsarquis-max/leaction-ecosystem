"""
MAtivas - Modelos SQLAlchemy (área administrativa)
=================================================================
Define as tabelas de autenticação admin e regras de vocabulário.
Usado como referência de schema e base para futuros endpoints admin.

Uso (criar tabelas via SQLAlchemy):
    from database.models import Base, engine
    Base.metadata.create_all(engine)
"""

import os
from urllib.parse import quote_plus

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

_engine = None
_SessionLocal = None


class AdminUser(Base):
    """Usuário da área administrativa."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


class VocabularyRule(Base):
    """Regra de vocabulário gerenciável pelo painel admin."""

    __tablename__ = "vocabulary_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), unique=True, nullable=False)
    rule_type = Column(String(50), nullable=False)  # bloqueada | substituir | obrigatoria
    replacement = Column(String(255), nullable=True)
    is_active = Column(Integer, nullable=False, default=1, server_default="1")


class UiContent(Base):
    """Textos e URLs de imagens da interface, editáveis pelo admin."""

    __tablename__ = "ui_content"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_key = Column(String(120), unique=True, nullable=False)
    content_value = Column(String(2000), nullable=False)
    content_type = Column(String(20), nullable=False, default="text")  # text | image_url
    label = Column(String(255), nullable=True)
    is_active = Column(Integer, nullable=False, default=1, server_default="1")


def get_engine():
    """Monta engine SQLAlchemy a partir das mesmas variáveis do backend."""
    global _engine
    if _engine is None:
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        dbname = os.environ.get("DB_NAME", "MAtivas")
        user = os.environ.get("DB_USER") or os.environ.get("DB_USERNAME") or "postgres"
        password = os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS") or "Cmgv6190!@"
        sslmode = os.environ.get("DB_SSLMODE", "disable")
        url = (
            f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{dbname}?sslmode={sslmode}"
        )
        _engine = create_engine(url)
    return _engine


def get_session_factory():
    """Retorna factory de sessões SQLAlchemy (singleton)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


def get_db_session():
    """Abre uma nova sessão SQLAlchemy (o chamador deve fechar)."""
    return get_session_factory()()
