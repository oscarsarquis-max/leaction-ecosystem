from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


def _alembic(engine, revision: str, direction: str) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        getattr(command, direction)(config, revision)


def _column_default(engine) -> str | None:
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'technical_product' AND column_name = 'supply_mode'
                """
            )
        ).scalar_one()


def test_supply_mode_default_removed_without_reclassifying(engine) -> None:
    _alembic(engine, "0025_economic_audit_policy", "downgrade")
    suffix = uuid4().hex[:8]
    session = sessionmaker(bind=engine, future=True)()
    try:
        org_id = session.execute(
            text(
                """
                INSERT INTO organization (slug, legal_name, display_name, status)
                VALUES (:slug, 'Razão preservada', 'Nome preservado', 'active')
                RETURNING id
                """
            ),
            {"slug": f"mod-{suffix}"},
        ).scalar_one()
        produced_id = session.execute(
            text(
                """
                INSERT INTO technical_product (organization_id, code, display_name, supply_mode)
                VALUES (:org, :code, 'Pão explícito', 'produced')
                RETURNING id
                """
            ),
            {"org": org_id, "code": f"PAO-{suffix}"},
        ).scalar_one()
        purchased_id = session.execute(
            text(
                """
                INSERT INTO technical_product (organization_id, code, display_name, supply_mode)
                VALUES (:org, :code, 'Manteiga comprada', 'purchased')
                RETURNING id
                """
            ),
            {"org": org_id, "code": f"MANTEIGA-{suffix}"},
        ).scalar_one()
        implicit_id = session.execute(
            text(
                """
                INSERT INTO technical_product (organization_id, code, display_name)
                VALUES (:org, :code, 'Item pelo default antigo')
                RETURNING id
                """
            ),
            {"org": org_id, "code": f"LEG-{suffix}"},
        ).scalar_one()
        session.commit()
    finally:
        session.close()

    _alembic(engine, "0026_supply_mode_no_default", "upgrade")
    assert _column_default(engine) is None

    check = sessionmaker(bind=engine, future=True)()
    try:
        rows = {
            row.id: row.supply_mode
            for row in check.execute(
                text(
                    """
                    SELECT id, supply_mode
                    FROM technical_product
                    WHERE id IN (:produced, :purchased, :implicit)
                    """
                ),
                {"produced": produced_id, "purchased": purchased_id, "implicit": implicit_id},
            )
        }
        assert rows[produced_id] == "produced"
        assert rows[purchased_id] == "purchased"
        assert rows[implicit_id] == "produced"
        with pytest.raises(IntegrityError) as caught:
            check.execute(
                text(
                    """
                    INSERT INTO technical_product (organization_id, code, display_name)
                    VALUES (:org, :code, 'Sem modalidade')
                    """
                ),
                {"org": org_id, "code": f"SEM-{suffix}"},
            )
            check.commit()
        check.rollback()
        assert "supply_mode" in str(caught.value)
        still_missing = check.execute(
            text("SELECT id FROM technical_product WHERE code = :code"),
            {"code": f"SEM-{suffix}"},
        ).first()
        assert still_missing is None
    finally:
        check.close()

    _alembic(engine, "0025_economic_audit_policy", "downgrade")
    assert "produced" in (_column_default(engine) or "")
    after_down = sessionmaker(bind=engine, future=True)()
    try:
        preserved = {
            row.id: row.supply_mode
            for row in after_down.execute(
                text(
                    """
                    SELECT id, supply_mode
                    FROM technical_product
                    WHERE id IN (:produced, :purchased, :implicit)
                    """
                ),
                {"produced": produced_id, "purchased": purchased_id, "implicit": implicit_id},
            )
        }
        assert preserved == {
            produced_id: "produced",
            purchased_id: "purchased",
            implicit_id: "produced",
        }
    finally:
        after_down.close()

    _alembic(engine, "head", "upgrade")
    assert _column_default(engine) is None
