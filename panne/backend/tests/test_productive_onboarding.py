from pathlib import Path
from uuid import uuid4
import json
import threading

import pytest
from alembic import command
from alembic.config import Config
from app.modules.identity_organization.models import (
    AppUser,
    AuditEvent,
    AuthIdentity,
    Establishment,
    Organization,
    OrganizationMembership,
    OrganizationMembershipRole,
)
from app.modules.identity_organization.services import (
    IdentityResolutionError,
    ensure_productive_onboarding,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests import helpers


def _ensure_head(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    _ensure_head(engine)


def _args(**overrides: str) -> dict[str, str]:
    base = {
        "issuer": "https://idp.example.invalid",
        "subject": "subject-loja-1",
        "email": "owner@example.invalid",
        "display_name": "Pessoa de teste",
        "organization_slug": "loja-teste-gate",
        "legal_name": "Razão de teste",
        "organization_display_name": "Nome de teste",
        "establishment_code": "LOJA-1",
        "establishment_display_name": "Estabelecimento de teste",
    }
    base.update(overrides)
    return base


def _counts(session: Session) -> dict[str, int]:
    models = {
        "organization": Organization,
        "establishment": Establishment,
        "membership": OrganizationMembership,
        "identity": AuthIdentity,
        "audit": AuditEvent,
    }
    return {
        name: int(session.scalar(select(func.count()).select_from(model)) or 0)
        for name, model in models.items()
    }


def test_creates_once_and_repeats_without_duplicating(db_session: Session) -> None:
    first = ensure_productive_onboarding(db_session, **_args())
    assert first.created is True
    assert first.membership.legacy_role_label == "owner"
    after_create = _counts(db_session)
    second = ensure_productive_onboarding(db_session, **_args())
    assert second.created is False
    assert second.organization.id == first.organization.id
    assert second.establishment.id == first.establishment.id
    assert second.user.id == first.user.id
    assert second.identity.id == first.identity.id
    assert _counts(db_session) == after_create
    audits = list(
        db_session.scalars(
            select(AuditEvent).where(AuditEvent.event_type == "organization.onboarded")
        )
    )
    assert len(audits) == 1
    blob = json.dumps(audits[0].payload)
    assert audits[0].payload == {"created": True}
    assert "email" not in blob
    assert "token" not in blob
    assert "password" not in blob
    assert "@" not in blob
    assert not hasattr(first.user, "password")


def test_rejects_email_already_linked_to_another_person(db_session: Session) -> None:
    existing = helpers.user(db_session, "outra-pessoa@example.invalid")
    with pytest.raises(IdentityResolutionError) as caught:
        ensure_productive_onboarding(
            db_session, **_args(email="Outra-Pessoa@example.invalid", subject="subject-novo")
        )
    assert caught.value.reason == "email_ja_vinculado"
    assert "@" not in str(caught.value)
    identities = list(
        db_session.scalars(select(AuthIdentity).where(AuthIdentity.user_id == existing.id))
    )
    memberships = list(
        db_session.scalars(
            select(OrganizationMembership).where(OrganizationMembership.user_id == existing.id)
        )
    )
    assert identities == []
    assert memberships == []


def test_existing_owner_email_does_not_grant_another_identity(db_session: Session) -> None:
    created = ensure_productive_onboarding(db_session, **_args())
    with pytest.raises(IdentityResolutionError) as caught:
        ensure_productive_onboarding(
            db_session,
            **_args(subject="subject-sem-prova", organization_slug="outra-loja-email"),
        )
    assert caught.value.reason == "email_ja_vinculado"
    identities = list(
        db_session.scalars(select(AuthIdentity).where(AuthIdentity.user_id == created.user.id))
    )
    roles = list(
        db_session.scalars(
            select(OrganizationMembershipRole).where(
                OrganizationMembershipRole.organization_id == created.organization.id,
                OrganizationMembershipRole.revoked_at.is_(None),
            )
        )
    )
    assert len(identities) == 1
    assert [role.role for role in roles] == ["owner"]


def test_rejects_identity_linked_to_another_organization(db_session: Session) -> None:
    ensure_productive_onboarding(db_session, **_args())
    with pytest.raises(IdentityResolutionError) as caught:
        ensure_productive_onboarding(db_session, **_args(organization_slug="outra-loja"))
    assert caught.value.reason == "identidade_vinculada_a_outra_organizacao"


def test_rejects_slug_owned_by_someone_else(db_session: Session) -> None:
    ensure_productive_onboarding(db_session, **_args())
    with pytest.raises(IdentityResolutionError) as caught:
        ensure_productive_onboarding(
            db_session,
            **_args(
                issuer="https://idp.example.invalid",
                subject="subject-alheio",
                email="alheio@example.invalid",
            ),
        )
    assert caught.value.reason == "slug_indisponivel"


def test_rejects_confirmed_field_that_diverges(db_session: Session) -> None:
    created = ensure_productive_onboarding(db_session, **_args())
    with pytest.raises(IdentityResolutionError) as caught:
        ensure_productive_onboarding(db_session, **_args(legal_name="Outra razão"))
    assert caught.value.reason == "dados_confirmados_divergem"
    rows = list(
        db_session.scalars(
            select(Establishment).where(Establishment.organization_id == created.organization.id)
        )
    )
    assert len(rows) == 1


def test_rejects_blank_identity_without_writing(db_session: Session) -> None:
    before = _counts(db_session)
    with pytest.raises(IdentityResolutionError) as caught:
        ensure_productive_onboarding(db_session, **_args(issuer="  ", subject=""))
    assert caught.value.reason == "identidade_invalida"
    assert _counts(db_session) == before


def _unique_args(**overrides: str) -> dict[str, str]:
    token = uuid4().hex[:10]
    base = _args(
        subject=f"subject-{token}",
        email=f"owner-{token}@example.invalid",
        organization_slug=f"loja-{token}",
        establishment_code=f"LOJA-{token}",
    )
    base.update(overrides)
    return base


def _run_pair(engine, first: dict[str, str], second: dict[str, str]):
    outcomes: list[tuple[str, object]] = []
    barrier = threading.Barrier(2)

    def run(args: dict[str, str]) -> None:
        session = sessionmaker(bind=engine, future=True)()
        try:
            barrier.wait(timeout=15)
            result = ensure_productive_onboarding(session, **args)
            snapshot = (
                result.created,
                result.organization.id,
                result.establishment.id,
                result.user.id,
                result.membership.id,
                result.identity.id,
            )
            session.commit()
            outcomes.append(("ok", snapshot))
        except IdentityResolutionError as caught:
            session.rollback()
            outcomes.append(("conflict", caught.reason))
        except Exception as caught:
            session.rollback()
            outcomes.append(("raw", type(caught).__name__))
        finally:
            session.close()

    threads = [threading.Thread(target=run, args=(first,)), threading.Thread(target=run, args=(second,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()
    assert all(kind != "raw" for kind, _ in outcomes)
    assert not any(isinstance(payload, str) and payload == "IntegrityError" for _, payload in outcomes)
    return outcomes


def _org_shape(session: Session, organization_id) -> dict[str, int]:
    return {
        "establishment": int(
            session.scalar(
                select(func.count())
                .select_from(Establishment)
                .where(Establishment.organization_id == organization_id)
            )
            or 0
        ),
        "membership": int(
            session.scalar(
                select(func.count())
                .select_from(OrganizationMembership)
                .where(OrganizationMembership.organization_id == organization_id)
            )
            or 0
        ),
        "owner": int(
            session.scalar(
                select(func.count())
                .select_from(OrganizationMembershipRole)
                .where(
                    OrganizationMembershipRole.organization_id == organization_id,
                    OrganizationMembershipRole.role == "owner",
                    OrganizationMembershipRole.revoked_at.is_(None),
                )
            )
            or 0
        ),
        "audit": int(
            session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.organization_id == organization_id,
                    AuditEvent.event_type == "organization.onboarded",
                )
            )
            or 0
        ),
    }


def test_concurrent_same_data_returns_one_organization(engine) -> None:
    args = _unique_args()
    outcomes = _run_pair(engine, args, args)
    assert [kind for kind, _ in outcomes] == ["ok", "ok"]
    created_flags = [payload[0] for _, payload in outcomes]
    assert created_flags.count(True) == 1
    assert created_flags.count(False) == 1
    ids = {payload[1:] for _, payload in outcomes}
    assert len(ids) == 1
    org_id = next(iter(ids))[0]
    check = sessionmaker(bind=engine, future=True)()
    try:
        assert _org_shape(check, org_id) == {
            "establishment": 1,
            "membership": 1,
            "owner": 1,
            "audit": 1,
        }
        identity_count = check.scalar(
            select(func.count())
            .select_from(AuthIdentity)
            .where(AuthIdentity.subject == args["subject"])
        )
        assert identity_count == 1
        audit = check.scalar(
            select(AuditEvent).where(
                AuditEvent.organization_id == org_id,
                AuditEvent.event_type == "organization.onboarded",
            )
        )
        blob = json.dumps(audit.payload)
        assert "@" not in blob
        assert "token" not in blob
        assert "password" not in blob
    finally:
        check.close()


def test_concurrent_same_email_different_identity_does_not_attach(engine) -> None:
    email = f"shared-{uuid4().hex[:8]}@example.invalid"
    first = _unique_args(email=email)
    second = _unique_args(email=email)
    outcomes = _run_pair(engine, first, second)
    kinds = sorted(kind for kind, _ in outcomes)
    assert kinds == ["conflict", "ok"]
    assert any(payload == "email_ja_vinculado" for kind, payload in outcomes if kind == "conflict")
    check = sessionmaker(bind=engine, future=True)()
    try:
        users = list(check.scalars(select(AppUser).where(func.lower(AppUser.email) == email.lower())))
        assert len(users) == 1
        identities = list(
            check.scalars(select(AuthIdentity).where(AuthIdentity.user_id == users[0].id))
        )
        assert len(identities) == 1
        assert identities[0].subject in {first["subject"], second["subject"]}
    finally:
        check.close()


def test_concurrent_same_slug_different_owners(engine) -> None:
    slug = f"loja-{uuid4().hex[:8]}"
    first = _unique_args(organization_slug=slug)
    second = _unique_args(organization_slug=slug)
    outcomes = _run_pair(engine, first, second)
    assert sorted(kind for kind, _ in outcomes) == ["conflict", "ok"]
    assert any(payload == "slug_indisponivel" for kind, payload in outcomes if kind == "conflict")
    check = sessionmaker(bind=engine, future=True)()
    try:
        orgs = list(check.scalars(select(Organization).where(Organization.slug == slug)))
        assert len(orgs) == 1
        assert _org_shape(check, orgs[0].id)["owner"] == 1
    finally:
        check.close()


def test_concurrent_divergent_confirmed_data(engine) -> None:
    base = _unique_args()
    other = dict(base)
    other["legal_name"] = "Outra razão social"
    outcomes = _run_pair(engine, base, other)
    assert sorted(kind for kind, _ in outcomes) == ["conflict", "ok"]
    assert any(
        payload == "dados_confirmados_divergem" for kind, payload in outcomes if kind == "conflict"
    )
    check = sessionmaker(bind=engine, future=True)()
    try:
        orgs = list(
            check.scalars(select(Organization).where(Organization.slug == base["organization_slug"]))
        )
        assert len(orgs) == 1
        assert orgs[0].legal_name in {base["legal_name"], other["legal_name"]}
        assert _org_shape(check, orgs[0].id)["establishment"] == 1
    finally:
        check.close()


def test_rollback_leaves_no_partial_onboarding(engine) -> None:
    args = _unique_args()
    session = sessionmaker(bind=engine, future=True)()
    try:
        ensure_productive_onboarding(session, **args)
        session.rollback()
    finally:
        session.close()
    check = sessionmaker(bind=engine, future=True)()
    try:
        assert (
            check.scalar(select(Organization.id).where(Organization.slug == args["organization_slug"]))
            is None
        )
        assert (
            check.scalar(select(AppUser.id).where(func.lower(AppUser.email) == args["email"].lower()))
            is None
        )
    finally:
        check.close()


def test_failed_email_conflict_can_commit_without_partial_rows(engine) -> None:
    email = f"legado-{uuid4().hex[:8]}@example.invalid"
    setup = sessionmaker(bind=engine, future=True)()
    try:
        helpers.user(setup, email)
        setup.commit()
    finally:
        setup.close()
    args = _unique_args(email=email)
    session = sessionmaker(bind=engine, future=True)()
    try:
        with pytest.raises(IdentityResolutionError) as caught:
            ensure_productive_onboarding(session, **args)
        assert caught.value.reason == "email_ja_vinculado"
        session.commit()
    finally:
        session.close()
    check = sessionmaker(bind=engine, future=True)()
    try:
        assert (
            check.scalar(select(Organization.id).where(Organization.slug == args["organization_slug"]))
            is None
        )
        assert (
            check.scalar(select(AuthIdentity.id).where(AuthIdentity.subject == args["subject"]))
            is None
        )
    finally:
        check.close()


def test_controlled_conflict_is_not_a_raw_integrity_error() -> None:
    assert not issubclass(IdentityResolutionError, IntegrityError)
