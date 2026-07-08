"""Patches leves de schema para evolução do RDO sem Alembic."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.extensions import db


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns(table)}
    if column not in cols:
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
        db.session.commit()


def ensure_rdo_schema() -> None:
    """Adiciona colunas novas em bases já existentes (create_all não altera tabelas)."""
    _add_column_if_missing("daily_logs", "ppe_compliant", "ppe_compliant BOOLEAN")
    _add_column_if_missing("daily_logs", "ppe_compliant_details", "ppe_compliant_details TEXT")
    _add_column_if_missing(
        "daily_logs",
        "supplies_data",
        "supplies_data JSONB DEFAULT '[]'::jsonb",
    )

    _add_column_if_missing("workforce", "presence_details", "presence_details TEXT")
    _add_column_if_missing(
        "workforce", "absences_count", "absences_count INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing("workforce", "absences_details", "absences_details TEXT")
    _add_column_if_missing(
        "workforce", "extra_hours_count", "extra_hours_count INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing("workforce", "extra_hours_details", "extra_hours_details TEXT")
    _add_column_if_missing("workforce", "general_remarks", "general_remarks TEXT")
    _add_column_if_missing(
        "workforce", "overtime_hours", "overtime_hours INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing("workforce", "absences", "absences INTEGER NOT NULL DEFAULT 0")

    if "workforce" in inspect(db.engine).get_table_names():
        db.session.execute(
            text(
                """
                UPDATE workforce
                SET absences_count = CASE WHEN absences_count = 0 THEN absences ELSE absences_count END,
                    extra_hours_count = CASE WHEN extra_hours_count = 0 THEN overtime_hours ELSE extra_hours_count END
                WHERE absences > 0 OR overtime_hours > 0
                """
            )
        )
        db.session.commit()

    _add_column_if_missing(
        "equipment_statuses", "quantity", "quantity INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing("equipment_statuses", "remarks", "remarks TEXT")
    _add_column_if_missing("executed_services", "remarks", "remarks TEXT")

    _add_column_if_missing(
        "daily_logs", "delay_waiting_material", "delay_waiting_material BOOLEAN NOT NULL DEFAULT FALSE"
    )
    _add_column_if_missing(
        "daily_logs", "delay_rework", "delay_rework BOOLEAN NOT NULL DEFAULT FALSE"
    )
    _add_column_if_missing(
        "daily_logs", "delay_lack_of_front", "delay_lack_of_front BOOLEAN NOT NULL DEFAULT FALSE"
    )
    _add_column_if_missing("daily_logs", "end_shift_clean", "end_shift_clean BOOLEAN")
    _add_column_if_missing("daily_logs", "end_shift_tools_stored", "end_shift_tools_stored BOOLEAN")
    _add_column_if_missing(
        "daily_logs", "end_shift_loose_materials", "end_shift_loose_materials BOOLEAN"
    )

    _add_column_if_missing("daily_logs", "sprint_daily_goal", "sprint_daily_goal TEXT")
    _add_column_if_missing(
        "daily_logs", "sprint_goal_locked", "sprint_goal_locked BOOLEAN NOT NULL DEFAULT FALSE"
    )
    _add_column_if_missing("daily_logs", "goal_achieved", "goal_achieved BOOLEAN")
    _add_column_if_missing("daily_logs", "impediment_details", "impediment_details TEXT")
    _add_column_if_missing("daily_logs", "mitigation_action", "mitigation_action TEXT")
    _add_column_if_missing("daily_logs", "preventive_action", "preventive_action TEXT")

    _add_column_if_missing("occurrences", "exact_location", "exact_location TEXT")
    _add_column_if_missing("occurrences", "what_happened", "what_happened TEXT")
    _add_column_if_missing(
        "occurrences", "immediate_action_taken", "immediate_action_taken TEXT"
    )

    if "occurrences" in inspect(db.engine).get_table_names():
        cols = {c["name"] for c in inspect(db.engine).get_columns("occurrences")}
        if "description" in cols and "what_happened" in cols:
            db.session.execute(
                text(
                    """
                    UPDATE occurrences
                    SET what_happened = COALESCE(NULLIF(TRIM(what_happened), ''), description),
                        exact_location = COALESCE(NULLIF(TRIM(exact_location), ''), 'Não informado'),
                        description = COALESCE(description, what_happened)
                    WHERE what_happened IS NULL OR TRIM(what_happened) = ''
                       OR exact_location IS NULL OR TRIM(exact_location) = ''
                    """
                )
            )
            db.session.execute(
                text("ALTER TABLE occurrences ALTER COLUMN description DROP NOT NULL")
            )
            db.session.commit()
