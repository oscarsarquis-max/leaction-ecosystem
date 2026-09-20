import pytest
from app.models.catalog import DoughIngredientCompatibility, DoughType, Ingredient, PairingTip
from app.seed import seed_demo_catalog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.db_fixtures import priced_catalog


def test_slug_unique(db: Session) -> None:
    db.add(
        DoughType(
            name="A",
            slug="same-slug",
            short_description="x",
            sort_order=0,
            is_active=True,
        )
    )
    db.flush()
    db.add(
        DoughType(
            name="B",
            slug="same-slug",
            short_description="y",
            sort_order=1,
            is_active=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_compat_pair_unique(db: Session) -> None:
    catalog = priced_catalog(db)
    db.add(
        DoughIngredientCompatibility(
            dough_type_id=catalog["dough"].id,
            ingredient_id=catalog["ingredient"].id,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_pairing_rejects_self_and_inverted_duplicate(db: Session) -> None:
    first = Ingredient(
        name="Alecrim", slug="alecrim-t", description="a", sort_order=0, is_active=True
    )
    second = Ingredient(
        name="Damasco", slug="damasco-t", description="b", sort_order=1, is_active=True
    )
    db.add_all([first, second])
    db.flush()
    left, right = (first.id, second.id) if first.id < second.id else (second.id, first.id)
    db.add(PairingTip(ingredient_id=left, paired_ingredient_id=right, message="ok", priority=1))
    db.flush()
    db.add(PairingTip(ingredient_id=left, paired_ingredient_id=right, message="dup", priority=2))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    db.add(PairingTip(ingredient_id=first.id, paired_ingredient_id=first.id, message="self", priority=0))
    with pytest.raises(IntegrityError):
        db.flush()


def test_pairing_single_ingredient_unique_with_null(db: Session) -> None:
    ingredient = Ingredient(
        name="Nozes", slug="nozes-t", description="n", sort_order=0, is_active=True
    )
    db.add(ingredient)
    db.flush()
    db.add(PairingTip(ingredient_id=ingredient.id, paired_ingredient_id=None, message="a", priority=1))
    db.flush()
    db.add(PairingTip(ingredient_id=ingredient.id, paired_ingredient_id=None, message="b", priority=2))
    with pytest.raises(IntegrityError):
        db.flush()


def test_negative_price_rejected(db: Session) -> None:
    db.add(
        DoughType(
            name="X",
            slug="neg-price",
            short_description="x",
            sort_order=0,
            is_active=True,
            base_price_cents=-1,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_seed_is_idempotent_and_preserves_edits(db: Session) -> None:
    seed_demo_catalog(db)
    db.commit()
    count = db.query(DoughType).count()
    dough = db.query(DoughType).filter_by(slug="sourdough-classico").one()
    dough.short_description = "editado editorialmente"
    db.commit()
    seed_demo_catalog(db)
    db.commit()
    assert db.query(DoughType).count() == count
    again = db.query(DoughType).filter_by(slug="sourdough-classico").one()
    assert again.short_description == "editado editorialmente"
