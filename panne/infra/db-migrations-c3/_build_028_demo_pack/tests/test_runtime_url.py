import pytest
from app.db_urls import (
    RuntimeUrlError,
    configured_runtime_url,
    is_placeholder_url,
    uses_same_database_role,
)
from fastapi import HTTPException

ADMIN = "postgresql+asyncpg://migrator:x@127.0.0.1:5434/panne"
RUNTIME = "postgresql+asyncpg://runtime:y@127.0.0.1:5434/panne"
PLACEHOLDER = (
    "postgresql+asyncpg://<configure-runtime-user>:<configure-runtime-password>@127.0.0.1:5434/panne"
)


def test_placeholder_is_not_configured() -> None:
    assert is_placeholder_url(PLACEHOLDER, kind="runtime") is True
    assert configured_runtime_url(ADMIN, PLACEHOLDER) is None
    assert configured_runtime_url(ADMIN, "") is None


def test_runtime_never_falls_back_to_admin() -> None:
    resolved = configured_runtime_url(ADMIN, PLACEHOLDER)
    assert resolved is None
    assert resolved != ADMIN
    resolved_ok = configured_runtime_url(ADMIN, RUNTIME)
    assert resolved_ok == RUNTIME
    assert resolved_ok != ADMIN


def test_same_role_is_rejected_not_used_as_admin() -> None:
    assert uses_same_database_role(ADMIN, ADMIN) is True
    with pytest.raises(RuntimeUrlError, match="runtime_nao_separado"):
        configured_runtime_url(ADMIN, ADMIN)


def test_alembic_uses_admin_setting_name() -> None:
    from tests.test_migrations import ROOT

    text = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert 'attributes.get("connection")' in text
    assert "settings.database_url" not in text
    assert "get_settings" not in text
    assert "runtime_database_url" not in text
    assert "get_runtime_session" not in text


def test_me_depends_on_runtime_not_admin_session() -> None:
    from tests.test_migrations import ROOT

    text = (
        ROOT / "app" / "modules" / "identity_organization" / "http.py"
    ).read_text(encoding="utf-8")
    assert "get_runtime_session" in text
    assert "Depends(get_session)" not in text
    assert "from app.db import get_session" not in text


def test_unconfigured_runtime_session_is_unavailable() -> None:
    from app import db as dbmod

    if dbmod.RuntimeSessionLocal is not None:
        pytest.skip("runtime local configurado nesta estação")
    with pytest.raises(HTTPException) as caught:
        next(dbmod.get_runtime_session())
    assert caught.value.status_code == 503
    assert caught.value.detail == "indisponivel"
