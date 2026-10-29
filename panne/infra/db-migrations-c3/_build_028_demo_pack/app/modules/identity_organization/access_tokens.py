"""Porta de verificação de access token. Sem confiança em decode sem assinatura."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Protocol
from urllib.parse import urlparse

import jwt
from jwt import algorithms

ALLOWED_ALG = "RS256"
MAX_TOKEN_SEGMENTS = 3


class TokenVerificationError(Exception):
    def __init__(self, reason: str, *, unavailable: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.unavailable = unavailable


class VerifiedAccessToken:
    __slots__ = ("issuer", "subject", "client_id", "scopes", "raw_claims")

    def __init__(
        self,
        issuer: str,
        subject: str,
        client_id: str | None,
        scopes: frozenset[str],
        raw_claims: dict[str, Any],
    ) -> None:
        self.issuer = issuer
        self.subject = subject
        self.client_id = client_id
        self.scopes = scopes
        self.raw_claims = raw_claims


class AccessTokenVerifier(Protocol):
    def verify(self, token: str) -> VerifiedAccessToken: ...


class JwksFetcher(Protocol):
    def fetch(self, url: str, timeout: float) -> dict[str, Any]: ...


class UrllibJwksFetcher:
    def fetch(self, url: str, timeout: float) -> dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"}:
            raise TokenVerificationError("jwks_indisponivel", unavailable=True)
        request = urllib.request.Request(url, method="GET")
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                payload = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TokenVerificationError("jwks_indisponivel", unavailable=True) from exc
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TokenVerificationError("jwks_indisponivel", unavailable=True) from exc
        if not isinstance(data, dict):
            raise TokenVerificationError("jwks_indisponivel", unavailable=True)
        return data


class JwksCache:
    def __init__(self, fetcher: JwksFetcher, url: str, timeout: float) -> None:
        self._fetcher = fetcher
        self._url = url
        self._timeout = timeout
        self._keys: dict[str, Any] = {}
        self._fetched_at: float | None = None

    @property
    def has_cache(self) -> bool:
        return bool(self._keys)

    def key_for(self, kid: str) -> Any:
        if kid in self._keys:
            return self._keys[kid]
        self.refresh()
        if kid not in self._keys:
            raise TokenVerificationError("kid_desconhecido")
        return self._keys[kid]

    def refresh(self) -> None:
        try:
            data = self._fetcher.fetch(self._url, self._timeout)
        except TokenVerificationError:
            if self._keys:
                raise TokenVerificationError("kid_desconhecido")
            raise
        keys = data.get("keys")
        if not isinstance(keys, list):
            if not self._keys:
                raise TokenVerificationError("jwks_indisponivel", unavailable=True)
            raise TokenVerificationError("kid_desconhecido")
        ingested: dict[str, Any] = {}
        for item in keys:
            if not isinstance(item, dict):
                continue
            kid = item.get("kid")
            kty = item.get("kty")
            if not isinstance(kid, str) or kty != "RSA":
                continue
            ingested[kid] = algorithms.RSAAlgorithm.from_jwk(json.dumps(item))
        if not ingested and not self._keys:
            raise TokenVerificationError("jwks_indisponivel", unavailable=True)
        if ingested:
            self._keys = ingested
            self._fetched_at = time.monotonic()


def assert_structural_token(token: str) -> tuple[str, str, str]:
    if not isinstance(token, str) or not token.strip():
        raise TokenVerificationError("formato_invalido")
    parts = token.split(".")
    if len(parts) != MAX_TOKEN_SEGMENTS or any(not part for part in parts):
        raise TokenVerificationError("formato_invalido")
    return parts[0], parts[1], parts[2]


class CognitoAccessTokenVerifier:
    def __init__(
        self,
        issuer: str,
        client_id: str,
        *,
        audience: str | None = None,
        required_scopes: frozenset[str] | None = None,
        jwks_cache: JwksCache | None = None,
        jwks_fetcher: JwksFetcher | None = None,
        jwks_timeout: float = 3.0,
    ) -> None:
        if not issuer or not client_id:
            raise ValueError("emissor e cliente sao obrigatorios")
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.audience = audience or None
        self.required_scopes = required_scopes or frozenset()
        self._jwks = jwks_cache or JwksCache(
            jwks_fetcher or UrllibJwksFetcher(),
            f"{self.issuer}/.well-known/jwks.json",
            jwks_timeout,
        )

    def verify(self, token: str) -> VerifiedAccessToken:
        assert_structural_token(token)
        try:
            header = jwt.get_unverified_header(token)
        except jwt.exceptions.DecodeError as exc:
            raise TokenVerificationError("formato_invalido") from exc
        if header.get("alg") != ALLOWED_ALG:
            raise TokenVerificationError("algoritmo_invalido")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise TokenVerificationError("kid_ausente")
        key = self._jwks.key_for(kid)
        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[ALLOWED_ALG],
                issuer=self.issuer,
                options={
                    "require": ["exp", "iss", "sub"],
                    "verify_aud": False,
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenVerificationError("token_expirado") from exc
        except jwt.InvalidIssuerError as exc:
            raise TokenVerificationError("emissor_invalido") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenVerificationError("assinatura_invalida") from exc
        return self._assert_claims(claims)

    def _assert_claims(self, claims: dict[str, Any]) -> VerifiedAccessToken:
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise TokenVerificationError("subject_invalido")
        if claims.get("token_use") != "access":
            raise TokenVerificationError("token_use_invalido")
        client_id = claims.get("client_id")
        if client_id != self.client_id:
            raise TokenVerificationError("cliente_invalido")
        if "aud" in claims:
            audience = claims["aud"]
            expected = self.audience or self.client_id
            values = audience if isinstance(audience, list) else [audience]
            if expected not in values:
                raise TokenVerificationError("audiencia_invalida")
        scopes = _scopes_of(claims.get("scope"))
        if self.required_scopes and not self.required_scopes.issubset(scopes):
            raise TokenVerificationError("escopo_insuficiente")
        issuer = claims.get("iss")
        if issuer != self.issuer:
            raise TokenVerificationError("emissor_invalido")
        return VerifiedAccessToken(
            issuer=self.issuer,
            subject=subject,
            client_id=client_id if isinstance(client_id, str) else None,
            scopes=scopes,
            raw_claims=claims,
        )


class FakeAccessTokenVerifier:
    def __init__(self) -> None:
        self._tokens: dict[str, VerifiedAccessToken] = {}
        self.unavailable = False

    def register(
        self,
        token: str,
        *,
        issuer: str,
        subject: str,
        client_id: str = "test-client",
        scopes: frozenset[str] | None = None,
        claims: dict[str, Any] | None = None,
    ) -> None:
        self._tokens[token] = VerifiedAccessToken(
            issuer=issuer,
            subject=subject,
            client_id=client_id,
            scopes=scopes or frozenset(),
            raw_claims=claims or {},
        )

    def verify(self, token: str) -> VerifiedAccessToken:
        if self.unavailable:
            raise TokenVerificationError("jwks_indisponivel", unavailable=True)
        found = self._tokens.get(token)
        if found is not None:
            return found
        from app.config import get_settings

        settings = get_settings()
        if settings.auth_verifier == "fake" and settings.env in {"local", "test", "demo"}:
            if token.startswith("panne-demo:"):
                subject = token.split(":", 1)[1]
                # Alias canônico: demo-viewer ≡ demo-reader (leitor econômico).
                if subject == "demo-viewer":
                    subject = "demo-reader"
                return VerifiedAccessToken(
                    issuer=settings.fake_issuer,
                    subject=subject,
                    client_id="panne-demo",
                    scopes=frozenset(),
                    raw_claims={},
                )
            if settings.fake_access_token and token == settings.fake_access_token:
                return VerifiedAccessToken(
                    issuer=settings.fake_issuer,
                    subject=settings.fake_subject,
                    client_id="panne-local",
                    scopes=frozenset(),
                    raw_claims={},
                )
        raise TokenVerificationError("token_invalido")


def _scopes_of(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset(part for part in value.split() if part)
    if isinstance(value, (list, tuple, set)):
        return frozenset(str(item) for item in value if item)
    return frozenset()
