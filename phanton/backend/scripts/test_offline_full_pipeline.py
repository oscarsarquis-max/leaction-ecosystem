#!/usr/bin/env python3
"""
Smoke end-to-end — generate-spec → start → approve até COMPLETED (Ollama).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

API_BASE = "http://127.0.0.1:8000"
PROMPT = (
    "Quero criar um micro-SaaS de gestão de hábitos diários. "
    "Aplique a metodologia do Loop do Hábito (Deixa, Rotina, Recompensa). "
    "Como o sistema está offline, pule pesquisas complexas. "
    "Consolide as ideias na síntese, gere um PRD detalhando as regras de notificação, "
    "crie um SDD com arquitetura baseada em React e LocalStorage, "
    "e finalize gerando o prompt de codificação para o Cursor."
)

# Cada fase LLM no 1B pode demorar; start/approve cobrem geração da próxima fase.
PHASE_TIMEOUT = 600.0
SPEC_TIMEOUT = 300.0
MAX_PHASES = 20


def _preview(value: Any, limit: int = 1200) -> str:
    if value is None:
        return "(vazio)"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, indent=2)
    else:
        text = str(value)
    if len(text) > limit:
        return text[:limit] + f"\n... [{len(text) - limit} chars omitidos]"
    return text


def _artifact_summary(phase_id: str, artifact: Any) -> None:
    print(f"\n===== Artefato: {phase_id} =====")
    if not isinstance(artifact, dict):
        print(_preview(artifact))
        return
    score = artifact.get("quality_score")
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    if score is None:
        score = meta.get("quality_score")
    print(f"quality_score: {score}")
    inner = artifact.get("artifact_data", artifact)
    if isinstance(inner, dict):
        # PRD/SDD/prompt costumam trazer markdown em chaves conhecidas
        for key in (
            "markdown",
            "prd_markdown",
            "sdd_markdown",
            "content",
            "prompt",
            "prompt_text",
            "sintese",
            "synthesis",
            "text",
        ):
            if key in inner and inner[key]:
                print(f"--- {key} ---")
                print(_preview(inner[key], limit=2500))
                return
        print(_preview(inner, limit=2500))
    else:
        print(_preview(inner, limit=2500))


def main() -> int:
    client = httpx.Client(base_url=API_BASE, timeout=PHASE_TIMEOUT)

    print("==> Full offline pipeline (Ollama)")
    try:
        health = client.get("/health", timeout=5.0)
        health.raise_for_status()
        print(f"Health: {health.json()}")
    except Exception as exc:
        print(f"ERRO: backend inacessível: {exc}", file=sys.stderr)
        return 1

    print("\n[1/3] POST /api/pipeline/generate-spec ...")
    t0 = time.perf_counter()
    try:
        spec_resp = client.post(
            "/api/pipeline/generate-spec",
            json={"prompt": PROMPT},
            timeout=SPEC_TIMEOUT,
        )
    except Exception as exc:
        print(f"ERRO generate-spec: {exc}", file=sys.stderr)
        return 2
    if spec_resp.status_code >= 400:
        print(f"ERRO HTTP {spec_resp.status_code}: {spec_resp.text}", file=sys.stderr)
        return 2

    payload = spec_resp.json()
    spec = payload.get("spec")
    model = payload.get("model")
    if not isinstance(spec, dict):
        print("ERRO: sem Spec", file=sys.stderr)
        return 2

    # Força aprovação humana via loop (1B tende a score baixo; não depender de auto).
    spec["auto_approve"] = False
    phases = spec.get("phases") if isinstance(spec.get("phases"), dict) else {}
    print(f"Modelo: {model} | Spec: {spec.get('name')} v{spec.get('version')} | fases={len(phases)}")
    print(f"generate-spec em {time.perf_counter() - t0:.1f}s")

    print("\n[2/3] POST /api/pipeline/start ...")
    t1 = time.perf_counter()
    try:
        start_resp = client.post("/api/pipeline/start", json={"spec": spec})
    except Exception as exc:
        print(f"ERRO start: {exc}", file=sys.stderr)
        return 3
    if start_resp.status_code >= 400:
        print(f"ERRO HTTP {start_resp.status_code}: {start_resp.text}", file=sys.stderr)
        return 3

    start = start_resp.json()
    run_id = start["run_id"]
    task_token = start.get("task_token")
    status = start.get("status")
    phase_id = start.get("phase_id")
    print(f"run_id={run_id}")
    print(f"1ª fase: {phase_id} status={status} ({time.perf_counter() - t1:.1f}s)")
    _artifact_summary(str(phase_id), start.get("artifact_data"))

    print("\n[3/3] Aprovar fases até COMPLETED ...")
    for step in range(1, MAX_PHASES + 1):
        if status in ("COMPLETED", "completed", "FAILED", "failed"):
            break
        if not task_token:
            # Recarrega status
            st = client.get(f"/api/pipeline/{run_id}").json()
            status = st.get("status")
            awaiting = [
                p
                for p in (st.get("phases") or [])
                if (p.get("status") or "").upper() == "AWAITING_APPROVAL"
            ]
            if not awaiting:
                print(f"Sem task_token e sem AWAITING_APPROVAL. status={status}")
                break
            task_token = awaiting[0].get("task_token")
            phase_id = awaiting[0].get("phase_id")

        print(f"\n--- Aprovar passo {step}: phase={phase_id} ---")
        t_step = time.perf_counter()
        try:
            appr = client.post(
                f"/api/pipeline/approve/{task_token}",
                json={"approver": "offline-smoke", "comments": "aprovação automática do smoke e2e"},
            )
        except Exception as exc:
            print(f"ERRO approve: {exc}", file=sys.stderr)
            return 4
        if appr.status_code >= 400:
            print(f"ERRO HTTP {appr.status_code}: {appr.text}", file=sys.stderr)
            return 4

        body = appr.json()
        status = body.get("status")
        nxt = body.get("next_phase") if isinstance(body.get("next_phase"), dict) else {}
        approved = body.get("approved_phase_id")
        print(f"aprovado={approved} -> run_status={status} ({time.perf_counter() - t_step:.1f}s)")

        if nxt:
            phase_id = nxt.get("phase_id") or nxt.get("approved_phase_id")
            task_token = nxt.get("task_token")
            status = nxt.get("status") or status
            _artifact_summary(str(phase_id), nxt.get("artifact_data"))
            # Encadeia auto-approves aninhados se houver
            cursor = nxt.get("next_phase")
            while isinstance(cursor, dict):
                phase_id = cursor.get("phase_id") or cursor.get("approved_phase_id") or phase_id
                task_token = cursor.get("task_token") or task_token
                status = cursor.get("status") or status
                if cursor.get("artifact_data"):
                    _artifact_summary(str(phase_id), cursor.get("artifact_data"))
                if (cursor.get("status") or "").upper() == "AWAITING_APPROVAL":
                    break
                cursor = cursor.get("next_phase")
        else:
            task_token = body.get("task_token")
            if (status or "").upper() in ("COMPLETED", "FAILED"):
                break

    print("\n==> Status final do run")
    final = client.get(f"/api/pipeline/{run_id}").json()
    print(f"status={final.get('status')} acceptance={final.get('acceptance_status')}")
    print(f"project={final.get('project_key')} v{final.get('version')}")

    for p in final.get("phases") or []:
        pid = p.get("phase_id")
        pst = p.get("status")
        print(f"  - {pid}: {pst}")
        if (pst or "").upper() in ("APPROVED", "AWAITING_APPROVAL"):
            _artifact_summary(str(pid), p.get("artifact_data"))

    out_path = Path(__file__).resolve().parent / "offline_full_pipeline_last.json"
    out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nDump salvo em: {out_path}")

    ok = (final.get("status") or "").upper() == "COMPLETED"
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
