from decimal import Decimal
from uuid import uuid4

import pytest
from app.modules.formula_lab.models import Formulation, FormulationItem
from app.modules.formula_lab.rules import (
    PublishedFormulationFrozenError,
    PublishRequiresApprovalError,
    derived_gross_quantity,
    ensure_formulation_version_editable,
    publish_formulation_version,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests import helpers


def _stack(session: Session, slug: str):
    organization = helpers.org(session, slug)
    actor = helpers.user(session, f"{slug}@panne.test")
    unit = helpers.gram(session)
    product = helpers.technical_product(session, organization, "PAO-1")
    recipe = helpers.formulation(session, product, "REC-1")
    version = helpers.formulation_version(session, recipe)
    flour = helpers.published_ingredient(session, organization, unit, "FAR-1")
    return organization, actor, unit, product, recipe, version, flour


def test_codes_unique_per_organization_only(db_session: Session) -> None:
    one = helpers.org(db_session, "org-code-a")
    two = helpers.org(db_session, "org-code-b")
    product_one = helpers.technical_product(db_session, one, "PAO-X")
    product_two = helpers.technical_product(db_session, two, "PAO-X")
    helpers.formulation(db_session, product_one, "REC-X")
    helpers.formulation(db_session, product_two, "REC-X")
    with pytest.raises(IntegrityError):
        helpers.technical_product(db_session, one, "PAO-X")


def test_formulation_rejects_foreign_product(db_session: Session) -> None:
    one = helpers.org(db_session, "org-prod-a")
    two = helpers.org(db_session, "org-prod-b")
    foreign = helpers.technical_product(db_session, two, "PAO-Y")
    row = Formulation(
        organization_id=one.id,
        technical_product_id=foreign.id,
        code="REC-Y",
        display_name="REC-Y",
        status="development",
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_version_number_unique(db_session: Session) -> None:
    _, _, _, _, recipe, _, _ = _stack(db_session, "org-ver-n")
    with pytest.raises(IntegrityError):
        helpers.formulation_version(db_session, recipe, number=1)


def test_publish_without_approval_rejected_by_domain(db_session: Session) -> None:
    _, _, _, _, _, version, _ = _stack(db_session, "org-no-appr-d")
    with pytest.raises(PublishRequiresApprovalError):
        publish_formulation_version(db_session, version)


def test_publish_without_approval_rejected_by_database(db_session: Session) -> None:
    _, _, _, _, _, version, _ = _stack(db_session, "org-no-appr-b")
    version.status = "published"
    with pytest.raises(Exception, match="publish_requires_approval"):
        db_session.flush()


def test_published_version_immutable(db_session: Session) -> None:
    _, actor, unit, _, _, version, flour = _stack(db_session, "org-pub-imm")
    helpers.formulation_item(
        db_session, version, flour, unit, 1, Decimal("1000"), is_flour_basis=True
    )
    helpers.approve_version(db_session, version, actor)
    publish_formulation_version(db_session, version)
    db_session.flush()
    with pytest.raises(PublishedFormulationFrozenError):
        ensure_formulation_version_editable(version)
    version.notes = "nao"
    with pytest.raises(Exception, match="published_frozen"):
        db_session.flush()


def test_only_one_published_version(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-one-pub")
    actor = helpers.user(db_session, "one-pub@panne.test")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-2")
    recipe = helpers.formulation(db_session, product, "REC-2")
    first = helpers.formulation_version(db_session, recipe, number=1)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-2")
    helpers.formulation_item(db_session, first, flour, unit, 1, Decimal("500"), is_flour_basis=True)
    helpers.approve_version(db_session, first, actor)
    publish_formulation_version(db_session, first)
    db_session.flush()
    second = helpers.formulation_version(db_session, recipe, number=2)
    helpers.approve_version(db_session, second, actor)
    second.status = "published"
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_item_rejects_foreign_ingredient(db_session: Session) -> None:
    organization, _, unit, _, _, version, _ = _stack(db_session, "org-item-a")
    other = helpers.org(db_session, "org-item-b")
    foreign = helpers.published_ingredient(db_session, other, unit, "FAR-Z")
    row = FormulationItem(
        organization_id=organization.id,
        formulation_version_id=version.id,
        ingredient_version_id=foreign.id,
        sequence=1,
        net_quantity=Decimal("10"),
        measurement_unit_id=unit.id,
        correction_factor=Decimal("1"),
        is_flour_basis=False,
        role="ingredient",
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_item_rejects_unknown_ingredient_version(db_session: Session) -> None:
    organization, _, unit, _, _, version, _ = _stack(db_session, "org-miss")
    row = FormulationItem(
        organization_id=organization.id,
        formulation_version_id=version.id,
        ingredient_version_id=uuid4(),
        sequence=1,
        net_quantity=Decimal("10"),
        measurement_unit_id=unit.id,
        correction_factor=Decimal("1"),
        is_flour_basis=False,
        role="ingredient",
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_item_rejects_non_mass_unit(db_session: Session) -> None:
    organization, _, _, _, _, version, flour = _stack(db_session, "org-unit")
    volume = helpers.milliliter(db_session)
    row = FormulationItem(
        organization_id=organization.id,
        formulation_version_id=version.id,
        ingredient_version_id=flour.id,
        sequence=1,
        net_quantity=Decimal("10"),
        measurement_unit_id=volume.id,
        correction_factor=Decimal("1"),
        is_flour_basis=False,
        role="ingredient",
    )
    db_session.add(row)
    with pytest.raises(Exception, match="formulation_item_unit_must_be_mass"):
        db_session.flush()


def test_item_rejects_duplicate_sequence(db_session: Session) -> None:
    _, _, unit, _, _, version, flour = _stack(db_session, "org-seq")
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("10"))
    with pytest.raises(IntegrityError):
        helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("20"))


def test_item_rejects_zero_quantity(db_session: Session) -> None:
    _, _, unit, _, _, version, flour = _stack(db_session, "org-qty")
    with pytest.raises(IntegrityError):
        helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("0"))


def test_item_rejects_invalid_factor(db_session: Session) -> None:
    _, _, unit, _, _, version, flour = _stack(db_session, "org-fac")
    with pytest.raises(IntegrityError):
        helpers.formulation_item(
            db_session, version, flour, unit, 1, Decimal("10"), correction_factor=Decimal("0")
        )


def test_gross_is_derived(db_session: Session) -> None:
    _, _, unit, _, _, version, flour = _stack(db_session, "org-gross")
    item = helpers.formulation_item(
        db_session,
        version,
        flour,
        unit,
        1,
        Decimal("100"),
        correction_factor=Decimal("1.1"),
    )
    assert derived_gross_quantity(item.net_quantity, item.correction_factor) == Decimal(
        "110.000000"
    )
    assert "gross_quantity" not in item.__table__.c
