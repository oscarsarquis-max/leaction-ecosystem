"""Cria organização descartável para capturas autenticadas. Não toca Demo nem Loja."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.config import get_settings
from app.modules.identity_organization.models import AppUser, AuthIdentity
from tests import helpers


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
    get_settings.cache_clear()
    settings = get_settings()
    sync = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(sync, future=True)
    session = sessionmaker(bind=engine, future=True)()
    slug = f"ensaio-insumo-{uuid4().hex[:6]}"
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
        organization.display_name = "Ensaio insumo (descartável)"
        owner = session.get(AppUser, identity.user_id)
        if owner is None:
            raise SystemExit("usuario local ausente")
        helpers.membership(session, organization, owner, "owner")
        place = helpers.establishment(session, organization, "LOJA")
        gram_unit = helpers.gram(session)
        helpers.kilogram(session)
        helpers.each(session)
        session.commit()
        org_id = str(organization.id)
        place_id = str(place.id)
        gram_id = str(gram_unit.id)
    finally:
        session.close()
        engine.dispose()

    token = settings.fake_access_token or f"panne-demo:{settings.fake_subject}"
    base = f"http://127.0.0.1:{settings.http_port}/api/v1/organizations/{org_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Correlation-Id": str(uuid4()),
    }

    def post(path: str, body: dict) -> dict:
        response = httpx.post(
            f"{base}{path}",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json=body,
            timeout=20,
        )
        if response.status_code >= 400:
            raise SystemExit(f"{path} {response.status_code} {response.text}")
        return response.json()

    gram = httpx.get(f"{base}/ingredients?limit=1", headers=headers, timeout=20)
    if gram.status_code >= 400:
        raise SystemExit(f"API local recusou o ensaio: {gram.status_code} {gram.text}")

    created = post(
        "/ingredients",
        {
            "code": f"ENS-{slug[-4:]}",
            "display_name": "Farinha de trigo ensaio",
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": gram_id,
        },
    )
    ingredient_id = created["data"]["id"]
    extra = post(
        "/ingredients",
        {
            "code": f"LIM-{slug[-4:]}",
            "display_name": "Limão siciliano ensaio",
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": gram_id,
        },
    )
    lemon_id = extra["data"]["id"]
    location = post(
        "/inventory/locations",
        {
            "establishment_id": place_id,
            "code": "DESP",
            "display_name": "Despensa ensaio",
            "kind": "warehouse",
        },
    )
    location_id = location["data"]["id"]
    post(
        "/inventory/openings",
        {
            "ingredient_id": lemon_id,
            "inventory_location_id": location_id,
            "quantity": "2",
            "unit_code": "un",
            "origin": "contagem física da despensa",
            "unit_cost": "4.50",
            "confirmed": True,
            "internal_lot_code": f"ABR-{slug[-4:]}K",
        },
    )
    post(
        "/inventory/openings",
        {
            "ingredient_id": lemon_id,
            "inventory_location_id": location_id,
            "quantity": "1",
            "unit_code": "un",
            "origin": "sobra sem nota",
            "cost_unknown": True,
            "confirmed": True,
            "internal_lot_code": f"ABR-{slug[-4:]}U",
        },
    )
    document = post(
        "/fiscal/documents",
        {
            "establishment_id": place_id,
            "supplier_name": "Fornecedor ensaio",
            "document_number": "103219",
            "items": [
                {
                    "description": "Farinha de Trigo de 1 Kg, Tipo 0",
                    "gtin": "8014601028747",
                    "quantity": "1",
                    "unit_code": "UN",
                    "unit_price": "10",
                    "gross_amount": "10",
                },
                {
                    "description": "Farinha de Trigo de 1 Kg, Tipo 0",
                    "gtin": "8014601028747",
                    "quantity": "3",
                    "unit_code": "UN",
                    "unit_price": "10",
                    "gross_amount": "30",
                },
            ],
        },
    )["data"]
    reviewed = post(
        f"/fiscal/documents/{document['id']}/review",
        {
            "expected_row_version": document["row_version"],
            "lines": [
                {
                    "item_id": item["id"],
                    "suggested_ingredient_name": item["supplier_description"],
                    "reviewed_quantity": item["invoiced_quantity"],
                    "as_expected": True,
                }
                for item in document["items"]
            ],
        },
    )["data"]
    received = post(
        f"/fiscal/documents/{reviewed['id']}/receive",
        {
            "new_location_name": "Despensa nota ensaio",
            "lines": [
                {
                    "item_id": item["id"],
                    "create_ingredient": True,
                    "new_ingredient_name": f"{item['supplier_description']} {index + 1}",
                    "stock_unit": "un",
                    "conversion_factor": "1",
                    "received_quantity": item["invoiced_quantity"],
                    "result": "ok",
                }
                for index, item in enumerate(reviewed["items"])
            ],
        },
    )["data"]

    out = {
        "organization_id": org_id,
        "organization_slug": slug,
        "display_name": "Ensaio insumo (descartável)",
        "place_id": place_id,
        "ingredient_id": ingredient_id,
        "lemon_id": lemon_id,
        "document_id": received["id"],
        "document_number": received["document_number"],
    }
    target = ROOT / "documentacao" / "evidencias" / "cursor-insumo-manual" / "trial.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
