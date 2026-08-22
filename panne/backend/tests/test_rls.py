from uuid import uuid4

import pytest
from app.modules.identity_organization.authorization import (
    PERMISSION_COMPLIANCE_REVIEW,
    PERMISSION_IDENTITY_READ_ME,
    PERMISSION_PRODUCTION_ORDER_RELEASE,
    Association,
    AuthorizationError,
    Principal,
    permissions_for_role,
    require_permission,
)
from app.modules.identity_organization.rls_inventory import RLS_TABLES, UNMANAGED_TABLES
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from tests import helpers
from tests.rls_support import runtime_engine as build_runtime_engine


def _admin_session(engine: Engine):
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


@pytest.fixture
def runtime(engine: Engine):
    created = build_runtime_engine(engine)
    try:
        yield created
    finally:
        created.dispose()


def _set_context(connection, organization_id=None, user_id=None, issuer="", subject=""):
    connection.execute(
        text("SELECT set_config('app.current_organization_id', :v, true)"),
        {"v": "" if organization_id is None else str(organization_id)},
    )
    connection.execute(
        text("SELECT set_config('app.current_user_id', :v, true)"),
        {"v": "" if user_id is None else str(user_id)},
    )
    connection.execute(text("SELECT set_config('app.current_issuer', :v, true)"), {"v": issuer})
    connection.execute(text("SELECT set_config('app.current_subject', :v, true)"), {"v": subject})


def test_runtime_role_is_not_privileged(engine: Engine, runtime) -> None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
                "FROM pg_roles WHERE rolname = 'panne_runtime'"
            )
        ).one()
        owner = connection.execute(
            text(
                "SELECT COUNT(*) FROM pg_tables "
                "WHERE schemaname = 'public' AND tableowner = 'panne_runtime'"
            )
        ).scalar_one()
    assert row == (False, False, False, False)
    assert owner == 0


