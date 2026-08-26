"""ISOI-009 — live HTTP Core → QMind OI (no client mock).

Spawns a real uvicorn process for qmind-oi, points Core settings at it,
builds a case snapshot and persists an Execution Intelligence run.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.main import app
from tests.conftest import ADMIN_URL
from tests.test_execution_intelligence import _case

OI_ROOT = Path(r"C:\Projetos\qmind-oi")
OI_PYTHON = OI_ROOT / ".venv" / "Scripts" / "python.exe"
ENDPOINT = "/api/v1/organizations/current/improvement-cases"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_oi_base_url():
    if not OI_PYTHON.is_file():
        pytest.skip("qmind-oi venv missing")
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(OI_ROOT / "src")
    proc = subprocess.Popen(
        [
            str(OI_PYTHON),
            "-m",
            "uvicorn",
            "qmind_oi.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(OI_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                pytest.fail("qmind-oi process exited early")
            try:
                # OpenAPI docs always available on FastAPI
                r = httpx.get(f"{base}/openapi.json", timeout=1.0)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            proc.kill()
            pytest.fail("qmind-oi did not become ready")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_execution_intelligence_live_http_core_to_oi(live_oi_base_url, monkeypatch):
    """Seed case → Core builds input → real HTTP OI → Core persists result."""
    monkeypatch.setenv("QMIND_OI_BASE_URL", live_oi_base_url)
    get_settings.cache_clear()
    client = TestClient(app)
    headers, org, case_id = _case(client)

    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        actor = conn.execute(
            text(
                """
                SELECT m.id AS membership_id, m.user_id
                FROM memberships m
                WHERE m.organization_id = :org
                ORDER BY m.created_at
                LIMIT 1
                """
            ),
            {"org": uuid.UUID(org)},
        ).one()
        plan_id = conn.execute(
            text(
                """
                INSERT INTO action_plans (
                  organization_id, assessment_id, improvement_case_id, status
                ) VALUES (:org, NULL, :case_id, 'active')
                RETURNING id
                """
            ),
            {"org": uuid.UUID(org), "case_id": uuid.UUID(case_id)},
        ).scalar_one()
        action_id = conn.execute(
            text(
                """
                INSERT INTO action_items (
                  organization_id, action_plan_id, action_kind, description,
                  owner_membership_id, due_at, status, is_overdue
                ) VALUES (
                  :org, :plan, 'improvement', 'Reduzir atraso da fila',
                  :owner, :due_at, 'in_progress', true
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org),
                "plan": plan_id,
                "owner": actor.membership_id,
                "due_at": datetime.now(UTC) - timedelta(days=2),
            },
        ).scalar_one()
        squad_id = conn.execute(
            text(
                """
                INSERT INTO agile_squads (
                  organization_id, name, purpose, created_by
                ) VALUES (:org, 'Equipe EI', 'Executar melhoria', :user_id)
                RETURNING id
                """
            ),
            {"org": uuid.UUID(org), "user_id": actor.user_id},
        ).scalar_one()
        sprint_id = conn.execute(
            text(
                """
                INSERT INTO agile_sprints (
                  organization_id, squad_id, name, goal, starts_at, ends_at,
                  status, created_by, activated_by, activated_at
                ) VALUES (
                  :org, :squad, 'Sprint EI', 'Reduzir atraso',
                  now() - interval '7 days', now() + interval '7 days',
                  'active', :user_id, :user_id, now() - interval '7 days'
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org),
                "squad": squad_id,
                "user_id": actor.user_id,
            },
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO agile_sprint_cards (
                  organization_id, sprint_id, action_item_id, priority,
                  position, created_by
                ) VALUES (:org, :sprint, :action, 'high', 1, :user_id)
                """
            ),
            {
                "org": uuid.UUID(org),
                "sprint": sprint_id,
                "action": action_id,
                "user_id": actor.user_id,
            },
        )
        evidence_id = conn.execute(
            text(
                """
                INSERT INTO evidences (
                  organization_id, assessment_id, improvement_case_id, status,
                  classification, content_type, byte_size, content_hash,
                  storage_key, lineage_id, uploaded_by, collected_phase
                ) VALUES (
                  :org, NULL, :case_id, 'approved', 'internal',
                  'text/plain', 20, :content_hash, :storage_key,
                  gen_random_uuid(), :user_id, 'action_execution'
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org),
                "case_id": uuid.UUID(case_id),
                "content_hash": "a" * 64,
                "storage_key": f"test/{uuid.uuid4()}",
                "user_id": actor.user_id,
            },
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO evidence_links (
                  organization_id, evidence_id, target_type, target_id
                ) VALUES (:org, :evidence, 'action_item', :action)
                """
            ),
            {
                "org": uuid.UUID(org),
                "evidence": evidence_id,
                "action": action_id,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO action_execution_check_ins (
                  organization_id, action_item_id, health, progress_note,
                  next_step, reported_by, reported_at
                ) VALUES (
                  :org, :action, 'blocked', 'Fila ainda bloqueada',
                  'Remover bloqueio', :user_id, now() - interval '4 days'
                )
                """
            ),
            {
                "org": uuid.UUID(org),
                "action": action_id,
                "user_id": actor.user_id,
            },
        )
        measurement_plan_id = conn.execute(
            text(
                """
                INSERT INTO action_measurement_plans (
                  organization_id, action_plan_id, assessment_id,
                  improvement_case_id, objective, owner_membership_id,
                  review_cadence_days, next_review_at, status,
                  activated_by, activated_at, created_by
                ) VALUES (
                  :org, :plan, NULL, :case_id, 'Verificar redução do atraso',
                  :owner, 1, now() - interval '1 day', 'active',
                  :user_id, now() - interval '10 days', :user_id
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org),
                "plan": plan_id,
                "case_id": uuid.UUID(case_id),
                "owner": actor.membership_id,
                "user_id": actor.user_id,
            },
        ).scalar_one()
        indicator_id = conn.execute(
            text(
                """
                INSERT INTO indicator_definitions (
                  organization_id, measurement_plan_id, code, name, question,
                  owner_membership_id, value_type, unit_kind, decimal_places,
                  direction, target_value, target_due_at,
                  measurement_frequency_days, data_source, collection_method,
                  status, lineage_id, created_by
                ) VALUES (
                  :org, :measurement_plan, 'QUEUE_TIME', 'Tempo de fila',
                  'Quanto tempo o cliente espera?', :owner, 'decimal',
                  'dimensionless', 2, 'lower_is_better', 24,
                  now() - interval '1 day', 1, 'Sistema de atendimento',
                  'Extração diária', 'active', gen_random_uuid(), :user_id
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org),
                "measurement_plan": measurement_plan_id,
                "owner": actor.membership_id,
                "user_id": actor.user_id,
            },
        ).scalar_one()
        for kind, value, days_ago in (("baseline", 48, 10), ("observation", 30, 3)):
            conn.execute(
                text(
                    """
                    INSERT INTO measurement_records (
                      organization_id, measurement_plan_id,
                      indicator_definition_id, measurement_kind, value,
                      measured_at, note, collection_method, recorded_by
                    ) VALUES (
                      :org, :measurement_plan, :indicator, :kind, :value,
                      now() - make_interval(days => :days_ago),
                      'Leitura factual', 'Extração diária', :user_id
                    )
                    """
                ),
                {
                    "org": uuid.UUID(org),
                    "measurement_plan": measurement_plan_id,
                    "indicator": indicator_id,
                    "kind": kind,
                    "value": value,
                    "days_ago": days_ago,
                    "user_id": actor.user_id,
                },
            )
        conn.execute(
            text(
                """
                INSERT INTO action_impediments (
                  organization_id, action_item_id, title, description,
                  severity, status, owner_membership_id, opened_by
                ) VALUES (
                  :org, :action, 'Dependência externa', 'Aguardando liberação',
                  'high', 'open', :owner, :user_id
                )
                """
            ),
            {
                "org": uuid.UUID(org),
                "action": action_id,
                "owner": actor.membership_id,
                "user_id": actor.user_id,
            },
        )
    engine.dispose()

    path = f"{ENDPOINT}/{case_id}/execution-intelligence/runs"
    response = client.post(
        path,
        headers={**headers, "Idempotency-Key": f"live-{uuid.uuid4()}"},
        json={},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["schema_version"] == "1.0"
    assert body["mechanism_version"] == "execution-intelligence-rules-v1"
    assert body["result"]["execution_posture"]
    signals = body["result"].get("signals") or []
    codes = {signal["code"] for signal in signals}
    assert {
        "action_overdue",
        "active_impediment",
        "measurement_overdue",
        "target_not_met_attention",
    } <= codes
    assert all(s.get("requires_human_validation") is True for s in signals)
    refs = body["input_snapshot"]["fact_refs"]
    assert "action:1" not in refs
    assert "execution-plan" not in refs
    assert "case" not in refs
    assert "execution.action:action:1:is_overdue" in refs
    assert "execution.action:action:1:active_impediment_count" in refs
    assert "measurement.indicator:indicator:1:target_posture" in refs
    snapshot_blob = json.dumps(body["input_snapshot"], ensure_ascii=False)
    assert headers["X-Dev-User-Email"] not in snapshot_blob
    assert "Aguardando liberação" not in snapshot_blob
    assert body["is_stale"] is False

    latest = client.get(
        f"{ENDPOINT}/{case_id}/execution-intelligence/latest", headers=headers
    )
    assert latest.status_code == 200, latest.text
    assert latest.json()["id"] == body["id"]

    # Operational domain untouched: case still exists with same problem text
    case = client.get(f"{ENDPOINT}/{case_id}", headers=headers)
    assert case.status_code == 200
    assert "Atrasos" in case.json()["problem_statement"]

    get_settings.cache_clear()
