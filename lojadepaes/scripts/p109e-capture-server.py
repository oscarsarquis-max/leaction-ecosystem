"""Servidor local de captura do 109E: SPA construída + banco lojadepaes_capture + Hub simulado.

Só loopback e só o banco de captura. O Hub é simulado em processo (nenhuma chamada de rede, nenhum
pagamento real): a cobrança Pix devolve um código de exemplo e nunca fica paga.

    python scripts/p109e-capture-server.py        # http://127.0.0.1:5176
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CAPTURE_URL = "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"
PORT = 5176


def main() -> None:
    from sqlalchemy.engine.url import make_url

    parsed = make_url(CAPTURE_URL)
    if (parsed.host or "").lower() not in {"127.0.0.1", "localhost"} or parsed.database != "lojadepaes_capture":
        raise SystemExit("recusando: não é o banco de captura local")

    os.environ.update(
        {
            "LOJADEPAES_DATABASE_URL": CAPTURE_URL,
            "LOJADEPAES_SPA_DIR": str(ROOT / "frontend" / "dist"),
            "LOJADEPAES_CORS_ORIGINS": f"http://127.0.0.1:{PORT}",
            "LOJADEPAES_PREVIEW_PROTECTION": "false",
            "LOJADEPAES_PUBLIC_ORDERS_ENABLED": "true",
            "LOJADEPAES_PUBLIC_PAYMENTS_ENABLED": "true",
            "LOJADEPAES_PUBLIC_DATE_REQUESTS_ENABLED": "true",
            "LOJADEPAES_MAIL_BACKEND": "ses",
            "LOJADEPAES_MAIL_FROM": "loja@lojadepaes.com.br",
            "LOJADEPAES_MAIL_IDENTITY_READY": "false",
            "LOJADEPAES_MAIL_OPS_TO": "",
            "LOJADEPAES_PUBLIC_ORIGIN": f"http://127.0.0.1:{PORT}",
        }
    )
    sys.path.insert(0, str(BACKEND))

    import uvicorn

    from app.core.config import get_settings
    from app.domain import storefront_orders
    from app.domain.actionhub_client import HubCheckoutResult

    get_settings.cache_clear()

    def fake_checkout(*_args, **kwargs):
        return HubCheckoutResult(
            order_id="hub-capture-109e",
            status="PENDING",
            checkout_url=None,
            amount_cents=kwargs.get("amount_cents") or 0,
            reused=False,
            method=kwargs.get("method", "pix"),
            pix_qr_code="00020126-codigo-pix-de-exemplo-109e",
            pix_date_of_expiration="2099-01-01T00:00:00-03:00",
            mp_payment_id="109e",
        )

    storefront_orders.request_amount_checkout = fake_checkout
    storefront_orders.lookup_amount_checkout = lambda *_a, **_k: None
    storefront_orders.cancel_amount_checkout = lambda *_a, **_k: None

    from app.main import create_app

    uvicorn.run(create_app(), host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
