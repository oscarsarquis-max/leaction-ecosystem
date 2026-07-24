"""Entrypoint do plugin Marketplace (porta isolada — não substitui gateway :4001)."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("MARKETPLACE_PORT", "4012"))
    debug = bool(app.config.get("DEBUG", False))
    # Reloader no Windows deixa processos órfãos em :4012 e responde com app
    # SQLAlchemy sem bind — desliga por padrão; use MARKETPLACE_USE_RELOADER=1 se precisar.
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=os.getenv("MARKETPLACE_USE_RELOADER", "0") == "1",
    )
