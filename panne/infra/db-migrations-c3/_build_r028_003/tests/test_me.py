from uuid import uuid4

from app.db import get_runtime_session
from app.main import app
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.identity_organization.http import get_access_token_verifier
from app.modules.identity_organization.models import (
    AuthIdentity,
    OrganizationMembership,
    OrganizationMembershipRole,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker
from tests import helpers
from tests.conftest import postgres_url
from tests.jwt_support import ISSUER
from tests.rls_support import ensure_runtime_role, runtime_postgres_url


def _client(engine, fake: FakeAccessTokenVerifier) -> TestClient:
    ensure_runtime_role(engine)
    runtime = create_engine(runtime_postgres_url(), future=True, pool_pre_ping=True)
    factory = sessionmaker(bind=runtime, expire_on_commit=False, future=True)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_runtime_session] = override_session
    app.dependency_overrides[get_access_token_verifier] = lambda: fake
    client = TestClient(app)
    client.runtime_engine = runtime
    return client


def _cleanup(client: TestClient) -> None:
    app.dependency_overrides.clear()
    engine = getattr(client, "runtime_engine", None)
    if engine is not None:
        engine.dispose()


def test_me_requires_token() -> None:
    fake = FakeAccessTokenVerifier()
    engine = create_engine(postgres_url(), future=True)
    client = _client(engine, fake)
    try:
        response = client.get("/api/v1/me")
        assert response.status_code == 401
        assert response.json() == {"detail": "nao_autenticado"}
    finally:
        _cleanup(client)
        engine.dispose()


def test_health_and_ready_remain_public(engine) -> None:
    fake = FakeAccessTokenVerifier()
    client = _client(engine, fake)
    try:
        health = client.get("/health")
        ready = client.get("/ready")
        assert health.status_code == 200
        assert ready.status_code == 200
        assert health.json()["service"] == "panne"
        assert ready.json() == {"status": "ok", "service": "panne"}
    finally:
        _cleanup(client)


def test_me_success_and_denials(engine) -> None:
    fake = FakeAccessTokenVerifier()
    session: Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    suffix = uuid4().hex[:8]
    issuer = ISSUER
    owner = helpers.user(session, f"me-owner-{suffix}@example.com")
    org = helpers.org(session, f"me-org-{suffix}")
    helpers.membership(session, org, owner, role="owner")
    helpers.auth_identity(session, owner, issuer, f"sub-owner-{suffix}")
    lonely = helpers.user(session, f"me-lonely-{suffix}@example.com")
    helpers.auth_identity(session, lonely, issuer, f"sub-lonely-{suffix}")
    restricted = helpers.user(session, f"me-rest-{suffix}@example.com")
    helpers.membership(session, org, restricted, role="restricted")
    helpers.auth_identity(session, restricted, issuer, f"sub-rest-{suffix}")
    owner_id, lonely_id, restricted_id, org_id = owner.id, lonely.id, restricted.id, org.id
    session.commit()
    session.close()

    fake.register("token-owner", issuer=issuer, subject=f"sub-owner-{suffix}")
    fake.register("token-lonely", issuer=issuer, subject=f"sub-lonely-{suffix}")
    fake.register("token-rest", issuer=issuer, subject=f"sub-rest-{suffix}")
    fake.register("token-unknown", issuer=issuer, subject="nobody")

    client = _client(engine, fake)
    try:
        denied = client.get("/api/v1/me", headers={"Authorization": "Bearer invalido"})
        assert denied.status_code == 401
        assert "nao_autenticado" in denied.text

        lonely_resp = client.get("/api/v1/me", headers={"Authorization": "Bearer token-lonely"})
        assert lonely_resp.status_code == 403
        assert lonely_resp.json() == {"detail": "nao_autorizado"}

        rest_resp = client.get("/api/v1/me", headers={"Authorization": "Bearer token-rest"})
        assert rest_resp.status_code == 403

        unknown = client.get("/api/v1/me", headers={"Authorization": "Bearer token-unknown"})
        assert unknown.status_code == 403

        ok = client.get(
            "/api/v1/me",
            headers={
                "Authorization": "Bearer token-owner",
                "X-Panne-Organization-Id": str(org_id),
            },
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["user_id"] == str(owner_id)
        assert body["display_name"]
        assert "email" not in body
        assert body["selected_organization_id"] == str(org_id)
        assert "owner" in body["roles"]
        assert "identity.read_me" in body["permissions"]
        assert "role" not in body["associations"][0]
        assert "owner" in body["associations"][0]["roles"]
        assert body["associations"][0]["display_name"]
        assert "password" not in str(body).lower()

        fake.unavailable = True
        down = client.get("/api/v1/me", headers={"Authorization": "Bearer token-owner"})
        assert down.status_code == 503
        assert down.json() == {"detail": "indisponivel"}
    finally:
        _cleanup(client)
        admin = sessionmaker(bind=engine, future=True)()
        ids = [owner_id, lonely_id, restricted_id]
        admin.execute(delete(AuthIdentity).where(AuthIdentity.user_id.in_(ids)))
        admin.execute(
            delete(OrganizationMembershipRole).where(
                OrganizationMembershipRole.membership_id.in_(
                    select(OrganizationMembership.id).where(
                        OrganizationMembership.user_id.in_(ids)
                    )
                )
            )
        )
        admin.execute(delete(OrganizationMembership).where(OrganizationMembership.user_id.in_(ids)))
        admin.commit()
        admin.close()
