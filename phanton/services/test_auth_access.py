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


def test_register_rejects_invalid_code(client):
    r = client.post(
        "/api/auth/register",
        json={
            "codigo": "nao-existe",
            "nome": "Ana Teste",
            "email": "ana.reg@test.local",
            "senha": "secret-r",
        },
    )
    assert r.status_code == 400
    assert "código" in r.json()["detail"].lower() or "Codigo" in r.json()["detail"]


def test_register_and_login_nivel_user(client, db, monkeypatch):
    from auth import CodigoAcesso, User
    from hub_client import clear_perfil_cache

    clear_perfil_cache()
    monkeypatch.setattr(
        "auth_api.sync_usuario_hub", lambda **kwargs: (True, None)
    )
    monkeypatch.setattr(
        "auth_middleware.resolve_perfil_cached",
        lambda email: (
            {
                "nivel": "usuario_executor",
                "funcao": "analista_requisitos",
                "permissoes": ["ver_sessao", "encerrar_sessao"],
                "status": "ativo",
            },
            None,
        ),
    )

    old = db.query(User).filter(User.email == "ana.reg@test.local").one_or_none()
    if old:
        db.delete(old)
        db.commit()
    used = db.query(CodigoAcesso).filter(CodigoAcesso.codigo == "reg-ok-1").one_or_none()
    if used:
        db.delete(used)
        db.commit()

    db.add(
        CodigoAcesso(
            codigo="reg-ok-1",
            nivel="usuario_executor",
            funcao="analista_requisitos",
            ativo=True,
        )
    )
    db.commit()

    created = client.post(
        "/api/auth/register",
        json={
            "codigo": "reg-ok-1",
            "nome": "Ana Teste",
            "email": "ana.reg@test.local",
            "senha": "secret-r",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["nivel"] == "usuario_executor"

    reused = client.post(
        "/api/auth/register",
        json={
            "codigo": "reg-ok-1",
            "nome": "Outra",
            "email": "outra.reg@test.local",
            "senha": "secret-r",
        },
    )
    assert reused.status_code == 400

    login = client.post(
        "/api/auth/login",
        json={"username": "ana.reg@test.local", "password": "secret-r"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["nivel"] == "usuario_executor"

    tok = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["nivel"] == "usuario_executor"

    pipe = client.get("/api/pipeline", headers=headers)
    assert pipe.status_code == 403


def test_register_keeps_user_when_hub_sync_fails(client, db, monkeypatch):
    from auth import CodigoAcesso, User

    monkeypatch.setattr(
        "auth_api.sync_usuario_hub", lambda **kwargs: (False, "hub down")
    )

    email = "sync.fail@test.local"
    old = db.query(User).filter(User.email == email).one_or_none()
    if old:
        db.delete(old)
        db.commit()
    used = db.query(CodigoAcesso).filter(CodigoAcesso.codigo == "reg-fail-1").one_or_none()
    if used:
        db.delete(used)
        db.commit()
    db.add(CodigoAcesso(codigo="reg-fail-1", nivel="gestor_produtivo", ativo=True))
    db.commit()

    created = client.post(
        "/api/auth/register",
        json={
            "codigo": "reg-fail-1",
            "nome": "Sync Fail",
            "email": email,
            "senha": "secret-r",
        },
    )
    assert created.status_code == 200, created.text
    row = db.query(User).filter(User.email == email).one()
    db.refresh(row)
    assert row.sync_pendente is True
    assert row.role is None


def test_codigos_acesso_admin_only(client, db):
    _mk_user(db, "admin_codes", "secret-c", "admin")
    _mk_user(db, "tester_codes", "secret-t", "restricted_tester")

    denied = client.post(
        "/api/auth/codigos-acesso",
        json={"nivel": "usuario_executor", "funcao": "analista_requisitos"},
        headers={
            "Authorization": (
                "Bearer "
                + client.post(
                    "/api/auth/login",
                    json={"username": "tester_codes", "password": "secret-t"},
                ).json()["access_token"]
            )
        },
    )
    assert denied.status_code == 403

    ok = client.post(
        "/api/auth/codigos-acesso",
        json={"nivel": "usuario_executor", "funcao": "analista_requisitos"},
        headers={
            "Authorization": (
                "Bearer "
                + client.post(
                    "/api/auth/login",
                    json={"username": "admin_codes", "password": "secret-c"},
                ).json()["access_token"]
            )
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["codigo"]
    assert ok.json()["nivel"] == "usuario_executor"


def test_executor_permissions_are_independent_of_restricted():
    from auth import (
        executor_has_permission,
        path_allowed_for_restricted,
        permission_for_executor_route,
    )

    assert (
        permission_for_executor_route("POST", "/api/crystal-ball/experimental-run")
        == "executar_simulacao"
    )
    assert (
        permission_for_executor_route("GET", "/api/crystal-ball/corpora")
        == "listar_corpora"
    )
    assert permission_for_executor_route("GET", "/api/pipeline") == "listar_pipeline"
    assert path_allowed_for_restricted("GET", "/api/crystal-ball/corpora") is False
    assert executor_has_permission(
        ["executar_simulacao"], "POST", "/api/crystal-ball/experimental-run"
    )
    assert not executor_has_permission(
        ["executar_simulacao"], "GET", "/api/crystal-ball/corpora"
    )
    assert not executor_has_permission([], "GET", "/api/auth/me")


def test_usuario_executor_uses_hub_permissions(client, db, monkeypatch):
    from auth import User, hash_password
    from hub_client import clear_perfil_cache

    clear_perfil_cache()
    monkeypatch.setattr(
        "auth_middleware.resolve_perfil_cached",
        lambda email: (
            {
                "nivel": "usuario_executor",
                "funcao": "analista_requisitos",
                "permissoes": [
                    "ver_sessao",
                    "listar_corpora",
                    "listar_ciclos",
                ],
                "status": "ativo",
            },
            None,
        ),
    )

    email = "exec.allow@test.local"
    old = db.query(User).filter(User.username == email).one_or_none()
    if old:
        db.delete(old)
        db.commit()
    db.add(
        User(
            id=uuid.uuid4(),
            username=email,
            password_hash=hash_password("secret-e"),
            role=None,
            nome="Executor Allow",
            email=email,
            nivel="usuario_executor",
            funcao="analista_requisitos",
        )
    )
    db.commit()

    tok = client.post(
        "/api/auth/login",
        json={"username": email, "password": "secret-e"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    corpora = client.get("/api/crystal-ball/corpora", headers=headers)
    assert corpora.status_code == 200, corpora.text

    ciclos = client.get(
        "/api/crystal-ball/corpus/mativas/ciclos", headers=headers
    )
    assert ciclos.status_code in (200, 404), ciclos.text

    sim = client.post(
        "/api/crystal-ball/experimental-run",
        headers=headers,
        json={"user_prompt": "x" * 20, "metodologia": "PBL"},
    )
    assert sim.status_code == 403
    assert "executar_simulacao" in sim.json()["detail"]

    pipe = client.get("/api/pipeline", headers=headers)
    assert pipe.status_code == 403
    assert "listar_pipeline" in pipe.json()["detail"]


def test_restricted_tester_still_denied_on_executor_only_routes(client, db):
    _mk_user(db, "tester_no_lab", "secret-t", "restricted_tester")
    tok = client.post(
        "/api/auth/login",
        json={"username": "tester_no_lab", "password": "secret-t"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    corpora = client.get("/api/crystal-ball/corpora", headers=headers)
    assert corpora.status_code == 403, corpora.text
    assert "restricted_tester" in corpora.json()["detail"]


def test_nivel_user_fail_closed_without_hub_cache(client, db, monkeypatch):
    from auth import User
    from hub_client import clear_perfil_cache

    clear_perfil_cache()
    monkeypatch.setattr(
        "auth_middleware.resolve_perfil_cached",
        lambda email: (None, "hub down"),
    )

    old = db.query(User).filter(User.username == "nivel.nocache@test.local").one_or_none()
    if old:
        db.delete(old)
        db.commit()

    from auth import hash_password
    import uuid as _uuid

    row = User(
        id=_uuid.uuid4(),
        username="nivel.nocache@test.local",
        password_hash=hash_password("secret-n"),
        role=None,
        nome="Sem cache",
        email="nivel.nocache@test.local",
        nivel="admin",
    )
    db.add(row)
    db.commit()

    tok = client.post(
        "/api/auth/login",
        json={"username": "nivel.nocache@test.local", "password": "secret-n"},
    ).json()["access_token"]
    pipe = client.get(
        "/api/pipeline",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert pipe.status_code == 403
    assert "cache" in pipe.json()["detail"].lower()
