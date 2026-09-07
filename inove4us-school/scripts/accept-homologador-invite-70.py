#!/usr/bin/env python3
"""Ativa vínculo Homologador via handler real TEACHER_INVITE_ACCEPTED.

Desvio: o B2C em produção tentou POST em http://127.0.0.1:5012 (School local)
e recusou conexão. Aqui invocamos o mesmo handler do webhook School, no host
School, com o payload que o Inove teria enviado.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from webhook_b2c_routes import _handle_teacher_invite_accepted  # noqa: E402

PAYLOAD = {
    "professor_email": "homologador@leaction.com.br",
    "email": "homologador@leaction.com.br",
    "instituicao_id": "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50",
    "vinculo_id": "53ba52b8-35c7-4c24-8f77-93877e58716f",
    "professor_b2c_id": 21,
    "institutional_name": "Escola Teste",
}


def main() -> None:
    result = _handle_teacher_invite_accepted(PAYLOAD)
    print(result)


if __name__ == "__main__":
    main()
