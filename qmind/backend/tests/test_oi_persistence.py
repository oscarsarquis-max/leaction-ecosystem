"""OI-010 — persist organizational intelligence runs (mocked OI HTTP)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.errors import AppError
from app.main import app
from app.modules.oi.client import OrganizationalIntelligenceClient
from app.modules.oi.context_builder import build_organization_context_input
from app.modules.oi.schemas import OrganizationContextInput, OrganizationalInsights
from app.modules.orgs.schemas import OrganizationProfileOut

ANALYZE = "/api/v1/organizations/current/intelligence/analyze"
RUNS = "/api/v1/organizations/current/intelligence/runs"
WHEN = datetime(2026, 8, 17, 19, 0, 0, tzinfo=UTC)


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
        json={"name": name or f"OI Run Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _insights_payload(*, org_id: str | UUID, request_id: str, correlation_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "core_organization_id": str(org_id),
        "request_id": request_id,
        "correlation_id": correlation_id,
        "generated_at": "2026-08-17T19:00:00Z",
        "insights": [
            {
                "insight_id": "insight-clause-4",
                "type": "CONTEXT",
                "title": "Context readiness",
                "summary": "Clause 4 assessment",
                "confidence": 0.5,
                "evidence_refs": [],
                "explanation": {
                    "reasons": ["priority:LOW"],
                    "evidence_refs": [],
                    "supporting_facts": ["unit_count present"],
                    "mechanism_version": "oi-alpha-1",
                },
            }
        ],
        "explanations": [],
        "metadata": {"producer_version": "oi-0.0.1", "environment": "local"},
    }


def _fake_analyze_factory(org_id: str, *, request_id: str | None = None):
    def _fake(payload: OrganizationContextInput) -> OrganizationalInsights:
        rid = request_id or payload.request_id
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=org_id,
                request_id=rid,
                correlation_id=payload.correlation_id,
            )
        )

    return _fake


def test_successful_analyze_creates_run_and_preserves_envelope() -> None:
    client = TestClient(app)
    sub = f"oi-persist-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = _fake_analyze_factory(org_id)
        response = client.post(ANALYZE, headers=h)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["insights"][0]["explanation"]["supporting_facts"] == ["unit_count present"]

    listed = client.get(RUNS, headers=h)
    assert listed.status_code == 200, listed.text
    runs = listed.json()
    assert len(runs) == 1
    run = runs[0]
    assert run["organization_id"] == org_id
    assert run["schema_version"] == "1.0"
    assert run["insights"]["core_organization_id"] == org_id
    assert run["insights"]["insights"][0]["type"] == "CONTEXT"
    assert run["insights"]["metadata"]["producer_version"] == "oi-0.0.1"

    detail = client.get(f"{RUNS}/{run['id']}", headers=h)
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == run["id"]
    assert detail.json()["insights"] == run["insights"]


def test_two_runs_history_newest_first() -> None:
    client = TestClient(app)
    sub = f"oi-hist-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)
    seq = {"n": 0}

    def _fake(payload: OrganizationContextInput) -> OrganizationalInsights:
        seq["n"] += 1
        rid = f"req-{seq['n']}"
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=org_id,
                request_id=rid,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = _fake
        assert client.post(ANALYZE, headers=h).status_code == 200
        assert client.post(ANALYZE, headers=h).status_code == 200

    runs = client.get(RUNS, headers=h).json()
    assert len(runs) >= 2
    assert runs[0]["created_at"] >= runs[1]["created_at"]
    assert runs[0]["request_id"] == "req-2"
    assert runs[1]["request_id"] == "req-1"


def test_organization_id_from_org_context_not_envelope_tenant() -> None:
    """Divergent OI core_organization_id is rejected (OI-011 guard) and not persisted."""
    client = TestClient(app)
    sub = f"oi-ctx-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)
    before = client.get(RUNS, headers=h).json()
    foreign = str(uuid.uuid4())

    def _fake(payload: OrganizationContextInput) -> OrganizationalInsights:
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=foreign,
                request_id=payload.request_id,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = _fake
        response = client.post(ANALYZE, headers=h)

    assert response.status_code == 502
    assert response.json()["code"] == "oi_organization_mismatch"
    assert client.get(RUNS, headers=h).json() == before


def test_http_isolation_tenant_a_cannot_read_tenant_b_runs() -> None:
    client = TestClient(app)
    sub_a = f"oi-ra-{uuid.uuid4()}"
    sub_b = f"oi-rb-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a, "OI Persist A")
    org_b = _create_org(client, sub_b, "OI Persist B")
    ha = _headers(sub_a, org_a)
    hb = _headers(sub_b, org_b)
    client.get("/api/v1/organizations/current/profile", headers=ha)
    client.get("/api/v1/organizations/current/profile", headers=hb)

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = _fake_analyze_factory(org_a)
        assert client.post(ANALYZE, headers=ha).status_code == 200
        mock_cls.return_value.analyze.side_effect = _fake_analyze_factory(org_b)
        assert client.post(ANALYZE, headers=hb).status_code == 200

    runs_a = client.get(RUNS, headers=ha).json()
    runs_b = client.get(RUNS, headers=hb).json()
    assert all(r["organization_id"] == org_a for r in runs_a)
    assert all(r["organization_id"] == org_b for r in runs_b)
    assert {r["id"] for r in runs_a}.isdisjoint({r["id"] for r in runs_b})

    foreign_id = runs_b[0]["id"]
    leak = client.get(f"{RUNS}/{foreign_id}", headers=ha)
    assert leak.status_code == 404


def test_oi_timeout_does_not_persist() -> None:
    client = TestClient(app)
    sub = f"oi-nto-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)
    before = client.get(RUNS, headers=h).json()

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = AppError(
            "oi_timeout", "QMind OI request timed out", status_code=504
        )
        response = client.post(ANALYZE, headers=h)
    assert response.status_code == 504
    assert client.get(RUNS, headers=h).json() == before


def test_oi_http_error_does_not_persist() -> None:
    client = TestClient(app)
    sub = f"oi-nhttp-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)
    before = len(client.get(RUNS, headers=h).json())

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = AppError(
            "oi_error", "QMind OI returned a server error", status_code=502
        )
        response = client.post(ANALYZE, headers=h)
    assert response.status_code == 502
    assert len(client.get(RUNS, headers=h).json()) == before


def test_invalid_oi_response_does_not_persist() -> None:
    client = TestClient(app)
    sub = f"oi-ninv-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)
    before = len(client.get(RUNS, headers=h).json())

    get_settings.cache_clear()
    settings = get_settings()
    profile = OrganizationProfileOut(
        organization_id=UUID(org_id),
        trade_name="",
        legal_name="",
        summary="",
        industry="",
        business_model="",
        employee_range="",
        unit_count=None,
        certification_status="unknown",
        quality_structure="unknown",
        created_at=WHEN,
        updated_at=WHEN,
    )
    payload = build_organization_context_input(
        profile,
        core_organization_id=UUID(org_id),
        request_id="req-bad",
        correlation_id="corr-bad",
        occurred_at=WHEN,
    )

    with patch("app.modules.oi.client.httpx.Client") as mock_cls:
        mock_http = mock_cls.return_value.__enter__.return_value
        mock_http.post.return_value = httpx.Response(200, json={"not": "an-envelope"})
        with pytest.raises(AppError) as ei:
            OrganizationalIntelligenceClient(settings).analyze(payload)
    assert ei.value.code == "oi_invalid_response"

    # Endpoint path: invalid response must not create a run.
    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_svc:
        mock_svc.return_value.analyze.side_effect = AppError(
            "oi_invalid_response",
            "QMind OI returned an invalid OrganizationalInsights payload",
            status_code=502,
        )
        assert client.post(ANALYZE, headers=h).status_code == 502
    assert len(client.get(RUNS, headers=h).json()) == before


def test_intelligence_runs_rls_isolation(app_engine, admin_engine, two_orgs) -> None:
    org_a = two_orgs["org_a"]
    org_b = two_orgs["org_b"]
    envelope_a = _insights_payload(org_id=org_a, request_id="r-a", correlation_id="c-a")
    envelope_b = _insights_payload(org_id=org_b, request_id="r-b", correlation_id="c-b")

    with admin_engine.begin() as conn:
        id_a = conn.execute(
            text(
                """
                INSERT INTO organization_intelligence_runs (
                  organization_id, schema_version, request_id, correlation_id,
                  generated_at, insights
                )
                VALUES (
                  :org, '1.0', 'r-a', 'c-a', :gen, CAST(:ins AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "org": org_a,
                "gen": WHEN,
                "ins": json.dumps(envelope_a),
            },
        ).scalar_one()
        id_b = conn.execute(
            text(
                """
                INSERT INTO organization_intelligence_runs (
                  organization_id, schema_version, request_id, correlation_id,
                  generated_at, insights
                )
                VALUES (
                  :org, '1.0', 'r-b', 'c-b', :gen, CAST(:ins AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "org": org_b,
                "gen": WHEN,
                "ins": json.dumps(envelope_b),
            },
        ).scalar_one()
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(org_a)},
        )
        ids = conn.execute(
            text("SELECT id FROM organization_intelligence_runs")
        ).scalars().all()
        assert id_a in ids
        assert id_b not in ids

        n_other = conn.execute(
            text(
                "UPDATE organization_intelligence_runs SET request_id = 'leak' WHERE id = :id"
            ),
            {"id": id_b},
        ).rowcount
        assert n_other == 0
        conn.commit()

    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM organization_intelligence_runs WHERE id IN (:a, :b)"
            ),
            {"a": id_a, "b": id_b},
        )
