"""Auth aditivo — login, allowlist restricted_tester, admin livre."""

from __future__ import annotations

import sys
import uuid
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
    # Garante coluna owned_by_user_id (ambiente sem apply-schema recente)
    with eng.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE crystal_shadow_runs "
                "ADD COLUMN IF NOT EXISTS owned_by_user_id UUID"
            )
        )
    Session = sessionmaker(bind=eng)
    session = Session()
    yield session
    session.rollback()
    session.close()
    eng.dispose()


@pytest.fixture()
def client(db):
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


def _mk_user(db, username: str, password: str, role: str):
    from auth_api import create_user

    # limpa se já existir de run anterior
    from auth import User

    old = db.query(User).filter(User.username == username).one_or_none()
    if old:
        db.delete(old)
        db.commit()
    return create_user(db, username=username, password=password, role=role)


def test_login_and_me(client, db):
    _mk_user(db, "tester_auth_a", "secret-a", "restricted_tester")
    r = client.post(
        "/api/auth/login",
        json={"username": "tester_auth_a", "password": "secret-a"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert body["user"]["role"] == "restricted_tester"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "tester_auth_a"


def test_no_token_requires_auth(client):
    me = client.get("/api/auth/me")
    assert me.status_code == 401
    pipe = client.get("/api/pipeline")
    assert pipe.status_code == 401


def test_restricted_forbidden_on_pipeline_and_preview(client, db):
    user = _mk_user(db, "tester_auth_b", "secret-b", "restricted_tester")
    tok = client.post(
        "/api/auth/login",
        json={"username": "tester_auth_b", "password": "secret-b"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    forbidden = [
        ("GET", "/api/pipeline"),
        ("POST", "/api/pipeline/draft-requirements"),
        ("POST", "/api/crystal-ball/quick-preview"),
        ("GET", f"/api/crystal-ball/{uuid.uuid4()}/lineage"),
        ("POST", f"/api/pipeline/{uuid.uuid4()}/export/linear"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("GET", "/api/projects/search"),
    ]
    for method, path in forbidden:
        if method == "GET":
            resp = client.get(path, headers=headers)
        else:
            resp = client.post(path, headers=headers, json={})
        assert resp.status_code == 403, f"{method} {path} -> {resp.status_code} {resp.text}"

    assert user.role == "restricted_tester"


def test_restricted_can_experimental_and_own_shadow_only(client, db, monkeypatch):
    """Allowlist: experimental-run + shadow próprio; shadow alheio = 403."""
    from auth_api import create_user
    from auth import User
    from services.crystal_ball.models import CrystalShadowRun

    for name in ("tester_own", "tester_other"):
        old = db.query(User).filter(User.username == name).one_or_none()
        if old:
            db.delete(old)
            db.commit()

    own = create_user(
        db, username="tester_own", password="secret-o", role="restricted_tester"
    )
    other = create_user(
        db, username="tester_other", password="secret-x", role="restricted_tester"
    )

    # Shadow "alheio"
    alien = CrystalShadowRun(
        id=uuid.uuid4(),
        source_run_id=None,
        fork_phase_id="context7_mativas",
        status="experimental_done",
        spec={"experimental": True, "phases": {}},
        owned_by_user_id=other.id,
    )
    db.add(alien)
    db.commit()

    tok = client.post(
        "/api/auth/login",
        json={"username": "tester_own", "password": "secret-o"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    # Shadow de outro → 403
    denied = client.get(
        f"/api/crystal-ball/shadow/{alien.id}", headers=headers
    )
    assert denied.status_code == 403, denied.text

    # Mock experimental-run (não chama LLM/Google)
    async def _fake_run(db_sess, *, user_prompt, metodologia, owned_by_user_id=None):
        shadow = CrystalShadowRun(
            id=uuid.uuid4(),
            source_run_id=None,
            fork_phase_id="context7_mativas",
            status="experimental_done",
            spec={"experimental": True, "phases": {}},
            owned_by_user_id=owned_by_user_id,
        )
        db_sess.add(shadow)
        db_sess.commit()
        return {
            "shadow_run_id": str(shadow.id),
            "status": "experimental_done",
            "phases": [],
            "is_simulation": True,
            "experimental": True,
        }

    monkeypatch.setattr(
        "crystal_ball_api.run_mativas_experimental", _fake_run
    )

    ok = client.post(
        "/api/crystal-ball/experimental-run",
        headers=headers,
        json={
            "user_prompt": "Desafio longo o bastante para passar validação mínima.",
            "metodologia": "Aprendizagem Baseada em Problemas",
        },
    )
    assert ok.status_code == 200, ok.text
    shadow_id = ok.json()["shadow_run_id"]

    own_get = client.get(
        f"/api/crystal-ball/shadow/{shadow_id}", headers=headers
    )
    assert own_get.status_code == 200, own_get.text

    # Sem token não passa (não há bypass admin)
    bare = client.get("/api/pipeline")
    assert bare.status_code == 401

    assert own.id != other.id


def test_admin_token_full_access(client, db):
    _mk_user(db, "admin_auth_c", "secret-c", "admin")
    tok = client.post(
        "/api/auth/login",
        json={"username": "admin_auth_c", "password": "secret-c"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    pipe = client.get("/api/pipeline", headers=headers)
    assert pipe.status_code == 200
