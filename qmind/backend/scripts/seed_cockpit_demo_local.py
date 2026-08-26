"""Seed demonstrativo do Cockpit ISO Intelligence (ISOI-010) — DEV/TEST ONLY.

Dados fictícios para o roteiro de ~5 minutos. NÃO usar em produção/homolog.

Idempotente: casos marcados com o prefixo `[DEMO-ISOI-010]` e org pelo nome.

Uso (API local em :8009, AUTH_MODE=dev):
  cd qmind/backend
  .\\.venv\\Scripts\\python.exe scripts\\seed_cockpit_demo_local.py

Pré-requisito: Core up em http://127.0.0.1:8009 com AUTH_MODE=dev.
Este script NÃO chama OI — persiste runs de Execution Intelligence realistas
via SQL (seed-only) com fingerprint alinhado ao batch do Cockpit.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8009"
ADMIN_URL = "postgresql+psycopg://admin:password123@localhost:5433/qmind_dev"

# --- Demo markers (idempotency) ---
ORG_NAME = "QMind Cockpit Demo ISOI-010"
DEMO_PREFIX = "[DEMO-ISOI-010]"
GESTOR_SUB = "demo-cockpit"
GESTOR_EMAIL = "cockpit.demo@example.com"

CASE_PROGRESSING = f"{DEMO_PREFIX} Jornada progresso com EI atual — fila em dia"
CASE_OVERDUE = f"{DEMO_PREFIX} Jornada bloqueada: ação vencida + impedimento aberto"
CASE_REVIEW = f"{DEMO_PREFIX} Jornada meta atingida aguardando revisão humana"
CASE_NEVER = f"{DEMO_PREFIX} Jornada ainda sem interpretação de execução (nunca analisada)"

LABELS = {
    "progressing_current_ei": CASE_PROGRESSING,
    "immediate_overdue_impediment": CASE_OVERDUE,
    "target_met_awaiting_review": CASE_REVIEW,
    "never_analyzed": CASE_NEVER,
}


def _ok(msg: str) -> None:
    print(f"OK   {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def _dev(sub: str, email: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": email,
        "Content-Type": "application/json",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _assert_dev_only(client: httpx.Client) -> None:
    """Refuse outside AUTH_MODE=dev / local-ish environments."""
    try:
        health = client.get("/health", timeout=5.0)
    except httpx.ConnectError:
        _fail("API não responde em :8009 — suba o Core local antes do seed")
    if health.status_code != 200:
        _fail(f"health: {health.status_code} {health.text}")
    body = health.json()
    auth_mode = (body.get("auth_mode") or "").lower()
    environment = (body.get("environment") or "").lower()
    if auth_mode != "dev":
        _fail(
            f"Recusado: AUTH_MODE={auth_mode!r} (este seed só roda com AUTH_MODE=dev). "
            "Dados demonstrativos — não para produção."
        )
    if environment in ("homolog", "prod"):
        _fail(
            f"Recusado: ENVIRONMENT={environment!r}. "
            "Seed demonstrativo apenas para local/dev/test."
        )
    _ok(f"ambiente permitido auth_mode={auth_mode} environment={environment}")


def _ensure_user(sub: str, email: str) -> str:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE idp_sub = :sub"),
            {"sub": sub},
        ).first()
        if row:
            uid = row[0]
        else:
            uid = conn.execute(
                text(
                    """
                    INSERT INTO users (idp_sub, email, status)
                    VALUES (:sub, :email, 'active')
                    RETURNING id
                    """
                ),
                {"sub": sub, "email": email},
            ).scalar_one()
    eng.dispose()
    return str(uid)


def _ensure_membership(org_id: str, user_id: str, roles: list[str]) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT id, roles FROM memberships
                WHERE organization_id = :org AND user_id = :user AND status = 'active'
                """
            ),
            {"org": org_id, "user": user_id},
        ).first()
        if existing:
            conn.execute(
                text("UPDATE memberships SET roles = :roles WHERE id = :id"),
                {"roles": roles, "id": existing[0]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO memberships (organization_id, user_id, roles, status)
                    VALUES (:org, :user, :roles, 'active')
                    """
                ),
                {"org": org_id, "user": user_id, "roles": roles},
            )
    eng.dispose()


def _membership_ids(org_id: str) -> tuple[uuid.UUID, uuid.UUID]:
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT m.id AS membership_id, m.user_id
                FROM memberships m
                WHERE m.organization_id = :org AND m.status = 'active'
                ORDER BY m.created_at
                LIMIT 1
                """
            ),
            {"org": uuid.UUID(org_id)},
        ).one()
    eng.dispose()
    return row.membership_id, row.user_id


