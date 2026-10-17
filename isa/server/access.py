"""Dono a partir de identidade validada. O laboratório não passa por aqui."""

import base64
import hashlib
import json
import os

import jwt
from jwt import PyJWK


def oidc_ready():
    needed = ("ISA_OIDC_ISSUER", "ISA_OIDC_AUDIENCE", "ISA_OIDC_JWKS", "ISA_OIDC_CLIENT_ID")
    return all(os.environ.get(name) for name in needed)


def allowed_subs():
    raw = os.environ.get("ISA_OIDC_ALLOWED_SUBS") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def authorize_url(state, verifier):
    if not oidc_ready():
        return None
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    redirect = os.environ.get("ISA_OIDC_REDIRECT") or "https://isa.actionhub.com.br/callback"
    query = (
        "response_type=code&client_id=" + os.environ["ISA_OIDC_CLIENT_ID"]
        + "&redirect_uri=" + redirect
        + "&scope=openid"
        + "&code_challenge=" + challenge
        + "&code_challenge_method=S256"
        + "&state=" + state
    )
    return os.environ["ISA_OIDC_ISSUER"].rstrip("/") + "/oauth2/authorize?" + query


def claims_from_bearer(header):
    if not header or not header.startswith("Bearer "):
        raise jwt.InvalidTokenError("sem token")
    if not oidc_ready():
        raise jwt.InvalidTokenError("diretório desligado")
    token = header.split(" ", 1)[1].strip()
    unverified = jwt.get_unverified_header(token)
    if unverified.get("alg") != "RS256":
        raise jwt.InvalidTokenError("algoritmo")
    jwks = json.loads(os.environ["ISA_OIDC_JWKS"])
    key = None
    for item in jwks.get("keys") or []:
        if item.get("kid") == unverified.get("kid"):
            key = PyJWK.from_dict(item).key
            break
    if key is None:
        raise jwt.InvalidTokenError("chave")
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=os.environ["ISA_OIDC_AUDIENCE"],
        issuer=os.environ["ISA_OIDC_ISSUER"],
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
