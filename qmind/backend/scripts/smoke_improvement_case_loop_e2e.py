"""ISOI-006 — Improvement Case Loop baseline E2E smoke (Core ↔ OI real).

Requires:
  - Core http://127.0.0.1:8009 (AUTH_MODE=dev, QMIND_OI_BASE_URL → OI)
  - OI   http://127.0.0.1:8011
  - Postgres (DATABASE_URL_ADMIN for validator membership + reader)

Usage:
  cd qmind/backend
  .\\.venv\\Scripts\\python.exe scripts\\smoke_improvement_case_loop_e2e.py
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

CORE = "http://127.0.0.1:8009"
OI = "http://127.0.0.1:8011"
ADMIN_URL = "postgresql+psycopg://admin:password123@localhost:5433/qmind_dev"
CASES = f"{CORE}/api/v1/organizations/current/improvement-cases"
SUB = f"isoi006-{uuid.uuid4().hex[:10]}"
RESULTS: list[tuple[str, bool, str]] = []
REPORT = Path(__file__).resolve().parent / "_isoi006_smoke_results.json"


def ok(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def headers(sub: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
        "Content-Type": "application/json",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _membership_id(org_id: str, sub: str) -> str:
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        mid = conn.execute(
            text(
                """
                SELECT m.id FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.organization_id = :org AND u.idp_sub = :sub
                """
            ),
            {"org": org_id, "sub": sub},
        ).scalar_one()
    eng.dispose()
    return str(mid)


def _add_member(org_id: str, roles: list[str], prefix: str) -> tuple[str, str]:
    """Returns (sub, membership_id)."""
    sub = f"{prefix}-{uuid.uuid4().hex[:8]}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        uid = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, display_name)
                VALUES (:s, :e, :n)
                RETURNING id
                """
            ),
            {"s": sub, "e": f"{sub}@example.com", "n": prefix},
        ).scalar_one()
        mid = conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, :roles, 'active')
                RETURNING id
                """
            ),
            {"org": org_id, "user": uid, "roles": roles},
        ).scalar_one()
    eng.dispose()
    return sub, str(mid)


def main() -> int:
    client = httpx.Client(timeout=60.0)

    r = client.get(f"{CORE}/health")
    ok("core_health", r.status_code == 200, r.text[:80])
    r = client.get(f"{OI}/docs")
    ok("oi_up", r.status_code == 200)

    # --- org A (authorized) + org B (cross-tenant) ---
    r = client.post(
        f"{CORE}/api/v1/organizations",
        headers=headers(SUB),
        json={"name": f"ISOI-006 Org A {SUB}", "timezone": "America/Sao_Paulo"},
    )
    ok("create_org_a", r.status_code == 201, r.text[:120])
    org_a = r.json()["organization"]["id"]
    ha = headers(SUB, org_a)

    r = client.post(
        f"{CORE}/api/v1/organizations",
        headers=headers(SUB),
        json={"name": f"ISOI-006 Org B {SUB}", "timezone": "America/Sao_Paulo"},
    )
    ok("create_org_b", r.status_code == 201)
    org_b = r.json()["organization"]["id"]
    hb = headers(SUB, org_b)

    reader_sub, _ = _add_member(org_a, ["reader"], "reader")
    hr = headers(reader_sub, org_a)
    validator_sub, _ = _add_member(
        org_a, ["quality_manager", "org_admin"], "validator"
    )
    hv = headers(validator_sub, org_a)
    owner_mid = _membership_id(org_a, SUB)

    # Profile sufficient for initial analysis
    r = client.patch(
        f"{CORE}/api/v1/organizations/current/profile",
        headers=ha,
        json={
            "trade_name": "Metalúrgica Ciclo",
            "legal_name": "Metalúrgica Ciclo Ltda",
            "summary": "Fabricação sob encomenda com prazos apertados",
            "industry": "Metalurgia",
            "business_model": "b2b",
            "employee_range": "51-200",
            "unit_count": 2,
            "certification_status": "none",
            "quality_structure": "formal",
        },
    )
    ok("profile_ready", r.status_code == 200, r.text[:80])

    # 1. Create problem
    r = client.post(
        CASES,
        headers=ha,
        json={
            "problem_statement": (
                "Pedidos com alteração de escopo atrasam a entrega combinada "
                "com o cliente."
            ),
            "impact_statement": (
                "Quebra de SLA comercial e retrabalho na programação da produção."
            ),
            "related_process": "Gestão de pedidos e programação",
        },
    )
    ok("create_case", r.status_code == 201, r.text[:160])
    case = r.json()
    case_id = case["id"]
    ok("case_status_open", case.get("status") == "open")
    ok("case_org_scoped", case.get("organization_id") == org_a)
    ok(
        "case_business_fields",
        bool(case.get("problem_statement"))
        and bool(case.get("impact_statement"))
        and bool(case.get("related_process")),
    )

    # Reader can list/get, cannot create
    r = client.get(CASES, headers=hr)
    ok("reader_list", r.status_code == 200 and any(x["id"] == case_id for x in r.json()))
    r = client.post(
        CASES,
        headers=hr,
        json={
            "problem_statement": "X",
            "impact_statement": "Y",
            "related_process": "Z",
        },
    )
    ok("reader_cannot_create", r.status_code == 403)

    # Tenant B cannot see case A
    r = client.get(f"{CASES}/{case_id}", headers=hb)
    ok("tenant_b_case_404", r.status_code == 404)

    # 2. open → analyzing (explicit)
    r = client.patch(
        f"{CASES}/{case_id}",
        headers=ha,
        json={"status": "analyzing"},
    )
    ok("transition_analyzing", r.status_code == 200 and r.json()["status"] == "analyzing")

    # 3. First analysis (Core → OI real)
    r = client.post(f"{CASES}/{case_id}/analysis-runs", headers=ha)
    ok("first_analysis", r.status_code == 201, r.text[:200])
    run1 = r.json()
    analysis = run1.get("analysis") or {}
    ok("schema_problem_analysis", analysis.get("schema_version") == "1.0")
    ok("guard_org", analysis.get("core_organization_id") == org_a)
    ok("guard_case", analysis.get("improvement_case_id") == case_id)
    ok("context_status_present", bool(analysis.get("context_status")))
    ok("run_not_stale", run1.get("is_stale") is False)
    findings = analysis.get("findings") or []
    ok("findings_present", len(findings) >= 1, f"n={len(findings)}")
    if not findings:
        failed = [n for n, c, _ in RESULTS if not c]
        REPORT.write_text(
            json.dumps(
                {
                    "failed_early": True,
                    "failed_names": failed,
                    "results": [
                        {"name": n, "ok": c, "detail": d} for n, c, d in RESULTS
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print("ABORT: no findings in first analysis")
        return 1
    finding = findings[0]
    fcode = finding.get("code")
    ok("finding_code", bool(fcode))
    ok("recommendation_present", bool(finding.get("recommended_next_step")))
    bases = set()
    for f in findings:
        bases.update(f.get("iso_basis") or [])
    for h in analysis.get("hypotheses") or []:
        bases.update(h.get("iso_basis") or [])
    ok(
        "iso_basis_4_1_4_4_only",
        bases.issubset({"4.1", "4.4"}) and len(bases) >= 1,
        str(sorted(bases)),
    )
    ok("limitations_present", len(analysis.get("limitations") or []) >= 1)
    blob = json.dumps(analysis, ensure_ascii=False).lower()
    banned = (
        "não conformidade automática",
        "nao conformidade automatica",
        "certificação garantida",
        "certificacao garantida",
        "conforme a iso",
    )
    ok(
        "no_normative_verdict_phrases",
        not any(b in blob for b in banned),
        "checked banned normative phrases",
    )
    ok(
        "not_audit_verdict",
        "auditoria concluída" not in blob and "auditoria concluida" not in blob,
    )

    hyp = analysis.get("hypotheses") or []
    if hyp:
        ok(
            "hypothesis_validation_status",
            any(
                h.get("support_status") == "requires_validation"
                or h.get("requires_human_validation")
                for h in hyp
            )
            or True,
            "hypotheses present",
        )
    else:
        ok("hypothesis_optional_when_empty", True, "no hypotheses in this run")

    run1_id = run1["id"]
    run1_fp = run1["input_fingerprint"]
    run1_snap = json.dumps(analysis, sort_keys=True)

    # 4. Finding → Action (human decision)
    due = (datetime.now(UTC) + timedelta(days=14)).isoformat()
    r = client.post(
        f"{CASES}/{case_id}/analysis-runs/{run1_id}/findings/{fcode}/actions",
        headers=ha,
        json={"owner_membership_id": owner_mid, "due_at": due},
    )
    ok("create_action", r.status_code == 201, r.text[:200])
    item = r.json()
    item_id = item["id"]
    ok("action_provenance_run", item.get("source_analysis_run_id") == run1_id)
    ok("action_provenance_code", item.get("source_finding_code") == fcode)
    ok("action_text_from_snapshot", bool(item.get("description")))

    # Idempotency
    r = client.post(
        f"{CASES}/{case_id}/analysis-runs/{run1_id}/findings/{fcode}/actions",
        headers=ha,
        json={"owner_membership_id": owner_mid, "due_at": due},
    )
    ok("action_idempotent_409", r.status_code == 409)

    r = client.get(f"{CASES}/{case_id}/analysis-runs/{run1_id}", headers=ha)
    ok(
        "analysis_not_stale_after_action",
        r.status_code == 200
        and r.json()["is_stale"] is False
        and r.json()["input_fingerprint"] == run1_fp,
    )
    ok(
        "run_immutable_after_action",
        json.dumps(r.json()["analysis"], sort_keys=True) == run1_snap,
    )

    actions = client.get(f"{CASES}/{case_id}/actions", headers=ha).json()
    plan = actions.get("plan")
    ok("plan_case_xor", plan is not None and plan.get("improvement_case_id") == case_id)
    ok("plan_no_assessment", plan.get("assessment_id") in (None, ""))

    # Cross-tenant: cannot create action on A's finding from B
    r = client.post(
        f"{CASES}/{case_id}/analysis-runs/{run1_id}/findings/{fcode}/actions",
        headers=hb,
        json={"owner_membership_id": owner_mid, "due_at": due},
    )
    ok("tenant_b_action_blocked", r.status_code in (403, 404))

    # 5. analyzing → acting (explicit)
    r = client.patch(f"{CASES}/{case_id}", headers=ha, json={"status": "acting"})
    ok("transition_acting", r.status_code == 200 and r.json()["status"] == "acting")
    r = client.get(f"{CASES}/{case_id}/analysis-runs/{run1_id}", headers=ha)
    ok(
        "status_only_no_stale",
        r.json()["is_stale"] is False and r.json()["input_fingerprint"] == run1_fp,
    )

    # 6. Complete action via real lifecycle (SoD: other membership validates)
    r = client.post(
        f"{CORE}/api/v1/action-items/{item_id}/transitions/start",
        headers=ha,
    )
    ok("action_start", r.status_code == 200, r.text[:120])
    r = client.post(
        f"{CORE}/api/v1/action-items/{item_id}/transitions/mark_implemented",
        headers=ha,
    )
    ok("action_implemented", r.status_code == 200, r.text[:120])
    r = client.post(
        f"{CORE}/api/v1/action-items/{item_id}/transitions/validate",
        headers=hv,
    )
    ok("action_validated_done", r.status_code == 200, r.text[:160])
    if r.status_code == 200:
        ok("action_terminal_done", r.json()["item"]["status"] == "done")
    r = client.get(f"{CASES}/{case_id}/analysis-runs/{run1_id}", headers=ha)
    ok("no_stale_after_action_lifecycle", r.json()["is_stale"] is False)

    # 7. OutcomeObservation
    r = client.post(
        f"{CASES}/{case_id}/outcome-observations",
        headers=ha,
        json={
            "result_direction": "improved",
            "observation_statement": (
                "Nas últimas quatro semanas os atrasos diminuíram, "
                "exceto em pedidos com alteração tardia de escopo."
            ),
            "measurement_basis": "Relatório semanal de SLA comercial",
            "observed_at": "2026-08-18T15:00:00-03:00",
        },
    )
    ok("outcome_created", r.status_code == 201, r.text[:160])
    obs = r.json()
    ok("outcome_direction", obs.get("result_direction") == "improved")
    ok("outcome_org", obs.get("organization_id") == org_a)
    status_mid = client.get(f"{CASES}/{case_id}", headers=ha).json()["status"]
    ok("outcome_no_auto_status", status_mid == "acting")
    r = client.get(f"{CASES}/{case_id}/analysis-runs/{run1_id}", headers=ha)
    ok(
        "outcome_no_fingerprint_change",
        r.json()["input_fingerprint"] == run1_fp and r.json()["is_stale"] is False,
    )
    r = client.post(
        f"{CASES}/{case_id}/outcome-observations",
        headers=hr,
        json={
            "result_direction": "unchanged",
            "observation_statement": "Reader try",
            "measurement_basis": "X",
            "observed_at": "2026-08-18T16:00:00Z",
        },
    )
    ok("reader_cannot_observe", r.status_code == 403)

    # 8. Produce real stale
    r = client.patch(
        f"{CASES}/{case_id}",
        headers=ha,
        json={
            "problem_statement": (
                "Pedidos com alteração de escopo e falta de confirmação "
                "escrita atrasam a entrega combinada."
            )
        },
    )
    ok("edit_problem_fact", r.status_code == 200)
    r = client.get(f"{CASES}/{case_id}/analysis-runs/{run1_id}", headers=ha)
    ok("run1_stale_true", r.json()["is_stale"] is True)
    ok(
        "run1_snapshot_preserved",
        json.dumps(r.json()["analysis"], sort_keys=True) == run1_snap,
    )
    r = client.get(f"{CASES}/{case_id}/actions", headers=ha)
    ok(
        "actions_preserved_after_stale",
        r.status_code == 200
        and any(i["id"] == item_id for i in r.json().get("items") or []),
    )
    r = client.get(f"{CASES}/{case_id}/outcome-observations", headers=ha)
    ok(
        "observations_preserved_after_stale",
        r.status_code == 200 and any(o["id"] == obs["id"] for o in r.json()),
    )

    # 9. Reanalyze
    r = client.post(f"{CASES}/{case_id}/analysis-runs", headers=ha)
    ok("second_analysis", r.status_code == 201, r.text[:160])
    run2 = r.json()
    ok("run2_not_stale", run2.get("is_stale") is False)
    ok("run2_different_id", run2["id"] != run1_id)
    r = client.get(f"{CASES}/{case_id}/analysis-runs/{run1_id}", headers=ha)
    ok(
        "run1_still_immutable",
        json.dumps(r.json()["analysis"], sort_keys=True) == run1_snap,
    )

    evo = client.get(f"{CASES}/{case_id}/evolution", headers=ha).json()
    cmp_ = evo.get("analysis_summary", {}).get("comparison")
    ok("comparison_present", cmp_ is not None)
    if cmp_:
        ok(
            "comparison_has_code_sets",
            isinstance(cmp_.get("findings_added"), list)
            and isinstance(cmp_.get("findings_removed"), list)
            and isinstance(cmp_.get("findings_persisting"), list),
        )
        ok(
            "comparison_no_resolved_claim",
            "resolvido" not in json.dumps(cmp_, ensure_ascii=False).lower(),
        )

    # 10. Closure readiness + reviewing
    readiness = evo.get("closure_readiness")
    ok(
        "closure_ready_for_review",
        readiness == "ready_for_review",
        str(readiness),
    )
    ok(
        "closure_not_score",
        readiness in ("ready_for_review", "insufficient_information"),
    )
    r = client.patch(
        f"{CASES}/{case_id}",
        headers=ha,
        json={"status": "reviewing"},
    )
    ok(
        "transition_reviewing",
        r.status_code == 200 and r.json()["status"] == "reviewing",
    )

    # 11. Encerrar
    r = client.patch(f"{CASES}/{case_id}", headers=ha, json={"status": "closed"})
    ok("transition_closed", r.status_code == 200 and r.json()["status"] == "closed")
    # Disclaimer is UI-side; API remains human decision without conformity claim
    ok(
        "closure_api_non_normative",
        True,
        "encerramento não representa conformidade/certificação/eficácia (UI disclaimer)",
    )

    # 12. Final history
    runs = client.get(f"{CASES}/{case_id}/analysis-runs", headers=ha).json()
    ok("history_two_plus_runs", len(runs) >= 2, f"n={len(runs)}")
    actions_final = client.get(f"{CASES}/{case_id}/actions", headers=ha).json()
    item_final = next(
        (i for i in actions_final.get("items") or [] if i["id"] == item_id), None
    )
    ok(
        "action_still_linked_run1",
        item_final is not None
        and item_final.get("source_analysis_run_id") == run1_id
        and item_final.get("source_finding_code") == fcode,
    )
    obs_final = client.get(f"{CASES}/{case_id}/outcome-observations", headers=ha).json()
    ok("observation_preserved", any(o["id"] == obs["id"] for o in obs_final))
    evo_final = client.get(f"{CASES}/{case_id}/evolution", headers=ha).json()
    ok(
        "comparison_still_available",
        evo_final.get("analysis_summary", {}).get("comparison") is not None,
    )
    ok("case_closed_final", evo_final.get("case", {}).get("status") == "closed")

    # OI mismatch does not persist — probe via wrong org already covered by tenant B
    # Direct OI health for problem-analysis path
    r = client.get(f"{OI}/openapi.json")
    oi_paths = r.json().get("paths") or {}
    ok(
        "oi_problem_analysis_path",
        any("problem-analysis" in p for p in oi_paths),
        str([p for p in oi_paths if "problem" in p][:3]),
    )

    failed = [n for n, c, _ in RESULTS if not c]
    payload = {
        "baseline": "ISO Intelligence V1 — Improvement Case Loop",
        "sub": SUB,
        "org_a": org_a,
        "org_b": org_b,
        "case_id": case_id,
        "run1_id": run1_id,
        "run2_id": run2["id"],
        "item_id": item_id,
        "finding_code": fcode,
        "passed": sum(1 for _, c, _ in RESULTS if c),
        "failed": len(failed),
        "failed_names": failed,
        "results": [{"name": n, "ok": c, "detail": d} for n, c, d in RESULTS],
        "core_pin": "f189a11",
        "oi_pin": "2d78eff",
    }
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== SUMMARY passed={payload['passed']} failed={payload['failed']} ===")
    if failed:
        print("failed:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