def _find_org_by_name(client: httpx.Client, h: dict, name: str) -> str | None:
    mems = client.get("/api/v1/organizations/me/memberships", headers=h)
    if mems.status_code != 200:
        return None
    for m in mems.json():
        if m.get("organization_name") == name:
            return m["organization_id"]
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM organizations WHERE name = :n LIMIT 1"),
            {"n": name},
        ).first()
    eng.dispose()
    return str(row[0]) if row else None


def _ensure_org(client: httpx.Client) -> str:
    h0 = _dev(GESTOR_SUB, GESTOR_EMAIL)
    client.get("/api/v1/organizations/me/memberships", headers=h0)
    found = _find_org_by_name(client, h0, ORG_NAME)
    if found:
        _ok(f"org existente: {ORG_NAME} ({found})")
        return found
    created = client.post(
        "/api/v1/organizations",
        json={"name": ORG_NAME, "timezone": "America/Sao_Paulo"},
        headers=h0,
    )
    if created.status_code != 201:
        _fail(f"criar org: {created.status_code} {created.text}")
    org_id = created.json()["organization"]["id"]
    _ok(f"org criada: {ORG_NAME} ({org_id})")
    return org_id


def _find_case_by_problem(client: httpx.Client, h: dict, problem: str) -> str | None:
    listed = client.get(
        "/api/v1/organizations/current/improvement-cases",
        headers=h,
        params={"limit": 100},
    )
    if listed.status_code != 200:
        return None
    for item in listed.json():
        if item.get("problem_statement") == problem:
            return item["id"]
    # SQL fallback (pagination / older cases)
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id FROM improvement_cases
                WHERE organization_id = :org AND problem_statement = :p
                LIMIT 1
                """
            ),
            {"org": uuid.UUID(h["X-Organization-Id"]), "p": problem},
        ).first()
    eng.dispose()
    return str(row[0]) if row else None


def _ensure_case(
    client: httpx.Client,
    h: dict,
    *,
    problem: str,
    impact: str,
    process: str,
) -> str:
    existing = _find_case_by_problem(client, h, problem)
    if existing:
        _ok(f"caso existente: {problem[:48]}… ({existing})")
        return existing
    created = client.post(
        "/api/v1/organizations/current/improvement-cases",
        headers=h,
        json={
            "problem_statement": problem,
            "impact_statement": impact,
            "related_process": process,
        },
    )
    if created.status_code not in (200, 201):
        _fail(f"criar caso: {created.status_code} {created.text}")
    case_id = created.json()["id"]
    _ok(f"caso criado: {problem[:48]}… ({case_id})")
    return case_id


def _patch_case_status(client: httpx.Client, h: dict, case_id: str, status: str) -> None:
    r = client.patch(
        f"/api/v1/organizations/current/improvement-cases/{case_id}",
        headers=h,
        json={"status": status},
    )
    if r.status_code != 200:
        _fail(f"status {status} caso {case_id}: {r.status_code} {r.text}")


def _case_to_acting(client: httpx.Client, h: dict, case_id: str) -> None:
    """open → analyzing → acting (product transition graph)."""
    current = client.get(
        f"/api/v1/organizations/current/improvement-cases/{case_id}",
        headers=h,
    )
    if current.status_code != 200:
        _fail(f"get case {case_id}: {current.status_code} {current.text}")
    status = current.json().get("status")
    if status == "acting":
        return
    if status == "open":
        _patch_case_status(client, h, case_id, "analyzing")
        status = "analyzing"
    if status == "analyzing":
        _patch_case_status(client, h, case_id, "acting")
        return
    if status == "reviewing":
        _patch_case_status(client, h, case_id, "acting")
        return
    _fail(f"não foi possível levar caso {case_id} para acting (status={status})")


def _case_to_reviewing(client: httpx.Client, h: dict, case_id: str) -> None:
    _case_to_acting(client, h, case_id)
    current = client.get(
        f"/api/v1/organizations/current/improvement-cases/{case_id}",
        headers=h,
    ).json()
    if current.get("status") == "reviewing":
        return
    _patch_case_status(client, h, case_id, "reviewing")


def _clear_case_actions(org_id: str, case_id: str) -> None:
    """Reset demo actions for idempotent re-seed of supporting facts."""
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        plan_ids = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT id FROM action_plans
                    WHERE organization_id = :org AND improvement_case_id = :case_id
                    """
                ),
                {"org": uuid.UUID(org_id), "case_id": uuid.UUID(case_id)},
            ).all()
        ]
        if not plan_ids:
            eng.dispose()
            return
        action_ids = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT id FROM action_items
                    WHERE organization_id = :org AND action_plan_id = ANY(:plans)
                    """
                ),
                {"org": uuid.UUID(org_id), "plans": plan_ids},
            ).all()
        ]
        if action_ids:
            conn.execute(
                text(
                    """
                    DELETE FROM action_impediments
                    WHERE organization_id = :org AND action_item_id = ANY(:aids)
                    """
                ),
                {"org": uuid.UUID(org_id), "aids": action_ids},
            )
            conn.execute(
                text(
                    """
                    DELETE FROM action_items
                    WHERE organization_id = :org AND id = ANY(:aids)
                    """
                ),
                {"org": uuid.UUID(org_id), "aids": action_ids},
            )
        # Measurement plans tied to these action plans (demo only)
        mplan_ids = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT id FROM action_measurement_plans
                    WHERE organization_id = :org AND action_plan_id = ANY(:plans)
                    """
                ),
                {"org": uuid.UUID(org_id), "plans": plan_ids},
            ).all()
        ]
        if mplan_ids:
            conn.execute(
                text(
                    """
                    DELETE FROM measurement_records
                    WHERE organization_id = :org AND measurement_plan_id = ANY(:mp)
                    """
                ),
                {"org": uuid.UUID(org_id), "mp": mplan_ids},
            )
            conn.execute(
                text(
                    """
                    DELETE FROM indicator_definitions
                    WHERE organization_id = :org AND measurement_plan_id = ANY(:mp)
                    """
                ),
                {"org": uuid.UUID(org_id), "mp": mplan_ids},
            )
            conn.execute(
                text(
                    """
                    DELETE FROM action_measurement_plans
                    WHERE organization_id = :org AND id = ANY(:mp)
                    """
                ),
                {"org": uuid.UUID(org_id), "mp": mplan_ids},
            )
        conn.execute(
            text(
                """
                DELETE FROM action_plans
                WHERE organization_id = :org AND id = ANY(:plans)
                """
            ),
            {"org": uuid.UUID(org_id), "plans": plan_ids},
        )
    eng.dispose()


