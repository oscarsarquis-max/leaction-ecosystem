from decimal import Decimal

import pytest
from app.modules.ingredient_catalog.models import SupplierItem, SupplierItemPrice
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests import helpers


def test_supplier_item_same_organization(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-sup")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "FAR")
    vendor = helpers.supplier(db_session, organization, "FOR-1")
    db_session.add(
        SupplierItem(
            organization_id=organization.id,
            supplier_id=vendor.id,
            ingredient_id=item.id,
            supplier_sku="SKU-1",
            description="saco",
            package_quantity=Decimal("25"),
            measurement_unit_id=unit.id,
            status="active",
        )
    )
    db_session.flush()


def test_supplier_item_cross_organization_rejected(db_session: Session) -> None:
    one = helpers.org(db_session, "org-sup-a")
    two = helpers.org(db_session, "org-sup-b")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, two, "FAR")
    vendor = helpers.supplier(db_session, one, "FOR-1")
    db_session.add(
        SupplierItem(
            organization_id=one.id,
            supplier_id=vendor.id,
            ingredient_id=item.id,
            supplier_sku="SKU-X",
            package_quantity=Decimal("1"),
            measurement_unit_id=unit.id,
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_package_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-pkg")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "ACU")
    vendor = helpers.supplier(db_session, organization, "FOR-2")
    db_session.add(
        SupplierItem(
            organization_id=organization.id,
            supplier_id=vendor.id,
            ingredient_id=item.id,
            supplier_sku="SKU-0",
            package_quantity=Decimal("0"),
            measurement_unit_id=unit.id,
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_negative_price_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-price")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "MAN")
    vendor = helpers.supplier(db_session, organization, "FOR-3")
    offer = SupplierItem(
        organization_id=organization.id,
        supplier_id=vendor.id,
        ingredient_id=item.id,
        supplier_sku="SKU-M",
        package_quantity=Decimal("1"),
        measurement_unit_id=unit.id,
        status="active",
    )
    db_session.add(offer)
    db_session.flush()
    db_session.add(
        SupplierItemPrice(
            supplier_item_id=offer.id,
            unit_price=Decimal("-0.01"),
            currency="BRL",
            observed_at=offer.created_at,
            source="manual",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_price_history_is_append_only(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-hist")
    unit = helpers.gram(db_session)
    item = helpers.ingredient(db_session, organization, "CAF")
    vendor = helpers.supplier(db_session, organization, "FOR-4")
    offer = SupplierItem(
        organization_id=organization.id,
        supplier_id=vendor.id,
        ingredient_id=item.id,
        supplier_sku="SKU-C",
        package_quantity=Decimal("1"),
        measurement_unit_id=unit.id,
        status="active",
    )
    db_session.add(offer)
    db_session.flush()
    first = SupplierItemPrice(
        supplier_item_id=offer.id,
        unit_price=Decimal("10.0000"),
        currency="BRL",
        observed_at=offer.created_at,
        source="manual",
    )
    db_session.add(first)
    db_session.flush()
    db_session.add(
        SupplierItemPrice(
            supplier_item_id=offer.id,
            unit_price=Decimal("11.0000"),
            currency="BRL",
            observed_at=offer.created_at,
            source="manual",
        )
    )
    db_session.flush()
    with pytest.raises(Exception, match="append_only"):
        db_session.execute(
            text("UPDATE supplier_item_price SET unit_price = 1 WHERE id = :id"),
            {"id": first.id},
        )
        db_session.flush()
