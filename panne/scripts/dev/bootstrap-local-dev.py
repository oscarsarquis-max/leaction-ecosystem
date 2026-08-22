"""Prepara runtime local e o primeiro proprietário. Sem imprimir segredos."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
BACKEND = ROOT / "backend"


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value
    return values


def _write_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _runtime_url(admin_url: str, password: str) -> str:
    parsed = urlparse(admin_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5434
    netloc = f"panne_runtime:{password}@{host}:{port}"
    return urlunparse((parsed.scheme, netloc, "/panne", "", "", ""))


def main() -> None:
    os.chdir(BACKEND)
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    env = _load_env(ENV_PATH)
    admin = env.get("PANNE_DATABASE_URL", "")
    if "://" not in admin:
        raise SystemExit("PANNE_DATABASE_URL ausente no .env local.")
    password = os.environ.get("PANNE_RUNTIME_PASSWORD", "panne_runtime_test")
    updates = {
        "PANNE_RUNTIME_DATABASE_URL": env.get("PANNE_RUNTIME_DATABASE_URL")
        if env.get("PANNE_RUNTIME_DATABASE_URL")
        and "<configure-runtime-" not in env.get("PANNE_RUNTIME_DATABASE_URL", "")
        else _runtime_url(admin, password),
        "PANNE_AUTH_VERIFIER": env.get("PANNE_AUTH_VERIFIER") or "fake",
        "PANNE_FAKE_ACCESS_TOKEN": env.get("PANNE_FAKE_ACCESS_TOKEN") or "panne-fake-access-token",
        "PANNE_FAKE_ISSUER": env.get("PANNE_FAKE_ISSUER") or "https://panne.local/fake",
        "PANNE_FAKE_SUBJECT": env.get("PANNE_FAKE_SUBJECT") or "local-dev-owner",
    }
    _write_env(ENV_PATH, updates)

    from app.config import get_settings
    from app.modules.identity_organization.models import AuthIdentity
    from app.modules.identity_organization.services import (
        IdentityResolutionError,
        bootstrap_first_owner,
    )
    from tests.rls_support import ensure_runtime_role

    get_settings.cache_clear()
    settings = get_settings()
    sync = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(sync, future=True)
    ensure_runtime_role(engine)
    factory = sessionmaker(bind=engine, future=True)
    session = factory()
    try:
        issuer = settings.fake_issuer
        subject = settings.fake_subject
        existing = session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.issuer == issuer,
                AuthIdentity.subject == subject,
            )
        )
        if existing is None:
            try:
                bootstrap_first_owner(
                    session,
                    issuer=issuer,
                    subject=subject,
                    email="ana.padeiro@panne.local",
                    display_name="Ana Padeiro",
                    organization_slug="panne-local",
                    legal_name="Panne Local LTDA",
                    organization_display_name="Padaria Central",
                    role="owner",
                )
                session.commit()
            except IdentityResolutionError:
                session.rollback()
                raise
        else:
            session.rollback()
    finally:
        session.close()
        engine.dispose()
    print("runtime e proprietario local prontos")


if __name__ == "__main__":
    main()
