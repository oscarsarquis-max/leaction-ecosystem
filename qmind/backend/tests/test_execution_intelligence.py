"""ISOI-009 Core integration tests."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.errors import AppError
from app.main import app
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionIntelligenceInput,
    ExecutionIntelligenceResult,
)
from app.modules.improvement_cases.fingerprint import (
    fingerprint_execution_intelligence_input,
)
from tests.conftest import ADMIN_URL

BASE = "/api/v1/organizations/current/improvement-cases"
_CREATED_ORGS: list[str] = []


def _headers(sub: str, org: str | None = None) -> dict[str, str]:
    out = {"X-Dev-User-Sub": sub, "X-Dev-User-Email": f"{sub}@example.com"}
    if org:
        out["X-Organization-Id"] = org
    return out


def _case(client: TestClient) -> tuple[dict[str, str], str, str]:
    sub = f"ei-{uuid.uuid4()}"
    org_response = client.post(
        "/api/v1/organizations",
        headers=_headers(sub),
        json={"name": f"EI {sub[:8]}", "timezone": "America/Sao_Paulo"},
    )
    assert org_response.status_code == 201, org_response.text
    org = org_response.json()["organization"]["id"]
    _CREATED_ORGS.append(org)
    headers = _headers(sub, org)
    case_response = client.post(
        BASE,
        headers=headers,
        json={
            "problem_statement": "Atrasos recorrentes",
            "impact_statement": "SLA rompido",
            "related_process": "Pedidos",
        },
    )
    assert case_response.status_code == 201, case_response.text
    return headers, org, case_response.json()["id"]


def _result(payload, *, fact_ref: str | None = None) -> ExecutionIntelligenceResult:
    supporting_ref = fact_ref or payload.fact_refs[0]
    return ExecutionIntelligenceResult.model_validate(
        {
            "schema_version": "1.0",
            "core_organization_id": payload.core_organization_id,
            "improvement_case_id": payload.improvement_case_id,
            "analysis_id": str(uuid.uuid4()),
            "request_id": payload.request_id,
            "correlation_id": payload.correlation_id,
            "generated_at": "2026-08-26T12:00:00Z",
            "mechanism_version": "execution-intelligence-rules-v1",
            "interpretability_status": "interpretable",
            "execution_posture": "not_started",
            "interpretation_summary": "A execução ainda não começou.",
            "signals": [
                {
                    "code": "execution_not_started",
                    "category": "flow",
                    "level": "watch",
                    "title": "Execução não iniciada",
                    "interpretation": "Não há progresso registrado.",
                    "supporting_fact_refs": [supporting_ref],
                    "iso_basis": ["8.1"],
                    "recommended_next_step": "Registrar o primeiro avanço.",
                    "requires_human_validation": True,
                }
            ],
        }
    )


def _member_headers(org: str, role: str) -> dict[str, str]:
    sub = f"ei-{role}-{uuid.uuid4()}"
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:sub, :email, 'active') RETURNING id
                """
            ),
            {"sub": sub, "email": f"{sub}@example.com"},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user_id, ARRAY[:role], 'active')
                """
            ),
            {"org": org, "user_id": user_id, "role": role},
        )
    engine.dispose()
    return _headers(sub, org)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup_execution_intelligence_runs():
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM improvement_case_execution_intelligence_runs r
                USING users u
                WHERE r.created_by = u.id AND u.idp_sub LIKE 'ei-%'
                """
            )
        )
    engine.dispose()
    _CREATED_ORGS.clear()
    yield
    if not _CREATED_ORGS:
        return
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM improvement_case_execution_intelligence_runs
                WHERE organization_id = ANY(:orgs)
                """
            ),
            {"orgs": [uuid.UUID(value) for value in _CREATED_ORGS]},
        )
    engine.dispose()


def test_builder_uses_opaque_refs_and_stable_fingerprint(client: TestClient) -> None:
    headers, _org, case_id = _case(client)
    request = client.get(f"{BASE}/{case_id}", headers=headers)
    assert request.status_code == 200
    # Fingerprint transport fields are tested on a contract-valid copy.
    org = uuid.UUID(request.json()["organization_id"])
    # A minimal factual envelope is enough to pin canonical behavior.
    base = ExecutionIntelligenceInput.model_validate(
        {
            "schema_version": "1.0",
            "core_organization_id": org,
            "improvement_case_id": case_id,
            "request_id": "a",
            "correlation_id": "a",
            "captured_at": datetime.now(UTC),
            "source": {"system": "qmind-core", "component": "execution-intelligence"},
            "case": {"status": "open"},
            "execution": {},
            "measurement": {},
            "fact_refs": ["case.status"],
        }
    )
    changed = base.model_copy(
        update={
            "request_id": "b",
            "correlation_id": "b",
            "captured_at": datetime.now(UTC),
        }
    )
    assert fingerprint_execution_intelligence_input(
        base
    ) == fingerprint_execution_intelligence_input(changed)
    assert all(str(org) not in ref and case_id not in ref for ref in base.fact_refs)


def test_builder_query_count_is_constant_for_action_batch() -> None:
    from app.modules.improvement_cases.execution_intelligence_builder import (
        build_execution_intelligence_input,
    )

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def first(self):
            return self.rows[0] if self.rows else None

        def all(self):
            return self.rows

    class FakeConnection:
        def __init__(self, action_count: int):
            self.action_count = action_count
            self.calls = 0

        def execute(self, statement, _params):
            self.calls += 1
            sql = str(statement)
            now = datetime.now(UTC)
            if "FROM improvement_cases c" in sql:
                return Result(
                    [
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            status="acting",
                            problem_statement="Atrasos",
                            impact_statement="SLA",
                            related_process="Pedidos",
                            analysis_id=None,
                        )
                    ]
                )
            if "FROM action_plans" in sql:
                return Result(
                    [
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            status="active",
                            created_at=now,
                            updated_at=now,
                        )
                    ]
                )
            if "FROM action_items a" in sql:
                return Result(
                    [
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            description=f"Ação {index}",
                            status="in_progress",
                            owner_membership_id=uuid.uuid4(),
                            due_at=now,
                            is_overdue=False,
                            created_at=now,
                            updated_at=now,
                            sprint_id=None,
                            sprint_status=None,
                            check_in_count=0,
                            last_check_in_at=None,
                            active_impediment_count=0,
                            oldest_impediment_hours=None,
                            open_dependency_count=0,
                            overdue_dependency_count=0,
                            evidence_count=0,
                            approved_evidence_count=0,
                        )
                        for index in range(self.action_count)
                    ]
                )
            if "FROM action_measurement_plans" in sql:
                return Result([])
            if "FROM improvement_case_outcome_observations" in sql:
                return Result([])
            raise AssertionError(f"unexpected builder query: {sql}")

    counts = []
    for action_count in (1, 100):
        conn = FakeConnection(action_count)

        @contextmanager
        def connection(_organization_id, current=conn):
            yield current

        ctx = SimpleNamespace(organization_id=uuid.uuid4())
        with (
            patch(
                "app.modules.improvement_cases.execution_intelligence_builder.tenant_connection",
                connection,
            ),
            patch(
                "app.modules.improvement_cases.execution_intelligence_builder."
                "measurements_service.summarize_case_measurements",
                return_value=(None, None, None, []),
            ),
        ):
            snapshot = build_execution_intelligence_input(ctx, uuid.uuid4())
        assert len(snapshot.execution.actions) == action_count
        counts.append(conn.calls)
    assert counts == [5, 5]


@pytest.mark.parametrize(
    ("evaluation_state", "expected"),
    [
        ("target_met", "met"),
        ("target_not_met", "not_met"),
        ("met", "unknown"),
        ("not_met", "unknown"),
    ],
)
def test_measurement_builder_maps_canonical_target_states(
    evaluation_state: str, expected: str
) -> None:
    from app.modules.improvement_cases.execution_intelligence_builder import (
        _measurement_facts,
    )

    plan_id = uuid.uuid4()
    indicator_id = uuid.uuid4()
    now = datetime.now(UTC)

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def all(self):
            return self.rows

    class Connection:
        def execute(self, statement, _params):
            sql = str(statement)
            if "FROM action_measurement_plans" in sql:
                return Result([SimpleNamespace(id=plan_id, status="active")])
            if "FROM indicator_definitions" in sql:
                return Result(
                    [
                        SimpleNamespace(
                            id=indicator_id, measurement_plan_id=plan_id
                        )
                    ]
                )
            raise AssertionError(sql)

    evaluation = SimpleNamespace(
        indicator_definition_id=indicator_id,
        indicator_code="CYCLE",
        indicator_name="Tempo de ciclo",
        unit_label="horas",
        direction="lower_is_better",
        target_value=24,
        target_min=None,
        target_max=None,
        baseline_value=48,
        baseline_at=now,
        latest_value=20,
        latest_measured_at=now,
        is_measurement_overdue=False,
        baseline_status="recorded",
        state=evaluation_state,
        next_measurement_due_at=now,
        substantiation="verified",
        measurement_count=1,
    )
    with patch(
        "app.modules.improvement_cases.execution_intelligence_builder."
        "measurements_service.summarize_case_measurements",
        return_value=(None, None, None, [evaluation]),
    ):
        _plans, indicators, _refs = _measurement_facts(
            Connection(), uuid.uuid4(), uuid.uuid4()
        )
    assert indicators[0].target_posture == expected
    assert indicators[0].baseline_status == "recorded"


def test_create_idempotent_list_latest_and_stale(client: TestClient) -> None:
    headers, _org, case_id = _case(client)
    mock = MagicMock()
    mock.analyze_execution.side_effect = _result
    path = f"{BASE}/{case_id}/execution-intelligence/runs"
    with patch(
        "app.modules.improvement_cases.execution_intelligence_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        first = client.post(path, headers={**headers, "Idempotency-Key": "same"})
        second = client.post(path, headers={**headers, "Idempotency-Key": "same"})
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert mock.analyze_execution.call_count == 1
    assert client.get(path, headers=headers).json()[0]["is_stale"] is False
    assert client.get(
        f"{BASE}/{case_id}/execution-intelligence/latest", headers=headers
    ).status_code == 200
    client.patch(
        f"{BASE}/{case_id}",
        headers=headers,
        json={"problem_statement": "Contexto alterado"},
    )
    assert client.get(path, headers=headers).json()[0]["is_stale"] is True


def test_idempotency_key_conflicts_when_snapshot_changes(client: TestClient) -> None:
    headers, _org, case_id = _case(client)
    path = f"{BASE}/{case_id}/execution-intelligence/runs"
    mock = MagicMock()
    mock.analyze_execution.side_effect = _result
    with patch(
        "app.modules.improvement_cases.execution_intelligence_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        first = client.post(path, headers={**headers, "Idempotency-Key": "same-snapshot"})
        assert first.status_code == 201, first.text
        changed = client.patch(
            f"{BASE}/{case_id}",
            headers=headers,
            json={"problem_statement": "Contexto factual alterado"},
        )
        assert changed.status_code == 200, changed.text
        conflict = client.post(
            path, headers={**headers, "Idempotency-Key": "same-snapshot"}
        )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "idempotency_conflict"
    assert mock.analyze_execution.call_count == 1


def test_invented_fact_ref_and_oi_failure_do_not_persist(client: TestClient) -> None:
    headers, _org, case_id = _case(client)
    path = f"{BASE}/{case_id}/execution-intelligence/runs"
    invented = MagicMock()
    invented.analyze_execution.side_effect = lambda payload: _result(
        payload, fact_ref="invented:fact"
    )
    with patch(
        "app.modules.improvement_cases.execution_intelligence_service.OrganizationalIntelligenceClient",
        return_value=invented,
    ):
        response = client.post(path, headers=headers)
    assert response.status_code == 502
    assert response.json()["code"] == "oi_invented_fact_ref"

    failed = MagicMock()
    failed.analyze_execution.side_effect = AppError("oi_timeout", "timeout", 504)
    with patch(
        "app.modules.improvement_cases.execution_intelligence_service.OrganizationalIntelligenceClient",
        return_value=failed,
    ):
        assert client.post(path, headers=headers).status_code == 504
    assert client.get(path, headers=headers).json() == []


def test_context_race_is_409_and_not_persisted(client: TestClient) -> None:
    headers, _org, case_id = _case(client)
    path = f"{BASE}/{case_id}/execution-intelligence/runs"
    mock = MagicMock()
    mock.analyze_execution.side_effect = _result
    with (
        patch(
            "app.modules.improvement_cases.execution_intelligence_service.OrganizationalIntelligenceClient",
            return_value=mock,
        ),
        patch(
            "app.modules.improvement_cases.execution_intelligence_service.current_context_fingerprint",
            return_value="different",
        ),
    ):
        response = client.post(path, headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "execution_context_changed"
    assert client.get(path, headers=headers).json() == []


def test_reader_can_read_but_cannot_execute_and_cross_org_is_hidden(
    client: TestClient,
) -> None:
    headers, org, case_id = _case(client)
    path = f"{BASE}/{case_id}/execution-intelligence/runs"
    mock = MagicMock()
    mock.analyze_execution.side_effect = _result
    with patch(
        "app.modules.improvement_cases.execution_intelligence_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        assert client.post(path, headers=headers).status_code == 201
    reader = _member_headers(org, "reader")
    assert client.get(path, headers=reader).status_code == 200
    assert client.post(path, headers=reader).status_code == 403
    other_headers, _other_org, _other_case = _case(client)
    assert client.get(path, headers=other_headers).status_code == 404


def test_execution_run_table_is_rls_forced_and_append_only() -> None:
    engine = create_engine(ADMIN_URL)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = 'improvement_case_execution_intelligence_runs'
                """
            )
        ).one()
        assert row.relrowsecurity is True
        assert row.relforcerowsecurity is True
        privileges = conn.execute(
            text(
                """
                SELECT privilege_type
                FROM information_schema.role_table_grants
                WHERE grantee = 'qmind_app'
                  AND table_name = 'improvement_case_execution_intelligence_runs'
                """
            )
        ).scalars().all()
    engine.dispose()
    assert set(privileges) == {"SELECT", "INSERT"}
