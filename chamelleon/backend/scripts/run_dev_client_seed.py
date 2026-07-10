"""Aplica seed dev-client por e-mail (requer SEED_DEV_ALLOW=1 em produção)."""
from __future__ import annotations

import sys

from app import create_app
from app.services.dev_client_seed_service import apply_dev_client_stage_for_email

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/run_dev_client_seed.py <stage:1|2|3> <email>")
        sys.exit(1)
    stage = int(sys.argv[1])
    email = sys.argv[2]
    app = create_app()
    with app.app_context():
        result = apply_dev_client_stage_for_email(stage, email)
        print(result)
