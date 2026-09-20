"""Configura o primeiro administrador no .env local. Não é uma rota HTTP."""

from __future__ import annotations

import argparse
import os
import secrets
from collections.abc import Callable
from getpass import getpass
from pathlib import Path

from argon2 import PasswordHasher

ADMIN_USERNAME = "LOJADEPAES_ADMIN_USERNAME"
ADMIN_HASH = "LOJADEPAES_ADMIN_PASSWORD_HASH"
ADMIN_SECRET = "LOJADEPAES_ADMIN_SESSION_SECRET"
REPLACE_TOKEN = "SUBSTITUIR"
_hasher = PasswordHasher()


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_env_path() -> Path:
    return backend_root() / ".env"


def env_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def parse_env_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def read_env_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        values[key.strip()] = parse_env_value(raw)
    return values


def upsert_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            out.append(f"{key}={env_quote(updates[key])}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={env_quote(value)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def gitignore_covers_env(repo_root: Path) -> bool:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return False
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if item in {".env", "**/.env", "/.env"} or item.endswith(".env"):
            return True
    return False


def account_present(values: dict[str, str]) -> bool:
    return bool(values.get(ADMIN_USERNAME, "").strip() or values.get(ADMIN_HASH, "").strip())


def secret_present(values: dict[str, str]) -> bool:
    return len(values.get(ADMIN_SECRET, "").strip()) >= 32


def configure_admin(
    *,
    env_path: Path,
    repo_root: Path,
    replace: bool,
    ask: Callable[[str], str],
    secret: Callable[[str], str],
) -> str:
    if not gitignore_covers_env(repo_root):
        raise SystemExit("recusa: .env não está ignorado pelo Git")
    current = read_env_map(env_path)
    if account_present(current) and not replace:
        confirmation = ask(
            "Já existe uma conta administrativa. Digite SUBSTITUIR para trocar: "
        ).strip()
        if confirmation != REPLACE_TOKEN:
            raise SystemExit("nenhuma alteração: a configuração existente foi preservada")
    username = ask("Login administrativo: ").strip()
    if not username or len(username) > 80 or "\n" in username:
        raise SystemExit("login vazio ou inválido")
    password = secret("Senha administrativa (não ecoa): ")
    confirm = secret("Confirme a senha: ")
    if not password or password != confirm:
        raise SystemExit("senhas vazias ou diferentes")
    password_hash = _hasher.hash(password)
    session_secret = current.get(ADMIN_SECRET, "").strip()
    if len(session_secret) < 32:
        session_secret = secrets.token_urlsafe(48)
    upsert_env(
        env_path,
        {
            ADMIN_USERNAME: username,
            ADMIN_HASH: password_hash,
            ADMIN_SECRET: session_secret,
        },
    )
    return "conta administrativa gravada no ambiente local; reinicie a API"


def ensure_local_session_secret(env_path: Path | None = None) -> bool:
    """Gera o segredo de sessão local se o modo sem senha estiver pedido e o segredo faltar.

    Não pede senha, não imprime o segredo e não sobrescreve um valor válido.
    """
    if env_path is None and os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    from app.core.config import _is_loopback_bind, get_settings

    get_settings.cache_clear()
    settings = get_settings()
    env_name = settings.env.strip().lower()
    if not settings.admin_local_passwordless:
        return False
    if env_name in {"production", "prod"} or env_name not in {"local", "development", "dev"}:
        return False
    if not _is_loopback_bind(settings.http_host):
        return False
    path = env_path or default_env_path()
    if secret_present(read_env_map(path)):
        return False
    if len(settings.admin_session_secret.strip()) >= 32:
        return False
    upsert_env(path, {ADMIN_SECRET: secrets.token_urlsafe(48)})
    get_settings.cache_clear()
    return True


def main(
    argv: list[str] | None = None,
    *,
    env_path: Path | None = None,
    repo_root: Path | None = None,
    ask: Callable[[str], str] = input,
    secret: Callable[[str], str] = getpass,
) -> None:
    parser = argparse.ArgumentParser(
        description="Configura o primeiro administrador da Loja de Pães no .env local."
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="substitui a conta existente (não altera em silêncio sem esta opção ou SUBSTITUIR)",
    )
    args = parser.parse_args(argv)
    message = configure_admin(
        env_path=env_path or default_env_path(),
        repo_root=repo_root or backend_root().parent,
        replace=args.replace,
        ask=ask,
        secret=secret,
    )
    print(message)
