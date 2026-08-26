"""Webhook S2S do Cofre — criar / rotacionar contas privilegiadas."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

DATABASE_URL = "postgresql+psycopg2://postgres:password@127.0.0.1:5435/orquestrador"
VAULT_SECRET = "f3e6fe344ec367f48bb2ee38842971a3390d7dd7a72e2d7fe1177bb23304a70a"
WRONG_SECRET = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ENDPOINT = "/api/webhooks/contas"


def _db_available() -> bool:
    try:
        eng = create_engine(DATABASE_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="Postgres Phanton :5435 indisponível"
)


@pytest.fixture()
def db():
    from auth import User
    from database import Base
    import services.crystal_ball.models  # noqa: F401

    eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=eng)
    with eng.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE crystal_shadow_runs "
                "ADD COLUMN IF NOT EXISTS owned_by_user_id UUID"
            )
        )
        _sql07 = (_ROOT / "database" / "07_identidade.sql").read_text(encoding="utf-8")
        for stmt in [s.strip() for s in _sql07.split(";") if s.strip()]:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
    Session = sessionmaker(bind=eng)
    session = Session()
    yield session
    session.rollback()
    session.close()
    eng.dispose()


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setenv("PHANTON_VAULT_CONTA_SECRET", VAULT_SECRET)
    from main import app
    from database import get_db

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _s2s_headers(secret: str = VAULT_SECRET) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {secret}",
        "X-App-Secret": secret,
    }


def _wipe_email(db, email: str) -> None:
    from auth import User

    old = db.query(User).filter((User.username == email) | (User.email == email)).all()
    for row in old:
        db.delete(row)
    if old:
        db.commit()


def test_criar_conta_nova(client, db, monkeypatch):
    from auth import User, verify_password

    email = "vault.criar@test.local"
    _wipe_email(db, email)
    sync_calls: list[dict] = []

    def _sync(**kwargs):
        sync_calls.append(kwargs)
        return True, None

    monkeypatch.setattr("contas_webhook.sync_usuario_hub", _sync)

    r = client.post(
        ENDPOINT,
        headers=_s2s_headers(),
        json={
            "acao": "criar",
            "email": email,
            "senha": "SenhaVault-1",
            "nivel": "admin",
            "funcao": "homologacao",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "email": email}

    row = db.query(User).filter(User.email == email).one()
    assert row.role is None
    assert row.nivel == "admin"
    assert row.funcao == "homologacao"
    assert row.username == email
    assert row.sync_pendente is False
    assert verify_password("SenhaVault-1", row.password_hash)
    assert len(sync_calls) == 1
    assert sync_calls[0]["email"] == email
    assert sync_calls[0]["nivel"] == "admin"
    assert sync_calls[0]["funcao"] == "homologacao"


def test_criar_conta_email_existente_409(client, db, monkeypatch):
    email = "vault.dup@test.local"
    _wipe_email(db, email)
    monkeypatch.setattr(
        "contas_webhook.sync_usuario_hub", lambda **kwargs: (True, None)
    )

    first = client.post(
        ENDPOINT,
        headers=_s2s_headers(),
        json={
            "acao": "criar",
            "email": email,
            "senha": "SenhaVault-1",
            "nivel": "gestor_produtivo",
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        ENDPOINT,
        headers=_s2s_headers(),
        json={
            "acao": "criar",
            "email": email,
            "senha": "OutraSenha-2",
            "nivel": "admin",
        },
    )
    assert second.status_code == 409


def test_rotacionar_senha_conta_existente(client, db, monkeypatch):
    from auth import User, verify_password

    email = "vault.rot@test.local"
    _wipe_email(db, email)
    sync_calls: list[dict] = []

    def _sync(**kwargs):
        sync_calls.append(kwargs)
        return True, None

    monkeypatch.setattr("contas_webhook.sync_usuario_hub", _sync)

    created = client.post(
        ENDPOINT,
        headers=_s2s_headers(),
        json={
            "acao": "criar",
            "email": email,
            "senha": "SenhaAntiga-1",
            "nivel": "usuario_executor",
            "funcao": "teste",
        },
    )
    assert created.status_code == 200, created.text
    sync_calls.clear()

    rotated = client.post(
        ENDPOINT,
        headers=_s2s_headers(),
        json={
            "acao": "rotacionar_senha",
            "email": email,
            "novo_valor": "SenhaNova-2",
        },
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json() == {"ok": True, "email": email}
    assert sync_calls == []

    row = db.query(User).filter(User.email == email).one()
    db.refresh(row)
    assert row.nivel == "usuario_executor"
    assert row.funcao == "teste"
    assert row.role is None
    assert verify_password("SenhaNova-2", row.password_hash)
    assert not verify_password("SenhaAntiga-1", row.password_hash)

    login = client.post(
        "/api/auth/login",
        json={"username": email, "password": "SenhaNova-2"},
    )
    assert login.status_code == 200, login.text


def test_rotacionar_senha_email_inexistente_404(client):
    r = client.post(
        ENDPOINT,
        headers=_s2s_headers(),
        json={
            "acao": "rotacionar_senha",
            "email": "nao.existe.vault@test.local",
            "novo_valor": "SenhaNova-2",
        },
    )
    assert r.status_code == 404


def test_webhook_sem_secret_correto(client, db, monkeypatch):
    monkeypatch.setattr(
        "contas_webhook.sync_usuario_hub", lambda **kwargs: (True, None)
    )
    payload = {
        "acao": "criar",
        "email": "vault.sem.secret@test.local",
        "senha": "SenhaVault-1",
        "nivel": "admin",
    }

    sem_header = client.post(ENDPOINT, json=payload)
    assert sem_header.status_code in (401, 403)

    errado = client.post(ENDPOINT, headers=_s2s_headers(WRONG_SECRET), json=payload)
    assert errado.status_code in (401, 403)

    so_x = client.post(
        ENDPOINT,
        headers={"X-App-Secret": WRONG_SECRET},
        json=payload,
    )
    assert so_x.status_code in (401, 403)
