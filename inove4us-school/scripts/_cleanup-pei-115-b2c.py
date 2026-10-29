#!/usr/bin/env python3
"""115 — desativa override B2C do teste (higiene). Não é correção de produto."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from b2c_integration_service import dispatch_pei_override_updated  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
ALUNO = "817b2c34-edcd-4478-b3cf-318e5d02fa96"
PEI = "aa3df1c8-92f7-4c54-a305-59e5ff5ed352"


def main() -> int:
    base = dispatch_pei_override_updated(
        {
            "nivel": "aee_base",
            "instituicao_id": INST,
            "condicao": "Deficiência Visual",
            "diretriz": "",
            "versao": 99,
            "is_active": False,
        }
    )
    indiv = dispatch_pei_override_updated(
        {
            "nivel": "individual",
            "instituicao_id": INST,
            "aluno_id": ALUNO,
            "aluno_nome": "[TESTE VARREDURA 115] Aluno PEI",
            "condicao": "Deficiência Visual",
            "particularidades": "",
            "pei_aluno_id": PEI,
            "versao": 99,
            "is_active": False,
        }
    )
    print(json.dumps({"base": base, "individual": indiv}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
