"""
Smoke test: gera Spec, inicia pipeline (auto_approve), mede tempos por fase.

Uso (backend com uvicorn em :8000 e Google configurado):
  cd phanton/backend
  .\\venv\\Scripts\\python.exe scripts\\smoke_pipeline_timing.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

API = __import__("os").environ.get("PHANTON_API", "http://127.0.0.1:8000").rstrip("/")
PROMPT = (
    "Quero um software SaaS habit tracker offline-first com React, Tailwind e "
    "LocalStorage, acessível WCAG, para usuários com TDAH. Incluir PRD, SDD e "
    "prompts de implementação."
)


def main() -> int:
    client = httpx.Client(base_url=API, timeout=600.0)
    t0 = time.perf_counter()
    print("=== SMOKE Phanton — timing ===\n")

    # Health
    r = client.get("/health")
    r.raise_for_status()
    print(f"[ok] health {r.elapsed.total_seconds():.2f}s")

    # Spec
    t = time.perf_counter()
    r = client.post("/api/pipeline/generate-spec", json={"prompt": PROMPT})
    r.raise_for_status()
    spec = r.json()["spec"]
    dt_spec = time.perf_counter() - t
    phases = spec.get("phases") or {}
    types = sorted(
        ((k, v.get("type"), v.get("order")) for k, v in phases.items()),
        key=lambda x: int(x[2] or 999),
    )
    has_sec = any(v.get("type") == "security_guidelines" for v in phases.values())
    print(f"[ok] generate-spec {dt_spec:.1f}s — {len(phases)} fases")
    for pid, ptype, order in types:
        print(f"     {order:>2} {pid} ({ptype})")
    print(f"     security_guidelines: {'SIM' if has_sec else 'NÃO ← FALHA'}")
    if not has_sec:
        print("FAIL: Spec sem security_guidelines")
        return 1

    # Start (auto_approve) — security ainda exige humano
    spec["auto_approve"] = True
    spec["user_prompt"] = PROMPT
    t = time.perf_counter()
    r = client.post("/api/pipeline/start", json={"spec": spec})
    r.raise_for_status()
    data = r.json()
    run_id = data["run_id"]
    dt_start = time.perf_counter() - t
    print(f"[ok] start {dt_start:.1f}s run={run_id}")

    # Confirma Spec persistida no run
    r = client.get(f"/api/pipeline/{run_id}")
    r.raise_for_status()
    run_spec = r.json().get("spec") or {}
    run_phases = run_spec.get("phases") or {}
    has_sec_run = any(
        v.get("type") == "security_guidelines" for v in run_phases.values()
    )
    print(
        f"[ok] run.phases={len(run_phases)} security={'SIM' if has_sec_run else 'NÃO ← FALHA'}"
    )
    if not has_sec_run:
        return 1

    # Poll até AWAITING (security ou outra) / COMPLETED / timeout
    seen: dict[str, str] = {}
    phase_timings: list[tuple[str, str, float]] = []
    last_change = time.perf_counter()
    deadline = time.perf_counter() + 900
    print("\n--- poll execução ---")
    while time.perf_counter() < deadline:
        r = client.get(f"/api/pipeline/{run_id}")
        r.raise_for_status()
        body = r.json()
        status = body.get("status")
        now = time.perf_counter()
        for ph in body.get("phases") or []:
            pid = ph["phase_id"]
            st = ph["status"]
            if seen.get(pid) != st:
                elapsed = now - t0
                delta = now - last_change
                last_change = now
                seen[pid] = st
                phase_timings.append((pid, st, elapsed))
                q = None
                art = ph.get("artifact_data") or {}
                if isinstance(art, dict):
                    q = art.get("quality_score")
                    meta = art.get("meta") or {}
                    attempts = meta.get("quality_attempts")
                else:
                    attempts = None
                extra = f" nota={q}" if q is not None else ""
                if attempts:
                    extra += f" quality_attempts={len(attempts)}"
                print(f"  +{elapsed:6.1f}s (+{delta:5.1f}s) {pid}: {st}{extra}")
        if status in ("COMPLETED",) or any(
            (p.get("status") or "").upper() == "AWAITING_APPROVAL"
            and (p.get("phase_id") == "security_guidelines" or True)
            for p in (body.get("phases") or [])
            if (p.get("status") or "").upper() == "AWAITING_APPROVAL"
        ):
            # Para no primeiro AWAITING (típico: security ou fase <80)
            awaiting = [
                p
                for p in (body.get("phases") or [])
                if (p.get("status") or "").upper() == "AWAITING_APPROVAL"
            ]
            if awaiting or status == "COMPLETED":
                print(f"\n[stop] run_status={status} awaiting={[p['phase_id'] for p in awaiting]}")
                break
        time.sleep(1.0)
    else:
        print("TIMEOUT 900s")
        return 1

    total = time.perf_counter() - t0
    print("\n=== RESUMO ===")
    print(f"total wall: {total:.1f}s")
    print(f"generate-spec: {dt_spec:.1f}s")
    print(f"start HTTP: {dt_start:.1f}s")
    print("transições:")
    for pid, st, elapsed in phase_timings:
        print(f"  {elapsed:6.1f}s  {pid} → {st}")
    print(json.dumps({"run_id": run_id, "total_s": round(total, 1)}, indent=2))
    return 0 if has_sec_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
