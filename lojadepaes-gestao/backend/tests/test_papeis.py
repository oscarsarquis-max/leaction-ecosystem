import io

import pytest
from app import cli
from app.domain.papeis import PAPEIS, pode
from app.models.usuarios import Usuario
from sqlalchemy import select

from tests.conftest import SENHA, entrar


def test_matriz_de_permissoes():
    assert all(pode(papel, "ver_hoje") for papel in PAPEIS)
    assert pode("dono", "lancar") and pode("operador", "lancar")
    assert not pode("somente_leitura", "lancar")
    assert pode("dono", "gerenciar_usuarios")
    assert not pode("operador", "gerenciar_usuarios")
    assert not pode("somente_leitura", "gerenciar_usuarios")
    assert not pode("dono", "acao_que_nao_existe")


@pytest.mark.parametrize("rota", ["/api/v1/hoje", "/api/v1/usuarios"])
def test_sem_login_nada_abre(client, rota):
    assert client.get(rota).status_code == 401


@pytest.mark.parametrize("papel", ["dono", "operador", "somente_leitura"])
def test_todos_os_papeis_veem_o_hoje(client, papel):
    entrar(client, f"u-{papel}", papel)
    assert client.get("/api/v1/hoje").status_code == 200


@pytest.mark.parametrize(
    ("papel", "esperado"), [("dono", 200), ("operador", 403), ("somente_leitura", 403)]
)
def test_so_o_dono_lista_usuarios(client, papel, esperado):
    entrar(client, f"v-{papel}", papel)
    resposta = client.get("/api/v1/usuarios")
    assert resposta.status_code == esperado
    if esperado == 200:
        corpo = resposta.json()
        assert corpo[0]["papel"] == "dono"
        assert "senha_hash" not in corpo[0] and "senha" not in corpo[0]


def test_sessao_informa_papel_e_permissoes(client):
    dados = entrar(client, "wilma", "operador")
    assert dados["papel"] == "operador"
    assert dados["permissoes"] == ["lancar", "ver_hoje"]


def test_papel_invalido_e_barrado_pelo_banco(db):
    from sqlalchemy.exc import IntegrityError

    db.add(Usuario(usuario="x", nome="X", senha_hash="h", papel="chefe"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_primeiro_usuario_pelo_comando_com_senha_no_stdin(monkeypatch, capsys, client, db):
    monkeypatch.setattr("sys.stdin", io.StringIO(SENHA + "\n"))
    assert cli.main(["criar-usuario", "--usuario", "Oscar", "--nome", "Oscar", "--papel", "dono"]) == 0
    saida = capsys.readouterr().out
    assert SENHA not in saida  # a senha nunca é impressa
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == "oscar"))
    assert usuario.papel == "dono" and usuario.senha_hash.startswith("$argon2")
    entrada = client.post("/api/v1/auth/entrar", json={"usuario": "oscar", "senha": SENHA})
    assert entrada.status_code == 200 and entrada.json()["papel"] == "dono"


def test_comando_recusa_senha_curta_e_usuario_repetido(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("curta\n"))
    with pytest.raises(SystemExit) as erro:
        cli.main(["criar-usuario", "--usuario", "a", "--nome", "A", "--papel", "dono"])
    assert "pelo menos" in str(erro.value)

    monkeypatch.setattr("sys.stdin", io.StringIO(SENHA + "\n"))
    cli.main(["criar-usuario", "--usuario", "b", "--nome", "B", "--papel", "operador"])
    monkeypatch.setattr("sys.stdin", io.StringIO(SENHA + "\n"))
    with pytest.raises(SystemExit) as repetido:
        cli.main(["criar-usuario", "--usuario", "b", "--nome", "B", "--papel", "operador"])
    assert "já existe" in str(repetido.value)


def test_comando_nao_aceita_senha_por_argumento():
    with pytest.raises(SystemExit):
        cli.main(["criar-usuario", "--usuario", "c", "--nome", "C", "--papel", "dono", "--senha", "x"])
