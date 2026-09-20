from collections.abc import Iterator

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from fastapi.testclient import TestClient

pytest_plugins = ["tests.db_fixtures"]


@pytest.fixture(autouse=True)
def _disable_local_passwordless(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("LOJADEPAES_ADMIN_LOCAL_PASSWORDLESS", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()
