"""Evolution Map — deterministic engine + API gates."""

from __future__ import annotations

import uuid
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.modules.evolution_map.catalog import CATALOG_VERSION, RULES
from app.modules.evolution_map.engine import (
    AssessmentFacts,
    EvidenceFact,
    FindingFact,
    GuidedAnswerFact,
    evaluate_rules,
    fingerprint_facts,
)
from app.schemas.enums import EvolutionGenerationMode
from tests.conftest import ADMIN_URL
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _dev_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _reader_headers(org_id: str) -> dict[str, str]:
    sub = f"reader-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:sub, :email, 'active')
                RETURNING id
                """
            ),
            {"sub": sub, "email": f"{sub}@example.com"},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, ARRAY['reader'], 'active')
                """
            ),
            {"org": org_id, "user": user_id},
        )
    eng.dispose()
    return {**_dev_headers(sub), "X-Organization-Id": org_id}


def test_catalog_covers_required_themes():
    assert CATALOG_VERSION
    assert len(RULES) >= 15
    cats = {r.category.value for r in RULES}
    assert "direction_governance" in cats
    assert "correction_improvement" in cats
    kinds = {str(r.conditions.get("kind")) for r in RULES}
    for k in (
        "guided_answer_value",
        "evidence_pending",
        "evidence_rejected",
        "action_efficacy_unverified",
        "finding_cause_missing",
    ):
        assert k in kinds


def test_engine_partial_no_unknown_and_evidence():
    aid = uuid4()
    org = uuid4()
    facts = AssessmentFacts(
        assessment_id=aid,
        organization_id=org,
        status="draft",
        generation_mode=EvolutionGenerationMode.preliminary,
        answers=[
            GuidedAnswerFact(
                answer_id=uuid4(),
                question_id="Q-OPS-01",
                question_version="1",
                answer_value="partial",
                evidence_mode="none",
                provide_later=False,
            ),
            GuidedAnswerFact(
                answer_id=uuid4(),
                question_id="Q-LDR-01",
                question_version="1",
                answer_value="no",
                evidence_mode="none",
                provide_later=False,
            ),
            GuidedAnswerFact(
                answer_id=uuid4(),
                question_id="Q-RSK-01",
                question_version="1",
                answer_value="unknown",
                evidence_mode="none",
                provide_later=False,
            ),
            GuidedAnswerFact(
                answer_id=uuid4(),
                question_id="Q-DOC-01",
                question_version="1",
                answer_value="partial",
                evidence_mode="provide_later",
                provide_later=True,
            ),
        ],
        evidences=[
            EvidenceFact(evidence_id=uuid4(), status="upload_pending"),
            EvidenceFact(evidence_id=uuid4(), status="rejected"),
        ],
        context={
            "processes": [{"name": "Orçamento"}, {"name": "Entrega"}],
            "risks": [{"name": "Atraso", "action": None}],
            "stakeholders": [{"name": "Cliente"}],
        },
    )
    ranked = evaluate_rules(facts)
    assert ranked
    assert len(ranked) <= len(RULES)
    rule_ids = {c.rule.rule_id for c in ranked}
    assert "EVO-ANS-PARTIAL-OPS" in rule_ids
    assert "EVO-ANS-NO-GOV" in rule_ids
    assert "EVO-ANS-UNKNOWN-PLAN" in rule_ids
    assert "EVO-EVID-PENDING" in rule_ids
    assert "EVO-EVID-REJECTED" in rule_ids
    unknown = next(c for c in ranked if c.rule.rule_id == "EVO-ANS-UNKNOWN-PLAN")
    assert unknown.confidence.value == "low"
    assert unknown.priority.value == "investigate"
    for c in ranked:
        assert c.source_references
        assert "conform" not in c.observation.lower()
        assert "ISO 9001" not in c.rule.title


def test_engine_analysis_findings_and_actions():
    facts = AssessmentFacts(
        assessment_id=uuid4(),
        organization_id=uuid4(),
        status="analysis",
        generation_mode=EvolutionGenerationMode.analysis_ready,
        findings=[
            FindingFact(
                finding_id=uuid4(),
                status="approved",
                finding_type="nonconformity",
                title="Prazo sem causa",
                has_cause=False,
            )
        ],
        action_items=[],
    )
    # add action via mutation
    from app.modules.evolution_map.engine import ActionItemFact

    facts.action_items.append(
        ActionItemFact(item_id=uuid4(), status="implemented", finding_id=None)
    )
    ranked = evaluate_rules(facts)
    ids = {c.rule.rule_id for c in ranked}
    assert "EVO-FINDING-CAUSE" in ids
    assert "EVO-ACTION-EFFICACY" in ids


