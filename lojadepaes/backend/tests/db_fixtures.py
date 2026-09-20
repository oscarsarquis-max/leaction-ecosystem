from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.db.session import reset_engine
from app.domain.orders import new_public_reference
from app.models import Base
from app.models.catalog import (
    BreadShape,
    DoughIngredientCompatibility,
    DoughShapeCompatibility,
    DoughType,
    Ingredient,
)
from app.models.enums import BatchStatus, FulfillmentModality
from app.models.orders import Order, OrderItem, OrderItemIngredient
from app.models.production import FulfillmentSlot, ProductionBatch
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def assert_safe_test_url(url: str) -> None:
    lowered = url.lower()
    if "lojadepaes_test" not in lowered:
        raise RuntimeError("recusando teste: URL não aponta para lojadepaes_test")
    if any(token in lowered for token in ("amazonaws.com", "production", "prod.", "actionhub.com")):
        raise RuntimeError("recusando teste: URL parece produção")


def _ensure_database(admin_url: str, db_name: str) -> None:
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    test_url = settings.test_database_url
    assert_safe_test_url(test_url)
    _ensure_database(settings.database_url, "lojadepaes_test")
    ini = Path(__file__).resolve().parents[2] / "database" / "alembic.ini"
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    previous = settings.database_url
    get_settings.cache_clear()
    import os

    os.environ["LOJADEPAES_DATABASE_URL"] = test_url
    get_settings.cache_clear()
    reset_engine()
    command.upgrade(config, "head")
    engine = create_engine(test_url, pool_pre_ping=True)
    yield engine
    engine.dispose()
    if previous:
        os.environ["LOJADEPAES_DATABASE_URL"] = previous
    get_settings.cache_clear()
    reset_engine()


@pytest.fixture
def db(test_engine: Engine) -> Iterator[Session]:
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    session = sessionmaker(bind=test_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def priced_catalog(session: Session) -> dict:
    dough = DoughType(
        name="Sourdough clássico",
        slug=f"dough-{uuid4().hex[:8]}",
        short_description="teste",
        fermentation_hours=24,
        sort_order=0,
        is_active=True,
        base_price_cents=1200,
    )
    ingredient = Ingredient(
        name="Nozes",
        slug=f"ing-{uuid4().hex[:8]}",
        description="teste",
        sort_order=0,
        is_active=True,
        surcharge_cents=200,
    )
    shape = BreadShape(
        name="Rústico de cesto",
        slug=f"shape-{uuid4().hex[:8]}",
        description="teste",
        crust_crumb_notes="crosta",
        sort_order=0,
        is_active=True,
    )
    session.add_all([dough, ingredient, shape])
    session.flush()
    session.add_all(
        [
            DoughIngredientCompatibility(dough_type_id=dough.id, ingredient_id=ingredient.id),
            DoughShapeCompatibility(dough_type_id=dough.id, bread_shape_id=shape.id),
        ]
    )
    start = datetime.now(UTC) + timedelta(hours=1)
    available = start + timedelta(hours=10)
    batch = ProductionBatch(
        code=f"B-{uuid4().hex[:6]}",
        planned_start_at=start,
        breads_available_at=available,
        order_deadline_at=available,
        capacity_units=2,
        status=BatchStatus.OPEN.value,
    )
    session.add(batch)
    session.flush()
    slot = FulfillmentSlot(
        production_batch_id=batch.id,
        starts_at=available + timedelta(minutes=30),
        ends_at=available + timedelta(hours=2),
        capacity_units=2,
        is_active=True,
        modality=FulfillmentModality.PICKUP.value,
    )
    session.add(slot)
    session.flush()
    return {
        "dough": dough,
        "ingredient": ingredient,
        "shape": shape,
        "batch": batch,
        "slot": slot,
    }


def draft_order(session: Session, catalog: dict, quantity: int = 1, extras: bool = True) -> Order:
    order = Order(
        public_reference=new_public_reference(),
        status="draft",
        fulfillment_modality=FulfillmentModality.PICKUP.value,
        fulfillment_slot_id=catalog["slot"].id,
        production_batch_id=catalog["batch"].id,
        customer_name="Visitante Teste",
        customer_email="visitante@example.test",
        currency="BRL",
    )
    session.add(order)
    session.flush()
    item = OrderItem(
        order_id=order.id,
        dough_type_id=catalog["dough"].id,
        bread_shape_id=catalog["shape"].id,
        quantity=quantity,
    )
    session.add(item)
    session.flush()
    if extras:
        session.add(
            OrderItemIngredient(order_item_id=item.id, ingredient_id=catalog["ingredient"].id)
        )
        session.flush()
    return order
