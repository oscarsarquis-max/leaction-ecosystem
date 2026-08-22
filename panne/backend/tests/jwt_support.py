import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

ISSUER = "https://cognito-idp.sa-east-1.amazonaws.com/sa-east-1_testpool"
CLIENT_ID = "panne-test-client"
KID_A = "kid-a"
KID_B = "kid-b"


def rsa_pair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key, key.public_key()


PRIVATE_A, PUBLIC_A = rsa_pair()
PRIVATE_B, PUBLIC_B = rsa_pair()


def jwk_for(public_key, kid: str) -> dict[str, Any]:
    payload = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    payload["kid"] = kid
    payload["use"] = "sig"
    payload["alg"] = "RS256"
    return payload


class ScriptedJwksFetcher:
    def __init__(self) -> None:
        self.responses: list[dict[str, Any] | Exception] = []
        self.calls = 0

    def queue(self, value: dict[str, Any] | Exception) -> None:
        self.responses.append(value)

    def fetch(self, url: str, timeout: float) -> dict[str, Any]:
        self.calls += 1
        if not self.responses:
            raise RuntimeError("jwks sem resposta roteada")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def mint(
    *,
    private_key=PRIVATE_A,
    kid: str = KID_A,
    issuer: str = ISSUER,
    subject: str = "cognito-subject-not-a-uuid",
    client_id: str = CLIENT_ID,
    token_use: str = "access",
    exp: int | None = None,
    audience: str | None = None,
    scope: str = "panne/me",
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "iss": issuer,
        "exp": exp if exp is not None else now + 3600,
        "iat": now,
        "token_use": token_use,
        "client_id": client_id,
        "scope": scope,
    }
    if audience is not None:
        payload["aud"] = audience
    if extra:
        payload.update(extra)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})
