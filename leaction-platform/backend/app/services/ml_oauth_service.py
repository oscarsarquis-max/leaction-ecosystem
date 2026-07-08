"""OAuth 2.0 Mercado Livre — persistência de tokens e refresh automático."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def resolve_tokens_file() -> Path:
    explicit = (os.getenv("ML_TOKENS_FILE") or "").strip()
    if explicit:
        return Path(explicit)

    backend_tokens = BACKEND_DIR / ".ml_tokens.json"
    persistent = Path("/var/lib/leaction-platform/.ml_tokens.json")

    if persistent.is_file():
        return persistent
    if backend_tokens.is_file():
        return backend_tokens
    if str(BACKEND_DIR).startswith("/var/www/"):
        return persistent
    return backend_tokens


def _tokens_path() -> Path:
    """Resolve path após load_marketplace_env (evita path congelado no import)."""
    return resolve_tokens_file()
# API global ML — manter mercadolibre.com (domínio oficial da API).
ML_API_BASE_URL = "https://api.mercadolibre.com"
TOKEN_URL = f"{ML_API_BASE_URL}/oauth/token"
# Brasil — auth e painel usam mercadolivre.com.br (mercadolibre.com.br costuma falhar no browser).
ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
ML_DEVELOPERS_URL = "https://developers.mercadolivre.com.br"
TOKEN_SKEW_S = 60
OAUTH_CALLBACK_PATH = "/marketplace-api/ml/callback"
DEFAULT_OAUTH_SCOPE = "offline_access read write"

_file_lock = threading.Lock()


class MercadoLivreOAuthError(Exception):
    """Falha no fluxo OAuth do Mercado Livre."""


def resolve_app_id() -> str:
    """App ID — ML_APP_ID, alias ML_CLIENT_ID ou derivado do MP_ACCESS_TOKEN (mesma app MP)."""
    direct = (os.getenv("ML_APP_ID") or os.getenv("ML_CLIENT_ID") or "").strip()
    if direct:
        return direct
    return _app_id_from_mp_access_token()


def _app_id_from_mp_access_token() -> str:
    """
    Extrai Application ID do token Mercado Pago (formato TEST-{app_id}-...).
    Mesma aplicação no painel developers.mercadolivre.com.br quando checkout MP está ativo.
    """
    token = (
        os.getenv("MP_ACCESS_TOKEN")
        or os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        or ""
    ).strip()
    if not token:
        return ""
    parts = token.split("-")
    if len(parts) >= 5 and parts[0] in ("TEST", "APP_USR", "APP") and parts[1].isdigit():
        return parts[1]
    return ""


def resolve_secret_key() -> str:
    """Secret — ML_SECRET_KEY, alias ML_CLIENT_SECRET ou MP_CLIENT_SECRET (mesma app)."""
    return (
        os.getenv("ML_SECRET_KEY")
        or os.getenv("ML_CLIENT_SECRET")
        or os.getenv("MP_CLIENT_SECRET")
        or os.getenv("MERCADOPAGO_CLIENT_SECRET")
        or ""
    ).strip()


def resolve_redirect_uri() -> str:
    """
    Redirect URI OAuth — Mercado Livre exige HTTPS (http://localhost é rejeitado).

    Ordem:
      1. ML_REDIRECT_URI (URL completa HTTPS)
      2. ML_PUBLIC_BASE_URL + /api/marketplace/ml/callback (túnel ngrok/cloudflared)
    """
    explicit = (os.getenv("ML_REDIRECT_URI") or "").strip()
    if explicit:
        return explicit

    base = (os.getenv("ML_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if base:
        return f"{base}{OAUTH_CALLBACK_PATH}"
    return ""


def validate_redirect_uri(uri: str | None = None) -> tuple[bool, str | None]:
    """Valida redirect para o painel ML (HTTPS obrigatório)."""
    target = (uri or resolve_redirect_uri()).strip()
    if not target:
        return (
            False,
            "Configure ML_REDIRECT_URI (HTTPS) ou ML_PUBLIC_BASE_URL com túnel "
            "(ex.: cloudflared tunnel --url http://127.0.0.1:4012).",
        )
    if not target.lower().startswith("https://"):
        return (
            False,
            "Mercado Livre não aceita redirect URI sem HTTPS. "
            "Use ngrok/cloudflared e defina ML_PUBLIC_BASE_URL=https://seu-tunel...",
        )
    return True, None


def oauth_setup_info() -> dict[str, Any]:
    """Metadados para cadastro no painel ML e login via túnel."""
    redirect_uri = resolve_redirect_uri()
    valid, error = validate_redirect_uri(redirect_uri)
    login_url = None
    if valid and redirect_uri.endswith("/callback"):
        login_url = f"{redirect_uri[:-len('/callback')]}/login"

    return {
        "redirect_uri": redirect_uri or None,
        "redirect_uri_https": valid,
        "redirect_uri_error": error,
        "login_url": login_url,
        "callback_path": OAUTH_CALLBACK_PATH,
        "developers_url": ML_DEVELOPERS_URL,
        "tunnel_hint": (
            "Dev local: cloudflared tunnel --url http://127.0.0.1:4012 "
            "→ copie a URL https e defina ML_PUBLIC_BASE_URL no backend/.env"
        ),
    }


def is_oauth_app_configured() -> bool:
    return bool(resolve_app_id() and resolve_secret_key())


def has_persisted_or_env_tokens() -> bool:
    if os.getenv("ML_ACCESS_TOKEN", "").strip():
        return True
    if os.getenv("ML_REFRESH_TOKEN", "").strip():
        return True
    stored = _read_tokens_file()
    return bool(stored.get("refresh_token") or stored.get("access_token"))


def resolve_oauth_scope() -> str:
    return (os.getenv("ML_OAUTH_SCOPE") or DEFAULT_OAUTH_SCOPE).strip() or DEFAULT_OAUTH_SCOPE


def build_authorization_url(*, state: str | None = None) -> str:
    app_id = resolve_app_id()
    if not app_id:
        raise MercadoLivreOAuthError(
            "Configure ML_APP_ID (ou ML_CLIENT_ID) em backend/.env"
        )

    redirect_uri = resolve_redirect_uri()
    ok, err = validate_redirect_uri(redirect_uri)
    if not ok:
        raise MercadoLivreOAuthError(err or "Redirect URI OAuth inválida")

    params: dict[str, str] = {
        "response_type": "code",
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": resolve_oauth_scope(),
        "prompt": "consent",
    }
    if state:
        params["state"] = state

    return f"{ML_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_authorization_code(code: str) -> dict[str, Any]:
    app_id = resolve_app_id()
    secret = resolve_secret_key()
    if not (app_id and secret):
        raise MercadoLivreOAuthError(
            "Configure ML_APP_ID e ML_SECRET_KEY (ou ML_CLIENT_ID / ML_CLIENT_SECRET)"
        )

    payload = _request_token(
        {
            "grant_type": "authorization_code",
            "client_id": app_id,
            "client_secret": secret,
            "code": code.strip(),
            "redirect_uri": resolve_redirect_uri(),
        }
    )
    oauth_refresh = _extract_refresh_token(payload)
    if oauth_refresh:
        logger.info(
            "Mercado Livre OAuth: refresh_token recebido no callback (len=%d)",
            len(oauth_refresh),
        )
    else:
        logger.warning(
            "Mercado Livre OAuth: resposta sem refresh_token (keys=%s)",
            sorted(payload.keys()),
        )
    return _persist_token_response(payload, require_refresh=False)


def get_valid_access_token(*, force_refresh: bool = False) -> str | None:
    """
    Retorna Bearer token válido para /sites/MLB/search.
    Ordem: ML_ACCESS_TOKEN (.env) → arquivo .ml_tokens.json → refresh via ML_REFRESH_TOKEN.
    """
    direct = os.getenv("ML_ACCESS_TOKEN", "").strip()
    if direct and not force_refresh:
        return direct

    with _file_lock:
        stored = _read_tokens_file()
        now = time.time()

        access_token = str(stored.get("access_token") or "").strip()
        expires_at = float(stored.get("expires_at") or 0)
        refresh_token = str(stored.get("refresh_token") or "").strip()

        if not refresh_token:
            refresh_token = os.getenv("ML_REFRESH_TOKEN", "").strip()

        if access_token and not force_refresh and expires_at > now + TOKEN_SKEW_S:
            return access_token

        if not refresh_token:
            if access_token and not force_refresh:
                logger.warning(
                    "Token ML sem expires_at/refresh — usando access_token persistido"
                )
                return access_token
            logger.warning(
                "Mercado Livre OAuth: nenhum token disponível. "
                "Acesse GET /api/marketplace/ml/login para autenticar."
            )
            return None

        try:
            refreshed = _refresh_access_token(refresh_token)
        except MercadoLivreOAuthError as exc:
            logger.error("Mercado Livre OAuth refresh falhou: %s", exc)
            return None

        token = str(refreshed.get("access_token") or "").strip()
        return token or None


def _refresh_access_token(refresh_token: str) -> dict[str, Any]:
    app_id = resolve_app_id()
    secret = resolve_secret_key()
    if not (app_id and secret):
        raise MercadoLivreOAuthError("Credenciais OAuth do Mercado Livre não configuradas")

    payload = _request_token(
        {
            "grant_type": "refresh_token",
            "client_id": app_id,
            "client_secret": secret,
            "refresh_token": refresh_token,
        }
    )
    return _persist_token_response(payload, require_refresh=True)


def _extract_refresh_token(payload: dict[str, Any]) -> str:
    """Extrai refresh_token da resposta JSON do POST oauth/token."""
    raw = payload.get("refresh_token")
    if raw is None:
        return ""
    return str(raw).strip()


def _persist_token_response(
    payload: dict[str, Any],
    *,
    require_refresh: bool = False,
) -> dict[str, Any]:
    access_token = str(payload.get("access_token") or "").strip()
    if not access_token:
        raise MercadoLivreOAuthError("Resposta OAuth sem access_token")

    oauth_refresh = _extract_refresh_token(payload)
    persisted_refresh = ""
    if oauth_refresh:
        persisted_refresh = oauth_refresh
    else:
        persisted_refresh = str(_read_tokens_file().get("refresh_token") or "").strip()
    if not persisted_refresh:
        persisted_refresh = os.getenv("ML_REFRESH_TOKEN", "").strip()

    expires_in = int(payload.get("expires_in") or 21600)
    record: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": persisted_refresh,
        "expires_at": time.time() + max(expires_in, 300),
        "token_type": str(payload.get("token_type") or "bearer"),
        "scope": payload.get("scope"),
        "user_id": payload.get("user_id"),
        "updated_at": time.time(),
    }

    if not record["refresh_token"]:
        granted_scope = str(payload.get("scope") or record.get("scope") or "")
        logger.warning(
            "Mercado Livre OAuth sem refresh_token. scope_concedido=%r",
            granted_scope[:200],
        )
        if require_refresh:
            raise MercadoLivreOAuthError("Resposta OAuth sem refresh_token")

    tokens_path = _write_tokens_file(record)

    if oauth_refresh:
        logger.info("Mercado Livre OAuth: refresh_token persistido em %s", tokens_path)

    return record


def _request_token(form: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "LeAction-Marketplace-Plugin/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise MercadoLivreOAuthError(
            f"OAuth token falhou (HTTP {exc.code}): {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise MercadoLivreOAuthError("Não foi possível contactar oauth/token") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MercadoLivreOAuthError("Resposta OAuth inválida") from exc

    if not isinstance(data, dict):
        raise MercadoLivreOAuthError("Formato OAuth inesperado")
    return data


def _read_tokens_file() -> dict[str, Any]:
    path = _tokens_path()
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Não foi possível ler %s: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _write_tokens_file(record: dict[str, Any]) -> Path:
    path = _tokens_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except OSError as exc:
        raise MercadoLivreOAuthError(f"Não foi possível salvar tokens em {path}") from exc
    return path
