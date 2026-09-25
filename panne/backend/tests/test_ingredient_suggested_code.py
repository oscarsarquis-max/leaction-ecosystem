"""Código interno sugerido: alocação no servidor, por organização."""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from app.modules.ingredient_catalog.codes import peek_suggested_code
from app.modules.ingredient_catalog.commands import create_ingredient
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.production_planning.errors import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_ingredient_http import _create_ingredient, _headers, _setup
from tests.test_production_api import _cleanup


def _ensure_head(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    _ensure_head(engine)


def test_suggested_code_is_org_scoped_and_allocated_on_create(engine):
    from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier

    fake = FakeAccessTokenVerifier()
    left = _setup(engine, "sug-l", fake=fake)
    right = _setup(engine, "sug-r", fake=fake, client=left["client"])

    peek_left = left["client"].get(
        f"/api/v1/organizations/{left['organization'].id}/ingredients/suggested-code",
        headers=_headers(left["token"], left["organization"].id),
    )
    peek_right = right["client"].get(
        f"/api/v1/organizations/{right['organization'].id}/ingredients/suggested-code",
        headers=_headers(right["token"], right["organization"].id),
    )
    assert peek_left.status_code == 200, peek_left.text
    assert peek_right.status_code == 200, peek_right.text
    assert peek_left.json()["code"] == "ING-000001"
    assert peek_right.json()["code"] == "ING-000001"
    assert "nota" in peek_left.json()["explanation"]

    created = left["client"].post(
        f"/api/v1/organizations/{left['organization'].id}/ingredients",
        headers=_headers(left["token"], left["organization"].id, key=uuid4()),
        json={
            "code_mode": "suggested",
            "display_name": "Açúcar da casa",
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": str(left["unit"].id),
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["code"] == "ING-000001"
    still = left["client"].get(
        f"/api/v1/organizations/{left['organization'].id}/ingredients/suggested-code",
        headers=_headers(left["token"], left["organization"].id),
    )
    assert still.json()["code"] == "ING-000002"
    other = right["client"].get(
        f"/api/v1/organizations/{right['organization'].id}/ingredients/suggested-code",
        headers=_headers(right["token"], right["organization"].id),
    )
    assert other.json()["code"] == "ING-000001"

    occupied = left["client"].post(
        f"/api/v1/organizations/{left['organization'].id}/ingredients",
        headers=_headers(left["token"], left["organization"].id, key=uuid4()),
        json={
            "code": "ING-000001",
            "code_mode": "manual",
            "display_name": "Outro açúcar",
            "ingredient_type": "simple",
            "nutrition_basis_unit_id": str(left["unit"].id),
        },
    )
    assert occupied.status_code == 422
    payload = occupied.json()
    assert (payload.get("code") or (payload.get("detail") or {}).get("code")) == "codigo_duplicado"

    existing = _create_ingredient(left, "FAR-KEEP", "Farinha antiga")
    assert existing["data"]["code"] == "FAR-KEEP"
    _cleanup(left["client"])
    _cleanup(right["client"])
    left["admin"].close()
    right["admin"].close()


def test_suggested_create_is_idempotent_and_name_change_does_not_collide(engine):
    ctx = _setup(engine, "sug-id")
    key = uuid4()
    body = {
        "code_mode": "suggested",
        "code": "ING-000001",
        "display_name": "Sal",
        "ingredient_type": "simple",
        "nutrition_basis_unit_id": str(ctx["unit"].id),
    }
    first = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients",
        headers=_headers(ctx["token"], ctx["organization"].id, key=key),
        json=body,
    )
    second = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients",
        headers=_headers(ctx["token"], ctx["organization"].id, key=key),
        json=body,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    renamed = ctx["client"].post(
        f"/api/v1/organizations/{ctx['organization'].id}/ingredients",
        headers=_headers(ctx["token"], ctx["organization"].id, key=uuid4()),
        json={**body, "display_name": "Sal grosso"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["id"] != first.json()["data"]["id"]
    assert renamed.json()["data"]["code"] == "ING-000002"
    _cleanup(ctx["client"])
    ctx["admin"].close()


def test_concurrent_suggested_creates_get_distinct_codes(engine):
    ctx = _setup(engine, "sug-cc")
    session = Session(bind=engine, future=True)
    peek = peek_suggested_code(session, ctx["organization"].id)
    assert peek == "ING-000001"
    session.close()
    codes: list[str] = []
    errors: list[str] = []
    from tests import helpers

    principal = helpers.principal_for(ctx["actor"], ctx["organization"], "owner")

    def run(name: str) -> None:
        local = Session(bind=engine, future=True)
        try:
            row = create_ingredient(
                local,
                principal,
                code="ING-000001",
                display_name=name,
                ingredient_type="simple",
                nutrition_basis_unit_id=ctx["unit"].id,
                notes=None,
                idempotency_key=uuid4(),
                code_mode="suggested",
            )
            local.commit()
            codes.append(row.code)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            local.rollback()
        finally:
            local.close()

    threads = [Thread(target=run, args=("Açúcar um",)), Thread(target=run, args=("Açúcar dois",))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors, errors
    assert sorted(codes) == ["ING-000001", "ING-000002"]
    check = Session(bind=engine, future=True)
    rows = list(
        check.scalars(
            select(Ingredient).where(
                Ingredient.organization_id == ctx["organization"].id,
                Ingredient.code.in_(["ING-000001", "ING-000002"]),
            )
        )
    )
    check.close()
    assert len(rows) == 2
    _cleanup(ctx["client"])
    ctx["admin"].close()


def test_manual_occupied_code_does_not_write(engine):
    ctx = _setup(engine, "sug-occ")
    _create_ingredient(ctx, "MAN-1", "Manual um")
    with Session(bind=engine, future=True) as session:
        from tests import helpers

        principal = helpers.principal_for(ctx["actor"], ctx["organization"], "owner")
        before = session.scalar(
            select(Ingredient).where(
                Ingredient.organization_id == ctx["organization"].id, Ingredient.code == "MAN-2"
            )
        )
        assert before is None
        try:
            create_ingredient(
                session,
                principal,
                code="MAN-1",
                display_name="Cópia",
                ingredient_type="simple",
                nutrition_basis_unit_id=ctx["unit"].id,
                notes=None,
                idempotency_key=uuid4(),
                code_mode="manual",
            )
            session.commit()
            raise AssertionError("deveria recusar código ocupado")
        except ValidationError as exc:
            assert exc.reason == "codigo_duplicado"
            session.rollback()
        assert (
            session.scalar(
                select(Ingredient).where(
                    Ingredient.organization_id == ctx["organization"].id, Ingredient.display_name == "Cópia"
                )
            )
            is None
        )
    _cleanup(ctx["client"])
    ctx["admin"].close()
