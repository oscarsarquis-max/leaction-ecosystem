"""FastAPI foundation — health + Organization/Membership (dev auth)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "qmind"


def test_create_org_and_current_with_dev_auth(client: TestClient):
    sub = f"dev-{uuid.uuid4()}"
    email = f"{sub}@example.com"
    headers = {"X-Dev-User-Sub": sub, "X-Dev-User-Email": email}

    created = client.post(
        "/api/v1/organizations",
        json={"name": f"Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    org_id = created.json()["organization"]["id"]
    assert "org_admin" in created.json()["membership"]["roles"]

    memberships = client.get("/api/v1/organizations/me/memberships", headers=headers)
    assert memberships.status_code == 200
    assert any(m["organization_id"] == org_id for m in memberships.json())

    current = client.get(
        "/api/v1/organizations/current",
        headers={**headers, "X-Organization-Id": org_id},
    )
    assert current.status_code == 200
    assert current.json()["id"] == org_id


def test_ready_has_no_sensitive_fields(client: TestClient):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ready"}


def test_dev_auth_forbidden_when_environment_prod():
    import os

    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            auth_mode="dev",
            database_url_admin=os.environ["DATABASE_URL_ADMIN"],
            database_url_app=os.environ["DATABASE_URL_APP"],
        )


def test_prod_forbids_simulated_security_pass_and_memory_storage():
    import os

    from pydantic import ValidationError

    from app.config import Settings

    base = dict(
        environment="prod",
        auth_mode="cognito",
        cognito_user_pool_id="pool",
        cognito_app_client_id="client",
        database_url_admin=os.environ["DATABASE_URL_ADMIN"],
        database_url_app=os.environ["DATABASE_URL_APP"],
        storage_backend="s3",
        s3_bucket="qmind-evidences-example",
        allow_simulated_security_pass=True,
    )
    with pytest.raises(ValidationError):
        Settings(**base)
    with pytest.raises(ValidationError):
        Settings(
            **{
                **base,
                "allow_simulated_security_pass": False,
                "storage_backend": "memory",
            }
        )


def test_foreign_org_context_forbidden(client: TestClient):
    sub = f"dev-{uuid.uuid4()}"
    headers = {"X-Dev-User-Sub": sub, "X-Dev-User-Email": f"{sub}@example.com"}
    created = client.post(
        "/api/v1/organizations",
        json={"name": "Mine"},
        headers=headers,
    )
    assert created.status_code == 201

    other = client.get(
        "/api/v1/organizations/current",
        headers={
            **headers,
            "X-Organization-Id": str(uuid.uuid4()),
        },
    )
    assert other.status_code == 403
    assert other.json()["code"] == "forbidden_organization"
