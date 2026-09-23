"""Jornada HTTP do primeiro cadastro, com o papel de runtime e RLS ligado."""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.db import get_runtime_session
from app.main import app
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.identity_organization.account_profile import AccountProfileError
from app.modules.identity_organization.http import get_access_token_verifier, get_account_profile
from app.modules.identity_organization.models import Organization
from app.modules.identity_organization.onboarding import (
    formalize_organization,
    issue_onboarding_authorization,
)
from app.modules.identity_organization.tenant_context import apply_tenant_context
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from tests.jwt_support import ISSUER
from tests.rls_support import ensure_runtime_role, runtime_engine


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


class Directory:
    def __init__(self, emails: dict[str, str]) -> None:
        self.emails = emails
        self.unavailable = False

    def verified_email(self, access_token: str) -> str:
        if self.unavailable:
            raise AccountProfileError("provedor_indisponivel", unavailable=True)
        email = self.emails.get(access_token)
        if not email:
            raise AccountProfileError("email_invalido")
        return email


def _claims(subject: str) -> dict[str, str]:
    return {"username": "identificador-interno", "sub": subject, "client_id": "test-client"}


def _client(engine, fake: FakeAccessTokenVerifier, emails: dict[str, str] | None = None) -> TestClient:
    ensure_runtime_role(engine)
    runtime = runtime_engine(engine)
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

    directory = Directory(emails or {})
    app.dependency_overrides[get_runtime_session] = override_session
    app.dependency_overrides[get_access_token_verifier] = lambda: fake
    app.dependency_overrides[get_account_profile] = lambda: directory
    client = TestClient(app)
    client.runtime_engine = runtime
    client.directory = directory
    return client


def _body(token: str) -> dict:
    return {
        "trade_name": f"Operacao {token}",
        "holder_kind": "natural_person",
        "holder_name": "Titular de teste",
        "holder_fiscal_id": "39053344705",
        "formalization_state": "not_formalized",
        "legal_name": None,
        "organization_code": f"op-{token}",
        "establishment_name": "Estabelecimento de teste",
        "establishment_code": f"loja-{token}",
        "establishment_nature": "integrated",
        "capabilities": ["sale", "stock", "production"],
        "accept_commercial_condition": True,
    }


def test_runtime_creates_once_and_cannot_see_another_client(engine) -> None:
    suffix = uuid4().hex[:8]
    email = f"http-{suffix}@example.invalid"
    other_email = f"outro-{suffix}@example.invalid"
    admin = sessionmaker(bind=engine, future=True)()
    try:
        issue_onboarding_authorization(admin, email=email, commercial_condition="complimentary")
        issue_onboarding_authorization(
            admin, email=other_email, commercial_condition="standard"
        )
        admin.commit()
    finally:
        admin.close()

    fake = FakeAccessTokenVerifier()
    fake.register("token-novo", issuer=ISSUER, subject=f"sub-{suffix}", claims=_claims(f"sub-{suffix}"))
    fake.register(
        "token-outro",
        issuer=ISSUER,
        subject=f"sub-outro-{suffix}",
        claims=_claims(f"sub-outro-{suffix}"),
    )
    client = _client(engine, fake, {"token-novo": email, "token-outro": other_email})
    try:
        blocked = client.get("/api/v1/me", headers={"Authorization": "Bearer token-novo"})
        assert blocked.status_code == 200
        assert blocked.json()["access_state"] == "autorizado"
        assert "Acesso negado" not in blocked.text
        assert "39053344705" not in blocked.text

        refused = client.post(
            "/api/v1/onboarding",
            headers={"Authorization": "Bearer token-novo"},
            json={**_body(suffix), "accept_commercial_condition": False},
        )
        assert refused.status_code == 422

        created = client.post(
            "/api/v1/onboarding",
            headers={"Authorization": "Bearer token-novo"},
            json=_body(suffix),
        )
        assert created.status_code == 200, created.text
        assert created.json()["created"] is True
        assert "39053344705" not in created.text
        organization_id = created.json()["organization_id"]

        again = client.post(
            "/api/v1/onboarding",
            headers={"Authorization": "Bearer token-novo"},
            json=_body(suffix),
        )
        assert again.status_code == 200
        assert again.json()["created"] is False
        assert again.json()["organization_id"] == organization_id

        other = client.post(
            "/api/v1/onboarding",
            headers={"Authorization": "Bearer token-outro"},
            json=_body(f"b{suffix}"),
        )
        assert other.status_code == 200
        other_id = other.json()["organization_id"]
        assert other_id != organization_id

        mine = client.get("/api/v1/me", headers={"Authorization": "Bearer token-novo"})
        assert mine.status_code == 200
        assert mine.json()["access_state"] == "associado"
        assert mine.json()["roles"] == ["owner"]
        assert other.json()["display_name"] not in mine.text

        crossed = client.get(
            "/api/v1/me",
            headers={
                "Authorization": "Bearer token-novo",
                "X-Panne-Organization-Id": other_id,
            },
        )
        assert other.json()["display_name"] not in crossed.text
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()


