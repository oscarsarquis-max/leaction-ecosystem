"""Cria as tabelas do inove4us no banco PostgreSQL.

As credenciais de conexão (DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME) são
lidas do arquivo backend/.env por database/models.py.

Uso:
    python database/init_db.py
"""

from __future__ import annotations

from models import DB_HOST, DB_NAME, DB_PORT, Base, engine


def init_db() -> None:
    """Cria todas as tabelas definidas em models.py no PostgreSQL."""
    Base.metadata.create_all(bind=engine)
    print(
        f"Tabelas criadas/atualizadas no PostgreSQL em "
        f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    tabelas = ", ".join(sorted(Base.metadata.tables.keys()))
    print(f"Tabelas disponíveis: {tabelas}")


if __name__ == "__main__":
    init_db()
