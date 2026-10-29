"""Gera o par VAPID em duas linhas. A saída deve ir para arquivo, nunca para o log."""

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from py_vapid.utils import b64urlencode

vapid = Vapid()
vapid.generate_keys()
private = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))
public = b64urlencode(
    vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
)
print(f"LOJADEPAES_VAPID_PRIVATE_KEY={private}")
print(f"LOJADEPAES_VAPID_PUBLIC_KEY={public}")