def test_runtime_without_authorization_cannot_insert_a_client(engine) -> None:
    ensure_runtime_role(engine)
    runtime = runtime_engine(engine)
    session = sessionmaker(bind=runtime, future=True)()
    try:
        apply_tenant_context(
            session,
            organization_id=None,
            user_id=None,
            issuer=ISSUER,
            subject="sem-autorizacao",
            actor_email="sem-autorizacao@example.invalid",
        )
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO organization (slug, display_name, legal_name) "
                    "VALUES ('sem-auth', 'Sem autorizacao', 'Sem autorizacao')"
                )
            )
            session.flush()
        session.rollback()
    finally:
        session.close()
        runtime.dispose()


def test_owner_formalizes_the_same_client_under_rls(engine) -> None:
    suffix = uuid4().hex[:8]
    email = f"formal-{suffix}@example.invalid"
    admin = sessionmaker(bind=engine, future=True)()
    try:
        issue_onboarding_authorization(admin, email=email, commercial_condition="complimentary")
        admin.commit()
    finally:
        admin.close()
    fake = FakeAccessTokenVerifier()
    fake.register(
        "token-formal",
        issuer=ISSUER,
        subject=f"sub-formal-{suffix}",
        claims=_claims(f"sub-formal-{suffix}"),
    )
    client = _client(engine, fake, {"token-formal": email})
    try:
        created = client.post(
            "/api/v1/onboarding",
            headers={"Authorization": "Bearer token-formal"},
            json=_body(suffix),
        )
        assert created.status_code == 200, created.text
        organization_id = created.json()["organization_id"]
        me = client.get("/api/v1/me", headers={"Authorization": "Bearer token-formal"})
        user_id = me.json()["user_id"]
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()

    runtime = runtime_engine(engine)
    session = sessionmaker(bind=runtime, future=True)()
    try:
        row = formalize_organization(
            session,
            organization_id=organization_id,
            actor_user_id=user_id,
            legal_name="Razao posterior de teste",
            cnpj="12345678000195",
        )
        assert row.formalization_state == "formalized"
        assert row.legal_name == "Razao posterior de teste"
        assert row.holder_fiscal_id_type == "cnpj"
        session.commit()
    finally:
        session.close()
        runtime.dispose()


def test_real_token_shape_uses_the_provider_and_not_the_claim(engine) -> None:
    suffix = uuid4().hex[:8]
    email = f"alfa-{suffix}@example.invalid"
    decoy = f"isca-{suffix}@example.invalid"
    admin = sessionmaker(bind=engine, future=True)()
    try:
        issue_onboarding_authorization(admin, email=email, commercial_condition="complimentary")
        issue_onboarding_authorization(admin, email=decoy, commercial_condition="standard")
        admin.commit()
    finally:
        admin.close()
    subject = f"sub-alfa-{suffix}"
    other = f"sub-beta-{suffix}"
    empty = f"sub-vazio-{suffix}"
    fake = FakeAccessTokenVerifier()
    fake.register(
        "token-alfa",
        issuer=ISSUER,
        subject=subject,
        claims={**_claims(subject), "email": decoy},
    )
    fake.register("token-beta", issuer=ISSUER, subject=other, claims=_claims(other))
    fake.register("token-claim", issuer=ISSUER, subject=f"sub-claim-{suffix}", claims={**_claims(f"sub-claim-{suffix}"), "email": email})
    fake.register("token-vazio", issuer=ISSUER, subject=empty, claims=_claims(empty))
    client = _client(
        engine,
        fake,
        {"token-alfa": email, "token-beta": email, "token-claim": decoy},
    )
    try:
        opened = client.get("/api/v1/me", headers={"Authorization": "Bearer token-alfa"})
        assert opened.status_code == 200, opened.text
        assert opened.json()["access_state"] == "autorizado"
        assert email not in opened.text
        assert decoy not in opened.text

        client.directory.unavailable = True
        again = client.get("/api/v1/me", headers={"Authorization": "Bearer token-alfa"})
        assert again.status_code == 200
        assert again.json()["access_state"] == "autorizado"

        client.directory.unavailable = False
        stolen = client.get("/api/v1/me", headers={"Authorization": "Bearer token-beta"})
        assert stolen.json()["access_state"] == "sem_autorizacao"
        refused = client.post(
            "/api/v1/onboarding",
            headers={"Authorization": "Bearer token-beta"},
            json=_body(f"x{suffix}"),
        )
        assert refused.status_code == 403
        assert email not in refused.text

        ignored = client.get("/api/v1/me", headers={"Authorization": "Bearer token-claim"})
        assert ignored.json()["access_state"] == "autorizado"
        assert ignored.json()["commercial_condition_label"] != opened.json()["commercial_condition_label"]

        client.directory.unavailable = True
        down = client.get("/api/v1/me", headers={"Authorization": "Bearer token-vazio"})
        assert down.status_code == 503
        assert down.json()["detail"] == "indisponivel"
        assert "autorização" not in down.text
    finally:
        app.dependency_overrides.clear()
        client.runtime_engine.dispose()
