"""OI-016 live E2E smoke — Core ↔ OI (local validation only)."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path

import httpx

CORE = "http://127.0.0.1:8009"
OI = "http://127.0.0.1:8011"
SUB = f"oi016-{uuid.uuid4().hex[:10]}"
RESULTS: list[tuple[str, bool, str]] = []
REPORT = Path(__file__).resolve().parents[1] / "_oi016_smoke_results.json"


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


def _pids_on_port(port: int) -> list[int]:
    cmd = (
        f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue)"
        f".OwningProcess | Select-Object -Unique"
    )
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", cmd],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return [int(p.strip()) for p in out.splitlines() if p.strip().isdigit()]


def _kill_oi() -> None:
    for pid in _pids_on_port(8011):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
    time.sleep(1.5)


def _start_oi() -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [
            str(Path(r"C:\Projetos\qmind-oi\.venv\Scripts\python.exe")),
            "-m",
            "uvicorn",
            "qmind_oi.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
        ],
        cwd=r"C:\Projetos\qmind-oi",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    for _ in range(30):
        try:
            if httpx.get(f"{OI}/docs", timeout=1.0).status_code == 200:
                return proc
        except httpx.HTTPError:
            time.sleep(0.3)
    raise RuntimeError("OI failed to start")


def main() -> int:
    client = httpx.Client(timeout=30.0)
    r = client.get(f"{CORE}/health")
    ok("core_health", r.status_code == 200, r.text[:80])
    r = client.get(f"{OI}/docs")
    ok("oi_up", r.status_code == 200)

    r = client.post(
        f"{CORE}/api/v1/organizations",
        headers=headers(),
        json={"name": f"OI-016 Org A {SUB}", "timezone": "America/Sao_Paulo"},
    )
    ok("create_org_a", r.status_code == 201)
    org_a = r.json()["organization"]["id"]

    r = client.post(
        f"{CORE}/api/v1/organizations",
        headers=headers(),
        json={"name": f"OI-016 Org B {SUB}", "timezone": "America/Sao_Paulo"},
    )
    ok("create_org_b", r.status_code == 201)
    org_b = r.json()["organization"]["id"]

    r = client.patch(
        f"{CORE}/api/v1/organizations/current/profile",
        headers=headers(org_a),
        json={
            "trade_name": "Padaria OI-016",
            "legal_name": "Padaria OI-016 Ltda",
            "summary": "Organização de teste E2E OI-016",
            "industry": "Alimentos",
            "business_model": "b2c",
            "employee_range": "",
            "certification_status": "unknown",
            "quality_structure": "unknown",
        },
    )
    ok("patch_partial_profile", r.status_code == 200)
    profile1 = r.json()
    ok("profile_employee_range_empty", profile1.get("employee_range") in ("", None))

    r = client.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org_a),
    )
    ok("first_analyze", r.status_code == 200, f"status={r.status_code}")
    env1 = r.json()
    ok("schema_1_0", env1.get("schema_version") == "1.0")
    ok("org_id_match", env1.get("core_organization_id") == org_a)
    insights = env1.get("insights") or []
    ok("insights_present", len(insights) >= 1, f"n={len(insights)}")
    summaries = " | ".join(i.get("summary", "") for i in insights)
    titles = " | ".join(i.get("title", "") for i in insights)
    facts: list[str] = []
    for i in insights:
        facts.extend((i.get("explanation") or {}).get("supporting_facts") or [])

    ok(
        "summary_human_employee_range",
        "employee_range" not in summaries and "Número de colaboradores" in summaries,
        summaries[:240],
    )
    ok("summary_no_tech_employee_range", "employee_range" not in summaries)
    ok("summary_no_tech_quality_structure_token", "quality_structure" not in summaries)
    ok("title_stable_no_tech_keys", "employee_range" not in titles and "quality_structure" not in titles)
    ok("facts_technical_employee_range", "employee_range" in facts, str(sorted(set(facts))))
    # Documented limitation: Core default quality_structure=unknown is presence for OI.
    ok(
        "limitation_quality_unknown_not_gap",
        "quality_structure" not in facts,
        "unknown counts as present (OI-003)",
    )

    # Direct OI proves quality_structure humanization when truly null
    direct = {
        "schema_version": "1.0",
        "core_organization_id": org_a,
        "request_id": "oi016-direct",
        "correlation_id": "oi016-direct",
        "occurred_at": "2026-08-17T18:00:00Z",
        "source": {"system": "qmind-core", "component": "organizational-intelligence"},
        "context": {
            "profile": {
                "trade_name": "X",
                "summary": "Y",
                "industry": "Z",
                "business_model": "b2c",
                "employee_range": None,
                "unit_count": None,
                "certification_status": None,
                "quality_structure": None,
            }
        },
        "metadata": {"environment": "local"},
    }
    rd = client.post(f"{OI}/api/v1/organizational-intelligence/analyze", json=direct)
    ok("direct_oi_null_quality", rd.status_code == 200)
    dsum = " | ".join(i.get("summary", "") for i in rd.json().get("insights", []))
    dfacts: list[str] = []
    for i in rd.json().get("insights", []):
        dfacts.extend((i.get("explanation") or {}).get("supporting_facts") or [])
    ok(
        "direct_humanize_quality_structure",
        "quality_structure" not in dsum
        and "Estrutura responsável pela qualidade" in dsum
        and "quality_structure" in dfacts,
        dsum[:200],
    )

    r = client.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a))
    runs1 = r.json()
    ok("persisted_run1", r.status_code == 200 and len(runs1) == 1)
    run1_id = runs1[0]["id"]
    run1_snap = json.dumps(runs1[0]["insights"], sort_keys=True)

    r = client.patch(
        f"{CORE}/api/v1/organizations/current/profile",
        headers=headers(org_a),
        json={"employee_range": "51-200", "quality_structure": "formal", "unit_count": 2},
    )
    ok("patch_fill", r.status_code == 200)
    ok("profile_after_patch", r.json().get("employee_range") == "51-200" and r.json().get("quality_structure") == "formal")

    r = client.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a))
    runs_mid = r.json()
    ok("history_intact_after_patch", len(runs_mid) == 1 and runs_mid[0]["id"] == run1_id)
    ok("run1_snapshot_unchanged", json.dumps(runs_mid[0]["insights"], sort_keys=True) == run1_snap)

    r = client.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org_a),
    )
    ok("reanalyze", r.status_code == 200)
    env2 = r.json()
    facts2: list[str] = []
    for i in env2.get("insights") or []:
        facts2.extend((i.get("explanation") or {}).get("supporting_facts") or [])
    ok("gaps_cleared", not any(k in facts2 for k in ("employee_range", "quality_structure", "unit_count")), str(facts2))

    r = client.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a))
    runs2 = r.json()
    ok("two_runs", len(runs2) == 2)
    ok(
        "run1_preserved",
        any(x["id"] == run1_id and json.dumps(x["insights"], sort_keys=True) == run1_snap for x in runs2),
    )

    r = client.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_b))
    ok("tenant_b_empty_runs", r.status_code == 200 and r.json() == [])
    r = client.get(f"{CORE}/api/v1/organizations/current/profile", headers=headers(org_b))
    ok("tenant_b_profile_isolated", r.json().get("trade_name") != "Padaria OI-016")
    r = client.post(f"{CORE}/api/v1/organizations/current/intelligence/analyze", headers=headers(org_b))
    ok("tenant_b_analyze", r.status_code == 200 and r.json().get("core_organization_id") == org_b)
    r = client.get(f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a))
    ok(
        "tenant_a_uncontaminated",
        all(x["organization_id"] == org_a for x in r.json())
        and all(x["insights"]["core_organization_id"] == org_a for x in r.json()),
    )

    # OI unavailable
    runs_before_fail = client.get(
        f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a)
    ).json()
    n_before = len(runs_before_fail)
    _kill_oi()
    try:
        probe = client.get(f"{OI}/docs", timeout=2.0).status_code
    except httpx.HTTPError:
        probe = 0
    ok("oi_stopped", probe == 0)
    r = client.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org_a),
    )
    ok("analyze_oi_down_controlled", r.status_code == 502 and r.json().get("code") == "oi_unavailable", r.text[:160])
    runs_fail = client.get(
        f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a)
    ).json()
    ok("no_run_on_oi_failure", len(runs_fail) == n_before, f"{len(runs_fail)} vs {n_before}")
    prof = client.get(f"{CORE}/api/v1/organizations/current/profile", headers=headers(org_a)).json()
    ok("profile_intact_on_oi_failure", prof.get("trade_name") == "Padaria OI-016")

    oi_proc = _start_oi()
    r = client.post(
        f"{CORE}/api/v1/organizations/current/intelligence/analyze",
        headers=headers(org_a),
    )
    ok("recovery_analyze", r.status_code == 200 and r.json().get("schema_version") == "1.0")
    runs_rec = client.get(
        f"{CORE}/api/v1/organizations/current/intelligence/runs", headers=headers(org_a)
    ).json()
    ok("recovery_new_run", len(runs_rec) == n_before + 1, f"n={len(runs_rec)}")

    failed = [n for n, c, _ in RESULTS if not c]
    payload = {
        "sub": SUB,
        "org_a": org_a,
        "org_b": org_b,
        "passed": sum(1 for _, c, _ in RESULTS if c),
        "failed": len(failed),
        "failed_names": failed,
        "results": [{"name": n, "ok": c, "detail": d} for n, c, d in RESULTS],
        "oi_pid": oi_proc.pid,
    }
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== SUMMARY passed={payload['passed']} failed={payload['failed']} ===")
    if failed:
        print("failed:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
