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


@pytest.fixture(autouse=True)
def _silence_crm_tracking(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A suíte não fala com o Hub. Os testes de tracking ligam o segredo de propósito."""
    monkeypatch.setenv("LOJADEPAES_CRM_TRACKING_SECRET", "")
    monkeypatch.delenv("CRM_TRACKING_SECRET", raising=False)
    monkeypatch.delenv("LOJADEPAES_CRM_TRACKING_SYNC", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolate_mail_transport(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Não herdar SES real do .env local; a suíte não envia e-mail externo."""
    monkeypatch.setenv("LOJADEPAES_MAIL_IDENTITY_READY", "false")
    monkeypatch.setenv("LOJADEPAES_AWS_ACCESS_KEY_ID", "")
    monkeypatch.setenv("LOJADEPAES_AWS_SECRET_ACCESS_KEY", "")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
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
