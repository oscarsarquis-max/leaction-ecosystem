"""Core → OI HTTP integration (OI-009) — mocked HTTP boundary."""

from __future__ import annotations

import ast
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.errors import AppError
from app.main import app
from app.modules.oi.client import ANALYZE_PATH, OrganizationalIntelligenceClient
from app.modules.oi.context_builder import build_organization_context_input
from app.modules.oi.schemas import OrganizationContextInput, OrganizationalInsights
from app.modules.orgs.schemas import OrganizationProfileOut

ENDPOINT = "/api/v1/organizations/current/intelligence/analyze"
WHEN = datetime(2026, 8, 17, 18, 0, 0, tzinfo=UTC)
ORG = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


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
        json={"name": name or f"OI Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _empty_profile(org_id: UUID) -> OrganizationProfileOut:
    return OrganizationProfileOut(
        organization_id=org_id,
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


def _partial_profile(org_id: UUID) -> OrganizationProfileOut:
    p = _empty_profile(org_id)
    return p.model_copy(
        update={
            "trade_name": "Padaria Central",
            "industry": "Alimentos",
            "business_model": "b2c",
        }
    )


def _full_profile(org_id: UUID) -> OrganizationProfileOut:
    return OrganizationProfileOut(
        organization_id=org_id,
        trade_name="Acme Diagnóstico",
        legal_name="Acme Diagnóstico Ltda",
        summary="Laboratório regional",
        industry="Saúde",
        business_model="b2b",
        employee_range="51-200",
        unit_count=3,
        certification_status="in_progress",
        quality_structure="formal_partial",
        created_at=WHEN,
        updated_at=WHEN,
    )


def _insights_payload(*, org_id: UUID, request_id: str, correlation_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "core_organization_id": str(org_id),
        "request_id": request_id,
        "correlation_id": correlation_id,
        "generated_at": "2026-08-17T18:00:00Z",
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
                    "supporting_facts": [],
                    "mechanism_version": "oi-alpha-1",
                },
            }
        ],
        "explanations": [],
        "metadata": None,
    }


def test_profile_maps_to_organization_context_input() -> None:
    profile = _full_profile(ORG)
    envelope = build_organization_context_input(
        profile,
        core_organization_id=ORG,
        request_id="req-map",
        correlation_id="corr-map",
        occurred_at=WHEN,
        environment="local",
    )
    assert isinstance(envelope, OrganizationContextInput)
    assert envelope.schema_version == "1.0"
    assert envelope.core_organization_id == ORG
    assert envelope.request_id == "req-map"
    assert envelope.correlation_id == "corr-map"
    assert envelope.occurred_at == WHEN
    assert envelope.source.system == "qmind-core"
    assert envelope.source.component == "organizational-intelligence"
    assert envelope.context.organization is None
    assert envelope.context.profile is not None
    assert envelope.context.profile.trade_name == "Acme Diagnóstico"
    assert envelope.context.profile.unit_count == 3
    assert envelope.context.profile.certification_status == "in_progress"


def test_partial_and_empty_profile_mapping() -> None:
    empty = build_organization_context_input(
        _empty_profile(ORG),
        core_organization_id=ORG,
        request_id="r1",
        correlation_id="c1",
        occurred_at=WHEN,
    )
    assert empty.context.profile is not None
    assert empty.context.profile.trade_name == ""
    assert empty.context.profile.certification_status == "unknown"
    assert empty.context.profile.unit_count is None

    partial = build_organization_context_input(
        _partial_profile(ORG),
        core_organization_id=ORG,
        request_id="r2",
        correlation_id="c2",
        occurred_at=WHEN,
    )
    assert partial.context.profile is not None
    assert partial.context.profile.trade_name == "Padaria Central"
    assert partial.context.profile.legal_name == ""
    assert partial.context.profile.business_model == "b2c"


