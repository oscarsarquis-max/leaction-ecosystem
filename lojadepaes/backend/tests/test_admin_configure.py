from collections.abc import Iterator
from pathlib import Path

import pytest
from app.admin.configure import (
    ADMIN_HASH,
    ADMIN_SECRET,
    ADMIN_USERNAME,
    configure_admin,
    read_env_map,
)
from argon2 import PasswordHasher


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    return tmp_path


def _run(
    workspace: Path,
    *,
    replace: bool = False,
    username: str = "padaria-local",
    password: str = "senha-de-teste-nao-usar",
    confirm: str | None = None,
    existing: str = "",
) -> str:
    env_path = workspace / ".env"
    if existing:
        env_path.write_text(existing, encoding="utf-8")
    secrets: Iterator[str] = iter([password, confirm if confirm is not None else password])

    def ask(message: str) -> str:
        if "SUBSTITUIR" in message:
            return "SUBSTITUIR" if replace else "nao"
        return username

    def secret(_message: str) -> str:
        return next(secrets)

    return configure_admin(
        env_path=env_path,
        repo_root=workspace,
        replace=replace,
        ask=ask,
        secret=secret,
    )


def test_writes_hash_not_password_and_keeps_other_keys(workspace: Path) -> None:
    env_path = workspace / ".env"
    env_path.write_text("LOJADEPAES_ENV=local\n", encoding="utf-8")
    message = _run(workspace)
    text = env_path.read_text(encoding="utf-8")
    values = read_env_map(env_path)
    assert "conta administrativa gravada" in message
    assert "LOJADEPAES_ENV=local" in text
    assert values[ADMIN_USERNAME] == "padaria-local"
    assert "senha-de-teste-nao-usar" not in text
    assert "senha-de-teste-nao-usar" not in message
    assert values[ADMIN_HASH] not in message
    assert values[ADMIN_SECRET] not in message
    assert len(values[ADMIN_SECRET]) >= 32
    PasswordHasher().verify(values[ADMIN_HASH], "senha-de-teste-nao-usar")


def test_preserves_existing_account_without_replace(workspace: Path) -> None:
    existing = (
        "LOJADEPAES_ADMIN_USERNAME='ja-existe'\n"
        "LOJADEPAES_ADMIN_PASSWORD_HASH='hash-antigo'\n"
        "LOJADEPAES_ADMIN_SESSION_SECRET='segredo-antigo-com-mais-de-32-chars'\n"
    )
    with pytest.raises(SystemExit, match="preservada"):
        _run(workspace, existing=existing, replace=False)
    values = read_env_map(workspace / ".env")
    assert values[ADMIN_USERNAME] == "ja-existe"
    assert values[ADMIN_HASH] == "hash-antigo"
    assert values[ADMIN_SECRET] == "segredo-antigo-com-mais-de-32-chars"


def test_replace_keeps_existing_session_secret(workspace: Path) -> None:
    existing = (
        "LOJADEPAES_ADMIN_USERNAME='ja-existe'\n"
        "LOJADEPAES_ADMIN_PASSWORD_HASH='hash-antigo'\n"
        "LOJADEPAES_ADMIN_SESSION_SECRET='segredo-antigo-com-mais-de-32-chars'\n"
    )
    _run(workspace, existing=existing, replace=True, username="novo-login")
    values = read_env_map(workspace / ".env")
    assert values[ADMIN_USERNAME] == "novo-login"
    assert values[ADMIN_HASH] != "hash-antigo"
    assert values[ADMIN_SECRET] == "segredo-antigo-com-mais-de-32-chars"


def test_password_mismatch(workspace: Path) -> None:
    with pytest.raises(SystemExit, match="senhas"):
        _run(workspace, confirm="outra")


def test_ensure_local_secret_writes_once_and_keeps_existing(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.admin.configure import ADMIN_SECRET, ensure_local_session_secret
    from app.core.config import get_settings

    env_path = workspace / ".env"
    env_path.write_text(
        "LOJADEPAES_ENV=local\nLOJADEPAES_HTTP_HOST=127.0.0.1\nLOJADEPAES_ADMIN_LOCAL_PASSWORDLESS=true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOJADEPAES_ENV", "local")
    monkeypatch.setenv("LOJADEPAES_HTTP_HOST", "127.0.0.1")
    monkeypatch.setenv("LOJADEPAES_ADMIN_LOCAL_PASSWORDLESS", "true")
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", "")
    get_settings.cache_clear()
    assert ensure_local_session_secret(env_path) is True
    first = read_env_map(env_path)[ADMIN_SECRET]
    assert len(first) >= 32
    assert ensure_local_session_secret(env_path) is False
    assert read_env_map(env_path)[ADMIN_SECRET] == first


def test_ensure_skips_when_called_without_path_under_pytest() -> None:
    from app.admin.configure import ensure_local_session_secret

    assert ensure_local_session_secret() is False


def test_refuses_when_env_not_gitignored(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="ignorado"):
        configure_admin(
            env_path=tmp_path / ".env",
            repo_root=tmp_path,
            replace=False,
            ask=lambda _m: "alguem",
            secret=lambda _m: "x",
        )
