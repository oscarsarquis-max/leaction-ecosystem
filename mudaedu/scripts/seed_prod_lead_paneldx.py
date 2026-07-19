#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PanelDX — Seed de produção: SOMENTE sistema@paneldx.com.br

Remove e recria exclusivamente:
  • Cliente ctdi_clie / ctdi_matu / funil CTDI do e-mail sistema@paneldx.com.br
  • Código de acesso LA-PANEL1
  • Usuário paneldx_usuarios (role led) desse e-mail

NÃO remove:
  • sysadmin@leaction.com.br
  • executor@paneldx.com.br
  • Consultores demo
  • Outros clientes ou projetos do RDS

Uso local:
  python scripts/seed_prod_lead_paneldx.py 1

Uso produção (RDS — requer confirmação explícita):
  set SEED_DEV_ALLOW=1
  set SEED_PROD_CONFIRM=paneldx-demo-lead
  python scripts/seed_prod_lead_paneldx.py 1

Via deploy (recomendado — RDS na VPC):
  .\\scripts\\deploy\\12-seed-prod-lead-only.ps1 -Stage 1 -ConfirmLeadReset -ViaEc2

Estágios: 1=login | 2=pré-survey | 3=avaliação completa | 4=plano + Kanban
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    stage = "1"
    if len(sys.argv) > 1:
        stage = str(int(sys.argv[1]))
        if stage not in ("1", "2", "3", "4"):
            print("Estágio inválido. Use 1, 2, 3 ou 4.", file=sys.stderr)
            return 2

    os.environ.setdefault("SEED_PROD_CONFIRM", "paneldx-demo-lead")

    cmd = [
        sys.executable,
        str(ROOT / "seed_dev_client.py"),
        stage,
        "--lead-only",
    ]
    print("==> seed_prod_lead_paneldx.py")
    print(f"    Alvo: sistema@paneldx.com.br (LA-PANEL1)")
    print(f"    Estágio: {stage}")
    print(f"    SEED_PROD_CONFIRM={os.environ.get('SEED_PROD_CONFIRM')}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
