"""Validação positiva de URLs editoriais (imagem e CTA)."""

from __future__ import annotations

from urllib.parse import urlparse

# Hosts padrão para mídia pública do Action Hub / S3 / CloudFront (documentados).
# Sobrescrever via PANNE_LOGIN_EDITORIAL_MEDIA_HOSTS (CSV).
# Inclui hostname virtual-hosted-style regional (us-east-2) e o canônico sem região.
DEFAULT_MEDIA_HOSTS = frozenset(
    {
        "paneldx-cms-assets-2026.s3.amazonaws.com",
        "paneldx-cms-assets-2026.s3.us-east-2.amazonaws.com",
        "paneldx-cms-assets-2026.s3.us-east-1.amazonaws.com",
        "d1panne-cms.cloudfront.net",  # placeholder documentado — ajustar quando houver CF real
    }
)

# Bucket CMS: path público esperado (nunca aceitar objeto fora de /cms/).
_CMS_S3_HOST_SUFFIXES = (
    "paneldx-cms-assets-2026.s3.amazonaws.com",
    "paneldx-cms-assets-2026.s3.us-east-2.amazonaws.com",
    "paneldx-cms-assets-2026.s3.us-east-1.amazonaws.com",
)
_CMS_S3_PATH_PREFIX = "/cms/"


# Hosts HTTPS externos permitidos em CTA (além das rotas internas relativas).
DEFAULT_CTA_HOSTS = frozenset(
    {
        "leaction.com.br",
        "www.leaction.com.br",
        "docs.leaction.com.br",
    }
)

# Prefixos de path relativos bloqueados em CTA (auth / sessão).
_AUTH_PATH_BLOCKLIST = (
    "/entrar",
    "/callback",
    "/logout",
    "/sair",
    "/auth",
    "/oauth",
    "/token",
    "/login",
    "/organizacao",
)


def parse_host_allowlist(raw: str, defaults: frozenset[str]) -> frozenset[str]:
    items = {h.strip().lower() for h in (raw or "").split(",") if h.strip()}
    return frozenset(items) if items else defaults


def _is_safe_relative_path(path: str) -> bool:
    if not path.startswith("/") or path.startswith("//"):
        return False
    if "\\" in path or ".." in path.split("/"):
        return False
    if "@" in path:
        return False
    return True


def _is_cms_s3_host(host: str) -> bool:
    return host in _CMS_S3_HOST_SUFFIXES


def _https_host_allowed(url: str, hosts: frozenset[str]) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme.lower() != "https":
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in {".", "localhost"}:
        return False
    # Rejeitar IP ambíguo / literal sem allowlist explícita
    if host.replace(".", "").isdigit():
        return False
    if host.startswith("[") or (":" in host and host.count(".") == 0):
        return host in hosts
    # Sem wildcard *.amazonaws.com — só igualdade exata (ou subdomínio explícito de host allowlist).
    allowed = host in hosts or any(host == h or host.endswith("." + h) for h in hosts)
    if not allowed:
        return False
    if _is_cms_s3_host(host):
        path = parsed.path or ""
        if not path.startswith(_CMS_S3_PATH_PREFIX):
            return False
        # Evitar path traversal no objeto
        if ".." in path.split("/"):
            return False
    return True



def sanitize_image_url(raw: object, *, media_hosts: frozenset[str]) -> str:
    """
    Imagens: path relativo seguro OU https:// com host na allowlist.
    Rejeita http/ftp/file/javascript/data/vbscript, //, credenciais, hostname vazio.
    """
    text = str(raw or "").strip()
    if not text or len(text) > 240:
        return ""
    lower = text.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "ftp:", "file:", "http://")):
        return ""
    if text.startswith("//"):
        return ""
    if _is_safe_relative_path(text):
        # Só paths de mídia/estáticos locais
        if text.startswith(("/images/", "/assets/", "/static/")):
            return text
        return ""
    if lower.startswith("https://"):
        return text if _https_host_allowed(text, media_hosts) else ""
    return ""


def sanitize_cta_url(raw: object, *, cta_hosts: frozenset[str]) -> str:
    """
    CTA: rota interna relativa autorizada OU https:// em host allowlist.
    Nunca interfere em login/callback/token/logout/provedor.
    """
    text = str(raw or "").strip()
    if not text or len(text) > 240:
        return ""
    lower = text.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "ftp:", "file:", "http://")):
        return ""
    if text.startswith("//"):
        return ""
    if _is_safe_relative_path(text):
        path_only = text.split("?", 1)[0].split("#", 1)[0].lower()
        for blocked in _AUTH_PATH_BLOCKLIST:
            if path_only == blocked or path_only.startswith(blocked + "/"):
                return ""
        # Rotas internas editoriais / docs / marketing locais
        if path_only.startswith(("/docs", "/ajuda", "/sobre", "/privacidade", "/termos")):
            return text
        # Bloquear demais paths internos por padrão (CTA editorial costuma ser externo HTTPS)
        return ""
    if lower.startswith("https://"):
        return text if _https_host_allowed(text, cta_hosts) else ""
    return ""
