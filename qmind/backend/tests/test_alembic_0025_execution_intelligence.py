"""ISOI-009 migration round-trip and append-only downgrade guard."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

from alembic import command
from tests.alembic_support import ADMIN_URL, alembic_cfg, alembic_head, roundtrip

PREVIOUS = "20260824_0024"
TABLE = "improvement_case_execution_intelligence_runs"
BACKUP = "_iso009_ei_runs_backup"


def test_0024_to_0025_empty_roundtrip() -> None:
    def at_head(conn) -> None:
        assert conn.execute(text("SELECT to_regclass(:name)"), {"name": TABLE}).scalar()
        definition = conn.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conname = 'ck_ic_ei_idempotency_pair'
                """
            )
        ).scalar_one()
        assert "request_fingerprint" in definition

    def at_down(conn) -> None:
        assert (
            conn.execute(text("SELECT to_regclass(:name)"), {"name": TABLE}).scalar()
            is None
        )

    roundtrip(PREVIOUS, at_head=at_head, at_down=at_down)


def test_0025_empty_downgrade_allowed_without_crossing_0024_guard() -> None:
    """Empty EI history may downgrade 0025→0024 even when ISOI-008 history exists."""
    cfg = alembic_cfg()
    command.upgrade(cfg, "head")
    engine = create_engine(ADMIN_URL)
    try:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {BACKUP}"))
            conn.execute(text(f"CREATE TABLE {BACKUP} AS TABLE {TABLE}"))
            conn.execute(text(f"DELETE FROM {TABLE}"))
            assert conn.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar_one() == 0

        command.downgrade(cfg, PREVIOUS)
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT to_regclass(:name)"), {"name": TABLE}).scalar()
                is None
            )
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == PREVIOUS
            )

        command.upgrade(cfg, "head")
        with engine.begin() as conn:
            assert conn.execute(
                text("SELECT to_regclass(:name)"), {"name": TABLE}
            ).scalar()
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == alembic_head()
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO {TABLE}
                    SELECT * FROM {BACKUP}
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )
            conn.execute(text(f"DROP TABLE IF EXISTS {BACKUP}"))
    finally:
        command.upgrade(cfg, "head")
        with engine.begin() as conn:
            exists = conn.execute(
                text("SELECT to_regclass(:name)"), {"name": BACKUP}
            ).scalar()
            if exists:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {TABLE}
                        SELECT * FROM {BACKUP}
                        ON CONFLICT (id) DO NOTHING
                        """
                    )
                )
                conn.execute(text(f"DROP TABLE IF EXISTS {BACKUP}"))
        engine.dispose()


def test_0025_downgrade_refuses_when_history_exists() -> None:
    cfg = alembic_cfg()
    command.upgrade(cfg, "head")
    engine = create_engine(ADMIN_URL)
    created_id = None
    try:
        with engine.begin() as conn:
            owner = conn.execute(
                text(
                    """
                    SELECT c.organization_id, c.id AS case_id, m.user_id
                    FROM improvement_cases c
                    JOIN memberships m ON m.organization_id = c.organization_id
                    ORDER BY c.created_at
                    LIMIT 1
                    """
                )
            ).first()
            if owner is None:
                pytest.skip("database has no case and member for migration guard test")
            created_id = conn.execute(
                text(
                    f"""
                    INSERT INTO {TABLE} (
                      organization_id, improvement_case_id, schema_version,
                      mechanism_version, request_id, correlation_id, generated_at,
                      input_snapshot, input_fingerprint, result, created_by
                    ) VALUES (
                      :org, :case_id, '1.0', 'execution-intelligence-rules-v1',
                      'migration-test', 'migration-test', now(),
                      '{{}}'::jsonb, 'migration-test', '{{}}'::jsonb, :user_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "org": owner.organization_id,
                    "case_id": owner.case_id,
                    "user_id": owner.user_id,
                },
            ).scalar_one()

        with pytest.raises(DatabaseError, match="ISOI-009 downgrade refused"):
            command.downgrade(cfg, PREVIOUS)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                alembic_head()
            )
    finally:
        if created_id is not None:
            with engine.begin() as conn:
                conn.execute(
                    text(f"DELETE FROM {TABLE} WHERE id = :id"), {"id": created_id}
                )
        engine.dispose()
