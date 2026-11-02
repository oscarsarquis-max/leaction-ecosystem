from datetime import timedelta

from app.core.config import Settings, get_settings
from app.domain.auth import agora
from app.main import create_app
from app.models.usuarios import Sessao, TentativaLogin, Usuario
from sqlalchemy import select, update

from tests.conftest import SENHA, criar_usuario, entrar


def test_login_define_cookie_estrito_e_devolve_csrf(client, db):
    dados = entrar(client, "ana", "dono")
    assert dados["usuario"] == "ana" and dados["papel"] == "dono" and dados["csrf"]
    cookie = client.cookies.get("gestao_session")
    assert cookie
    sessao = db.scalar(select(Sessao))
    # o token nunca é guardado em claro
    assert sessao.token_hash != cookie and len(sessao.token_hash) == 64
    # TTL de 8 horas
    assert timedelta(hours=7, minutes=59) < sessao.expira_em - sessao.criada_em <= timedelta(hours=8, seconds=5)


def test_cookie_e_httponly_samesite_strict_e_secure_em_producao():
    from fastapi.testclient import TestClient

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        session_secret="s" * 48, cookie_secure=True
    )
    criar_usuario("bia", SENHA, "dono")
    with TestClient(app, base_url="https://testserver") as c:
        r = c.post("/api/v1/auth/entrar", json={"usuario": "bia", "senha": SENHA})
    assert r.status_code == 200
    cabecalho = r.headers["set-cookie"].lower()
    assert "gestao_session=" in cabecalho
    assert "httponly" in cabecalho
    assert "samesite=strict" in cabecalho
    assert "secure" in cabecalho
    assert "max-age=28800" in cabecalho
    assert r.headers["cache-control"] == "no-store"


def test_senha_e_guardada_com_argon2(client, db):
    entrar(client, "caio", "operador")
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == "caio"))
    assert usuario.senha_hash.startswith("$argon2")
    assert SENHA not in usuario.senha_hash


def test_login_errado_nao_revela_se_o_usuario_existe(client):
    criar_usuario("dani", SENHA, "dono")
    errado = client.post("/api/v1/auth/entrar", json={"usuario": "dani", "senha": "outra-senha-errada"})
    inexistente = client.post("/api/v1/auth/entrar", json={"usuario": "ninguem", "senha": "outra-senha-errada"})
    assert errado.status_code == inexistente.status_code == 401
    assert errado.json() == inexistente.json()


def test_usuario_inativo_nao_entra(client):
    criar_usuario("edu", SENHA, "dono", ativo=False)
    r = client.post("/api/v1/auth/entrar", json={"usuario": "edu", "senha": SENHA})
    assert r.status_code == 401


def test_usuario_e_normalizado_para_minusculas(client):
    criar_usuario("fabi", SENHA, "dono")
    r = client.post("/api/v1/auth/entrar", json={"usuario": "  FaBi ", "senha": SENHA})
    assert r.status_code == 200


def test_cinco_falhas_em_quinze_minutos_bloqueiam_ate_com_senha_certa(client, db):
    criar_usuario("gabi", SENHA, "dono")
    for _ in range(5):
        r = client.post("/api/v1/auth/entrar", json={"usuario": "gabi", "senha": "senha-errada-123"})
        assert r.status_code == 401
    bloqueado = client.post("/api/v1/auth/entrar", json={"usuario": "gabi", "senha": SENHA})
    assert bloqueado.status_code == 429
    falhas = db.scalars(select(TentativaLogin).where(TentativaLogin.sucesso.is_(False))).all()
    assert len(falhas) == 5  # as falhas ficaram gravadas, mesmo com a resposta de erro


def test_quatro_falhas_ainda_deixam_entrar(client):
    criar_usuario("hugo", SENHA, "dono")
    for _ in range(4):
        client.post("/api/v1/auth/entrar", json={"usuario": "hugo", "senha": "senha-errada-123"})
    assert client.post("/api/v1/auth/entrar", json={"usuario": "hugo", "senha": SENHA}).status_code == 200


def test_falhas_antigas_saem_da_janela(client, db):
    criar_usuario("ivo", SENHA, "dono")
    for _ in range(5):
        client.post("/api/v1/auth/entrar", json={"usuario": "ivo", "senha": "senha-errada-123"})
    db.execute(update(TentativaLogin).values(criada_em=agora() - timedelta(minutes=16)))
    db.commit()
    assert client.post("/api/v1/auth/entrar", json={"usuario": "ivo", "senha": SENHA}).status_code == 200


def test_sessao_devolve_novo_csrf_e_exige_login(client):
    assert client.get("/api/v1/auth/sessao").status_code == 401
    primeiro = entrar(client, "jana", "dono")
    de_novo = client.get("/api/v1/auth/sessao").json()
    assert de_novo["usuario"] == "jana" and de_novo["csrf"] and de_novo["csrf"] != primeiro["csrf"]


def test_sair_exige_csrf_e_revoga_a_sessao(client, db):
    dados = entrar(client, "kleber", "dono")
    sem_csrf = client.post("/api/v1/auth/sair")
    assert sem_csrf.status_code == 403
    com_csrf_errado = client.post("/api/v1/auth/sair", headers={"X-CSRF-Token": "errado"})
    assert com_csrf_errado.status_code == 403
    ok = client.post("/api/v1/auth/sair", headers={"X-CSRF-Token": dados["csrf"]})
    assert ok.status_code == 200
    assert db.scalar(select(Sessao)).revogada_em is not None
    assert client.get("/api/v1/auth/sessao").status_code == 401


def test_origem_de_outro_site_e_recusada_mesmo_com_csrf(client):
    dados = entrar(client, "lia", "dono")
    r = client.post(
        "/api/v1/auth/sair",
        headers={"X-CSRF-Token": dados["csrf"], "Origin": "https://outro-site.example"},
    )
    assert r.status_code == 403


def test_sessao_expirada_ou_revogada_nao_vale(client, db):
    entrar(client, "marco", "dono")
    db.execute(update(Sessao).values(expira_em=agora() - timedelta(seconds=1)))
    db.commit()
    assert client.get("/api/v1/auth/sessao").status_code == 401


def test_usuario_desativado_perde_a_sessao_na_hora(client, db):
    entrar(client, "nina", "dono")
    db.execute(update(Usuario).values(ativo=False))
    db.commit()
    assert client.get("/api/v1/auth/sessao").status_code == 401
