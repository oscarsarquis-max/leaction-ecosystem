"""Separação entre URL administrativa e URL de runtime. Sem fallback silencioso."""

from urllib.parse import urlparse


class RuntimeUrlError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def is_placeholder_url(url: str, *, kind: str) -> bool:
    if not url or "://" not in url:
        return True
    return f"<configure-{kind}-" in url


def connection_identity(url: str) -> tuple[str | None, str | None, str | None, str]:
    parsed = urlparse(url)
    port = str(parsed.port) if parsed.port else None
    return (parsed.username, parsed.hostname, port, parsed.path)


def uses_same_database_role(admin_url: str, runtime_url: str) -> bool:
    admin = connection_identity(admin_url)
    runtime = connection_identity(runtime_url)
    return admin == runtime


def configured_runtime_url(admin_url: str, runtime_url: str) -> str | None:
    """Devolve a URL de runtime ou None. Nunca devolve a URL administrativa."""
    if is_placeholder_url(runtime_url, kind="runtime"):
        return None
    if uses_same_database_role(admin_url, runtime_url):
        raise RuntimeUrlError("runtime_nao_separado")
    return runtime_url
