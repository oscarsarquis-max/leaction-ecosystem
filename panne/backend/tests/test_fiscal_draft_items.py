"""Rascunho sem itens ganha linhas na mesma nota, sem estoque."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.modules.fiscal_inbound import commands
from app.modules.fiscal_inbound.models import FiscalInboundItem
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.inventory_procurement.models import InventoryLot, InventoryMovement
from app.modules.production_planning.errors import ConcurrencyError, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests import helpers
from tests.test_fiscal_inbound import _review_document, _world

FIXTURE_XML = Path(__file__).parent / "fixtures" / "fiscal" / "demo_nfe.xml"


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


def _header(place_id, number="50661"):
    return {
        "establishment_id": str(place_id),
        "supplier_name": "Fornecedor real",
        "document_number": number,
        "series": "106",
    }


def _line(description="Farinha", quantity="10", unit="KG", price="5"):
    return {
        "description": description,
        "quantity": quantity,
        "unit_code": unit,
        "unit_price": price,
    }


def test_empty_draft_receives_items_on_same_note(db_session: Session):
    ctx = _world(db_session, f"dft{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id), idempotency_key=uuid4()
    )
    assert document.status == "draft"
    assert commands._items(session, ctx["organization"].id, document.id) == []

    same = commands.replace_items(
        session,
        principal,
        document.id,
        {"expected_row_version": document.row_version, "items": [_line(), _line("Açúcar", "2", "KG", "8")]},
        idempotency_key=uuid4(),
    )
    assert same.id == document.id
    assert same.status == "awaiting_match"
    items = commands._items(session, ctx["organization"].id, document.id)
    assert [item.description for item in items] == ["Farinha", "Açúcar"]
    assert session.scalar(
        select(func.count()).select_from(InventoryMovement).where(
            InventoryMovement.organization_id == ctx["organization"].id
        )
    ) == 0


def test_replace_items_replay_does_not_duplicate(db_session: Session):
    ctx = _world(db_session, f"rpl{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9001"), idempotency_key=uuid4()
    )
    key = uuid4()
    body = {"expected_row_version": document.row_version, "items": [_line()]}
    first = commands.replace_items(session, principal, document.id, body, idempotency_key=key)
    second = commands.replace_items(session, principal, document.id, body, idempotency_key=key)
    assert first.id == second.id
    assert session.scalar(
        select(func.count()).select_from(FiscalInboundItem).where(
            FiscalInboundItem.fiscal_inbound_document_id == document.id
        )
    ) == 1


def test_replace_items_conflict_and_invalid_line(db_session: Session):
    ctx = _world(db_session, f"cnf{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9002"), idempotency_key=uuid4()
    )
    with pytest.raises(ConcurrencyError):
        commands.replace_items(
            session,
            principal,
            document.id,
            {"expected_row_version": 99, "items": [_line()]},
            idempotency_key=uuid4(),
        )
    with pytest.raises(ValidationError, match="item_obrigatorio"):
        commands.replace_items(
            session,
            principal,
            document.id,
            {"expected_row_version": document.row_version, "items": []},
            idempotency_key=uuid4(),
        )
    with pytest.raises(ValidationError, match="quantidade_invalida"):
        commands.replace_items(
            session,
            principal,
            document.id,
            {"expected_row_version": document.row_version, "items": [_line(quantity="0")]},
            idempotency_key=uuid4(),
        )
    assert commands._items(session, ctx["organization"].id, document.id) == []


def test_commit_requires_item_and_duplicate_number_is_blocked(db_session: Session):
    ctx = _world(db_session, f"cmt{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    commands.create_manual(
        session, principal, _header(ctx["place"].id, "50661"), idempotency_key=uuid4()
    )
    with pytest.raises(ValidationError, match="item_obrigatorio"):
        commands.create_manual(
            session,
            principal,
            {**_header(ctx["place"].id, "9003"), "commit": True, "items": []},
            idempotency_key=uuid4(),
        )
    with pytest.raises(ValidationError, match="nota_numero_duplicada"):
        commands.create_manual(
            session, principal, _header(ctx["place"].id, "50661"), idempotency_key=uuid4()
        )


def test_review_and_receive_blocked_without_items(db_session: Session):
    ctx = _world(db_session, f"blk{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9004"), idempotency_key=uuid4()
    )
    with pytest.raises(ValidationError, match="item_obrigatorio"):
        commands.save_review(
            session,
            principal,
            document.id,
            {"expected_row_version": document.row_version, "lines": []},
            idempotency_key=uuid4(),
        )


def test_reviewed_xml_items_stay_locked(db_session: Session):
    ctx = _world(db_session, f"xml{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.import_xml(
        session,
        principal,
        {
            "establishment_id": str(ctx["place"].id),
            "content": FIXTURE_XML.read_text(encoding="utf-8"),
            "synthetic": True,
        },
        idempotency_key=uuid4(),
    )
    before = [
        (item.description, item.quantity, item.unit_code)
        for item in commands._items(session, ctx["organization"].id, document.id)
    ]
    assert before
    document = _review_document(session, principal, document)
    with pytest.raises(ValidationError, match="itens_bloqueados_apos_revisao"):
        commands.replace_items(
            session,
            principal,
            document.id,
            {"expected_row_version": document.row_version, "items": [_line()]},
            idempotency_key=uuid4(),
        )
    after = [
        (item.description, item.quantity, item.unit_code)
        for item in commands._items(session, ctx["organization"].id, document.id)
    ]
    assert after == before


def _new_ing(ctx, name="Açúcar cristal", code=None):
    return {
        "display_name": name,
        "code": code or f"ACU-{uuid4().hex[:6]}",
        "ingredient_type": "simple",
        "nutrition_basis_unit_id": str(ctx["unit"].id),
    }


def _ingredient_count(session: Session, org_id):
    return session.scalar(
        select(func.count()).select_from(Ingredient).where(Ingredient.organization_id == org_id)
    )


def test_other_org_cannot_edit_items(db_session: Session):
    left = _world(db_session, f"lft{uuid4().hex[:6]}")
    right = _world(db_session, f"rgt{uuid4().hex[:6]}")
    document = commands.create_manual(
        left["session"], left["principal"], _header(left["place"].id, "9005"), idempotency_key=uuid4()
    )
    with pytest.raises(ValidationError, match="recurso_nao_encontrado"):
        commands.replace_items(
            right["session"],
            right["principal"],
            document.id,
            {"expected_row_version": document.row_version, "items": [_line()]},
            idempotency_key=uuid4(),
        )


def test_existing_ingredient_links_on_same_note(db_session: Session):
    ctx = _world(db_session, f"lnk{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9101"), idempotency_key=uuid4()
    )
    same = commands.replace_items(
        session,
        principal,
        document.id,
        {
            "expected_row_version": document.row_version,
            "items": [{**_line(), "ingredient_id": str(ctx["ingredient"].id)}],
        },
        idempotency_key=uuid4(),
    )
    items = commands._items(session, ctx["organization"].id, same.id)
    assert len(items) == 1
    assert items[0].target_id == ctx["ingredient"].id
    assert items[0].description == "Farinha"
    assert session.scalar(
        select(func.count()).select_from(InventoryMovement).where(
            InventoryMovement.organization_id == ctx["organization"].id
        )
    ) == 0
    assert session.scalar(
        select(func.count()).select_from(InventoryLot).where(
            InventoryLot.organization_id == ctx["organization"].id
        )
    ) == 0


def test_new_ingredient_is_created_only_on_save_and_linked_to_the_right_line(db_session: Session):
    ctx = _world(db_session, f"new{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9102"), idempotency_key=uuid4()
    )
    before = _ingredient_count(session, ctx["organization"].id)
    spec = _new_ing(ctx, "Açúcar cristal", "ACU-9102")
    same = commands.replace_items(
        session,
        principal,
        document.id,
        {
            "expected_row_version": document.row_version,
            "items": [
                {**_line(), "ingredient_id": str(ctx["ingredient"].id)},
                {**_line("Açúcar da nota", "2", "KG", "8"), "new_ingredient": spec},
            ],
        },
        idempotency_key=uuid4(),
    )
    items = commands._items(session, ctx["organization"].id, same.id)
    assert [item.description for item in items] == ["Farinha", "Açúcar da nota"]
    assert items[0].target_id == ctx["ingredient"].id
    created = session.scalar(
        select(Ingredient).where(
            Ingredient.organization_id == ctx["organization"].id,
            Ingredient.code == "ACU-9102",
        )
    )
    assert created is not None
    assert created.display_name == "Açúcar cristal"
    assert items[1].target_id == created.id
    assert _ingredient_count(session, ctx["organization"].id) == before + 1
    assert session.scalar(
        select(func.count()).select_from(InventoryMovement).where(
            InventoryMovement.organization_id == ctx["organization"].id
        )
    ) == 0


def test_other_org_ingredient_cannot_be_linked(db_session: Session):
    left = _world(db_session, f"ola{uuid4().hex[:6]}")
    right = _world(db_session, f"ora{uuid4().hex[:6]}")
    document = commands.create_manual(
        right["session"], right["principal"], _header(right["place"].id, "9103"), idempotency_key=uuid4()
    )
    with pytest.raises(ValidationError, match="recurso_nao_encontrado"):
        commands.replace_items(
            right["session"],
            right["principal"],
            document.id,
            {
                "expected_row_version": document.row_version,
                "items": [{**_line(), "ingredient_id": str(left["ingredient"].id)}],
            },
            idempotency_key=uuid4(),
        )
    assert commands._items(right["session"], right["organization"].id, document.id) == []


def test_same_code_allowed_in_two_organizations(db_session: Session):
    left = _world(db_session, f"cla{uuid4().hex[:6]}")
    right = _world(db_session, f"cra{uuid4().hex[:6]}")
    spec = {
        "display_name": "Fermento fresco",
        "code": "FER-COMUM",
        "ingredient_type": "simple",
        "nutrition_basis_unit_id": str(left["unit"].id),
    }
    left_doc = commands.create_manual(
        left["session"], left["principal"], _header(left["place"].id, "9104"), idempotency_key=uuid4()
    )
    right_doc = commands.create_manual(
        right["session"], right["principal"], _header(right["place"].id, "9104"), idempotency_key=uuid4()
    )
    commands.replace_items(
        left["session"],
        left["principal"],
        left_doc.id,
        {"expected_row_version": left_doc.row_version, "items": [{**_line("Fermento"), "new_ingredient": spec}]},
        idempotency_key=uuid4(),
    )
    commands.replace_items(
        right["session"],
        right["principal"],
        right_doc.id,
        {
            "expected_row_version": right_doc.row_version,
            "items": [{**_line("Fermento"), "new_ingredient": {**spec, "nutrition_basis_unit_id": str(right["unit"].id)}}],
        },
        idempotency_key=uuid4(),
    )
    assert left["session"].scalar(
        select(Ingredient).where(
            Ingredient.organization_id == left["organization"].id, Ingredient.code == "FER-COMUM"
        )
    )
    assert right["session"].scalar(
        select(Ingredient).where(
            Ingredient.organization_id == right["organization"].id, Ingredient.code == "FER-COMUM"
        )
    )


def test_duplicate_code_is_rejected_without_writing_items(db_session: Session):
    ctx = _world(db_session, f"dup{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9105"), idempotency_key=uuid4()
    )
    before = _ingredient_count(session, ctx["organization"].id)
    with pytest.raises(ValidationError, match="codigo_duplicado"):
        commands.replace_items(
            session,
            principal,
            document.id,
            {
                "expected_row_version": document.row_version,
                "items": [{**_line(), "new_ingredient": _new_ing(ctx, "Cópia", ctx["ingredient"].code)}],
            },
            idempotency_key=uuid4(),
        )
    assert commands._items(session, ctx["organization"].id, document.id) == []
    assert _ingredient_count(session, ctx["organization"].id) == before


def test_replace_items_with_new_ingredient_replay_does_not_duplicate(db_session: Session):
    ctx = _world(db_session, f"rpi{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9106"), idempotency_key=uuid4()
    )
    spec = _new_ing(ctx, "Sal fino", "SAL-9106")
    body = {"expected_row_version": document.row_version, "items": [{**_line("Sal"), "new_ingredient": spec}]}
    key = uuid4()
    commands.replace_items(session, principal, document.id, body, idempotency_key=key)
    commands.replace_items(session, principal, document.id, body, idempotency_key=key)
    assert session.scalar(
        select(func.count()).select_from(FiscalInboundItem).where(
            FiscalInboundItem.fiscal_inbound_document_id == document.id
        )
    ) == 1
    assert session.scalar(
        select(func.count()).select_from(Ingredient).where(
            Ingredient.organization_id == ctx["organization"].id,
            Ingredient.code == "SAL-9106",
        )
    ) == 1


def test_mid_failure_does_not_leave_partial_ingredient_or_items(db_session: Session, monkeypatch):
    ctx = _world(db_session, f"mid{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9107"), idempotency_key=uuid4()
    )
    before = _ingredient_count(session, ctx["organization"].id)

    def boom(*_args, **_kwargs):
        raise ValidationError("falha_intermediaria")

    monkeypatch.setattr(commands, "_link_item_ingredient", boom)
    with pytest.raises(ValidationError, match="falha_intermediaria"):
        commands.replace_items(
            session,
            principal,
            document.id,
            {
                "expected_row_version": document.row_version,
                "items": [{**_line(), "new_ingredient": _new_ing(ctx, "Leite", "LEI-9107")}],
            },
            idempotency_key=uuid4(),
        )
    assert commands._items(session, ctx["organization"].id, document.id) == []
    assert _ingredient_count(session, ctx["organization"].id) == before
    assert session.scalar(
        select(Ingredient).where(
            Ingredient.organization_id == ctx["organization"].id,
            Ingredient.code == "LEI-9107",
        )
    ) is None


def _package_line(quantity: str, price: str, ingredient_id: str) -> dict:
    return {
        "description": "Erva-doce",
        "quantity": quantity,
        "unit_code": "pacote",
        "unit_price": price,
        "package_content_quantity": "100",
        "package_content_unit": "g",
        "ingredient_id": ingredient_id,
    }


def test_package_content_two_packs_without_stock(db_session: Session):
    ctx = _world(db_session, f"pk2{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9201"), idempotency_key=uuid4()
    )
    same = commands.replace_items(
        session,
        principal,
        document.id,
        {
            "expected_row_version": document.row_version,
            "items": [_package_line("2", "4.50", str(ctx["ingredient"].id))],
        },
        idempotency_key=uuid4(),
    )
    item = commands._items(session, ctx["organization"].id, same.id)[0]
    assert item.quantity == 2
    assert item.unit_code == "pacote"
    assert item.conversion_factor == 100
    assert item.converted_quantity == 200
    assert item.converted_unit_code == "g"
    assert (item.conversion_memory or {}).get("formula") == "2 pacotes × 100 g = 200 g"
    assert item.conversion_factor != 1
    assert session.scalar(
        select(func.count()).select_from(InventoryMovement).where(
            InventoryMovement.organization_id == ctx["organization"].id
        )
    ) == 0
    assert session.scalar(
        select(func.count()).select_from(InventoryLot).where(
            InventoryLot.organization_id == ctx["organization"].id
        )
    ) == 0


def test_package_content_one_hundred_packs_without_stock(db_session: Session):
    ctx = _world(db_session, f"pkh{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9203"), idempotency_key=uuid4()
    )
    same = commands.replace_items(
        session,
        principal,
        document.id,
        {
            "expected_row_version": document.row_version,
            "items": [_package_line("100", "5", str(ctx["ingredient"].id))],
        },
        idempotency_key=uuid4(),
    )
    packed = commands._items(session, ctx["organization"].id, same.id)[0]
    assert packed.quantity == 100
    assert packed.conversion_factor == 100
    assert packed.converted_quantity == 10000
    assert packed.converted_unit_code == "g"
    assert (packed.conversion_memory or {}).get("formula") == "100 pacotes × 100 g = 10 kg"
    assert packed.conversion_factor != 1
    assert session.scalar(
        select(func.count()).select_from(InventoryMovement).where(
            InventoryMovement.organization_id == ctx["organization"].id
        )
    ) == 0


def test_replace_items_requires_commercial_unit(db_session: Session):
    ctx = _world(db_session, f"unt{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9202"), idempotency_key=uuid4()
    )
    with pytest.raises(ValidationError, match="unidade_comercial_obrigatoria"):
        commands.replace_items(
            session,
            principal,
            document.id,
            {
                "expected_row_version": document.row_version,
                "items": [{**_line(), "unit_code": ""}],
            },
            idempotency_key=uuid4(),
        )
    assert commands._items(session, ctx["organization"].id, document.id) == []


def test_suggested_ingredient_code_is_allocated_on_save_only(db_session: Session):
    ctx = _world(db_session, f"sug{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9210"), idempotency_key=uuid4()
    )
    before = _ingredient_count(session, ctx["organization"].id)
    spec = {
        "display_name": "Açúcar da nota",
        "code_mode": "suggested",
        "ingredient_type": "simple",
        "nutrition_basis_unit_id": str(ctx["unit"].id),
    }
    same = commands.replace_items(
        session,
        principal,
        document.id,
        {"expected_row_version": document.row_version, "items": [{**_line("Açúcar"), "new_ingredient": spec}]},
        idempotency_key=uuid4(),
    )
    created = session.scalar(
        select(Ingredient).where(
            Ingredient.organization_id == ctx["organization"].id,
            Ingredient.display_name == "Açúcar da nota",
        )
    )
    assert created is not None
    assert created.code == "ING-000001"
    assert _ingredient_count(session, ctx["organization"].id) == before + 1
    items = commands._items(session, ctx["organization"].id, same.id)
    assert items[0].target_id == created.id
    assert session.scalar(
        select(func.count()).select_from(InventoryMovement).where(
            InventoryMovement.organization_id == ctx["organization"].id
        )
    ) == 0
