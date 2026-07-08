"""Entrypoint do plugin Marketplace (porta isolada — não substitui gateway :4001)."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("MARKETPLACE_PORT", "4012"))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
