from datetime import UTC, datetime
from uuid import uuid4

from app.domain.house_fidelity import (
    RULES_VERSION,
    activate_campaign,
    is_500g_unit,
    reward_catalog,
    reward_gaps,
)
from app.domain.house_fidelity_redeem import eligible_500g_variants
from app.domain.recipe_bases import create_recipe_base
from app.domain.showcase import ensure_slots
from app.models.enums import EditorialStatus
from app.models.house_fidelity import HouseFidelityCampaign
from app.models.products import Product, ProductVariant
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_house_fidelity_ledger import _settings


def _published(db: Session, *, grams: int = 500, units: int | None = None) -> Product:
    token = uuid4().hex[:8]
    base = create_recipe_base(db, code=f"rb{token}", name="Massa catálogo")
    product = Product(
        name="Pão da vitrine",
        slug=f"pao-vitrine-{token}",
        short_description="crosta",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    db.add(
        ProductVariant(
            product_id=product.id,
            display_name=f"{grams} g",
            presentation_type="weight",
            net_weight_grams=grams,
            physical_units=units,
            price_cents=2490,
            currency="BRL",
            is_active=True,
        )
    )
    db.flush()
    slots = ensure_slots(db)
    slots[0].product_id = product.id
    db.flush()
    return product


def test_weight_500g_without_physical_units_is_one_loaf(db: Session) -> None:
    product = _published(db, units=None)
    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    assert is_500g_unit(variant)
    catalog = reward_catalog(db)
    assert catalog[0]["eligible"] is True
    assert reward_gaps(db) == []
    assert any(item["slug"] == product.slug for item in eligible_500g_variants(db))


def test_activate_sets_server_now_and_does_not_rewrite(db: Session) -> None:
    settings = _settings()
    _published(db, units=None)
    campaign = HouseFidelityCampaign(
        slug="carimbos-da-casa",
        version=1,
        status="draft",
        rules_version="43a",
        title="Fidelidade da casa",
        starts_at=None,
        rules_json="{}",
    )
    db.add(campaign)
    db.flush()
    first = activate_campaign(db, settings)
    assert first.status == "active"
    assert first.starts_at is not None
    assert first.rules_version == RULES_VERSION
    started = first.starts_at
    again = activate_campaign(db, settings)
    assert again.starts_at == started
    assert again.starts_at != datetime(2026, 9, 1, tzinfo=UTC)
