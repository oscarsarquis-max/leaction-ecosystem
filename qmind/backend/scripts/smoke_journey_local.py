"""Smoke local — jornada MVP completa (usuário zero / técnico).

Pré-requisitos:
  - API :8009 (AUTH_MODE=dev, STORAGE_BACKEND=memory)
  - Opcional: prepare_demo_org_local.py

Uso:
  cd qmind/backend
  .\\.venv\\Scripts\\python.exe scripts\\smoke_journey_local.py

Cobre: org → wizard seed → plano → planned → campo → entrevista →
evidência → constatação (SoD) → análise → maturidade (SoD) → ações (SoD) →
relatório (SoD) → PDF → close → reopen → cross-org.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8009"
ADMIN_URL = "postgresql+psycopg://admin:password123@localhost:5433/qmind_dev"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f"OK   {msg}")


def _dev(sub: str | None = None, org: str | None = None) -> dict[str, str]:
    sub = sub or f"journey-{uuid.uuid4()}"
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
        "Content-Type": "application/json",
    }
    if org:
        h["X-Organization-Id"] = org
    return h


def _catalog_ids() -> tuple[str, str, str]:
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        model = conn.execute(
            text("SELECT id FROM assessment_models WHERE code = 'qmind_iso9001_diag' LIMIT 1")
        ).scalar_one()
        sv = conn.execute(
            text("SELECT id FROM standard_versions WHERE version_label = '2015' LIMIT 1")
        ).scalar_one()
        req = conn.execute(
            text("SELECT id FROM requirements WHERE standard_version_id = :sv LIMIT 1"),
            {"sv": sv},
        ).scalar_one()
    eng.dispose()
    return str(model), str(sv), str(req)


def _ensure_qm(org_id: str) -> dict[str, str]:
    sub = f"qm-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        uid = conn.execute(
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
                VALUES (:org, :user, :roles, 'active')
                """
            ),
            {"org": org_id, "user": uid, "roles": ["quality_manager"]},
        )
    eng.dispose()
    return _dev(sub, org_id)


def _seed_guided(client: httpx.Client, h: dict, aid: str) -> None:
    g = client.get(f"/api/v1/assessments/{aid}/guided", headers=h)
    if g.status_code != 200:
        _fail(f"guided GET {g.status_code}: {g.text}")
    body = {
        "context": {
            "organization_profile": {
                "trade_name": "Oficina Norte Demo",
                "summary": "Manutenção industrial",
                "size_band": "M",
            },
            "qms_scope": {
                "description": "Serviços de manutenção",
                "exclusions": "8.3",
                "exclusion_justification": "Sem projeto de produto",
            },
            "products_services": [{"name": "Manutenção preventiva", "notes": ""}],
            "sites": [{"name": "Unidade SP", "location": "São Paulo", "notes": ""}],
            "processes": [
                {"name": "Orçamentos", "owner": "Carla", "notes": ""},
                {"name": "Execução", "owner": "Rafael", "notes": ""},
            ],
            "stakeholders": [{"name": "Clientes industriais", "interest": "Prazo", "notes": ""}],
        },
        "current_step": "review",
    }
    patch = client.patch(f"/api/v1/assessments/{aid}/guided", json=body, headers=h)
    if patch.status_code != 200:
        _fail(f"guided patch {patch.status_code}: {patch.text}")