def test_fingerprint_idempotent():
    facts = AssessmentFacts(
        assessment_id=uuid4(),
        organization_id=uuid4(),
        status="draft",
        generation_mode=EvolutionGenerationMode.preliminary,
        answers=[
            GuidedAnswerFact(
                answer_id=uuid4(),
                question_id="Q-OPS-01",
                question_version="1",
                answer_value="partial",
                evidence_mode="none",
                provide_later=False,
            )
        ],
    )
    a = fingerprint_facts(facts)
    b = fingerprint_facts(facts)
    assert a == b


def _seed_guided_answer(org_id: str, assessment_id: str, *, value: str, qid: str = "Q-OPS-01"):
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        sess = conn.execute(
            text(
                """
                INSERT INTO guided_sessions (
                  organization_id, assessment_id, catalog_version, status, current_step, context
                ) VALUES (
                  :org, :aid, 'test', 'in_progress', 'route', CAST(:ctx AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "org": org_id,
                "aid": assessment_id,
                "ctx": '{"processes":[{"name":"Orçamentos"},{"name":"Entrega"}],'
                '"risks":[{"name":"Atraso"}],'
                '"stakeholders":[{"name":"Cliente"}]}',
            },
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO guided_answers (
                  organization_id, session_id, question_id, question_version,
                  answer_value, evidence_mode, provide_later
                ) VALUES (
                  :org, :sess, :qid, '1', :val, 'none', false
                )
                """
            ),
            {"org": org_id, "sess": sess, "qid": qid, "val": value},
        )
        # second answers for themes
        for q, v in (("Q-LDR-02", "no"), ("Q-RSK-03", "unknown"), ("Q-CUS-01", "no")):
            conn.execute(
                text(
                    """
                    INSERT INTO guided_answers (
                      organization_id, session_id, question_id, question_version,
                      answer_value, evidence_mode, provide_later
                    ) VALUES (
                      :org, :sess, :qid, '1', :val, 'none', false
                    )
                    """
                ),
                {"org": org_id, "sess": sess, "qid": q, "val": v},
            )
    eng.dispose()


