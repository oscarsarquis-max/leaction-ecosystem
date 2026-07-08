#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chamelleon — Seed de demonstração (local)

Recria o lead demo e posiciona no funil de implementação:

  • Sysadmin  : sysadmin@leaction.com.br  (senha — CHAMELLEON_SYSADMIN_PASSWORD)
  • Executor  : executor@paneldx.com.br   (senha — CHAMELLEON_EXECUTOR_PASSWORD)
  • Lead demo : sistema@paneldx.com.br    (código LA-PANEL1)

Estágios (parâmetro 1–3):

  1 — Primeiro login, sem questionário           → AGUARDANDO QUESTIONARIO
  2 — Questionário respondido (rascunho salvo)   → QUESTIONARIO OK
  3 — Diagnóstico calculado + dashboard          → DIAGNOSTICO OK

Uso local:
  python scripts/seed_dev_client.py 1
  python scripts/seed_dev_client.py 3 --framework construcao-civil-v1

Via API (dev):
  POST http://localhost:5010/api/seed/dev-client/3
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.core.dev_users import (
    DEV_DEFAULT_SECTOR,
    DEV_FRAMEWORK_ID,
    EMAIL_EXECUTOR_TEST,
    EMAIL_LEAD_CONSTRUCAO,
    EMAIL_LEAD_TEST,
    EMAIL_SYSADMIN,
    EXECUTOR_PASSWORD,
    LEAD_ACCESS_CODE,
    LEAD_CONSTRUCAO_ACCESS_CODE,
    SECTOR_PROFILES,
    SYSADMIN_PASSWORD,
)
from app.services.dev_client_seed_service import STAGE_LABELS, apply_dev_client_stage


def print_summary(payload: dict[str, object], sector: str) -> None:
    stage = payload["stage"]
    profile = SECTOR_PROFILES.get(sector, SECTOR_PROFILES[DEV_DEFAULT_SECTOR])
    print("")
    print("==> Seed Chamelleon concluido")
    print(f"    Estagio: {stage} — {payload['status']}")
    print(f"    Setor: {sector}")
    print(f"    Framework: {payload['framework_id']}")
    print(f"    Tenant lead: {payload['tenant_id']}")
    if payload.get("submission_id"):
        print(f"    Submission: {payload['submission_id']}")
    if payload.get("answers_count"):
        print(f"    Respostas: {payload['answers_count']}")
    if payload.get("score_global") is not None:
        print(f"    Score global: {payload['score_global']}")
        print(f"    Nivel: {payload.get('nivel_maturidade')}")
    print("")
    print("Credenciais:")
    print(f"  Lead   : {profile['email']}  codigo {profile['access_code']}")
    print(f"  Admin  : {EMAIL_SYSADMIN}  senha {SYSADMIN_PASSWORD}")
    print(f"  Executor: {EMAIL_EXECUTOR_TEST}  senha {EXECUTOR_PASSWORD}")
    print("")
    print("Fluxo esperado:")
    if stage == 1:
        print("  Login lead -> /diagnostico (questionario vazio)")
    elif stage == 2:
        print("  Login lead -> /diagnostico (respostas restauradas, pode finalizar)")
    else:
        print("  Login lead -> / (dashboard com score e plano mock)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed de cliente demo Chamelleon por estágio")
    parser.add_argument(
        "stage",
        type=int,
        choices=sorted(STAGE_LABELS.keys()),
        help="1=sem survey | 2=survey respondido | 3=diagnóstico calculado",
    )
    parser.add_argument(
        "--sector",
        choices=["telecom", "construcao"],
        default=DEV_DEFAULT_SECTOR,
        help="Perfil setorial do lead demo (padrao: construcao civil)",
    )
    parser.add_argument(
        "--framework",
        default=None,
        help="Framework ID (alternativa ao --sector)",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            payload = apply_dev_client_stage(
                args.stage,
                framework_id=args.framework,
                sector=args.sector,
            )
        except Exception as exc:
            print(f"\nErro: {exc}", file=sys.stderr)
            return 1

    print_summary(payload, args.sector)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
