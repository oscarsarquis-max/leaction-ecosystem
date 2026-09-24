"""Inicialização idempotente de produção: slots vazios e agenda padrão. Sem seed comercial."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine
from app.domain.schedule import ensure_schedule_settings
from app.domain.showcase import ensure_slots


def bootstrap(session: Session) -> None:
    ensure_schedule_settings(session)
    ensure_slots(session)


def main() -> None:
    settings = get_settings()
    if settings.env.strip().lower() not in {"production", "prod"}:
        raise SystemExit("bootstrap de produção recusado fora de production")
    reset_engine()
    with Session(get_engine()) as session:
        bootstrap(session)
        session.commit()
    print("agenda padrão e dez posições da vitrine conferidas")


if __name__ == "__main__":
    main()
