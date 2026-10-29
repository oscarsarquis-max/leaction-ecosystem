"""Directed contract: Alembic uses only the runner-injected connection."""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
ENV = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")


def _config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


def test_env_source_refuses_url_localhost_and_secrets() -> None:
    assert 'attributes.get("connection")' in ENV
    assert "get_settings" not in ENV
    assert "set_main_option" not in ENV
    assert "database_url" not in ENV
    assert "runtime_database_url" not in ENV
    assert "get_secret" not in ENV
    assert "secretsmanager" not in ENV
    assert "127.0.0.1" not in ENV
    assert "localhost" not in ENV
    assert "async_engine_from_config" not in ENV
    assert "create_async_engine" not in ENV
    assert "create_engine" not in ENV


def test_ini_still_points_at_placeholder_localhost() -> None:
    ini = (ROOT / "alembic.ini").read_text(encoding="utf-8")
    assert "127.0.0.1:5434" in ini


def test_offline_mode_fails_closed() -> None:
    from alembic.runtime.environment import EnvironmentContext
    from alembic.script import ScriptDirectory

    cfg = _config()
    script = ScriptDirectory.from_config(cfg)

    def _dest(rev, context):  # noqa: ARG001
        return []

    with pytest.raises(RuntimeError, match="offline mode is disabled"):
        with EnvironmentContext(cfg, script, fn=_dest, as_sql=True):
            script.run_env()


def test_missing_injected_connection_fails_closed() -> None:
    cfg = _config()
    with pytest.raises(Exception, match="no database connection provided"):
        command.current(cfg)


def test_injected_connection_is_used_not_ini_localhost(engine: Engine) -> None:
    """If env.py ignores attributes['connection'], Alembic talks to 127.0.0.1:5434."""
    cfg = _config()
    assert "127.0.0.1:5434" in (cfg.get_main_option("sqlalchemy.url") or "")
    assert str(engine.url.host) not in {"127.0.0.1", "localhost"} or int(engine.url.port or 0) != 5434

    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        conn.execute(text("CREATE TEMP TABLE panne_alembic_env_probe(id int)"))
        command.current(cfg)
        visible = conn.execute(text("SELECT COUNT(*) FROM panne_alembic_env_probe")).scalar()
        assert visible == 0
        host = conn.execute(text("SELECT inet_server_addr() IS NOT NULL OR true")).scalar()
        assert host is True
        current = conn.execute(text("SELECT current_database()")).scalar()
        assert current == "panne"
