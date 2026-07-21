import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Evita UnicodeDecodeError do libpq em locales Windows (ex.: pt-BR).
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

DATABASE_URL = "postgresql+psycopg2://postgres:password@127.0.0.1:5435/orquestrador"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"client_encoding": "utf8"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