def _seed_action(
    org_id: str,
    case_id: str,
    *,
    description: str,
    status: str = "in_progress",
    overdue: bool = False,
    impediment: bool = False,
    due_days: int = 5,
) -> uuid.UUID:
    membership_id, user_id = _membership_ids(org_id)
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        plan_id = conn.execute(
            text(
                """
                INSERT INTO action_plans (
                  organization_id, assessment_id, improvement_case_id, status
                ) VALUES (:org, NULL, :case_id, 'active')
                RETURNING id
                """
            ),
            {"org": uuid.UUID(org_id), "case_id": uuid.UUID(case_id)},
        ).scalar_one()
        action_id = conn.execute(
            text(
                """
                INSERT INTO action_items (
                  organization_id, action_plan_id, action_kind, description,
                  owner_membership_id, due_at, status, is_overdue
                ) VALUES (
                  :org, :plan, 'improvement', :desc,
                  :owner, :due_at, :status, :overdue
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org_id),
                "plan": plan_id,
                "desc": description,
                "owner": membership_id,
                "due_at": datetime.now(UTC) + timedelta(days=due_days),
                "status": status,
                "overdue": overdue,
            },
        ).scalar_one()
        if impediment:
            conn.execute(
                text(
                    """
                    INSERT INTO action_impediments (
                      organization_id, action_item_id, title, description,
                      status, opened_by, opened_at
                    ) VALUES (
                      :org, :action, 'Bloqueio demo ISOI-010',
                      'Recurso indisponível (dado fictício)',
                      'open', :user_id, now()
                    )
                    """
                ),
                {
                    "org": uuid.UUID(org_id),
                    "action": action_id,
                    "user_id": user_id,
                },
            )
    eng.dispose()
    return action_id


def _plan_id_for_case(org_id: str, case_id: str) -> uuid.UUID | None:
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id FROM action_plans
                WHERE organization_id = :org AND improvement_case_id = :case_id
                ORDER BY created_at DESC LIMIT 1
                """
            ),
            {"org": uuid.UUID(org_id), "case_id": uuid.UUID(case_id)},
        ).first()
    eng.dispose()
    return row[0] if row else None


