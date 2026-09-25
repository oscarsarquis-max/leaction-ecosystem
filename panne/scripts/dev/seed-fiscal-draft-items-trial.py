"""Organização e nota draft vazia para prova visual. Não toca Demo nem 50661."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)


def _load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value)


def main() -> None:
    _load_env()
    os.environ.setdefault("PANNE_FAKE_ACCESS_TOKEN", "panne-fake-access-token")
    from app.config import get_settings
    from app.modules.fiscal_inbound import commands
    from app.modules.identity_organization.models import AppUser, AuthIdentity
    from tests import helpers

    get_settings.cache_clear()
    settings = get_settings()
    sync = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(sync, future=True)
    session = sessionmaker(bind=engine, future=True)()
    slug = f"ensaio-itens-{uuid4().hex[:6]}"
    try:
        identity = session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.issuer == settings.fake_issuer,
                AuthIdentity.subject == settings.fake_subject,
            )
        )
        if identity is None:
            raise SystemExit("proprietario local ausente; rode bootstrap-local-dev.py")
        organization = helpers.org(session, slug)
        organization.display_name = "Ensaio itens (descartável)"
        owner = session.get(AppUser, identity.user_id)
        if owner is None:
            raise SystemExit("usuario local ausente")
        helpers.membership(session, organization, owner, "owner")
        place = helpers.establishment(session, organization, "LOJA")
        unit = helpers.gram(session)
        helpers.kilogram(session)
        flour = helpers.ingredient(session, organization, f"FAR-{slug[-6:]}")
        flour.display_name = "Farinha de trigo ensaio"
        helpers.version(session, flour, unit, status="published")
        principal = helpers.principal_for(owner, organization, "owner")
        documents = []
        for index, width in enumerate(("1440", "390"), start=1):
            documents.append(
                commands.create_manual(
                    session,
                    principal,
                    {
                        "establishment_id": str(place.id),
                        "supplier_name": "Moinho do ensaio",
                        "document_number": f"91{slug[-3:]}{index}",
                        "series": "3",
                    },
                    idempotency_key=uuid4(),
                )
            )
        session.commit()
        payload = {
            "organization_id": str(organization.id),
            "organization_name": organization.display_name,
            "documents": {
                width: {"id": str(row.id), "number": row.number, "status": row.status}
                for width, row in zip(("1440", "390"), documents, strict=True)
            },
            "ingredient_id": str(flour.id),
            "ingredient_name": flour.display_name,
            "ingredient_code": flour.code,
        }
    finally:
        session.close()
        engine.dispose()

    dest = ROOT / "documentacao" / "evidencias" / "fiscal-draft-items" / "trial.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(dest), **payload}, ensure_ascii=False))


if __name__ == "__main__":
    main()
