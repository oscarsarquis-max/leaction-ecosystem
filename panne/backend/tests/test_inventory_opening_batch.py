"""Inventário inicial em lote: POST /inventory/openings/batch (CURSOR-031)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.db import get_runtime_session
from app.main import app
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.identity_organization.http import get_access_token_verifier
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryItem,
    InventoryLot,
    InventoryMovement,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from tests import helpers
from tests.jwt_support import ISSUER
from tests.rls_support import ensure_runtime_role, runtime_postgres_url


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


def _client(engine, fake: FakeAccessTokenVerifier) -> TestClient:
    ensure_runtime_role(engine)
    runtime = create_engine(runtime_postgres_url(), future=True, pool_pre_ping=True)
    factory = sessionmaker(bind=runtime, expire_on_commit=False, future=True)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_runtime_session] = override_session
    app.dependency_overrides[get_access_token_verifier] = lambda: fake
    client = TestClient(app)
    client.runtime_engine = runtime
    return client


def _headers(token: str, *, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": str(uuid4())}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _liter(session) -> None:
    from app.modules.ingredient_catalog.models import MeasurementUnit

    if session.query(MeasurementUnit).filter_by(code="l").one_or_none() is None:
        session.add(
            MeasurementUnit(
                code="l",
                name="litro",
                plural_name="litros",
                dimension="volume",
                si_factor=Decimal("0.001"),
                symbol="l",
                status="active",
            )
        )
        session.flush()


class _World:
    def __init__(self, engine, *, role: str = "owner") -> None:
        self.engine = engine
        self.admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
        slug = f"inv{uuid4().hex[:7]}"
        self.organization = helpers.org(self.admin, slug)
        actor = helpers.user(self.admin, f"{slug}@example.com")
        helpers.membership(self.admin, self.organization, actor, role)
        self.place = helpers.establishment(self.admin, self.organization, "LOJA")
        subject = f"sub-{slug}"
        helpers.auth_identity(self.admin, actor, ISSUER, subject)
        for unit in (helpers.gram, helpers.kilogram, helpers.each, helpers.milliliter):
            unit(self.admin)
        _liter(self.admin)
        self.admin.commit()
        fake = FakeAccessTokenVerifier()
        self.token = f"token-{slug}"
        fake.register(self.token, issuer=ISSUER, subject=subject)
        self.client = _client(engine, fake)
        self.base = f"/api/v1/organizations/{self.organization.id}"
        self.location_id: str | None = None

    def close(self) -> None:
        app.dependency_overrides.clear()
        self.client.runtime_engine.dispose()
        self.admin.close()

    def make_location(self) -> str:
        response = self.client.post(
            f"{self.base}/inventory/locations",
            headers=_headers(self.token, key=str(uuid4())),
            json={"establishment_id": str(self.place.id), "code": "DESP", "display_name": "Despensa", "kind": "warehouse"},
        )
        assert response.status_code == 200, response.text
        self.location_id = response.json()["data"]["id"]
        return self.location_id

    def make_ingredient(self, name: str) -> str:
        gram = helpers.gram(self.admin)
        response = self.client.post(
            f"{self.base}/ingredients",
            headers=_headers(self.token, key=str(uuid4())),
            json={"display_name": name, "ingredient_type": "simple", "nutrition_basis_unit_id": str(gram.id)},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]["id"]

    def post(self, lines, *, key: str | None = None, **header):
        body = {
            "inventory_location_id": self.location_id,
            "lines": lines,
            **header,
        }
        return self.client.post(
            f"{self.base}/inventory/openings/batch",
            headers=_headers(self.token, key=key or str(uuid4())),
            json=body,
        )

    def counts(self) -> dict[str, int]:
        session = sessionmaker(bind=self.engine, future=True, expire_on_commit=True)()
        try:
            org = self.organization.id

            def count(model):
                return session.scalar(select(func.count()).select_from(model).where(model.organization_id == org)) or 0

            return {
                "ingredients": count(Ingredient),
                "items": count(InventoryItem),
                "lots": count(InventoryLot),
                "movements": count(InventoryMovement),
                "balances": count(InventoryBalance),
            }
        finally:
            session.close()


@pytest.fixture
def world(engine):
    built = _World(engine)
    built.make_location()
    try:
        yield built
    finally:
        built.close()


def _line(**extra):
    base = {"quantity": "2", "unit_code": "kg", "cost_unknown": True}
    base.update(extra)
    return base


def test_batch_writes_every_line_with_expiry_lot_cost_and_package_content(world, engine) -> None:
    flour = world.make_ingredient("Farinha de trigo")
    past = (date.today() - timedelta(days=3)).isoformat()
    response = world.post(
        [
            _line(ingredient_id=flour, quantity="12,5", lot_code="L-77", expires_on="2027-03-01", unit_cost="4,80", cost_unknown=False),
            _line(
                new_ingredient={"display_name": "  Granola   artesanal ", "unit_code": "embalagem"},
                quantity="6",
                unit_code="embalagem",
                package_content_quantity="500",
                package_content_unit="g",
                no_expiry=True,
            ),
            _line(new_ingredient={"display_name": "Mel", "unit_code": "g"}, quantity="900", unit_code="g"),
        ],
        counted_on=past,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["line_count"] == 3
    assert data["created_ingredients"] == 2
    assert data["replayed"] is False
    assert [row["ingredient_created"] for row in data["lines"]] == [False, True, True]
    assert data["lines"][1]["ingredient_name"] == "Granola artesanal"
    assert world.counts() == {"ingredients": 3, "items": 3, "lots": 3, "movements": 3, "balances": 3}

    probe = sessionmaker(bind=engine, future=True, expire_on_commit=True)()
    try:
        lots = {row["internal_lot_code"]: row for row in data["lines"]}
        first = probe.get(InventoryLot, data["lines"][0]["inventory_lot_id"])
        second = probe.get(InventoryLot, data["lines"][1]["inventory_lot_id"])
        third = probe.get(InventoryLot, data["lines"][2]["inventory_lot_id"])
        assert lots
        assert first.supplier_lot_code == "L-77"
        assert first.expires_on == date(2027, 3, 1)
        assert first.cost_status == "known" and first.declared_unit_cost == Decimal("4.80")
        assert first.received_quantity == Decimal("12.5") and first.unit_code == "kg"
        assert first.opening_origin == "Inventário inicial"
        assert second.unit_code == "un" and second.received_quantity == Decimal("6")
        assert second.package_content_quantity == Decimal("500") and second.package_content_unit == "g"
        assert second.expires_on is None and second.cost_status == "unknown"
        assert third.package_content_quantity is None and third.unit_code == "g"
        movement = probe.scalar(select(InventoryMovement).where(InventoryMovement.inventory_lot_id == first.id))
        assert movement.movement_type == "opening"
        assert movement.effective_at.date().isoformat() == past
        codes = probe.scalars(
            select(Ingredient.code).where(Ingredient.organization_id == world.organization.id)
        ).all()
        assert len(set(codes)) == 3
    finally:
        probe.close()


def test_same_new_ingredient_in_two_lines_is_created_once_with_two_lots(world) -> None:
    response = world.post(
        [
            _line(new_ingredient={"display_name": "Fermento", "unit_code": "g"}, unit_code="g", quantity="500", lot_code="A", expires_on="2027-01-10"),
            _line(new_ingredient={"display_name": "fermento", "unit_code": "g"}, unit_code="g", quantity="250", lot_code="B", expires_on="2027-05-10"),
        ]
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["created_ingredients"] == 1
    assert data["lines"][0]["ingredient_id"] == data["lines"][1]["ingredient_id"]
    assert world.counts() == {"ingredients": 1, "items": 1, "lots": 2, "movements": 2, "balances": 2}


def test_one_bad_line_writes_nothing_and_reports_each_line(world) -> None:
    flour = world.make_ingredient("Farinha integral")
    sugar = world.make_ingredient("Açúcar")
    before = world.counts()
    first = world.post([_line(ingredient_id=sugar, quantity="1")])
    assert first.status_code == 200, first.text  # sugar passa a ser controlado em kg
    before = world.counts()
    response = world.post(
        [
            _line(ingredient_id=flour, quantity="3"),
            _line(new_ingredient={"display_name": "Granola", "unit_code": "embalagem"}, unit_code="embalagem", quantity="4"),
            _line(ingredient_id=sugar, quantity="2", unit_code="g"),
            _line(ingredient_id=flour, quantity="abc"),
            _line(ingredient_id=flour, quantity="1", unit_cost="5", cost_unknown=False, expires_on="31/02/2027"),
            {"ingredient_id": flour, "quantity": "1", "unit_code": "kg"},
            _line(quantity="1"),
        ]
    )
    assert response.status_code == 422, response.text
    detail = response.json()
    assert detail["code"] == "inventario_com_erros"
    assert "Nada foi gravado" in detail["message"]
    errors = {(row["index"], row["field"]): row for row in detail["errors"]}
    assert set(errors) == {
        (1, "package_content_quantity"),
        (2, "unit_code"),
        (3, "quantity"),
        (4, "expires_on"),
        (5, "unit_cost"),
        (6, "ingredient"),
    }
    assert "controlado em quilos" in errors[(2, "unit_code")]["message"]
    assert "conteúdo" in errors[(1, "package_content_quantity")]["message"].lower()
    assert errors[(3, "quantity")]["message"] == "Informe uma quantidade maior que zero."
    for row in detail["errors"]:
        assert row["message"] != row["code"] and " " in row["message"]
    assert world.counts() == before


def test_new_ingredient_is_rolled_back_when_a_later_line_fails(world) -> None:
    before = world.counts()
    response = world.post(
        [
            _line(new_ingredient={"display_name": "Chocolate", "unit_code": "kg"}, quantity="2"),
            _line(new_ingredient={"display_name": "Cacau", "unit_code": "kg"}, quantity="0"),
        ]
    )
    assert response.status_code == 422, response.text
    assert [row["index"] for row in response.json()["errors"]] == [1]
    assert world.counts() == before


def test_existing_name_for_a_new_ingredient_is_refused(world) -> None:
    world.make_ingredient("Manteiga")
    response = world.post([_line(new_ingredient={"display_name": "manteiga", "unit_code": "kg"})])
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert (error["index"], error["field"], error["code"]) == (0, "ingredient", "ingrediente_ja_existe")


def test_new_name_equal_without_accent_case_or_extra_spaces_is_refused(world) -> None:
    world.make_ingredient("Açúcar cristal")
    before = world.counts()
    for typed in ("ACUCAR CRISTAL", "  acucar   cristal ", "Açúcar Cristal"):
        response = world.post([_line(new_ingredient={"display_name": typed, "unit_code": "kg"})])
        assert response.status_code == 422, typed
        error = response.json()["errors"][0]
        assert (error["index"], error["field"], error["code"]) == (0, "ingredient", "ingrediente_ja_existe")
        assert "Açúcar cristal" in error["message"]
    assert world.counts() == before


def test_a_similar_but_different_name_is_still_created(world) -> None:
    world.make_ingredient("Açúcar cristal")
    response = world.post([_line(new_ingredient={"display_name": "Açúcar refinado", "unit_code": "kg"})])
    assert response.status_code == 200, response.text
    assert response.json()["data"]["created_ingredients"] == 1


def test_two_new_names_that_only_differ_by_accent_in_one_batch_create_one_ingredient(world) -> None:
    response = world.post(
        [
            _line(new_ingredient={"display_name": "Pão de queijo", "unit_code": "kg"}, quantity="1"),
            _line(new_ingredient={"display_name": "PAO DE QUEIJO", "unit_code": "kg"}, quantity="2"),
        ]
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["created_ingredients"] == 1


def test_same_key_replays_without_writing_again_and_other_body_conflicts(world) -> None:
    flour = world.make_ingredient("Farinha 00")
    key = str(uuid4())
    lines = [_line(ingredient_id=flour, quantity="5")]
    first = world.post(lines, key=key)
    assert first.status_code == 200, first.text
    after_first = world.counts()
    again = world.post(lines, key=key)
    assert again.status_code == 200, again.text
    assert again.json()["data"]["replayed"] is True
    assert again.json()["data"]["batch_id"] == first.json()["data"]["batch_id"]
    assert world.counts() == after_first
    other = world.post([_line(ingredient_id=flour, quantity="6")], key=key)
    assert other.status_code == 409
    assert other.json()["code"] == "idempotencia_conflito"
    assert world.counts() == after_first


def test_header_limits_and_defaults(world) -> None:
    flour = world.make_ingredient("Farinha 0")
    assert world.post([]).status_code == 422
    too_many = world.post([_line(ingredient_id=flour)] * 201)
    assert too_many.status_code == 422
    assert too_many.json()["errors"][0]["code"] == "inventario_linhas_demais"
    future = (date.today() + timedelta(days=2)).isoformat()
    refused = world.post([_line(ingredient_id=flour)], counted_on=future)
    assert refused.status_code == 422
    assert refused.json()["errors"][0] == {
        "index": None,
        "field": "counted_on",
        "code": "data_contagem_futura",
        "message": "A data da contagem não pode ser depois de hoje.",
    }
    bad_place = world.client.post(
        f"{world.base}/inventory/openings/batch",
        headers=_headers(world.token, key=str(uuid4())),
        json={"inventory_location_id": str(uuid4()), "lines": [_line(ingredient_id=flour)]},
    )
    assert bad_place.status_code == 422
    assert bad_place.json()["errors"][0]["field"] == "inventory_location_id"
    assert world.counts()["lots"] == 0
    ok = world.post([_line(ingredient_id=flour)] * 200)
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["line_count"] == 200
    assert world.counts()["lots"] == 200


def test_package_unit_variants_require_content_and_mass_units_refuse_it(world) -> None:
    response = world.post(
        [
            _line(new_ingredient={"display_name": "Leite", "unit_code": "caixa"}, unit_code="caixa", quantity="3", package_content_quantity="1", package_content_unit="l"),
            _line(new_ingredient={"display_name": "Sal", "unit_code": "kg"}, unit_code="kg", quantity="3", package_content_quantity="1", package_content_unit="kg"),
            _line(new_ingredient={"display_name": "Cravo", "unit_code": "pacote"}, unit_code="pacote", quantity="3", package_content_quantity="1"),
            _line(new_ingredient={"display_name": "Canela", "unit_code": "pacote"}, unit_code="pacote", quantity="3", package_content_quantity="0", package_content_unit="g"),
            _line(new_ingredient={"display_name": "Anis", "unit_code": "pacote"}, unit_code="pacote", quantity="3", package_content_quantity="2", package_content_unit="un"),
            _line(new_ingredient={"display_name": "Azeite", "unit_code": "l"}, unit_code="l", quantity="3"),
        ]
    )
    assert response.status_code == 422, response.text
    errors = {row["index"]: row for row in response.json()["errors"]}
    assert set(errors) == {1, 2, 3, 4, 5}
    assert errors[5]["code"] == "unidade_volume_nao_suportada"
    assert errors[1]["code"] == "conteudo_embalagem_nao_se_aplica"
    assert errors[2]["code"] == "conteudo_embalagem_incompleto"
    assert errors[3]["field"] == "package_content_quantity"
    assert errors[4]["field"] == "package_content_unit"


def test_viewer_cannot_post_a_batch(engine) -> None:
    built = _World(engine, role="viewer")
    try:
        built.location_id = str(uuid4())
        response = built.post([_line(quantity="1")])
        assert response.status_code == 403, response.text
    finally:
        built.close()
