"""G14: migrate_once devolve o FORCE ROW LEVEL SECURITY mesmo quando o upgrade falha."""

from __future__ import annotations

import migrate_once
import pytest
from sqlalchemy import text


class _FakeConnection:
    def __init__(self) -> None:
        self.events: list[str] = []

    def execute(self, statement):
        sql = str(statement)
        self.events.append("restore" if "FORCE ROW LEVEL SECURITY" in sql and "NO FORCE" not in sql else "other")

    def rollback(self) -> None:
        self.events.append("rollback")

    def commit(self) -> None:
        self.events.append("commit")


def test_restore_force_runs_when_upgrade_fails(monkeypatch) -> None:
    def broken(_config, _revision):
        raise RuntimeError("falha simulada no upgrade")

    monkeypatch.setattr(migrate_once.command, "upgrade", broken)
    connection = _FakeConnection()
    config = type("Config", (), {"attributes": {}})()
    with pytest.raises(RuntimeError, match="falha simulada"):
        migrate_once.run_upgrade(connection, config)
    assert connection.events == ["rollback", "restore", "commit"]
    assert config.attributes["connection"] is connection


def test_restore_force_runs_when_upgrade_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(migrate_once.command, "upgrade", lambda _config, _revision: None)
    connection = _FakeConnection()
    config = type("Config", (), {"attributes": {}})()
    migrate_once.run_upgrade(connection, config)
    assert connection.events == ["restore", "commit"]


def _weak_tables(connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            text(
                """
                SELECT c.relname
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                  AND c.relrowsecurity AND NOT c.relforcerowsecurity
                """
            )
        )
    ]


def test_force_is_back_on_real_tables_after_failed_upgrade(engine, monkeypatch) -> None:
    def broken(config, _revision):
        # Falha no meio, com a transação já suja, como numa migração que quebra.
        config.attributes["connection"].execute(text("SELECT 1"))
        raise RuntimeError("falha simulada no upgrade")

    monkeypatch.setattr(migrate_once.command, "upgrade", broken)
    config = type("Config", (), {"attributes": {}})()
    with engine.connect() as connection:
        connection.execute(text(migrate_once.RELAX_FORCE_SQL))
        connection.commit()
        try:
            assert _weak_tables(connection) != [], "o teste precisa partir de tabelas sem FORCE"
            connection.rollback()
            with pytest.raises(RuntimeError, match="falha simulada"):
                migrate_once.run_upgrade(connection, config)
            assert _weak_tables(connection) == []
        finally:
            connection.rollback()
            connection.execute(text(migrate_once.RESTORE_FORCE_SQL))
            connection.commit()
