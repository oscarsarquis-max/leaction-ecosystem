"""Publica o piloto autorizado (Prompts 83–84 e Adendo 84A). Sem seed comercial global."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine
from app.domain.gigio.pairing import list_references, publish_authorized_pilot


def main() -> None:
    settings = get_settings()
    if settings.env.strip().lower() not in {"production", "prod"}:
        raise SystemExit("publicação do piloto recusada fora de production")
    reset_engine()
    with Session(get_engine()) as session:
        report = publish_authorized_pilot(session)
        session.commit()
        rows = list_references(session)
    print("pilot_publish")
    for item in report:
        print(
            item["action"],
            item["profile_key"],
            item.get("editorial_status"),
            item.get("reviewed_by"),
            "v" + str(item.get("version")),
            "loja_choice",
            item.get("loja_choice"),
        )
        if item.get("source_url"):
            print(" ", item["source_url"])
    print("inventory")
    for row in rows:
        print(row.profile_key, row.editorial_status, row.retrieval_role, row.verification_status, row.reviewed_by or "-")


if __name__ == "__main__":
    main()
