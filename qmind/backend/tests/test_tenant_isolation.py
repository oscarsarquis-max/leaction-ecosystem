"""Isolation between two organizations (RLS via qmind_app + app.organization_id)."""

from __future__ import annotations

import pytest
from sqlalchemy import text


def test_app_role_sees_only_current_org(app_engine, two_orgs):
    org_a = two_orgs["org_a"]
    org_b = two_orgs["org_b"]
    assess_a = two_orgs["assess_a"]
    assess_b = two_orgs["assess_b"]

    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.organization_id', :org, true)"), {"org": str(org_a)})
        rows = conn.execute(text("SELECT id FROM assessments ORDER BY created_at")).scalars().all()
        assert assess_a in rows
        assert assess_b not in rows

        conn.execute(text("SELECT set_config('app.organization_id', :org, true)"), {"org": str(org_b)})
        rows_b = conn.execute(text("SELECT id FROM assessments ORDER BY created_at")).scalars().all()
        assert assess_b in rows_b
        assert assess_a not in rows_b


def test_cannot_insert_cross_tenant_assessment_fk(app_engine, two_orgs):
    org_b = two_orgs["org_b"]
    assess_a = two_orgs["assess_a"]

    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.organization_id', :org, true)"), {"org": str(org_b)})
        with pytest.raises(Exception):
            conn.execute(
                text(
                    """
                    INSERT INTO assessment_scopes (organization_id, assessment_id, requirement_id)
                    SELECT :org, :assess, id FROM requirements LIMIT 1
                    """
                ),
                {"org": org_b, "assess": assess_a},
            )
            conn.commit()


def test_update_isolated_to_current_org(app_engine, two_orgs):
    org_a = two_orgs["org_a"]
    assess_a = two_orgs["assess_a"]
    assess_b = two_orgs["assess_b"]

    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.organization_id', :org, true)"), {"org": str(org_a)})
        n_own = conn.execute(
            text("UPDATE assessments SET status = 'planned' WHERE id = :id"),
            {"id": assess_a},
        ).rowcount
        n_other = conn.execute(
            text("UPDATE assessments SET status = 'planned' WHERE id = :id"),
            {"id": assess_b},
        ).rowcount
        conn.commit()
        assert n_own == 1
        assert n_other == 0


def test_delete_isolated_to_current_org(app_engine, admin_engine, two_orgs):
    org_a = two_orgs["org_a"]
    org_b = two_orgs["org_b"]

    with admin_engine.begin() as conn:
        model_id = conn.execute(text("SELECT id FROM assessment_models LIMIT 1")).scalar_one()
        sv_id = conn.execute(text("SELECT id FROM standard_versions LIMIT 1")).scalar_one()
        extra_a = conn.execute(
            text(
                """
                INSERT INTO assessments (organization_id, assessment_model_id, standard_version_id, type, status)
                VALUES (:org, :m, :sv, 'other', 'draft') RETURNING id
                """
            ),
            {"org": org_a, "m": model_id, "sv": sv_id},
        ).scalar_one()
        extra_b = conn.execute(
            text(
                """
                INSERT INTO assessments (organization_id, assessment_model_id, standard_version_id, type, status)
                VALUES (:org, :m, :sv, 'other', 'draft') RETURNING id
                """
            ),
            {"org": org_b, "m": model_id, "sv": sv_id},
        ).scalar_one()

    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.organization_id', :org, true)"), {"org": str(org_a)})
        n_own = conn.execute(text("DELETE FROM assessments WHERE id = :id"), {"id": extra_a}).rowcount
        n_other = conn.execute(text("DELETE FROM assessments WHERE id = :id"), {"id": extra_b}).rowcount
        conn.commit()
        assert n_own == 1
        assert n_other == 0

    with admin_engine.begin() as conn:
        still_b = conn.execute(
            text("SELECT count(*) FROM assessments WHERE id = :id"), {"id": extra_b}
        ).scalar_one()
        assert still_b == 1
        conn.execute(text("DELETE FROM assessments WHERE id = :id"), {"id": extra_b})


def test_admin_bypass_can_see_both(admin_engine, two_orgs):
    with admin_engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM assessments WHERE id IN (:a, :b)"),
            {"a": two_orgs["assess_a"], "b": two_orgs["assess_b"]},
        ).scalar_one()
        assert n == 2


def test_finding_conformity_rejects_insufficient_flag(admin_engine, two_orgs):
    org = two_orgs["org_a"]
    assess = two_orgs["assess_a"]
    with admin_engine.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES ('iso-test-user', 'iso-test@example.com', 'active')
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING id
                """
            )
        ).scalar_one()
        mem = conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, ARRAY['consultant_auditor'], 'active')
                ON CONFLICT (organization_id, user_id) DO UPDATE
                  SET roles = EXCLUDED.roles
                RETURNING id
                """
            ),
            {"org": org, "user": user_id},
        ).scalar_one()
        with pytest.raises(Exception):
            conn.execute(
                text(
                    """
                    INSERT INTO findings (
                      organization_id, assessment_id, finding_type, status,
                      title, body, insufficient_evidence, insufficient_evidence_rationale,
                      author_membership_id
                    ) VALUES (
                      :org, :assess, 'conformity', 'draft',
                      'Bad', 'body', true, 'should fail', :mem
                    )
                    """
                ),
                {"org": org, "assess": assess, "mem": mem},
            )


def test_qmind_app_has_no_bypass_rls(admin_engine):
    with admin_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'qmind_app'
                """
            )
        ).one()
        assert row.rolsuper is False
        assert row.rolbypassrls is False
