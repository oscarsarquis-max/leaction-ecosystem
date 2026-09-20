"""Seed demonstrativo. Não sobe com a API. Apenas env local/development/test/demo."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine
from app.seed import seed_demo_catalog

ALLOWED = frozenset({"local", "development", "test", "demo"})


def main() -> None:
    settings = get_settings()
    if settings.env not in ALLOWED:
        raise SystemExit(f"seed recusado: LOJADEPAES_ENV={settings.env}")
    reset_engine()
    with Session(get_engine()) as session:
        seed_demo_catalog(session)
        session.commit()
    print("seed demonstrativo aplicado (insert-if-missing por slug/id estável)")


if __name__ == "__main__":
    main()
