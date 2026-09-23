"""Estados de acesso e titular pessoa física. Banco descartável, sem cliente real."""

import json
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from app.modules.identity_organization.access_tokens import VerifiedAccessToken
from app.modules.identity_organization.models import Organization, OrganizationMembership
from app.modules.identity_organization.admin_command import assert_admin_target, main
from app.modules.identity_organization.onboarding import (
    accept_invitation,
    actor_email,
    create_organization_invitation,
    describe_access,
    formalize_organization,
    issue_onboarding_authorization,
    list_onboarding_authorizations,
    revoke_onboarding_authorization,
)
from app.modules.identity_organization.services import (
    IdentityResolutionError,
    ensure_productive_onboarding,
)
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


def _token(subject: str, email: str) -> VerifiedAccessToken:
    return VerifiedAccessToken(
        issuer="https://idp.example.invalid",
        subject=subject,
        client_id="test-client",
        scopes=frozenset(),
        raw_claims={"username": "identificador-interno", "sub": subject, "client_id": "test-client"},
    )


def _natural(**overrides: str) -> dict:
    token = uuid4().hex[:8]
    args = {
        "issuer": "https://idp.example.invalid",
        "subject": f"pf-{token}",
        "email": f"pf-{token}@example.invalid",
        "display_name": "Titular de teste",
        "organization_slug": f"op-{token}",
        "legal_name": None,
        "organization_display_name": f"Operacao {token}",
        "establishment_code": f"loja-{token}",
        "establishment_display_name": "Estabelecimento de teste",
        "holder_kind": "natural_person",
        "holder_name": "Titular de teste",
        "holder_fiscal_id": "39053344705",
        "formalization_state": "not_formalized",
        "establishment_nature": "integrated",
        "capabilities": ("sale", "stock", "production"),
    }
    args.update(overrides)
    return args


def test_natural_person_does_not_require_company_documents(db_session: Session) -> None:
    args = _natural()
    issue_onboarding_authorization(db_session, email=args["email"], commercial_condition="complimentary")
    created = ensure_productive_onboarding(db_session, **args)
    assert created.organization.legal_name is None
    assert created.organization.holder_fiscal_id_type == "cpf"
    assert created.organization.formalization_state == "not_formalized"
    assert created.organization.commercial_condition == "complimentary"
    assert created.organization.holder_kind == "natural_person"
    assert tuple(created.establishment.capabilities) == ("sale", "stock", "production")


def test_access_token_without_email_claim_does_not_identify_the_account() -> None:
    token = _token("pessoa", "pessoa@example.invalid")
    assert "email" not in token.raw_claims
    assert actor_email(token) is None


def test_authenticated_without_authorization_cannot_create(db_session: Session) -> None:
    args = _natural()
    view = describe_access(db_session, _token(args["subject"], args["email"]), args["email"])
    assert view.state == "sem_autorizacao"
    try:
        ensure_productive_onboarding(db_session, **args)
    except IdentityResolutionError as caught:
        assert caught.reason == "sem_autorizacao"
    else:
        raise AssertionError("deveria recusar")
    assert (
        db_session.scalar(select(Organization.id).where(Organization.slug == args["organization_slug"]))
        is None
    )


def test_pending_invite_is_distinct_from_creation(db_session: Session) -> None:
    owner = _natural()
    issue_onboarding_authorization(db_session, email=owner["email"], commercial_condition="standard")
    created = ensure_productive_onboarding(db_session, **owner)
    guest_email = f"convite-{uuid4().hex[:6]}@example.invalid"
    create_organization_invitation(
        db_session,
        organization_id=created.organization.id,
        email=guest_email,
        role="production",
        actor_user_id=created.user.id,
    )
    guest = _token(f"guest-{uuid4().hex[:6]}", guest_email)
    view = describe_access(db_session, guest, guest_email)
    assert view.state == "convidado"
    assert view.invite_organization_name == created.organization.display_name
    before = db_session.scalar(select(func.count()).select_from(Organization))
    accepted = accept_invitation(db_session, guest, guest_email)
    assert accepted.id == created.organization.id
    assert db_session.scalar(select(func.count()).select_from(Organization)) == before
    memberships = db_session.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(OrganizationMembership.organization_id == created.organization.id)
    )
    assert memberships == 2


def test_formalization_keeps_the_same_client(db_session: Session) -> None:
    args = _natural()
    issue_onboarding_authorization(db_session, email=args["email"], commercial_condition="complimentary")
    created = ensure_productive_onboarding(db_session, **args)
    formalize_organization(
        db_session,
        organization_id=created.organization.id,
        actor_user_id=created.user.id,
        legal_name="Razão posterior de teste",
        cnpj="12345678000195",
    )
    assert created.organization.id
    assert created.organization.formalization_state == "formalized"
    assert created.organization.legal_name == "Razão posterior de teste"
    assert created.organization.holder_fiscal_id_type == "cnpj"


