"""OpenAPI contract gates — validity, operationIds, errors, path policy, drift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.openapi_contract import dump_openapi_json

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi" / "openapi.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    app.openapi_schema = None
    return json.loads(dump_openapi_json(app))


def test_openapi_document_is_valid_v3(schema: dict):
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "QMind API"
    assert schema["info"]["version"] == "1.0.0"
    assert "paths" in schema and schema["paths"]
    assert "components" in schema
    assert "ErrorBody" in schema["components"]["schemas"]
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    props = schema["components"]["schemas"]["ErrorBody"]["properties"]
    assert set(props) >= {"code", "message", "correlation_id", "field_errors"}
    assert "details" not in props


def test_operation_ids_unique_and_stable(schema: dict):
    seen: dict[str, str] = {}
    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            if method.startswith("x-"):
                continue
            op_id = op.get("operationId")
            assert op_id, f"missing operationId on {method.upper()} {path}"
            assert op_id not in seen, f"duplicate operationId {op_id}: {seen[op_id]} vs {method} {path}"
            seen[op_id] = f"{method.upper()} {path}"
            # Stable camelCase / verbNoun style
            assert op_id[0].islower() or op_id.startswith("get"), op_id
    assert len(seen) >= 40


def test_no_anonymous_problematic_inline_error_schemas(schema: dict):
    """Error responses should $ref ErrorBody, not huge anonymous blobs."""
    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            if method.startswith("x-"):
                continue
            for code, resp in (op.get("responses") or {}).items():
                if code in {"400", "401", "403", "404", "409", "410", "422", "503"}:
                    content = (resp.get("content") or {}).get("application/json") or {}
                    sc = content.get("schema") or {}
                    assert "$ref" in sc or sc.get("title") == "ErrorBody", (
                        f"{method} {path} {code} should ref ErrorBody, got {sc}"
                    )


def test_error_responses_coverage(schema: dict):
    for path, methods in schema["paths"].items():
        if path in ("/health", "/ready"):
            continue
        for method, op in methods.items():
            if method.startswith("x-"):
                continue
            responses = op.get("responses") or {}
            # Contract injects standard errors for every tenant operation.
            assert "401" in responses or "403" in responses or "404" in responses
            assert "422" in responses or method == "get" or method == "delete"


def test_paths_only_api_v1_plus_health(schema: dict):
    for path in schema["paths"]:
        assert path in ("/health", "/ready") or path.startswith("/api/v1"), path
    assert "/" not in schema["paths"]


def test_security_and_org_header_documented(schema: dict):
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    tenant_path = "/api/v1/assessments"
    get_op = schema["paths"][tenant_path]["get"]
    assert get_op["security"] == [{"BearerAuth": []}]
    names = {p["name"] for p in get_op.get("parameters", []) if isinstance(p, dict)}
    assert "X-Organization-Id" in names
    assert "limit" in names
    # create org has no org header requirement in path list
    create_org = schema["paths"]["/api/v1/organizations"]["post"]
    assert any(
        p.get("name") == "Idempotency-Key" for p in create_org.get("parameters", []) if isinstance(p, dict)
    )


def test_state_machine_enums_in_components(schema: dict):
    names = set(schema["components"]["schemas"])
    # Pydantic may name enums AssessmentStatus, etc.
    enum_hits = [n for n in names if "Status" in n or n in {"FindingType", "ActionKind", "Applicability"}]
    assert len(enum_hits) >= 5, names


def test_committed_openapi_matches_generated():
    assert OPENAPI_PATH.is_file(), "Run scripts/export_openapi.py before commit"
    app.openapi_schema = None
    generated = dump_openapi_json(app)
    committed = OPENAPI_PATH.read_text(encoding="utf-8")
    assert generated == committed, "OpenAPI drift — run python scripts/export_openapi.py"


def test_error_body_runtime_shape_no_details():
    client = TestClient(app)
    # Missing auth → uniform ErrorBody
    r = client.get("/api/v1/assessments", headers={"X-Organization-Id": "00000000-0000-4000-8000-000000000001"})
    assert r.status_code in (401, 403, 404)
    body = r.json()
    assert "code" in body and "message" in body and "correlation_id" in body
    assert "details" not in body
    # Validation → field_errors
    bad = client.post(
        "/api/v1/organizations",
        json={"name": ""},
        headers={"X-Dev-User-Sub": "openapi-val", "X-Dev-User-Email": "o@ex.com"},
    )
    assert bad.status_code == 422
    vb = bad.json()
    assert vb["code"] == "validation_error"
    assert vb.get("field_errors")
    assert "details" not in vb