def test_rls_inventory_covers_organizational_tables(engine: Engine) -> None:
    with engine.connect() as connection:
        tables = set(
            connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
        )
        rls = {
            name: (enabled, forced)
            for name, enabled, forced in connection.execute(
                text(
                    "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
    assert UNMANAGED_TABLES <= tables
    missing = RLS_TABLES - tables
    assert not missing
    unclassified = tables - RLS_TABLES - UNMANAGED_TABLES
    assert not unclassified
    for table in RLS_TABLES:
        enabled, forced = rls[table]
        assert enabled is True
        assert forced is True
    assert rls["alembic_version"][0] is False


def test_isolation_and_org_id_immutable(engine: Engine, runtime) -> None:
    session = _admin_session(engine)
    org_a = helpers.org(session, f"rls-a-{uuid4().hex[:8]}")
    org_b = helpers.org(session, f"rls-b-{uuid4().hex[:8]}")
    user_a = helpers.user(session, f"rls-a-{uuid4().hex[:8]}@example.com")
    est_a = helpers.establishment(session, org_a, "A1")
    est_b = helpers.establishment(session, org_b, "B1")
    session.commit()
    session.close()

    with runtime.connect() as connection:
        trans = connection.begin()
        _set_context(connection, org_a.id, user_a.id)
        seen = connection.execute(text("SELECT id FROM establishment")).scalars().all()
        assert est_a.id in seen
        assert est_b.id not in seen
        updated = connection.execute(
            text("UPDATE establishment SET display_name = 'x' WHERE id = :id"),
            {"id": est_b.id},
        ).rowcount
        assert updated == 0
        with pytest.raises(Exception):
            connection.execute(
                text(
                    "INSERT INTO establishment (organization_id, code, display_name, status) "
                    "VALUES (:org, 'Z', 'Z', 'active')"
                ),
                {"org": org_b.id},
            )
        trans.rollback()

        trans = connection.begin()
        _set_context(connection, org_a.id, user_a.id)
        with pytest.raises(Exception):
            connection.execute(
                text("UPDATE establishment SET organization_id = :other WHERE id = :id"),
                {"other": org_b.id, "id": est_a.id},
            )
        trans.rollback()


def test_missing_and_invalid_context_deny(engine: Engine, runtime) -> None:
    session = _admin_session(engine)
    org = helpers.org(session, f"rls-deny-{uuid4().hex[:8]}")
    helpers.establishment(session, org, "D1")
    session.commit()
    session.close()

    with runtime.connect() as connection:
        trans = connection.begin()
        rows = connection.execute(text("SELECT id FROM establishment")).fetchall()
        assert rows == []
        with pytest.raises(Exception):
            connection.execute(
                text(
                    "INSERT INTO establishment (organization_id, code, display_name, status) "
                    "VALUES (:org, 'N', 'N', 'active')"
                ),
                {"org": org.id},
            )
        trans.rollback()

        trans = connection.begin()
        _set_context(connection, organization_id=None, user_id=None)
        connection.execute(
            text("SELECT set_config('app.current_organization_id', 'nao-uuid', true)")
        )
        rows = connection.execute(text("SELECT id FROM establishment")).fetchall()
        assert rows == []
        trans.rollback()


def test_reused_connection_does_not_leak_context(engine: Engine, runtime) -> None:
    session = _admin_session(engine)
    org = helpers.org(session, f"rls-leak-{uuid4().hex[:8]}")
    user = helpers.user(session, f"rls-leak-{uuid4().hex[:8]}@example.com")
    helpers.establishment(session, org, "L1")
    session.commit()
    session.close()

    with runtime.connect() as connection:
        trans = connection.begin()
        _set_context(connection, org.id, user.id)
        assert connection.execute(text("SELECT count(*) FROM establishment")).scalar_one() == 1
        trans.commit()

        trans = connection.begin()
        leaked = connection.execute(text("SELECT count(*) FROM establishment")).scalar_one()
        assert leaked == 0
        trans.rollback()


def test_global_catalog_and_restricted_knowledge(engine: Engine, runtime) -> None:
    from app.modules.knowledge_grounding.models import KnowledgeSource

    session = _admin_session(engine)
    org = helpers.org(session, f"rls-k-{uuid4().hex[:8]}")
    user = helpers.user(session, f"rls-k-{uuid4().hex[:8]}@example.com")
    helpers.gram(session)
    restricted = KnowledgeSource(
        organization_id=None,
        source_kind="technical",
        authority_level="curated",
        title="restrito",
        release_state="restricted",
        status="active",
    )
    released = KnowledgeSource(
        organization_id=None,
        source_kind="technical",
        authority_level="curated",
        title="liberado",
        release_state="released",
        status="active",
    )
    private = KnowledgeSource(
        organization_id=org.id,
        source_kind="internal_document",
        authority_level="user_provided",
        title="privado",
        release_state="private",
        status="active",
    )
    session.add_all([restricted, released, private])
    session.commit()
    session.close()

    with runtime.connect() as connection:
        trans = connection.begin()
        _set_context(connection, org.id, user.id)
        units = connection.execute(text("SELECT count(*) FROM measurement_unit")).scalar_one()
        assert units >= 1
        titles = set(
            connection.execute(text("SELECT title FROM knowledge_source")).scalars().all()
        )
        assert "liberado" in titles
        assert "privado" in titles
        assert "restrito" not in titles
        with pytest.raises(Exception):
            connection.execute(
                text(
                    "INSERT INTO measurement_unit (code, name, dimension, si_factor, status) "
                    "VALUES ('xx', 'x', 'mass', 1, 'active')"
                )
            )
        trans.rollback()

        trans = connection.begin()
        units = connection.execute(text("SELECT count(*) FROM measurement_unit")).scalar_one()
        assert units == 0
        trans.rollback()


def _principal(role: str) -> Principal:
    association = Association(
        organization_id=uuid4(),
        status="active",
        permissions=permissions_for_role(role),
        roles=(role,),
    )
    return Principal(
        user_id=uuid4(),
        display_name=role,
        status="active",
        issuer="iss",
        subject="sub",
        associations=(association,),
        selected=association,
    )


def test_permission_matrix_is_explicit() -> None:
    owner = _principal("owner")
    baker = _principal("baker_operator")
    require_permission(owner, PERMISSION_IDENTITY_READ_ME)
    require_permission(owner, PERMISSION_COMPLIANCE_REVIEW)
    require_permission(baker, PERMISSION_IDENTITY_READ_ME)
    with pytest.raises(AuthorizationError):
        require_permission(baker, PERMISSION_COMPLIANCE_REVIEW)
    with pytest.raises(AuthorizationError):
        require_permission(_principal("restricted"), PERMISSION_IDENTITY_READ_ME)
    require_permission(owner, PERMISSION_PRODUCTION_ORDER_RELEASE)
    with pytest.raises(AuthorizationError):
        require_permission(baker, PERMISSION_PRODUCTION_ORDER_RELEASE)
    with pytest.raises(AuthorizationError):
        require_permission(_principal("technical_responsible"), PERMISSION_PRODUCTION_ORDER_RELEASE)