def test_client_posts_correct_path_and_deserializes() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    payload = build_organization_context_input(
        _full_profile(ORG),
        core_organization_id=ORG,
        request_id="req-http",
        correlation_id="corr-http",
        occurred_at=WHEN,
    )
    response_json = _insights_payload(
        org_id=ORG, request_id="req-http", correlation_id="corr-http"
    )
    mock_response = httpx.Response(200, json=response_json)

    with patch("app.modules.oi.client.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        result = OrganizationalIntelligenceClient(settings).analyze(payload)

    mock_cls.assert_called_once()
    assert mock_cls.call_args.kwargs["timeout"] == settings.qmind_oi_timeout_seconds
    args, kwargs = mock_client.post.call_args
    assert args[0] == f"{settings.qmind_oi_base_url.rstrip('/')}{ANALYZE_PATH}"
    assert kwargs["json"]["core_organization_id"] == str(ORG)
    assert kwargs["json"]["context"]["profile"]["trade_name"] == "Acme Diagnóstico"
    assert isinstance(result, OrganizationalInsights)
    assert result.core_organization_id == ORG
    assert len(result.insights) == 1
    assert result.insights[0].type == "CONTEXT"


def test_client_timeout_raises_controlled_error() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    payload = build_organization_context_input(
        _empty_profile(ORG),
        core_organization_id=ORG,
        request_id="req-to",
        correlation_id="corr-to",
        occurred_at=WHEN,
    )
    with patch("app.modules.oi.client.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.TimeoutException("slow")
        with pytest.raises(AppError) as ei:
            OrganizationalIntelligenceClient(settings).analyze(payload)
    assert ei.value.code == "oi_timeout"
    assert ei.value.status_code == 504


def test_client_http_error_raises_controlled_error() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    payload = build_organization_context_input(
        _empty_profile(ORG),
        core_organization_id=ORG,
        request_id="req-err",
        correlation_id="corr-err",
        occurred_at=WHEN,
    )
    with patch("app.modules.oi.client.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = httpx.Response(500, json={"detail": "boom"})
        with pytest.raises(AppError) as ei:
            OrganizationalIntelligenceClient(settings).analyze(payload)
    assert ei.value.code == "oi_error"
    assert ei.value.status_code == 502


def test_endpoint_uses_org_context_and_preserves_insights() -> None:
    client = TestClient(app)
    sub = f"oi-ep-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.patch(
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
        },
    )

    captured: dict = {}

    def _fake_analyze(payload: OrganizationContextInput) -> OrganizationalInsights:
        captured["core_organization_id"] = payload.core_organization_id
        captured["trade_name"] = (
            payload.context.profile.trade_name if payload.context.profile else None
        )
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=payload.core_organization_id,
                request_id=payload.request_id,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.analyze.side_effect = _fake_analyze
        response = client.post(ENDPOINT, headers=h)

    assert response.status_code == 200, response.text
    assert str(captured["core_organization_id"]) == org_id
    assert captured["trade_name"] == "Acme Diagnóstico"
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["core_organization_id"] == org_id
    assert body["insights"][0]["type"] == "CONTEXT"


def test_endpoint_empty_profile_still_calls_oi() -> None:
    client = TestClient(app)
    sub = f"oi-empty-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)

    def _fake_analyze(payload: OrganizationContextInput) -> OrganizationalInsights:
        assert payload.context.profile is not None
        assert payload.context.profile.trade_name == ""
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=payload.core_organization_id,
                request_id=payload.request_id,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.analyze.side_effect = _fake_analyze
        response = client.post(ENDPOINT, headers=h)
    assert response.status_code == 200, response.text


def test_endpoint_isolation_between_organizations() -> None:
    client = TestClient(app)
    sub_a = f"oi-a-{uuid.uuid4()}"
    sub_b = f"oi-b-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a, "OI Org A")
    org_b = _create_org(client, sub_b, "OI Org B")
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

    seen: list[tuple[str, str | None]] = []

    def _fake_analyze(payload: OrganizationContextInput) -> OrganizationalInsights:
        trade = payload.context.profile.trade_name if payload.context.profile else None
        seen.append((str(payload.core_organization_id), trade))
        return OrganizationalInsights.model_validate(
            _insights_payload(
                org_id=payload.core_organization_id,
                request_id=payload.request_id,
                correlation_id=payload.correlation_id,
            )
        )

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.analyze.side_effect = _fake_analyze
        assert client.post(ENDPOINT, headers=ha).status_code == 200
        assert client.post(ENDPOINT, headers=hb).status_code == 200

    assert seen == [(org_a, "Only A"), (org_b, "Only B")]


def test_endpoint_propagates_oi_timeout() -> None:
    client = TestClient(app)
    sub = f"oi-to-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.analyze.side_effect = AppError(
            "oi_timeout", "QMind OI request timed out", status_code=504
        )
        response = client.post(ENDPOINT, headers=h)
    assert response.status_code == 504
    assert response.json()["code"] == "oi_timeout"


def test_endpoint_propagates_oi_http_error() -> None:
    client = TestClient(app)
    sub = f"oi-http-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    client.get("/api/v1/organizations/current/profile", headers=h)

    with patch(
        "app.modules.oi.service.OrganizationalIntelligenceClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.analyze.side_effect = AppError(
            "oi_error", "QMind OI returned a server error", status_code=502
        )
        response = client.post(ENDPOINT, headers=h)
    assert response.status_code == 502
    assert response.json()["code"] == "oi_error"


def test_oi_module_has_no_qmind_oi_imports() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "modules" / "oi"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("qmind_oi"), path
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith("qmind_oi"), path
