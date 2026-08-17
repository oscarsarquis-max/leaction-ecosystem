"""OI-018 live E2E — quality_structure/certification_status unknown readiness."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx

CORE = "http://127.0.0.1:8009"
OI = "http://127.0.0.1:8011"
SUB = f"oi018-{uuid.uuid4().hex[:10]}"
RESULTS: list[tuple[str, bool, str]] = []
REPORT = Path(__file__).resolve().parent / "_oi018_smoke_results.json"


def ok(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def headers(org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": SUB,
        "X-Dev-User-Email": f"{SUB}@example.com",
        "Content-Type": "application/json",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _facts(insights: list[dict]) -> list[str]:
    out: list[str] = []
    for i in insights:
        out.extend((i.get("explanation") or {}).get("supporting_facts") or [])
    return out


def _summaries(insights: list[dict]) -> str:
    return " | ".join(i.get("summary", "") for i in insights)


def main() -> int:
    c = httpx.Client(timeout=30.0)
    ok("core_health", c.get(f"{CORE}/health").status_code == 200)
    ok("oi_up", c.get(f"{OI}/docs").status_code == 200)

    r = c.post(
        f"{CORE}/api/v1/organizations",
        headers=headers(),
        json={"name": f"OI-018 Org {SUB}", "timezone": "America/Sao_Paulo"},
    )
    ok("create_org", r.status_code == 201, r.text[:100])
    if r.status_code != 201:
        return _finish(1)
    org = r.json()["organization"]["id"]

    # Profile: full enough to isolate quality_structure=unknown (+ certification known)
    r = c.patch(
        f"{CORE}/api/v1/organizations/current/profile",
        headers=headers(org),
        json={
            "trade_name": "Oficina OI-018",
            "legal_name": "Oficina OI-018 Ltda",
            "summary": "Organização de validação unknown readiness",
            "industry": "Serviços",
            "business_model": "services",
            "employee_range": "11-50",
            "unit_count": 2,
            "certification_status": "in_progress",
            "quality_structure": "unknown",
        },
    )
    ok("patch_profile_unknown_quality", r.status_code == 200)
    prof = r.json()
    ok(
        "fact_quality_structure_unknown_preserved",
        prof.get("quality_structure") == "unknown",
        str(prof.get("quality_structure")),
    )
    ok("fact_not_null", prof.get("quality_structure") is not None)
    ok("fact_not_empty_string", prof.get("quality_structure") != "")

    # Wire payload mirroring Core OrganizationContextInput (profile facts as stored)
    from datetime import UTC, datetime

    dumped = {
        "schema_version": "1.0",
        "core_organization_id": org,
        "request_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": {"system": "qmind-core", "component": "organizational-intelligence"},
        "context": {
            "organization": None,
            "profile": {
                "trade_name": prof.get("trade_name"),
                "legal_name": prof.get("legal_name"),
                "summary": prof.get("summary"),
                "industry": prof.get("industry"),
                "business_model": prof.get("business_model"),
                "employee_range": prof.get("employee_range"),
                "unit_count": prof.get("unit_count"),
                "certification_status": prof.get("certification_status"),
                "quality_structure": prof.get("quality_structure"),
            },
        },
        "metadata": {"environment": "local"},
    }
    ok(
        "context_input_quality_unknown",
        dumped["context"]["profile"]["quality_structure"] == "unknown",
        str(dumped["context"]["profile"].get("quality_structure")),
    )

    # Direct OI with that payload (proves OI sees unknown → gap)
    rd = c.post(
        f"{OI}/api/v1/organizational-intelligence/analyze",
        json=dumped,
    )
    ok("direct_oi_http", rd.status_code == 200, f"status={rd.status_code}")
    d_env = rd.json()
    ok("direct_schema_1_0", d_env.get("schema_version") == "1.0")
    d_facts = _facts(d_env.get("insights") or [])
    ok("direct_facts_quality", "quality_structure" in d_facts, str(sorted(set(d_facts))))
    ok(
        "direct_summary_humanized",
        "quality_structure" not in _summaries(d_env.get("insights") or [])
        and "Estrutura responsável pela qualidade" in _summaries(d_env.get("insights") or []),
    )

    # Core analyze (persist + full path)
    r = c.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org),
    )
    ok("core_analyze_1", r.status_code == 200, f"status={r.status_code}")
    env1 = r.json()
    ok("schema_1_0", env1.get("schema_version") == "1.0")
    ok("org_id_match", env1.get("core_organization_id") == org)
    insights1 = env1.get("insights") or []
    facts1 = _facts(insights1)
    sum1 = _summaries(insights1)
    support = next((i for i in insights1 if i.get("type") == "SUPPORT"), None)
    context = next((i for i in insights1 if i.get("type") == "CONTEXT"), None)
    ok("clause7_support_present", support is not None)
    ok(
        "clause7_missing_quality",
        support is not None
        and "quality_structure" in ((support.get("explanation") or {}).get("supporting_facts") or []),
    )
    ok(
        "clause4_missing_quality",
        context is not None
        and "quality_structure" in ((context.get("explanation") or {}).get("supporting_facts") or []),
    )
    ok("facts_technical_quality", "quality_structure" in facts1)
    ok(
        "summary_humanized_no_tech_key",
        "quality_structure" not in sum1 and "Estrutura responsável pela qualidade" in sum1,
        sum1[:220],
    )

    r = c.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org))
    runs1 = r.json()
    ok("run1_persisted", r.status_code == 200 and len(runs1) == 1)
    run1_id = runs1[0]["id"]
    run1_snap = json.dumps(runs1[0]["insights"], sort_keys=True)

    # PATCH to known value (simulates Completar + save)
    r = c.patch(
        f"{CORE}/api/v1/organizations/current/profile",
        headers=headers(org),
        json={"quality_structure": "formal"},
    )
    ok("patch_known_quality", r.status_code == 200 and r.json().get("quality_structure") == "formal")
    r = c.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org))
    runs_mid = r.json()
    ok(
        "history_intact_after_patch",
        len(runs_mid) == 1
        and runs_mid[0]["id"] == run1_id
        and json.dumps(runs_mid[0]["insights"], sort_keys=True) == run1_snap,
    )

    # Reanalyze
    r = c.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org),
    )
    ok("reanalyze", r.status_code == 200)
    env2 = r.json()
    facts2 = _facts(env2.get("insights") or [])
    sum2 = _summaries(env2.get("insights") or [])
    ok("gap_cleared_from_facts", "quality_structure" not in facts2, str(facts2))
    ok(
        "summary_no_longer_lists_quality_gap",
        "Estrutura responsável pela qualidade" not in sum2
        or "Informações ainda necessárias" not in sum2
        or "Estrutura responsável pela qualidade" not in sum2.split("Informações ainda necessárias")[-1],
        sum2[:220],
    )
    # Stronger: no quality in facts implies gap gone; if other gaps exist label might still appear elsewhere — assert facts only
    ok("reanalysis_quality_absent_from_facts", "quality_structure" not in facts2)

    r = c.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org))
    runs2 = r.json()
    ok("two_runs", len(runs2) == 2)
    ok(
        "run1_preserved",
        any(
            x["id"] == run1_id and json.dumps(x["insights"], sort_keys=True) == run1_snap for x in runs2
        ),
    )

    # certification_status=unknown technical smoke (separate org)
    r = c.post(
        f"{CORE}/api/v1/organizations",
        headers=headers(),
        json={"name": f"OI-018 Cert {SUB}", "timezone": "America/Sao_Paulo"},
    )
    org_c = r.json()["organization"]["id"]
    c.patch(
        f"{CORE}/api/v1/organizations/current/profile",
        headers=headers(org_c),
        json={
            "trade_name": "Cert Smoke",
            "summary": "Cert unknown smoke",
            "industry": "Serviços",
            "business_model": "services",
            "employee_range": "11-50",
            "unit_count": 1,
            "certification_status": "unknown",
            "quality_structure": "formal",
        },
    )
    prof_c = c.get(
        f"{CORE}/api/v1/organizations/current/profile", headers=headers(org_c)
    ).json()
    ok("cert_fact_unknown_preserved", prof_c.get("certification_status") == "unknown")
    r = c.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org_c),
    )
    ok("cert_analyze", r.status_code == 200)
    facts_c = _facts(r.json().get("insights") or [])
    sum_c = _summaries(r.json().get("insights") or [])
    ok("cert_in_supporting_facts", "certification_status" in facts_c, str(sorted(set(facts_c))))
    ok(
        "cert_summary_humanized",
        "certification_status" not in sum_c and "Situação da certificação" in sum_c,
        sum_c[:200],
    )

    return _finish(0 if all(x[1] for x in RESULTS) else 1)


def _finish(code: int) -> int:
    failed = [n for n, c, _ in RESULTS if not c]
    payload = {
        "sub": SUB,
        "passed": sum(1 for _, c, _ in RESULTS if c),
        "failed": len(failed),
        "failed_names": failed,
        "results": [{"name": n, "ok": c, "detail": d} for n, c, d in RESULTS],
    }
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== SUMMARY passed={payload['passed']} failed={payload['failed']} ===")
    if failed:
        print("failed:", ", ".join(failed))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
