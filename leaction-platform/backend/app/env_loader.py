"""Carrega variáveis de ambiente do plugin Marketplace (incl. fallback PanelDX)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def _paneldx_env_candidates() -> list[Path]:
    explicit = (os.getenv("PANELDX_ENV_FILE") or "").strip()
    if explicit:
        return [Path(explicit)]

    env_root = (os.getenv("PANELDX_ROOT") or "").strip()
    roots: list[Path] = []
    if env_root:
        roots.append(Path(env_root))
    roots.extend(
        [
            REPO_ROOT.parent / "PanelDX",
            Path(r"C:\Projetos\PanelDX"),
        ]
    )

    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        for rel in (
            "LeAction_SysF/.env",
            ".env",
            "LeAction_Sys_FE/.env.development",
        ):
            path = (root / rel).resolve()
            if path in seen:
                continue
            seen.add(path)
            candidates.append(path)
    return candidates


def load_marketplace_env() -> None:
    """
    Ordem (primeiro ganha — não sobrescreve variáveis já definidas no processo):
      1. backend/.env
      2. leaction-platform/.env
      3. PanelDX (LeAction_SysF/.env, etc.)
    """
    load_dotenv(BACKEND_DIR / ".env", override=False)
    load_dotenv(REPO_ROOT / ".env", override=False)

    secrets_path = BACKEND_DIR / ".env.ml.secrets"
    if secrets_path.is_file():
        _load_dotenv_nonempty(secrets_path, override=True)

    for path in _paneldx_env_candidates():
        if path.is_file():
            load_dotenv(path, override=False)

    _normalize_ml_env_aliases()


def _load_dotenv_nonempty(path: Path, *, override: bool = False) -> None:
    """Carrega .env ignorando chaves vazias (evita apagar credenciais já definidas)."""
    from dotenv import dotenv_values

    for key, value in dotenv_values(path).items():
        if not key or value is None or not str(value).strip():
            continue
        if override or not os.getenv(key, "").strip():
            os.environ[key] = str(value).strip()


def _normalize_ml_env_aliases() -> None:
    """Unifica nomes ML_APP_ID/ML_SECRET_KEY com aliases legados ML_CLIENT_*."""
    if not os.getenv("ML_APP_ID", "").strip() and os.getenv("ML_CLIENT_ID", "").strip():
        os.environ.setdefault("ML_APP_ID", os.getenv("ML_CLIENT_ID", "").strip())
    if not os.getenv("ML_SECRET_KEY", "").strip() and os.getenv("ML_CLIENT_SECRET", "").strip():
        os.environ.setdefault("ML_SECRET_KEY", os.getenv("ML_CLIENT_SECRET", "").strip())
    if not os.getenv("ML_CLIENT_ID", "").strip() and os.getenv("ML_APP_ID", "").strip():
        os.environ.setdefault("ML_CLIENT_ID", os.getenv("ML_APP_ID", "").strip())
    if not os.getenv("ML_CLIENT_SECRET", "").strip() and os.getenv("ML_SECRET_KEY", "").strip():
        os.environ.setdefault("ML_CLIENT_SECRET", os.getenv("ML_SECRET_KEY", "").strip())
    if not os.getenv("ML_SECRET_KEY", "").strip():
        for alias in ("ML_CLIENT_SECRET", "MP_CLIENT_SECRET", "MERCADOPAGO_CLIENT_SECRET"):
            value = os.getenv(alias, "").strip()
            if value:
                os.environ.setdefault("ML_SECRET_KEY", value)
                break
