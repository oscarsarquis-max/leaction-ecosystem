"""Organization Profile — persistence, PATCH, and tenant isolation."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app


def _headers(sub: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _create_org(client: TestClient, sub: str, name: str | None = None) -> str:
    r = client.post(
        "/api/v1/organizations",
        json={"name": name or f"Profile Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def test_get_creates_empty_profile_and_patch_partial():
    client = TestClient(app)
    sub = f"prof-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)

    first = client.get("/api/v1/organizations/current/profile", headers=h)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["organization_id"] == org_id
    assert body["trade_name"] == ""
    assert body["certification_status"] == "unknown"
    assert body["quality_structure"] == "unknown"
    assert body["unit_count"] is None

    patched = client.patch(
        "/api/v1/organizations/current/profile",
        headers=h,
        json={
            "trade_name": "Acme Diagnóstico",
            "industry": "Saúde",
            "business_model": "b2b",
            "employee_range": "51-200",
            "unit_count": 3,
            "certification_status": "in_progress",
            "quality_structure": "formal_partial",
            "summary": "Laboratório regional",
        },
    )
    assert patched.status_code == 200, patched.text
    p = patched.json()
    assert p["trade_name"] == "Acme Diagnóstico"
    assert p["industry"] == "Saúde"
    assert p["business_model"] == "b2b"
    assert p["employee_range"] == "51-200"
    assert p["unit_count"] == 3
    assert p["legal_name"] == ""

    partial = client.patch(
        "/api/v1/organizations/current/profile",
        headers=h,
        json={"legal_name": "Acme Diagnóstico Ltda"},
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["legal_name"] == "Acme Diagnóstico Ltda"
    assert partial.json()["trade_name"] == "Acme Diagnóstico"


def test_profile_rejects_organization_id_in_body():
    client = TestClient(app)
    sub = f"prof-id-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)

    bad = client.patch(
        "/api/v1/organizations/current/profile",
        headers=h,
        json={
            "organization_id": str(uuid.uuid4()),
            "trade_name": "Hacker",
        },
    )
    assert bad.status_code == 422


def test_profile_http_isolation_between_orgs():
    client = TestClient(app)
    sub_a = f"prof-a-{uuid.uuid4()}"
    sub_b = f"prof-b-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a, "Org Profile A")
    org_b = _create_org(client, sub_b, "Org Profile B")
    ha = _headers(sub_a, org_a)
    hb = _headers(sub_b, org_b)

    client.patch(
        "/api/v1/organizations/current/profile",
        headers=ha,
        json={"trade_name": "Only A"},
    )
    client.patch(
        "/api/v1/organizations/current/profile",
        headers=hb,
        json={"trade_name": "Only B"},
    )

    assert client.get("/api/v1/organizations/current/profile", headers=ha).json()[
        "trade_name"
    ] == "Only A"
    assert client.get("/api/v1/organizations/current/profile", headers=hb).json()[
        "trade_name"
    ] == "Only B"

    # User A cannot read B by swapping header without membership
    denied = client.get("/api/v1/organizations/current/profile", headers=_headers(sub_a, org_b))
    assert denied.status_code == 403


def test_profile_rls_uniqueness_and_isolation(app_engine, admin_engine, two_orgs):
    org_a = two_orgs["org_a"]
    org_b = two_orgs["org_b"]

    with admin_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO organization_profiles (organization_id, trade_name)
                VALUES (:a, 'A'), (:b, 'B')
                ON CONFLICT (organization_id) DO UPDATE
                  SET trade_name = EXCLUDED.trade_name
                """
            ),
            {"a": org_a, "b": org_b},
        )

    with admin_engine.connect() as conn:
        with conn.begin():
            with pytest.raises(Exception):
                conn.execute(
                    text(
                        """
                        INSERT INTO organization_profiles (organization_id, trade_name)
                        VALUES (:a, 'dup')
                        """
                    ),
                    {"a": org_a},
                )

    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(org_a)},
        )
        names = conn.execute(
            text("SELECT trade_name FROM organization_profiles")
        ).scalars().all()
        assert names == ["A"]

        n_other = conn.execute(
            text(
                "UPDATE organization_profiles SET trade_name = 'leak' WHERE organization_id = :b"
            ),
            {"b": org_b},
        ).rowcount
        assert n_other == 0
        conn.commit()

    with admin_engine.connect() as conn:
        b_name = conn.execute(
            text(
                "SELECT trade_name FROM organization_profiles WHERE organization_id = :b"
            ),
            {"b": org_b},
        ).scalar_one()
        assert b_name == "B"

    with admin_engine.begin() as conn:
        conn.execute(
            text("DELETE FROM organization_profiles WHERE organization_id IN (:a, :b)"),
            {"a": org_a, "b": org_b},
        )
