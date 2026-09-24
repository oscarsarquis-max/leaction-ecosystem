"""0030 sobre o head produtivo 0029: colunas novas, sem reescrever dados."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from tests import helpers
from tests.conftest import postgres_url

ROOT = Path(__file__).resolve().parents[1]
NEW_LOT_COLUMNS = {
    "package_content_quantity",
    "package_content_unit",
    "package_content_declared_at",
    "package_content_declared_by",
    "cost_status",
    "declared_unit_cost",
    "declared_cost_currency",
    "opening_origin",
}


def _alembic(connection) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.attributes["connection"] = connection
    return config


def _admin_url() -> str:
    parsed = urlparse(postgres_url())
    return urlunparse(parsed._replace(path="/postgres"))


def _db_url(name: str) -> str:
    parsed = urlparse(postgres_url())
    return urlunparse(parsed._replace(path=f"/{name}"))


def test_0030_from_productive_head_does_not_mutate_existing_rows() -> None:
    name = f"panne_mig_0030_{uuid4().hex[:8]}"
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT", future=True)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()

    engine = create_engine(_db_url(name), future=True)
    try:
        with engine.begin() as connection:
            command.upgrade(_alembic(connection), "0029_fiscal_review_without_stock")
            current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert current == "0029_fiscal_review_without_stock"
            lot_cols = {col["name"] for col in inspect(connection).get_columns("inventory_lot")}
            assert NEW_LOT_COLUMNS.isdisjoint(lot_cols)
            assert "ingredient_link_reassignment" not in inspect(connection).get_table_names()

        session = sessionmaker(bind=engine, future=True)()
        try:
            organization = helpers.org(session, f"mig-{name[-6:]}")
            actor = helpers.user(session, f"{name}@example.invalid")
            place = helpers.establishment(session, organization, "LOJA")
            flour = helpers.ingredient(session, organization, "FAR-T1")
            flour.display_name = "Farinha tipo 1 Globo"
            other = helpers.ingredient(session, organization, "FAR-00")
            other.display_name = "Farinha tipo 00 Caputo"
            brand = helpers.ingredient(session, organization, "FAR-T1B")
            brand.display_name = "Farinha tipo 1 Anaconda"
            session.flush()
            meta = MetaData()
            location_table = Table("inventory_location", meta, autoload_with=engine)
            item_table = Table("inventory_item", meta, autoload_with=engine)
            lot_table = Table("inventory_lot", meta, autoload_with=engine)
            balance_table = Table("inventory_balance", meta, autoload_with=engine)
            location_id = uuid4()
            item_id = uuid4()
            lot_id = uuid4()
            session.execute(
                location_table.insert().values(
                    id=location_id,
                    organization_id=organization.id,
                    establishment_id=place.id,
                    code="DESP",
                    display_name="Despensa",
                    kind="warehouse",
                    created_by_user_id=actor.id,
                )
            )
            session.execute(
                item_table.insert().values(
                    id=item_id,
                    organization_id=organization.id,
                    ingredient_id=flour.id,
                    unit_code="g",
                    created_by_user_id=actor.id,
                )
            )
            session.execute(
                lot_table.insert().values(
                    id=lot_id,
                    organization_id=organization.id,
                    establishment_id=place.id,
                    inventory_item_id=item_id,
                    inventory_location_id=location_id,
                    internal_lot_code="LOT-MIG-T1",
                    unit_code="g",
                    received_quantity=Decimal("25000"),
                    content_hash="mig-lot-hash",
                    created_by_user_id=actor.id,
                )
            )
            session.execute(
                balance_table.insert().values(
                    id=uuid4(),
                    organization_id=organization.id,
                    establishment_id=place.id,
                    inventory_location_id=location_id,
                    inventory_item_id=item_id,
                    inventory_lot_id=lot_id,
                    unit_code="g",
                    physical_quantity=Decimal("25000"),
                    reserved_quantity=Decimal("0"),
                )
            )
            session.commit()
            flour_id = flour.id
            other_id = other.id
            brand_id = brand.id
        finally:
            session.close()

        with engine.begin() as connection:
            before_lot = dict(
                connection.execute(
                    text(
                        "SELECT internal_lot_code, received_quantity::text, content_hash, "
                        "inventory_item_id::text, status FROM inventory_lot WHERE id = :id"
                    ),
                    {"id": str(lot_id)},
                ).mappings().one()
            )
            before_names = list(
                connection.execute(text("SELECT display_name FROM ingredient ORDER BY display_name")).scalars()
            )
            before_bal = connection.execute(
                text("SELECT physical_quantity::text FROM inventory_balance WHERE inventory_lot_id = :id"),
                {"id": str(lot_id)},
            ).scalar_one()
            command.upgrade(_alembic(connection), "0030_ingredient_link_lot")
            current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert current == "0030_ingredient_link_lot"
            lot_cols = {col["name"] for col in inspect(connection).get_columns("inventory_lot")}
            assert NEW_LOT_COLUMNS <= lot_cols
            assert "ingredient_link_reassignment" in inspect(connection).get_table_names()
            after_lot = dict(
                connection.execute(
                    text(
                        "SELECT internal_lot_code, received_quantity::text, content_hash, "
                        "inventory_item_id::text, status, package_content_quantity, "
                        "package_content_unit, cost_status, declared_unit_cost, opening_origin "
                        "FROM inventory_lot WHERE id = :id"
                    ),
                    {"id": str(lot_id)},
                ).mappings().one()
            )
            after_names = list(
                connection.execute(text("SELECT display_name FROM ingredient ORDER BY display_name")).scalars()
            )
            after_bal = connection.execute(
                text("SELECT physical_quantity::text FROM inventory_balance WHERE inventory_lot_id = :id"),
                {"id": str(lot_id)},
            ).scalar_one()
            links = connection.execute(text("SELECT count(*) FROM ingredient_link_reassignment")).scalar_one()

        assert before_names == after_names
        assert before_names == [
            "Farinha tipo 00 Caputo",
            "Farinha tipo 1 Anaconda",
            "Farinha tipo 1 Globo",
        ]
        assert before_lot["internal_lot_code"] == after_lot["internal_lot_code"] == "LOT-MIG-T1"
        assert before_lot["received_quantity"] == after_lot["received_quantity"]
        assert before_lot["content_hash"] == after_lot["content_hash"] == "mig-lot-hash"
        assert before_lot["inventory_item_id"] == after_lot["inventory_item_id"]
        assert before_lot["status"] == after_lot["status"]
        assert after_lot["package_content_quantity"] is None
        assert after_lot["package_content_unit"] is None
        assert after_lot["cost_status"] == "known"
        assert after_lot["declared_unit_cost"] is None
        assert after_lot["opening_origin"] is None
        assert before_bal == after_bal
        assert links == 0
        assert flour_id != other_id != brand_id
    finally:
        engine.dispose()
        admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT", future=True)
        try:
            with admin.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :name AND pid <> pg_backend_pid()"
                    ),
                    {"name": name},
                )
                connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        finally:
            admin.dispose()