def _clear_outcomes(org_id: str, case_id: str) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        obs_ids = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT id FROM improvement_case_outcome_observations
                    WHERE organization_id = :org AND improvement_case_id = :case_id
                    """
                ),
                {"org": uuid.UUID(org_id), "case_id": uuid.UUID(case_id)},
            ).all()
        ]
        if obs_ids:
            conn.execute(
                text(
                    """
                    DELETE FROM outcome_observation_measurements
                    WHERE organization_id = :org
                      AND outcome_observation_id = ANY(:ids)
                    """
                ),
                {"org": uuid.UUID(org_id), "ids": obs_ids},
            )
            conn.execute(
                text(
                    """
                    DELETE FROM improvement_case_outcome_observations
                    WHERE organization_id = :org AND id = ANY(:ids)
                    """
                ),
                {"org": uuid.UUID(org_id), "ids": obs_ids},
            )
    eng.dispose()


def _clear_ei_runs(org_id: str, case_id: str) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM improvement_case_execution_intelligence_runs
                WHERE organization_id = :org AND improvement_case_id = :case_id
                """
            ),
            {"org": uuid.UUID(org_id), "case_id": uuid.UUID(case_id)},
        )
    eng.dispose()


def _insert_ei_run(
    org_id: str,
    case_id: str,
    *,
    fingerprint: str,
    posture: str = "progressing",
    signal_level: str = "watch",
    summary: str = "Execução em andamento (seed demo).",
) -> None:
    """Persist a realistic EI run without calling OI (seed-only)."""
    _user_membership = _membership_ids(org_id)
    user_id = _user_membership[1]
    result = {
        "schema_version": "1.0",
        "core_organization_id": org_id,
        "improvement_case_id": case_id,
        "analysis_id": str(uuid.uuid4()),
        "request_id": f"demo-seed-{case_id[:8]}",
        "correlation_id": f"demo-seed-{case_id[:8]}",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mechanism_version": "execution-intelligence-rules-v1",
        "interpretability_status": "interpretable",
        "execution_posture": posture,
        "interpretation_summary": summary,
        "signals": [
            {
                "code": "execution_progress_observed",
                "category": "flow",
                "level": signal_level,
                "title": "Progresso observado",
                "interpretation": "Há avanço registrado na execução (dado demonstrativo).",
                "supporting_fact_refs": ["case.status"],
                "iso_basis": ["8.1"],
                "recommended_next_step": "Manter o ritmo e validar o próximo check-in.",
                "requires_human_validation": True,
            }
        ],
    }
    snapshot = {
        "schema_version": "1.0",
        "core_organization_id": org_id,
        "improvement_case_id": case_id,
        "request_id": result["request_id"],
        "correlation_id": result["correlation_id"],
        "captured_at": result["generated_at"],
        "source": {"system": "qmind-core", "component": "execution-intelligence"},
        "case": {"status": "acting"},
        "execution": {},
        "measurement": {},
        "fact_refs": ["case.status"],
    }
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO improvement_case_execution_intelligence_runs (
                  organization_id, improvement_case_id, schema_version,
                  mechanism_version, request_id, correlation_id, generated_at,
                  input_snapshot, input_fingerprint, result, created_by
                ) VALUES (
                  :org, :case_id, '1.0', 'execution-intelligence-rules-v1',
                  :rid, :cid, now(), CAST(:snapshot AS jsonb), :fp,
                  CAST(:result AS jsonb), :user_id
                )
                """
            ),
            {
                "org": uuid.UUID(org_id),
                "case_id": uuid.UUID(case_id),
                "rid": result["request_id"],
                "cid": result["correlation_id"],
                "snapshot": json.dumps(snapshot),
                "fp": fingerprint,
                "result": json.dumps(result),
                "user_id": user_id,
            },
        )
    eng.dispose()


def _current_fingerprint(org_id: str, case_id: str) -> str:
    from app.db import tenant_connection
    from app.modules.cockpit.batch_fingerprint import batch_fingerprints

    with tenant_connection(uuid.UUID(org_id)) as conn:
        batch = batch_fingerprints(
            conn, uuid.UUID(org_id), [uuid.UUID(case_id)]
        )
    return batch[uuid.UUID(case_id)][1]


def _seed_measurement_target_met(
    client: httpx.Client, h: dict, action_plan_id: str
) -> None:
    """Plan + indicator + reading that meets target (API product path)."""
    plan = client.post(
        "/api/v1/organizations/current/measurement-plans",
        headers=h,
        json={
            "action_plan_id": action_plan_id,
            "objective": "Reduzir retrabalho na linha demo (fictício)",
        },
    )
    if plan.status_code not in (200, 201):
        _fail(f"measurement plan: {plan.status_code} {plan.text}")
    plan_id = plan.json()["id"]
    ind = client.post(
        f"/api/v1/organizations/current/measurement-plans/{plan_id}/indicators",
        headers=h,
        json={
            "code": "DEMO-RETRAB",
            "name": "Retrabalho semanal (demo)",
            "question": "Quantas peças voltam por semana?",
            "unit": "min",
            "direction": "decrease_is_better",
            "baseline_value": "12.000000",
            "target_value": "5.000000",
            "target_due_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "measurement_frequency_days": 7,
        },
    )
    if ind.status_code not in (200, 201):
        _fail(f"indicator: {ind.status_code} {ind.text}")
    indicator_id = ind.json()["id"]
    act = client.post(
        f"/api/v1/organizations/current/measurement-plans/{plan_id}/transitions/activate",
        headers=h,
    )
    if act.status_code >= 400:
        _fail(f"activate measurement: {act.status_code} {act.text}")
    rec = client.post(
        f"/api/v1/organizations/current/measurement-plans/{plan_id}/measurements",
        headers=h,
        json={
            "indicator_definition_id": indicator_id,
            "value": "4.000000",
            "measured_at": datetime.now(UTC).isoformat(),
            "note": "Leitura demo — meta atingida (fictício)",
        },
    )
    if rec.status_code not in (200, 201):
        _fail(f"measurement record: {rec.status_code} {rec.text}")
    _ok("medição com meta atingida (demo)")


def _ensure_outcome(client: httpx.Client, h: dict, case_id: str) -> None:
    _clear_outcomes(h["X-Organization-Id"], case_id)
    r = client.post(
        f"/api/v1/organizations/current/improvement-cases/{case_id}/outcome-observations",
        headers=h,
        json={
            "result_direction": "improved",
            "observation_statement": (
                "Nas últimas semanas o retrabalho caiu abaixo da meta "
                "(observação fictícia ISOI-010)."
            ),
            "measurement_basis": "Indicador DEMO-RETRAB (seed)",
            "observed_at": datetime.now(UTC).isoformat(),
        },
    )
    if r.status_code not in (200, 201):
        _fail(f"outcome: {r.status_code} {r.text}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 60)
    print("ISOI-010 Cockpit demo seed — DEMONSTRATIVE DATA ONLY")
    print("Not for production. AUTH_MODE=dev required.")
    print("=" * 60)
    print(f"Target API: {BASE}")

    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        _assert_dev_only(client)

        gestor_id = _ensure_user(GESTOR_SUB, GESTOR_EMAIL)
        org_id = _ensure_org(client)
        _ensure_membership(org_id, gestor_id, ["org_admin", "consultant_auditor"])
        h = _dev(GESTOR_SUB, GESTOR_EMAIL, org_id)

        # Profile (harmless if already set)
        client.patch(
            "/api/v1/organizations/current/profile",
            headers=h,
            json={
                "trade_name": "Oficina Demo Cockpit",
                "summary": "Organização fictícia para demonstração ISOI-010",
                "industry": "Manufatura",
                "business_model": "b2b",
                "employee_range": "11-50",
                "unit_count": 1,
                "certification_status": "none",
                "quality_structure": "formal",
            },
        )

        results: dict[str, str] = {}

        # --- 1. Progressing with current EI (persisted run, no OI call) ---
        case1 = _ensure_case(
            client,
            h,
            problem=CASE_PROGRESSING,
            impact="Clientes sentem atraso pontual, mas a fila está sob controle.",
            process="Atendimento",
        )
        _clear_case_actions(org_id, case1)
        _clear_ei_runs(org_id, case1)
        _seed_action(
            org_id,
            case1,
            description="Padronizar confirmação de prazo (demo)",
            status="in_progress",
            overdue=False,
            due_days=10,
        )
        _case_to_acting(client, h, case1)
        fp1 = _current_fingerprint(org_id, case1)
        _insert_ei_run(
            org_id,
            case1,
            fingerprint=fp1,
            posture="progressing",
            summary="Execução em andamento sem alertas críticos (seed).",
        )
        results["progressing_current_ei"] = case1
        _ok("jornada 1: progressing + EI current (SQL insert, seed-only)")

        # --- 2. Overdue + open impediment → immediate_attention ---
        case2 = _ensure_case(
            client,
            h,
            problem=CASE_OVERDUE,
            impact="Parada de linha por falta de peça crítica.",
            process="Produção",
        )
        _clear_case_actions(org_id, case2)
        _clear_ei_runs(org_id, case2)
        _seed_action(
            org_id,
            case2,
            description="Desbloquear fornecimento de peça X (demo)",
            status="in_progress",
            overdue=True,
            impediment=True,
            due_days=-3,
        )
        _case_to_acting(client, h, case2)
        results["immediate_overdue_impediment"] = case2
        _ok("jornada 2: overdue + impediment -> immediate_attention")

        # --- 3. Target met / measured result awaiting human review ---
        case3 = _ensure_case(
            client,
            h,
            problem=CASE_REVIEW,
            impact="Retrabalho elevado; meta ja atingida na medicao.",
            process="Qualidade",
        )
        _clear_case_actions(org_id, case3)
        _clear_ei_runs(org_id, case3)
        _seed_action(
            org_id,
            case3,
            description="Implantar checklist de inspecao (demo)",
            status="done",
            overdue=False,
            due_days=-1,
        )
        plan_id = _plan_id_for_case(org_id, case3)
        if not plan_id:
            _fail("action plan ausente para jornada 3")
        _seed_measurement_target_met(client, h, str(plan_id))
        _ensure_outcome(client, h, case3)
        _case_to_reviewing(client, h, case3)
        results["target_met_awaiting_review"] = case3
        _ok("jornada 3: meta atingida + outcome -> revisao humana")

        # --- 4. Never analyzed (no EI run) ---
        case4 = _ensure_case(
            client,
            h,
            problem=CASE_NEVER,
            impact="Novo problema ainda sem interpretação de execução.",
            process="Logística",
        )
        _clear_case_actions(org_id, case4)
        _clear_ei_runs(org_id, case4)
        _seed_action(
            org_id,
            case4,
            description="Mapear gargalo de expedição (demo)",
            status="open",
            overdue=False,
            due_days=14,
        )
        _case_to_acting(client, h, case4)
        results["never_analyzed"] = case4
        _ok("jornada 4: never_analyzed (sem EI run)")

    print()
    print("=== Seed pronto (fictício / demonstrativo) ===")
    print(f"Organização: {ORG_NAME}")
    print(f"  org_id={org_id}")
    print(f"  sub={GESTOR_SUB} email={GESTOR_EMAIL}")
    print()
    print("Casos / labels:")
    for key, case_id in results.items():
        print(f"  [{key}]")
        print(f"    label: {LABELS[key]}")
        print(f"    case_id={case_id}")
    print()
    print("Web local:")
    print("  VITE_AUTH_MODE=dev")
    print(f"  VITE_DEV_USER_SUB={GESTOR_SUB}")
    print(f"  VITE_DEV_USER_EMAIL={GESTOR_EMAIL}")
    print("  http://127.0.0.1:5173/cockpit")
    print()
    print("Nota: EI runs foram INSERIDOS via SQL (seed-only); OI não foi chamado.")


if __name__ == "__main__":
    main()
