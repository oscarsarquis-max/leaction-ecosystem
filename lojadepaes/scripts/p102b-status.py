"""Confere o push sem imprimir chave."""

from app.core.config import get_settings
from app.domain.web_push import push_status

settings = get_settings()
status = push_status(settings)
print("configured", status["configured"])
print("public_key_length", len(status["public_key"]))
print("receipt_confirmed", status["receipt_confirmed"])
print("private_in_status", "vapid_private" in status)
