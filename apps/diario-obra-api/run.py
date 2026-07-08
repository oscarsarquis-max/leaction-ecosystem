"""
Diário de Obra API — micro-serviço satélite (porta exclusiva 6010).

Desacoplado do Gateway (:4001), Marketplace (:4012) e Chamelleon (:5010).
Integração apenas via HTTP (webhooks/API).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from app import create_app

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "6010"))
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    app.run(host="0.0.0.0", port=port, debug=debug)
