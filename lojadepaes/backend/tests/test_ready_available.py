import pytest
from app.core.config import get_settings
from app.db.session import get_engine, reset_engine
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def test_ready_ok_when_postgres_accepts_connection() -> None:
    get_settings.cache_clear()
    reset_engine()
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        reset_engine()
        get_settings.cache_clear()
        pytest.skip("PostgreSQL de desenvolvimento indisponível em 127.0.0.1:5438")
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ready")
    reset_engine()
    get_settings.cache_clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "lojadepaes"}
