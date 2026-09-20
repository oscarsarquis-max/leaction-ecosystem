from collections.abc import Iterator

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TEST_ADMIN_USER = "padaria"
TEST_ADMIN_PASSWORD = "correct-horse-admin"
TEST_ADMIN_HASH = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash(
    TEST_ADMIN_PASSWORD
)
TEST_SESSION_SECRET = "test-admin-session-secret-32chars"


@pytest.fixture
def admin_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/admin/login",
        json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]
