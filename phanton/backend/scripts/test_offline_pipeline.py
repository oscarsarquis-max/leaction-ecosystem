#!/usr/bin/env python3
"""
Smoke test — pipeline Text-to-Spec 100%% offline (Ollama).

Pré-requisitos (terminais separados):
  1) ollama run llama3.1
     (ou: ollama pull llama3.1 && ollama serve já ativo)
  2) Backend Phanton com LLM_PROVIDER=ollama no backend/.env:
       cd phanton/backend
       .\\venv\\Scripts\\Activate.ps1
       uvicorn main:app --host 127.0.0.1 --port 8000
  3) Este script:
       python scripts/test_offline_pipeline.py

O teste NÃO sobe Ollama nem o Uvicorn — só valida a API local.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

API_BASE = "http://127.0.0.1:8000"
GENERATE_SPEC_URL = f"{API_BASE}/api/pipeline/generate-spec"

PROMPT = (
    "Quero criar um micro-SaaS de gestão de hábitos diários. "
    "Aplique a metodologia do Loop do Hábito (Deixa, Rotina, Recompensa). "
    "Como o sistema está offline, pule pesquisas complexas. "
    "Consolide as ideias na síntese, gere um PRD detalhando as regras de notificação, "
    "crie um SDD com arquitetura baseada em React e LocalStorage, "
    "e finalize gerando o prompt de codificação para o Cursor."
)

# generate-spec pode demorar com modelo local
TIMEOUT_SEC = 300.0


def main() -> int:
    print("==> Smoke offline — POST /api/pipeline/generate-spec")
    print(f"    API: {GENERATE_SPEC_URL}")
    print(f"    Timeout: {TIMEOUT_SEC:.0f}s\n")

    try:
        health = httpx.get(f"{API_BASE}/health", timeout=5.0)
        health.raise_for_status()
        print(f"Health: {health.json()}\n")
    except Exception as exc:
        print(
            "ERRO: backend inacessível em :8000.\n"
            "Suba o Uvicorn e confirme LLM_PROVIDER=ollama no .env.\n"
            f"Detalhe: {exc}",
            file=sys.stderr,
        )
        return 1

    try:
        response = httpx.post(
            GENERATE_SPEC_URL,
            json={"prompt": PROMPT},
            timeout=TIMEOUT_SEC,
        )
    except httpx.TimeoutException:
        print(
            "ERRO: timeout esperando o Spec.\n"
            "Confirme `ollama run llama3.1` e que LLM_BASE_URL aponta para :11434.",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        print(f"ERRO na chamada HTTP: {exc}", file=sys.stderr)
        return 3

    if response.status_code >= 400:
        print(f"ERRO HTTP {response.status_code}: {response.text}", file=sys.stderr)
        return 4

    payload = response.json()
    spec = payload.get("spec") if isinstance(payload, dict) else None
    model = payload.get("model") if isinstance(payload, dict) else None

    if not isinstance(spec, dict):
        print("ERRO: resposta sem Spec JSON.", file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 5

    phases = spec.get("phases") if isinstance(spec.get("phases"), dict) else {}
    print(f"Modelo reportado: {model or '(não informado)'}")
    print(f"Spec name/description: {spec.get('name') or spec.get('description')}")
    print(f"Versão: {spec.get('version')}")
    print(f"Fases no DAG ({len(phases)}):\n")

    # Resumo das fases (DAG)
    rows = []
    for phase_id, cfg in phases.items():
        if not isinstance(cfg, dict):
            cfg = {}
        rows.append(
            {
                "id": phase_id,
                "type": cfg.get("type"),
                "order": cfg.get("order"),
                "name": cfg.get("name"),
                "depends_on": cfg.get("depends_on") or [],
            }
        )
    rows.sort(key=lambda r: (r["order"] is None, r["order"] or 999, str(r["id"])))

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print("\n--- Spec completo (DAG) ---\n")
    print(json.dumps(spec, ensure_ascii=False, indent=2))

    types_found = {str(r.get("type") or "").lower() for r in rows}
    has_prd = any("prd" in t for t in types_found)
    has_sdd = any("sdd" in t for t in types_found)
    print("\n--- Checagem visual ---")
    print(f"Contém fase PRD-like: {'SIM' if has_prd else 'NÃO'}")
    print(f"Contém fase SDD-like: {'SIM' if has_sdd else 'NÃO'}")
    return 0


if __name__ == "__main__":
    # Garante imports relativos ao backend/ quando rodado de scripts/
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    raise SystemExit(main())
