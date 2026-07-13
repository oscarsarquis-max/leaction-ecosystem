"""
Diario de Obra API — micro-servico satelite (porta exclusiva 6010).

Desacoplado do Gateway (:4001), Marketplace (:4012) e Chamelleon (:5010).
Integracao apenas via HTTP (webhooks/API).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from app import create_app  # noqa: E402 — dotenv deve carregar antes do Config

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "6010"))
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    app.run(host="0.0.0.0", port=port, debug=debug)
