class AuthError(Exception):
    """Credenciais inválidas."""


class RateLimitError(Exception):
    """Falhas demais de login."""


class AuthDisabledError(Exception):
    """Sessão não configurada (segredo ausente ou curto)."""
