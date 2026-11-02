"""Organização descartável para capturar a tela de inventário em lote (CURSOR-031).

Não toca Demo nem Loja. Precisa de API local no ar e do proprietário local
(`bootstrap-local-dev.py`). Escreve o resultado em `--out` (padrão: pasta temporária).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.config import get_settings  # noqa: E402
from app.modules.identity_organization.models import AppUser, AuthIdentity  # noqa: E402
from tests import helpers  # noqa: E402


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "c031-trial.json"))
    args = parser.parse_args()

    _load_env()
    get_settings.cache_clear()
    settings = get_settings()
    sync = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(sync, future=True)
    session = sessionmaker(bind=engine, future=True)()
    slug = f"inventario-031-{uuid4().hex[:6]}"
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
        organization.display_name = "Ensaio inventário (descartável)"
        owner = session.get(AppUser, identity.user_id)
        helpers.membership(session, organization, owner, "owner")
        place = helpers.establishment(session, organization, "LOJA")
        gram = helpers.gram(session)
        helpers.kilogram(session)
        helpers.each(session)
        session.commit()
        org_id, place_id, gram_id = str(organization.id), str(place.id), str(gram.id)
    finally:
        session.close()
        engine.dispose()

    token = settings.fake_access_token or f"panne-demo:{settings.fake_subject}"
    base = f"http://127.0.0.1:{settings.http_port}/api/v1/organizations/{org_id}"
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": str(uuid4())}

    def post(path: str, body: dict) -> dict:
        response = httpx.post(
            f"{base}{path}",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json=body,
            timeout=30,
        )
        if response.status_code >= 400:
            raise SystemExit(f"{path} {response.status_code} {response.text}")
        return response.json()

    location = post(
        "/inventory/locations",
        {"establishment_id": place_id, "code": "DESP", "display_name": "Despensa da loja", "kind": "warehouse"},
    )["data"]["id"]

    stock = [
        ("Farinha de trigo tipo 1", "FAR1", "kg", "20", "4.20"),
        ("Açúcar cristal", "ACU1", "kg", "8", "3.90"),
        ("Manteiga sem sal", "MAN1", "un", "6", "32.00"),
        ("Leite integral", "LEI1", "un", "12", "5.10"),
    ]
    ids: dict[str, str] = {}
    for name, code, unit, quantity, cost in stock:
        created = post(
            "/ingredients",
            {"code": code, "display_name": name, "ingredient_type": "simple", "nutrition_basis_unit_id": gram_id},
        )["data"]["id"]
        ids[name] = created
        post(
            "/inventory/openings",
            {
                "ingredient_id": created,
                "inventory_location_id": location,
                "quantity": quantity,
                "unit_code": unit,
                "origin": "contagem de ensaio",
                "unit_cost": cost,
                "confirmed": True,
            },
        )

    out = {"organization_id": org_id, "display_name": "Ensaio inventário (descartável)", "location_id": location}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