def test_admin_can_issue_list_and_revoke_without_exposing_the_address(db_session: Session) -> None:
    email = f"admin-{uuid4().hex[:8]}@example.invalid"
    issued = issue_onboarding_authorization(
        db_session, email=email, commercial_condition="complimentary", valid_hours=48
    )
    listed = list_onboarding_authorizations(db_session, email)
    assert [item.id for item in listed] == [issued.id]
    assert listed[0].commercial_condition == "complimentary"
    assert listed[0].status == "issued"
    assert not hasattr(listed[0], "email_normalized")
    revoked = revoke_onboarding_authorization(db_session, issued.id)
    assert revoked.status == "revoked"
    try:
        revoke_onboarding_authorization(db_session, issued.id)
    except IdentityResolutionError as caught:
        assert caught.reason == "autorizacao_encerrada"
    else:
        raise AssertionError("autorização encerrada deveria permanecer encerrada")


def test_admin_command_refuses_demo_and_runtime_role() -> None:
    try:
        assert_admin_target("postgresql://owner@127.0.0.1:5545/panne_demo", "test")
    except SystemExit as caught:
        assert "Demo" in str(caught)
    else:
        raise AssertionError("Demo deveria ser recusada")
    try:
        assert_admin_target("postgresql://panne_prod_runtime@127.0.0.1:5545/panne", "production")
    except SystemExit as caught:
        assert "administrativa" in str(caught)
    else:
        raise AssertionError("papel de execução deveria ser recusado")
    assert_admin_target("postgresql://owner@127.0.0.1:5545/panne", "production")


def test_owner_without_bypass_can_issue_and_keeps_force(engine, capsys, monkeypatch) -> None:
    email = f"owner-{uuid4().hex[:8]}@example.invalid"
    with engine.begin() as connection:
        previous = connection.execute(
            text("SELECT tableowner FROM pg_tables WHERE tablename = 'onboarding_authorization'")
        ).scalar()
        if not isinstance(previous, str) or not previous.replace("_", "").isalnum():
            raise AssertionError("dono inesperado")
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_admin_owner') THEN
                    CREATE ROLE panne_admin_owner LOGIN PASSWORD 'panne_admin_owner_test'
                      NOSUPERUSER NOBYPASSRLS;
                  END IF;
                END
                $$
                """
            )
        )
        connection.execute(text("GRANT CONNECT ON DATABASE panne TO panne_admin_owner"))
        connection.execute(text("GRANT USAGE ON SCHEMA public TO panne_admin_owner"))
        connection.execute(text("ALTER TABLE onboarding_authorization OWNER TO panne_admin_owner"))
        connection.execute(text("ALTER TABLE audit_event OWNER TO panne_admin_owner"))
    parsed = urlparse(os.environ["PANNE_DATABASE_URL"])
    netloc = f"panne_admin_owner:panne_admin_owner_test@{parsed.hostname}:{parsed.port}"
    monkeypatch.setenv("PANNE_ENV", "test")
    monkeypatch.setenv(
        "PANNE_DATABASE_URL",
        urlunparse((parsed.scheme, netloc, "/panne", "", "", "")),
    )
    try:
        assert main(["issue", "--email", email, "--condition", "complimentary", "--hours", "2"]) == 0
        issued = json.loads(capsys.readouterr().out)
        assert issued["status"] == "issued"
        assert issued["commercial_condition"] == "complimentary"
        assert issued["organization_id"] is None
        assert main(["list", "--email", email]) == 0
        listed = json.loads(capsys.readouterr().out)
        assert listed[0]["id"] == issued["id"]
        with engine.connect() as connection:
            forced = connection.execute(
                text(
                    """
                    SELECT bool_and(relforcerowsecurity)
                    FROM pg_class
                    WHERE relname IN ('onboarding_authorization', 'audit_event')
                    """
                )
            ).scalar()
            assert forced is True
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE onboarding_authorization OWNER TO {previous}"))
            connection.execute(text(f"ALTER TABLE audit_event OWNER TO {previous}"))


def test_user_cannot_choose_the_commercial_condition(db_session: Session) -> None:
    args = _natural()
    issue_onboarding_authorization(db_session, email=args["email"], commercial_condition="standard")
    created = ensure_productive_onboarding(db_session, **args)
    assert created.organization.commercial_condition == "standard"
