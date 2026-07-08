"""Seed manual das regras de curadoria do marketplace."""

from app import create_app
from app.database import db
from app.database.models import MarketplaceCuration
from app.database.seed import DEFAULT_CURATION_ROWS, seed_curation_if_empty


def main() -> None:
    app = create_app()
    with app.app_context():
        inserted = seed_curation_if_empty()
        if inserted:
            print(f"Seed concluído: {inserted} regras inseridas.")
            return

        for row in DEFAULT_CURATION_ROWS:
            existing = db.session.get(MarketplaceCuration, row["id"])
            if existing is None:
                db.session.add(
                    MarketplaceCuration(
                        id=row["id"],
                        search_terms=list(row["search_terms"]),
                        positive_keywords=list(row["positive_keywords"]),
                        negative_keywords=list(row["negative_keywords"]),
                    )
                )
        db.session.commit()
        total = MarketplaceCuration.query.count()
        print(f"Tabela já existia. Total de regras: {total}")


if __name__ == "__main__":
    main()
