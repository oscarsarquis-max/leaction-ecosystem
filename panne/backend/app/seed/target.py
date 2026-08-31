"""Guardas de alvo. Recusa panne, produção e sufixo inválido."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

ALLOWED_ENV = frozenset({"local", "demo", "test"})
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "host.docker.internal", "::1"})
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,48}(_demo|_smoke)$")


class SeedTargetError(ValueError):
    pass


def sync_url(url: str) -> str:
    raw = url.strip()
    if "mysql" in raw.lower():
        raise SeedTargetError("alvo mysql proibido")
    return raw.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def parse_database_name(url: str) -> str:
    parsed = urlparse(sync_url(url))
    return parsed.path.lstrip("/").split("?")[0]


def _rds_host_allowed(host: str, name: str) -> bool:
    """Homologação: RDS demo só com flags explícitas e host exato."""
    if os.environ.get("PANNE_SEED_ALLOW_RDS", "").strip() != "1":
        return False
    expected = (os.environ.get("PANNE_SEED_RDS_HOST") or "").strip().lower()
    if not expected or host != expected:
        return False
    return name.endswith("_demo") and name != "panne"


def assert_seed_target(url: str, env: str) -> str:
    if env == "production":
        raise SeedTargetError("ambiente production recusado")
    if env not in ALLOWED_ENV:
        raise SeedTargetError(f"ambiente recusado: {env}")
    parsed = urlparse(sync_url(url))
    if parsed.scheme.split("+")[0] != "postgresql":
        raise SeedTargetError("mecanismo inválido")
    host = (parsed.hostname or "").lower()
    name = parse_database_name(url)
    if name == "panne":
        raise SeedTargetError("banco lógico panne recusado")
    if not NAME_RE.fullmatch(name):
        raise SeedTargetError(f"sufixo inválido: {name}")
    if host not in ALLOWED_HOSTS and not _rds_host_allowed(host, name):
        raise SeedTargetError(f"host recusado: {host or 'vazio'}")
    return name


def describe_target(url: str, env: str) -> dict[str, str]:
    parsed = urlparse(sync_url(url))
    name = assert_seed_target(url, env)
    return {
        "env": env,
        "host": parsed.hostname or "",
        "port": str(parsed.port or ""),
        "database": name,
        "user": parsed.username or "",
    }
