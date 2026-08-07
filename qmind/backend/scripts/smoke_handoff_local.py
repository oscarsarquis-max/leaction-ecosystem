"""Smoke local completo — Handoff Planejamento → Campo.

Uso (API local em :8009, AUTH_MODE=dev):
  cd qmind/backend
  .\\.venv\\Scripts\\python.exe scripts\\smoke_handoff_local.py

Gates:
  draft → Concluir Plano → Concluir planejamento → planned
  → abertura → Iniciar execução → in_progress → /work
  + emenda bloqueia / reconfirma libera
  + next_action do plano atualizada
  + double-click idempotente
  + reader sem mutação
"""

from __future__ import annotations

import sys
import uuid
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


def _dev_headers(sub: str | None = None) -> dict[str, str]:
    sub = sub or f"smoke-{uuid.uuid4()}"
    return {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
        "Content-Type": "application/json",
    }


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


def _reader_headers(org_id: str) -> dict[str, str]:
    """Create a reader membership in the same org (admin DB) and return headers."""
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
                VALUES (:org, :user, :roles, 'active')
                """
            ),
            {"org": org_id, "user": user_id, "roles": ["reader"]},
        )
    eng.dispose()
    return {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
        "X-Organization-Id": org_id,
        "Content-Type": "application/json",
    }


def _opening_id(client: httpx.Client, h: dict, aid: str) -> str:
    sched = client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=h)
    if sched.status_code != 200:
        _fail(f"schedule GET {sched.status_code}: {sched.text}")
    opening = next(
        i
        for i in sched.json()["items"]
        if i.get("plan_activity_kind") == "opening_meeting" and i["status"] != "cancelled"
    )
    return opening["id"]


def _complete_plan(client: httpx.Client, h: dict, aid: str, plan: dict, assess: dict) -> dict:
    processes = plan.get("processes") or [
        {"name": "Produção", "owner": "", "notes": "", "from_preparation": False}
    ]
    for p in processes:
        p["interview_justification"] = p.get("interview_justification") or (
            "Cobertura por observação documental neste ciclo"
        )
    body = {
        "objective": "Avaliar SGQ da planta (smoke handoff)",
        "scope_text": plan.get("scope_text") or "Escopo completo smoke",
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
                "duration_minutes": 60,
                "owner_membership_id": assess["lead_membership_id"],
            },
            headers=h,
        )
        if m.status_code != 201:
            _fail(f"create {kind} {m.status_code}: {m.text}")
    plan2 = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    if not plan2["readiness"]["ready"]:
        _fail(f"plan not ready: {plan2['readiness']}")
    return plan2


def _seed_guided(client: httpx.Client, h: dict, aid: str) -> None:
    g = client.get(f"/api/v1/assessments/{aid}/guided", headers=h)
    if g.status_code != 200:
        _fail(f"guided GET {g.status_code}: {g.text}")
    patch = client.patch(
        f"/api/v1/assessments/{aid}/guided",
        json={
            "context": {
                "organization_profile": {
                    "trade_name": "Smoke Acme",
                    "summary": "Indústria",
                    "size_band": "M",
                },
                "qms_scope": {
                    "description": "Fabricação",
                    "exclusions": "8.3",
                    "exclusion_justification": "Sem projeto",
                },
                "products_services": [{"name": "Peça X", "notes": ""}],
                "sites": [{"name": "Planta 1", "location": "SP", "notes": ""}],
                "processes": [
                    {"name": "Produção", "owner": "João", "notes": ""},
                    {"name": "Compras", "owner": "Ana", "notes": ""},
                ],
                "stakeholders": [],
            },
            "current_step": "route",
        },
        headers=h,
    )
    if patch.status_code != 200:
        _fail(f"guided patch {patch.status_code}: {patch.text}")


def main() -> None:
    print(f"Smoke handoff -> {BASE}")
    try:
        health = httpx.get(f"{BASE}/api/v1/health", timeout=5.0)
    except httpx.ConnectError:
        _fail(f"API não responde em {BASE} — suba uvicorn :8009")
    if health.status_code not in (200, 204):
        # some apps use /health without prefix
        pass

    model_id, sv_id, req_id = _catalog_ids()
    admin_sub = f"smoke-admin-{uuid.uuid4()}"
    h0 = _dev_headers(admin_sub)

    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        org = client.post(
            "/api/v1/organizations",
            json={"name": f"Smoke Handoff {uuid.uuid4().hex[:8]}"},
            headers=h0,
        )
        if org.status_code != 201:
            _fail(f"org create {org.status_code}: {org.text}")
        org_id = org.json()["organization"]["id"]
        h = {**h0, "X-Organization-Id": org_id}
        _ok(f"org {org_id}")

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
            _fail(f"assessment create {created.status_code}: {created.text}")
        aid = created.json()["id"]
        assert created.json()["status"] == "draft"
        _ok(f"assessment draft {aid}")

        _seed_guided(client, h, aid)
        plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
        assert plan["plan_status"] == "draft"
        assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
        plan2 = _complete_plan(client, h, aid, plan, assess)
        next0 = plan2["readiness"].get("next_action") or ""
        if not plan2["readiness"]["ready"]:
            _fail(f"checklist incompleto: {plan2['readiness']}")
        # Aceita rótulo atual ou legado (API reload) — o efeito importa.
        if not any(
            x in next0
            for x in ("Concluir Plano", "Marcar plano como pronto", "pronto")
        ):
            _fail(f"next_action inesperada após checklist: {next0!r}")
        _ok(f"plano completo — next_action={next0!r}")

        # 1) Concluir Plano (ready; assessment still draft)
        ready = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/ready",
            json={"expected_updated_at": plan2["updated_at"]},
            headers=h,
        )
        if ready.status_code != 200:
            _fail(f"ready {ready.status_code}: {ready.text}")
        assert ready.json()["plan_status"] == "ready"
        assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "draft"
        # Confirma next_action via GET fresco (mapa/dashboard leem o plano)
        plan_after_ready = client.get(
            f"/api/v1/assessments/{aid}/audit-plan", headers=h
        ).json()
        next_ready = plan_after_ready["readiness"]["next_action"]
        if plan_after_ready["plan_status"] != "ready":
            _fail(f"GET após ready sem plan_status=ready: {plan_after_ready['plan_status']}")
        if not plan_after_ready["readiness"]["ready"]:
            _fail(f"GET após ready com checklist falso: {plan_after_ready['readiness']}")
        if "Concluir planejamento" not in next_ready:
            _fail(f"next_action após ready inesperada: {next_ready!r}")
        _ok(f"Concluir Plano -> ready; assessment draft; next_action={next_ready!r}")

        # double-click ready idempotent
        ready2 = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/ready",
            json={"expected_updated_at": ready.json()["updated_at"]},
            headers=h,
        )
        if ready2.status_code != 200:
            _fail(f"ready idempotent {ready2.status_code}: {ready2.text}")
        assert ready2.json()["plan_status"] == "ready"
        _ok("duplo clique Concluir Plano idempotente")

        # reader blocked
        h_reader = _reader_headers(org_id)
        blocked_r = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
            json={},
            headers=h_reader,
        )
        if blocked_r.status_code != 403:
            _fail(f"reader should 403, got {blocked_r.status_code}: {blocked_r.text}")
        _ok("reader bloqueado em conclude-planning (403)")

        # 2) Concluir planejamento → planned
        conclude = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
            json={},
            headers=h,
        )
        if conclude.status_code != 200:
            _fail(f"conclude-planning {conclude.status_code}: {conclude.text}")
        assert conclude.json()["transition"]["to_status"] == "planned"
        assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "planned"
        _ok("Concluir planejamento → planned")

        # double-click conclude idempotent
        conclude2 = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
            json={},
            headers=h,
        )
        if conclude2.status_code != 200:
            _fail(f"conclude idempotent {conclude2.status_code}: {conclude2.text}")
        assert conclude2.json()["transition"]["to_status"] == "planned"
        _ok("duplo clique Concluir planejamento idempotente")

        # 3) Emenda bloqueia início
        cur = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
        amended = client.patch(
            f"/api/v1/assessments/{aid}/audit-plan",
            json={
                "objective": "Objetivo emendado no smoke",
                "amendment_reason": "Mudança de turno da planta visitada",
                "expected_updated_at": cur["updated_at"],
            },
            headers=h,
        )
        if amended.status_code != 200:
            _fail(f"amend {amended.status_code}: {amended.text}")
        assert amended.json()["plan_status"] == "amended"
        assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "planned"
        plan_am = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
        next_am = plan_am["readiness"]["next_action"]
        if plan_am["plan_status"] != "amended":
            _fail(f"GET após emenda sem amended: {plan_am['plan_status']}")
        if "Concluir Plano" not in next_am and "emenda" not in next_am.lower():
            _fail(f"next_action após emenda inesperada: {next_am!r}")
        _ok(f"emenda -> amended; assessment planned; next_action={next_am!r}")

        opening = _opening_id(client, h, aid)
        client.post(
            f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings/{opening}/perform",
            json={"observations": "Abertura ok"},
            headers=h,
        )
        blocked_start = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/start-field",
            json={},
            headers=h,
        )
        if blocked_start.status_code != 422:
            _fail(f"start com emenda deveria 422, got {blocked_start.status_code}: {blocked_start.text}")
        assert blocked_start.json()["code"] == "plan_amended_requires_reconfirm"
        _ok("emenda bloqueia Iniciar execução (plan_amended_requires_reconfirm)")

        # 4) Reconfirmação libera
        reconfirm = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/ready",
            json={
                "expected_updated_at": client.get(
                    f"/api/v1/assessments/{aid}/audit-plan", headers=h
                ).json()["updated_at"]
            },
            headers=h,
        )
        if reconfirm.status_code != 200:
            _fail(f"reconfirm {reconfirm.status_code}: {reconfirm.text}")
        assert reconfirm.json()["plan_status"] == "ready"
        _ok("reconfirmação → ready")

        # 5) Iniciar execução → in_progress + /work
        started = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/start-field",
            json={},
            headers=h,
        )
        if started.status_code != 200:
            _fail(f"start-field {started.status_code}: {started.text}")
        body = started.json()
        assert body["transition"]["to_status"] == "in_progress"
        assert body["redirect_href"] == f"/assessments/{aid}/work"
        assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "in_progress"
        _ok(f"Iniciar execução → in_progress; redirect={body['redirect_href']}")

        # double-click start idempotent
        started2 = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/start-field",
            json={},
            headers=h,
        )
        if started2.status_code != 200:
            _fail(f"start idempotent {started2.status_code}: {started2.text}")
        assert started2.json()["transition"]["to_status"] == "in_progress"
        assert (
            client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"]
            == "in_progress"
        )
        _ok("duplo clique Iniciar execução idempotente (sem transição duplicada)")

        # reader still blocked on mutate while in_progress
        blocked_start_r = client.post(
            f"/api/v1/assessments/{aid}/audit-plan/start-field",
            json={},
            headers=h_reader,
        )
        if blocked_start_r.status_code != 403:
            _fail(
                f"reader start should 403, got {blocked_start_r.status_code}: {blocked_start_r.text}"
            )
        _ok("reader bloqueado em start-field (403)")

        # second assessment: dispensa abertura (caminho alternativo)
        created_b = client.post(
            "/api/v1/assessments",
            json={
                "assessment_model_id": model_id,
                "standard_version_id": sv_id,
                "type": "diagnosis",
                "scope": [{"requirement_id": req_id}],
            },
            headers=h,
        )
        aid_b = created_b.json()["id"]
        _seed_guided(client, h, aid_b)
        plan_b = client.get(f"/api/v1/assessments/{aid_b}/audit-plan", headers=h).json()
        assess_b = client.get(f"/api/v1/assessments/{aid_b}", headers=h).json()
        _complete_plan(client, h, aid_b, plan_b, assess_b)
        client.post(f"/api/v1/assessments/{aid_b}/audit-plan/conclude-planning", json={}, headers=h)
        opening_b = _opening_id(client, h, aid_b)
        bad_waive = client.post(
            f"/api/v1/assessments/{aid_b}/audit-plan/schedule/meetings/{opening_b}/waive",
            json={"waiver_reason": "curto"},
            headers=h,
        )
        if bad_waive.status_code != 422:
            _fail(f"waive short should 422, got {bad_waive.status_code}")
        waived = client.post(
            f"/api/v1/assessments/{aid_b}/audit-plan/schedule/meetings/{opening_b}/waive",
            json={"waiver_reason": "Kickoff prévio documentado na preparação"},
            headers=h,
        )
        if waived.status_code != 200:
            _fail(f"waive {waived.status_code}: {waived.text}")
        assert waived.json()["status"] == "waived"
        start_b = client.post(
            f"/api/v1/assessments/{aid_b}/audit-plan/start-field", json={}, headers=h
        )
        if start_b.status_code != 200:
            _fail(f"start after waive {start_b.status_code}: {start_b.text}")
        assert start_b.json()["transition"]["to_status"] == "in_progress"
        _ok("dispensa com justificativa libera início")

    print()
    print("SMOKE HANDOFF PASS")
    print(f"  assessment A (perform): {aid} → in_progress → /assessments/{aid}/work")
    print(f"  assessment B (waive):   {aid_b} → in_progress")


if __name__ == "__main__":
    main()
