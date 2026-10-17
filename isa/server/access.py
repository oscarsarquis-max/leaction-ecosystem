"""Dono a partir de identidade validada. O laboratório não passa por aqui."""

import os

import jwt

import oidc


def oidc_ready():
    return oidc.ready()


def allowed_subs():
    raw = os.environ.get("ISA_OIDC_ALLOWED_SUBS") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def authorize_url(state, verifier):
    if not oidc_ready():
        return None
    return oidc.authorize_url(state, verifier)


def recovery_url():
    if not oidc_ready():
        return None
    return oidc.recovery_url()


def claims_from_bearer(header):
    if not header or not header.startswith("Bearer "):
        raise jwt.InvalidTokenError("sem token")
    if not oidc_ready():
        raise jwt.InvalidTokenError("diretório desligado")
    token = header.split(" ", 1)[1].strip()
    return oidc.claims_from_access_token(token)