def _complete_plan(client: httpx.Client, h: dict, aid: str, plan: dict, assess: dict) -> dict:
    processes = plan.get("processes") or [
        {"name": "Orçamentos", "owner": "Carla", "notes": "", "from_preparation": True},
        {"name": "Execução", "owner": "Rafael", "notes": "", "from_preparation": True},
    ]
    for p in processes:
        p["interview_justification"] = p.get("interview_justification") or (
            "Será entrevistado no campo"
        )
    body = {
        "objective": "Diagnóstico inicial do SGQ da Oficina Norte",
        "scope_text": "Manutenção preventiva e corretiva na Unidade SP",
        "criteria": {
            "iso9001_2015": True,
            "internal_processes": True,
            "legal_contractual": False,
            "legal_contractual_text": "",
            "additional_text": "",
        },
        "processes": processes,
        "lead_membership_id": assess["lead_membership_id"],
        "planned_start": "2026-09-01",
        "planned_end": "2026-09-05",
        "expected_updated_at": plan["updated_at"],
    }
    patched = client.patch(f"/api/v1/assessments/{aid}/audit-plan", json=body, headers=h)
    if patched.status_code != 200:
        _fail(f"patch plan {patched.status_code}: {patched.text}")
    for kind, day in (
        ("opening_meeting", "2026-09-01T13:00:00Z"),
        ("closing_meeting", "2026-09-05T17:00:00Z"),
    ):
        m = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings",
            json={
                "kind": kind,
                "objective": f"Objetivo {kind}",
                "starts_at": day,
                "duration_minutes": 45,
                "owner_membership_id": assess["lead_membership_id"],
            },
            headers=h,
        )
        if m.status_code != 201:
            _fail(f"meeting {kind}: {m.status_code} {m.text}")
    iv = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "mode": "onsite",
            "title": "Entrevista Orçamentos",
            "objective": "Entender o fluxo de orçamento",
            "process_name": "Orçamentos",
            "org_contact_name": "Carla",
            "scheduled_at": "2026-09-02T14:00:00Z",
            "duration_minutes": 60,
            "location": "Sala 2",
            "outside_period_justification": "Smoke journey — programação demonstrativa",
        },
        headers=h,
    )
    if iv.status_code != 201:
        _fail(f"interview create {iv.status_code}: {iv.text}")
    plan2 = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    if not plan2["readiness"]["ready"]:
        _fail(f"plan not ready: {plan2['readiness']}")
    return plan2


def _opening_id(client: httpx.Client, h: dict, aid: str) -> str:
    sched = client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=h)
    if sched.status_code != 200:
        _fail(f"schedule {sched.status_code}")
    opening = next(
        i
        for i in sched.json()["items"]
        if i.get("plan_activity_kind") == "opening_meeting" and i["status"] != "cancelled"
    )
    return opening["id"]


def _approve_evidence(client: httpx.Client, h: dict, aid: str) -> str:
    data = b"%PDF-1.4 smoke-journey-evidence"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    if auth.status_code != 201:
        _fail(f"authorize {auth.status_code}: {auth.text}")
    eid = auth.json()["evidence"]["id"]
    put = client.put(
        f"/api/v1/evidences/{eid}/bytes",
        content=data,
        headers={**h, "Content-Type": "application/pdf"},
    )
    if put.status_code not in (200, 204):
        _fail(f"bytes put {put.status_code}: {put.text}")
    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    if recv.status_code != 200:
        _fail(f"receive {recv.status_code}: {recv.text}")
    ok = client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h)
    if ok.status_code != 200:
        _fail(f"security_pass {ok.status_code}: {ok.text}")
    return eid