def test_api_generate_preliminary_max10_sources_and_roles(client: TestClient):
    _headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided_answer(org_id, aid, value="partial")

    empty = client.get(f"/api/v1/assessments/{aid}/evolution-map", headers=h)
    assert empty.status_code == 200
    assert empty.json() is None

    gen = client.post(
        f"/api/v1/assessments/{aid}/evolution-map/generate",
        json={"mode": "preliminary"},
        headers={**h, "Idempotency-Key": f"evo-{uuid.uuid4()}"},
    )
    assert gen.status_code == 200, gen.text
    pkg = gen.json()
    assert pkg["generation_mode"] == "preliminary"
    assert pkg["catalog_version"] == CATALOG_VERSION
    assert len(pkg["priority_suggestions"]) <= 10
    assert pkg["priority_suggestions"]
    for s in pkg["priority_suggestions"]:
        assert s["source_references"]
        assert s["status"] == "proposed"
        assert "ISO 9001" not in s["title"]

    # idempotent same fingerprint
    gen2 = client.post(
        f"/api/v1/assessments/{aid}/evolution-map/generate",
        json={"mode": "preliminary"},
        headers={**h, "Idempotency-Key": f"evo-{uuid.uuid4()}"},
    )
    assert gen2.status_code == 200
    assert gen2.json()["id"] == pkg["id"]
    assert gen2.json()["package_version"] == pkg["package_version"]

    sid = pkg["priority_suggestions"][0]["id"]
    got = client.get(f"/api/v1/evolution-suggestions/{sid}", headers=h)
    assert got.status_code == 200
    assert got.json()["id"] == sid

    # reader can read, cannot review/generate
    rh = _reader_headers(org_id)
    assert client.get(f"/api/v1/assessments/{aid}/evolution-map", headers=rh).status_code == 200
    deny_gen = client.post(
        f"/api/v1/assessments/{aid}/evolution-map/generate",
        json={},
        headers=rh,
    )
    assert deny_gen.status_code == 403
    deny_accept = client.post(
        f"/api/v1/evolution-suggestions/{sid}/accept",
        headers=rh,
    )
    assert deny_accept.status_code == 403

    # accept preserved across regenerate after source change
    acc = client.post(f"/api/v1/evolution-suggestions/{sid}/accept", headers=h)
    assert acc.status_code == 200
    assert acc.json()["status"] == "accepted"
    accepted_rule = acc.json()["rule_id"]

    # change sources → new package version, accept preserved
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO evidences (
                  organization_id, assessment_id, status, classification,
                  content_type, byte_size, version_no
                ) VALUES (
                  :org, :aid, 'rejected', 'internal',
                  'text/plain', 3, 1
                )
                """
            ),
            {"org": org_id, "aid": aid},
        )
    eng.dispose()

    gen3 = client.post(
        f"/api/v1/assessments/{aid}/evolution-map/generate",
        json={"mode": "preliminary"},
        headers=h,
    )
    assert gen3.status_code == 200
    pkg3 = gen3.json()
    assert pkg3["package_version"] == pkg["package_version"] + 1
    assert pkg3["supersedes_id"] == pkg["id"]
    preserved = [
        s for s in pkg3["priority_suggestions"] + pkg3["secondary_suggestions"]
        if s["rule_id"] == accepted_rule
    ]
    assert preserved
    assert preserved[0]["status"] == "accepted"

    # dismiss requires reason
    other = next(
        s
        for s in pkg3["priority_suggestions"] + pkg3["secondary_suggestions"]
        if s["status"] == "proposed"
    )
    bad = client.post(
        f"/api/v1/evolution-suggestions/{other['id']}/dismiss",
        json={"reason": ""},
        headers=h,
    )
    assert bad.status_code == 422
    ok = client.post(
        f"/api/v1/evolution-suggestions/{other['id']}/dismiss",
        json={"reason": "Já tratado em reunião de direção"},
        headers=h,
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "dismissed"

    inv = client.post(
        f"/api/v1/evolution-suggestions/{preserved[0]['id']}/investigate",
        json={"missing_information": "Precisa entrevista com comercial"},
        headers=h,
    )
    assert inv.status_code == 200
    assert inv.json()["priority"] == "investigate"

    # cross-org
    h2 = _dev_headers(f"other-{uuid.uuid4()}")
    org2 = client.post(
        "/api/v1/organizations",
        json={"name": f"Ctrl {uuid.uuid4().hex[:6]}"},
        headers=h2,
    ).json()["organization"]["id"]
    h2 = {**h2, "X-Organization-Id": org2}
    cross = client.get(f"/api/v1/assessments/{aid}/evolution-map", headers=h2)
    assert cross.status_code in (403, 404)
    cross_s = client.get(f"/api/v1/evolution-suggestions/{sid}", headers=h2)
    assert cross_s.status_code in (403, 404)


def test_analysis_ready_requires_phase(client: TestClient):
    _headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    bad = client.post(
        f"/api/v1/assessments/{aid}/evolution-map/generate",
        json={"mode": "analysis_ready"},
        headers=h,
    )
    assert bad.status_code == 409


def test_convert_to_action_phase_gate_and_link(client: TestClient):
    from datetime import datetime, timedelta, timezone

    from tests.test_findings import _setup_in_progress
    from tests.test_findings_lifecycle import _approve_finding

    h, org_id, aid, req_id = _setup_in_progress(client)
    _seed_guided_answer(org_id, aid, value="partial")

    gen = client.post(
        f"/api/v1/assessments/{aid}/evolution-map/generate",
        json={"mode": "preliminary"},
        headers=h,
    )
    assert gen.status_code == 200, gen.text
    sug = gen.json()["priority_suggestions"][0]
    sid = sug["id"]

    assert client.post(f"/api/v1/evolution-suggestions/{sid}/accept", headers=h).status_code == 200

    me = client.get("/api/v1/organizations/me/memberships", headers=h).json()
    owner = next(m["id"] for m in me if m["organization_id"] == org_id)
    due = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()

    blocked = client.post(
        f"/api/v1/evolution-suggestions/{sid}/convert-to-action",
        json={
            "create_plan_if_missing": True,
            "action_kind": "improvement",
            "description": "Primeiro passo prático da sugestão",
            "owner_membership_id": owner,
            "due_at": due,
            "title": sug["title"],
        },
        headers=h,
    )
    assert blocked.status_code == 409

    assert client.post(
        f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h
    ).status_code == 200

    still = client.post(
        f"/api/v1/evolution-suggestions/{sid}/convert-to-action",
        json={
            "create_plan_if_missing": True,
            "action_kind": "improvement",
            "description": "Primeiro passo prático da sugestão",
            "owner_membership_id": owner,
            "due_at": due,
        },
        headers=h,
    )
    assert still.status_code == 409
    assert still.json()["code"] == "actions_phase_required"

    _approve_finding(client, h, org_id, aid, req_id)
    assert client.post(
        f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h
    ).status_code == 200

    ok = client.post(
        f"/api/v1/evolution-suggestions/{sid}/convert-to-action",
        json={
            "create_plan_if_missing": True,
            "action_kind": "improvement",
            "description": "Primeiro passo prático da sugestão",
            "owner_membership_id": owner,
            "due_at": due,
            "efficacy_required": False,
        },
        headers={**h, "Idempotency-Key": f"conv-{uuid.uuid4()}"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["suggestion"]["status"] == "converted_to_action"
    assert body["action_item_id"]
    assert body["action_plan_id"]
    assert body["suggestion"]["action_item_id"] == body["action_item_id"]

    dup = client.post(
        f"/api/v1/evolution-suggestions/{sid}/convert-to-action",
        json={
            "create_plan_if_missing": True,
            "action_kind": "improvement",
            "description": "dup",
            "owner_membership_id": owner,
            "due_at": due,
        },
        headers=h,
    )
    assert dup.status_code == 409
