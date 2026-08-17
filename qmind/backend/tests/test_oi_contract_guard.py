"""OI contract compatibility + organization response guard (OI-011)."""

from __future__ import annotations

import copy
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.modules.oi.contract_compat import (
    DEFAULT_OI_SCHEMAS_DIR,
    check_contracts,
    compare_schemas,
    core_schema_for,
    irrelevant_metadata_only_diff_demo,
    load_json,
)
from app.modules.oi.schemas import OrganizationContextInput, OrganizationalInsights

ANALYZE = "/api/v1/organizations/current/intelligence/analyze"
RUNS = "/api/v1/organizations/current/intelligence/runs"


def _headers(sub: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _create_org(client: TestClient, sub: str) -> str:
    r = client.post(
        "/api/v1/organizations",
        json={"name": f"OI Guard Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _insights_payload(*, org_id: str, request_id: str, correlation_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "core_organization_id": org_id,
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
                "explanation": None,
            }
        ],
        "explanations": [],
        "metadata": None,
    }


def test_current_contracts_are_compatible() -> None:
    issues = check_contracts(oi_schemas_dir=DEFAULT_OI_SCHEMAS_DIR)
    assert issues == [], "\n".join(str(i) for i in issues)


def test_required_field_removal_is_detected() -> None:
    oi = load_json(DEFAULT_OI_SCHEMAS_DIR / "organizational-insights.schema.json")
    core = core_schema_for(OrganizationalInsights)
    mutated = copy.deepcopy(core)
    req = list(mutated.get("required") or [])
    assert "generated_at" in req
    mutated["required"] = [r for r in req if r != "generated_at"]
    issues = compare_schemas("OrganizationalInsights", oi, mutated)
    messages = [str(i) for i in issues]
    assert any("generated_at" in m and "missing in Core" in m for m in messages), messages


def test_type_mismatch_is_detected() -> None:
    oi = load_json(DEFAULT_OI_SCHEMAS_DIR / "organization-context-input.schema.json")
    core = core_schema_for(OrganizationContextInput)
    mutated = copy.deepcopy(core)
    mutated["properties"]["request_id"] = {"type": "integer"}
    issues = compare_schemas("OrganizationContextInput", oi, mutated)
    messages = [str(i) for i in issues]
    assert any("request_id" in m and "type mismatch" in m for m in messages), messages


def test_enum_mismatch_is_detected() -> None:
    oi = load_json(DEFAULT_OI_SCHEMAS_DIR / "organization-context-input.schema.json")
    core = core_schema_for(OrganizationContextInput)
    mutated = copy.deepcopy(core)
    facts = mutated["$defs"]["OrganizationProfileFacts"]
    bm = facts["properties"]["business_model"]
    enum_branch = next(b for b in bm["anyOf"] if "enum" in b)
    enum_branch["enum"] = [x for x in enum_branch["enum"] if x != "b2b"] + ["marketplace"]
    issues = compare_schemas("OrganizationContextInput", oi, mutated)
    messages = [str(i) for i in issues]
    assert any("business_model" in m and "enum incompatible" in m for m in messages), messages


def test_irrelevant_schema_metadata_does_not_fail() -> None:
    oi = load_json(DEFAULT_OI_SCHEMAS_DIR / "organizational-insights.schema.json")
    noisy = irrelevant_metadata_only_diff_demo(oi)
    core = core_schema_for(OrganizationalInsights)
    issues = compare_schemas("OrganizationalInsights", noisy, core)
    assert issues == [], "\n".join(str(i) for i in issues)


def test_matching_organization_id_is_accepted_and_persisted() -> None:
    client = TestClient(app)
    sub = f"oi-ok-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)

    def _fake(payload):
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=str(payload.core_organization_id),
                request_id=payload.request_id,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = _fake
        response = client.post(ANALYZE, headers=h)
    assert response.status_code == 200, response.text
    assert response.json()["core_organization_id"] == org_id
    runs = client.get(RUNS, headers=h).json()
    assert len(runs) == 1
    assert runs[0]["organization_id"] == org_id


def test_divergent_organization_id_is_rejected_and_not_persisted() -> None:
    client = TestClient(app)
    sub = f"oi-bad-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)
    before = client.get(RUNS, headers=h).json()
    foreign = str(uuid.uuid4())

    def _fake(payload):
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


def test_tenant_a_never_persists_result_identified_as_b() -> None:
    client = TestClient(app)
    sub_a = f"oi-ga-{uuid.uuid4()}"
    sub_b = f"oi-gb-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a)
    org_b = _create_org(client, sub_b)
    ha = _headers(sub_a, org_a)
    hb = _headers(sub_b, org_b)
    client.get("/api/v1/organizations/current/profile", headers=ha)
    client.get("/api/v1/organizations/current/profile", headers=hb)

    def _fake_as_b(payload):
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=org_b,
                request_id=payload.request_id,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_cls:
        mock_cls.return_value.analyze.side_effect = _fake_as_b
        response = client.post(ANALYZE, headers=ha)
    assert response.status_code == 502
    assert response.json()["code"] == "oi_organization_mismatch"
    assert client.get(RUNS, headers=ha).json() == []
    assert client.get(RUNS, headers=hb).json() == []