def _fill_maturity(client: httpx.Client, h: dict, mid: str, eid: str) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id
                FROM maturity_criteria c
                JOIN maturity_dimensions d ON d.id = c.maturity_dimension_id
                JOIN maturity_models m ON m.id = d.maturity_model_id
                WHERE m.model_code = 'qmind_maturity_iso9001' AND m.model_version = '0.1.0'
                ORDER BY d.sort_order, c.sort_order
                """
            )
        ).all()
    eng.dispose()
    scores = [
        {
            "criterion_id": str(r[0]),
            "applicability": "applicable",
            "level": 3,
            "rationale": "Prática observada no campo (smoke)",
            "evidence_ids": [eid],
        }
        for r in rows
    ]
    up = client.put(
        f"/api/v1/maturity-assessments/{mid}/scores",
        json={"scores": scores},
        headers=h,
    )
    if up.status_code != 200:
        _fail(f"maturity scores {up.status_code}: {up.text}")


def _due() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()


def main() -> None:
    print(f"Smoke journey -> {BASE}")
    try:
        httpx.get(f"{BASE}/api/v1/health", timeout=5.0)
    except httpx.ConnectError:
        _fail("API não responde em :8009")

    model_id, sv_id, req_id = _catalog_ids()
    admin_sub = f"journey-admin-{uuid.uuid4()}"
    h0 = _dev(admin_sub)

    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        org = client.post(
            "/api/v1/organizations",
            json={"name": f"Journey Demo {uuid.uuid4().hex[:6]}"},
            headers=h0,
        )
        if org.status_code != 201:
            _fail(f"org A {org.status_code}: {org.text}")
        org_a = org.json()["organization"]["id"]
        h = {**h0, "X-Organization-Id": org_a}
        qm = _ensure_qm(org_a)
        _ok(f"org A {org_a}")

        org_b_sub = f"ctrl-{uuid.uuid4()}"
        org_b_res = client.post(
            "/api/v1/organizations",
            json={"name": f"Journey Control {uuid.uuid4().hex[:6]}"},
            headers=_dev(org_b_sub),
        )
        if org_b_res.status_code != 201:
            _fail(f"org B {org_b_res.status_code}: {org_b_res.text}")
        org_b = org_b_res.json()["organization"]["id"]
        h_b = {**_dev(org_b_sub), "X-Organization-Id": org_b}
        _ok(f"org B {org_b}")

        created = client.post(
            "/api/v1/assessments",
            json={
                "assessment_model_id": model_id,
                "standard_version_id": sv_id,
                "type": "diagnosis",
                "scope": [{"requirement_id": req_id}],
            },
            headers=h,
        )
        if created.status_code != 201:
            _fail(f"assessment {created.status_code}: {created.text}")
        aid = created.json()["id"]
        _ok(f"draft {aid}")

        deny = client.get(f"/api/v1/assessments/{aid}", headers=h_b)
        if deny.status_code not in (403, 404):
            _fail(f"cross-org leak GET assessment: {deny.status_code}")
        _ok("cross-org assessment bloqueado")

        _seed_guided(client, h, aid)
        plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
        assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
        lead_mid = assess["lead_membership_id"]
        plan2 = _complete_plan(client, h, aid, plan, assess)
        _ok("plano checklist pronto")

        ready = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/ready",
            json={"expected_updated_at": plan2["updated_at"]},
            headers=h,
        )
        if ready.status_code != 200:
            _fail(f"ready {ready.status_code}: {ready.text}")
        concluded = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
            headers=h,
        )
        if concluded.status_code != 200:
            _fail(f"conclude-planning {concluded.status_code}: {concluded.text}")
        if client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] != "planned":
            _fail("status != planned")
        _ok("planned")

        opening = _opening_id(client, h, aid)
        waive = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings/{opening}/waive",
            json={"waiver_reason": "Abertura dispensada no smoke journey"},
            headers=h,
        )
        if waive.status_code != 200:
            _fail(f"waive opening {waive.status_code}: {waive.text}")
        start = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/start-field",
            headers=h,
        )
        if start.status_code != 200:
            _fail(f"start-field {start.status_code}: {start.text}")
        if client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] != "in_progress":
            _fail("status != in_progress")
        redirect = start.json().get("redirect_href") or ""
        if "/work" not in redirect:
            _fail(f"redirect_href inesperado: {redirect!r}")
        _ok("in_progress → /work")

        # Interview lifecycle
        ivs = client.get(f"/api/v1/assessments/{aid}/interviews", headers=h).json()
        if not ivs:
            _fail("nenhuma entrevista")
        iid = ivs[0]["id"]
        if ivs[0]["status"] in ("planned", "confirmed"):
            st = client.post(f"/api/v1/interviews/{iid}/start", headers=h)
            if st.status_code != 200:
                _fail(f"start interview {st.status_code}: {st.text}")
        ans = client.post(
            f"/api/v1/interviews/{iid}/answers",
            json={"body": "Fluxo de orçamento descrito pela responsável.", "question_id": None},
            headers=h,
        )
        if ans.status_code not in (200, 201):
            _fail(f"answer {ans.status_code}: {ans.text}")
        done_iv = client.post(f"/api/v1/interviews/{iid}/complete", headers=h)
        if done_iv.status_code != 200:
            _fail(f"complete interview {done_iv.status_code}: {done_iv.text}")
        _ok("entrevista concluída")

        eid = _approve_evidence(client, h, aid)
        _ok(f"evidência aprovada {eid}")

        fid = client.post(
            "/api/v1/findings",
            json={
                "assessment_id": aid,
                "finding_type": "conformity",
                "title": "Orçamento documentado",
                "body": "Processo de orçamento descrito e evidenciado.",
                "requirement_ids": [req_id],
                "evidence_ids": [eid],
            },
            headers=h,
        )
        if fid.status_code != 201:
            _fail(f"finding {fid.status_code}: {fid.text}")
        fid = fid.json()["id"]
        assert client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h).status_code == 200
        sod = client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=h)
        if sod.status_code != 403:
            _fail(f"SoD finding esperado 403, veio {sod.status_code}")
        assert (
            client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=qm).status_code
            == 200
        )
        _ok("constatação aprovada (SoD)")

        assert (
            client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h).status_code
            == 200
        )
        _ok("analysis")

        mid = client.post(
            "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
        ).json()["id"]
        _fill_maturity(client, h, mid, eid)
        assert (
            client.post(f"/api/v1/maturity-assessments/{mid}/transitions/submit", headers=h).status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/maturity-assessments/{mid}/transitions/approve", headers=qm).status_code
            == 200
        )
        _ok("maturidade aprovada (SoD)")

        assert (
            client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h).status_code
            == 200
        )
        plan_id = client.post(
            "/api/v1/action-plans", json={"assessment_id": aid}, headers=h
        ).json()["id"]
        item = client.post(
            f"/api/v1/action-plans/{plan_id}/items",
            json={
                "finding_id": fid,
                "action_kind": "improvement",
                "description": "Padronizar checklist de orçamento",
                "owner_membership_id": lead_mid,
                "due_at": _due(),
                "efficacy_required": False,
            },
            headers=h,
        )
        if item.status_code != 201:
            _fail(f"action item {item.status_code}: {item.text}")
        item_id = item.json()["id"]
        assert (
            client.post(f"/api/v1/action-plans/{plan_id}/transitions/activate", headers=h).status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/action-items/{item_id}/transitions/start", headers=h).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/action-items/{item_id}/transitions/mark_implemented", headers=h
            ).status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/action-items/{item_id}/transitions/validate", headers=qm).status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/action-plans/{plan_id}/transitions/complete", headers=h).status_code
            == 200
        )
        _ok("plano de ação concluído (SoD)")

        assert (
            client.post(f"/api/v1/assessments/{aid}/transitions/begin_report", headers=h).status_code
            == 200
        )
        rep = client.post(
            "/api/v1/reports",
            json={
                "assessment_id": aid,
                "include_maturity": True,
                "include_action_plan": True,
            },
            headers=h,
        )
        if rep.status_code != 201:
            _fail(f"report {rep.status_code}: {rep.text}")
        rid = rep.json()["id"]
        assert client.post(f"/api/v1/reports/{rid}/transitions/submit", headers=h).status_code == 200
        assert (
            client.post(f"/api/v1/reports/{rid}/transitions/publish", headers=qm).status_code == 200
        )
        _ok("relatório publicado (SoD)")

        job = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h)
        if job.status_code != 202:
            _fail(f"export-pdf {job.status_code}: {job.text}")
        job_body = job.json()
        if job_body.get("status") != "succeeded":
            _fail(
                f"PDF não materializado pela API (status={job_body.get('status')}, "
                f"err={job_body.get('error_safe_message')}). "
                "Com STORAGE_BACKEND=memory o export deve processar inline."
            )
        dl = client.get(f"/api/v1/reports/{rid}/export-pdf/download-url", headers=h)
        if dl.status_code != 200:
            _fail(f"download-url {dl.status_code}: {dl.text}")
        pdf = client.get(f"/api/v1/reports/{rid}/export-pdf/bytes", headers=h)
        if pdf.status_code != 200:
            _fail(f"pdf bytes {pdf.status_code}: {pdf.text}")
        if not pdf.content.startswith(b"%PDF"):
            _fail("PDF bytes sem assinatura %PDF")
        _ok(f"PDF gerado ({len(pdf.content)} bytes) e download ok")

        closed = client.post(f"/api/v1/assessments/{aid}/transitions/close", headers=h)
        if closed.status_code != 200:
            _fail(f"close {closed.status_code}: {closed.text}")
        reopened = client.post(
            f"/api/v1/assessments/{aid}/transitions/reopen",
            json={"reason": "Ajuste pós-fechamento no smoke journey"},
            headers=qm,
        )
        if reopened.status_code != 200:
            _fail(f"reopen {reopened.status_code}: {reopened.text}")
        if client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] != "report":
            _fail("reopen não voltou para report")
        _ok("close + reopen com justificativa")

        # audit trail presence (at least finding approve event)
        eng = create_engine(ADMIN_URL)
        with eng.connect() as conn:
            n = conn.execute(
                text(
                    """
                    SELECT count(*) FROM platform_audit_events
                    WHERE organization_id = :org
                      AND action LIKE 'finding.%'
                    """
                ),
                {"org": org_a},
            ).scalar_one()
        eng.dispose()
        if n < 1:
            _fail("auditoria finding.* ausente")
        _ok(f"auditoria presente ({n} eventos finding.*)")

        print()
        print("PASS smoke_journey_local")
        print(f"  assessment={aid}")
        print(f"  work=http://127.0.0.1:5173/assessments/{aid}/work")
        print(f"  analysis=http://127.0.0.1:5173/assessments/{aid}/advanced")


if __name__ == "__main__":
    main()
