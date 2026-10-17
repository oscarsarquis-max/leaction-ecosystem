"""Login por descoberta. O emissor do token e o endereço de entrada não são o mesmo campo."""

import base64
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

import jwt
from jwt import PyJWK

_discovery = {"at": 0, "body": None}
_jwks = {"at": 0, "keys": []}


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def reset():
    _discovery["at"] = 0
    _discovery["body"] = None
    _jwks["at"] = 0
    _jwks["keys"] = []


def discovery():
    issuer = os.environ.get("ISA_OIDC_ISSUER") or ""
    local = issuer.startswith("http://127.") or issuer.startswith("http://localhost") or issuer.startswith("http://[::1]")
    if local and os.environ.get("ISA_OIDC_REHEARSAL") != "1":
        raise jwt.InvalidTokenError("emissor de ensaio recusado")
    url = os.environ.get("ISA_OIDC_DISCOVERY") or ""
    if not url:
        raise jwt.InvalidTokenError("diretório sem descoberta")
    if _discovery["body"] and time.time() - _discovery["at"] < 300:
        return _discovery["body"]
    body = _get(url)
    issuer = os.environ.get("ISA_OIDC_ISSUER") or ""
    if body.get("issuer") != issuer:
        raise jwt.InvalidTokenError("descoberta de outro emissor")
    for name in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not body.get(name):
            raise jwt.InvalidTokenError("descoberta incompleta")
    _discovery["body"] = body
    _discovery["at"] = time.time()
    return body


def ready():
    return bool(os.environ.get("ISA_OIDC_ISSUER") and os.environ.get("ISA_OIDC_CLIENT_ID") and os.environ.get("ISA_OIDC_DISCOVERY"))


def authorize_url(state, verifier):
    body = discovery()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    redirect = os.environ.get("ISA_OIDC_REDIRECT") or "https://isa.actionhub.com.br/callback"
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": os.environ["ISA_OIDC_CLIENT_ID"],
        "redirect_uri": redirect,
        "scope": "openid",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    return body["authorization_endpoint"] + "?" + query


def recovery_url():
    configured = os.environ.get("ISA_OIDC_RECOVERY") or ""
    if configured:
        return configured
    body = discovery()
    return body.get("recovery_endpoint") or ""


def exchange(code, verifier):
    body = discovery()
    redirect = os.environ.get("ISA_OIDC_REDIRECT") or "https://isa.actionhub.com.br/callback"
    payload = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "client_id": os.environ["ISA_OIDC_CLIENT_ID"],
        "code_verifier": verifier,
    }).encode("utf-8")
    request = urllib.request.Request(body["token_endpoint"], data=payload, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(request, timeout=5) as response:
        token_body = json.loads(response.read().decode("utf-8"))
    token = token_body.get("access_token")
    if not token:
        raise jwt.InvalidTokenError("resposta sem token de acesso")
    return token


def _keys(force=False):
    if _jwks["keys"] and not force and time.time() - _jwks["at"] < 300:
        return _jwks["keys"]
    body = discovery()
    loaded = _get(body["jwks_uri"]).get("keys") or []
    _jwks["keys"] = loaded
    _jwks["at"] = time.time()
    return loaded


def claims_from_access_token(token):
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256":
        raise jwt.InvalidTokenError("algoritmo")
    kid = header.get("kid")
    key = _match(kid, _keys())
    if key is None:
        key = _match(kid, _keys(force=True))
    if key is None:
        raise jwt.InvalidTokenError("chave")
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        issuer=os.environ["ISA_OIDC_ISSUER"],
        options={"require": ["exp", "iss", "sub"], "verify_aud": False},
    )
    if claims.get("token_use") not in (None, "access"):
        raise jwt.InvalidTokenError("o token de identidade não autoriza a API")
    if claims.get("token_use") == "id":
        raise jwt.InvalidTokenError("token de identidade")
    client = os.environ["ISA_OIDC_CLIENT_ID"]
    audience = claims.get("client_id") or claims.get("aud")
    if isinstance(audience, list):
        audience = audience[0] if audience else ""
    if audience != client:
        raise jwt.InvalidTokenError("destinatário")
    return claims


def _match(kid, keys):
    for item in keys:
        if item.get("kid") == kid:
            return PyJWK.from_dict(item).key
    return None
