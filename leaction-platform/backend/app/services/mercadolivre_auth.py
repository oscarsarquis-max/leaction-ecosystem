"""Resolução de access token Mercado Livre — delega ao ml_oauth_service."""

from __future__ import annotations

from app.services.ml_oauth_service import (
    MercadoLivreOAuthError,
    get_valid_access_token,
    has_persisted_or_env_tokens,
    is_oauth_app_configured,
)


class MercadoLivreAuthError(Exception):
    """Falha ao obter token OAuth do Mercado Livre."""


def is_ml_api_configured() -> bool:
    """True se há tokens disponíveis ou credenciais OAuth da aplicação ML."""
    if has_persisted_or_env_tokens():
        return True
    return is_oauth_app_configured()


def resolve_access_token(*, force_refresh: bool = False) -> str | None:
    """Compatibilidade legada — usa get_valid_access_token do serviço OAuth."""
    try:
        return get_valid_access_token(force_refresh=force_refresh)
    except MercadoLivreOAuthError as exc:
        raise MercadoLivreAuthError(str(exc)) from exc
