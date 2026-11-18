import io

import pytest
from app import cli
from app.domain.papeis import PAPEIS, pode
from app.models.organizacao import Membro, Organizacao
from app.models.usuarios import Usuario
from sqlalchemy import select

from tests.conftest import SENHA, cnpj_de_teste, criar_org, entrar


def test_matriz_de_permissoes():
    assert all(pode(papel, "ver_hoje") and pode(papel, "ver_estoque") for papel in PAPEIS)
    for acao in ("lancar", "ajustar", "juntar"):
        assert pode("dono", acao) and pode("operador", acao)
        assert not pode("somente_leitura", acao)
    assert pode("dono", "gerenciar_usuarios")
    assert not pode("operador", "gerenciar_usuarios")
    assert not pode("somente_leitura", "gerenciar_usuarios")
    assert not pode("dono", "acao_que_nao_existe")
    assert not pode(None, "ver_hoje")  # quem não tem papel (admin da plataforma) não opera


@pytest.mark.parametrize(
    "rota", ["/api/v1/hoje", "/api/v1/usuarios", "/api/v1/entradas", "/api/v1/ingredientes"]
)
def test_sem_login_nada_abre(client, rota):
    assert client.get(rota).status_code == 401


@pytest.mark.parametrize("papel", ["dono", "operador", "somente_leitura"])
def test_todos_os_papeis_veem_o_hoje_e_o_estoque(client, papel):
    entrar(client, f"u-{papel}", papel)
    assert client.get("/api/v1/hoje").status_code == 200
    assert client.get("/api/v1/ingredientes").status_code == 200
    assert client.get("/api/v1/entradas").status_code == 200


def test_somente_leitura_nao_lanca_nem_ajusta_nem_junta(client):
    entrar(client, "leitor", "somente_leitura")
    h = {"X-CSRF-Token": client.get("/api/v1/auth/sessao").json()["csrf"]}
    corpo_entrada = {"chave": "k", "data": "2026-11-02", "motivo": "contagem", "linhas": []}
    assert client.post("/api/v1/entradas", json=corpo_entrada, headers=h).status_code == 403
    assert (
        client.post(
            "/api/v1/ingredientes", json={"nome": "Sal", "unidade_base": "g"}, headers=h
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    ("papel", "esperado"), [("dono", 200), ("operador", 403), ("somente_leitura", 403)]
)
def test_so_o_dono_lista_usuarios(client, papel, esperado):
    entrar(client, f"v-{papel}", papel)
    resposta = client.get("/api/v1/usuarios")
    assert resposta.status_code == esperado
    if esperado == 200:
        corpo = resposta.json()
        assert corpo[0]["papel"] == "dono" and corpo[0]["voce"] is True
        assert "senha_hash" not in corpo[0] and "senha" not in corpo[0]


def test_sessao_informa_papel_e_permissoes(client):
    dados = entrar(client, "wilma", "operador")
    assert dados["papel"] == "operador"
    assert dados["permissoes"] == ["ajustar", "juntar", "lancar", "ver_estoque", "ver_hoje"]


def test_dono_cria_membro_e_nao_remove_o_ultimo_dono(client):
    entrar(client, "chefe", "dono")
    h = {"X-CSRF-Token": client.get("/api/v1/auth/sessao").json()["csrf"]}
    novo = client.post(
        "/api/v1/usuarios",
        json={
            "usuario": "Ana",
            "nome": "Ana",
            "papel": "operador",
            "senha": SENHA,
            "email_contato": "a@x.test",
        },
        headers=h,
    )
    assert novo.status_code == 201, novo.text
    assert novo.json()["usuario"] == "ana" and novo.json()["papel"] == "operador"

    repetido = client.post(
        "/api/v1/usuarios",
        json={"usuario": "ana", "nome": "Ana", "papel": "dono", "senha": SENHA},
        headers=h,
    )
    assert repetido.status_code == 409

    meu = next(m for m in client.get("/api/v1/usuarios").json() if m["voce"])
    sair = client.patch(f"/api/v1/usuarios/{meu['id']}", json={"papel": "operador"}, headers=h)
    assert sair.status_code == 409 and sair.json()["detail"]["codigo"] == "ultimo_dono"
    inativar = client.patch(f"/api/v1/usuarios/{meu['id']}", json={"ativo": False}, headers=h)
    assert inativar.status_code == 409

    ana = next(m for m in client.get("/api/v1/usuarios").json() if m["usuario"] == "ana")
    assert (
        client.patch(f"/api/v1/usuarios/{ana['id']}", json={"papel": "dono"}, headers=h).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/usuarios/{meu['id']}", json={"papel": "operador"}, headers=h
        ).status_code
        == 200
    )


# --- comandos ------------------------------------------------------------------------------


def _cmd(monkeypatch, argumentos, senha: str | None = None):
    if senha is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(senha + "\n"))
    return cli.main(argumentos)


def test_organizacao_e_primeiro_membro_pelos_comandos(monkeypatch, capsys, client, db):
    cnpj = cnpj_de_teste()
    assert (
        _cmd(
            monkeypatch,
            [
                "criar-organizacao",
                "--nome",
                "Padaria Teste",
                "--nome-curto",
                "Padaria",
                "--cnpj",
                cnpj,
                "--fonte-loja",
                "--email-contato",
                "contato@x.test",
            ],
        )
        == 0
    )
    assert (
        _cmd(
            monkeypatch,
            [
                "criar-usuario",
                "--usuario",
                "Dono@Teste.com",
                "--nome",
                "Padaria",
                "--organizacao",
                "padaria",
                "--papel",
                "dono",
                "--email-contato",
                "contato@x.test",
            ],
            SENHA,
        )
        == 0
    )
    saida = capsys.readouterr().out
    assert SENHA not in saida  # a senha nunca é impressa
    org = db.scalar(select(Organizacao).where(Organizacao.nome_curto == "padaria"))
    assert org.cnpj == cnpj and org.fonte_loja and org.email_contato == "contato@x.test"
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == "dono@teste.com"))
    assert usuario.senha_hash.startswith("$argon2") and not usuario.admin_plataforma
    assert usuario.email_contato == "contato@x.test"
    assert db.scalar(select(Membro).where(Membro.usuario_id == usuario.id)).papel == "dono"
    entrada = client.post("/api/v1/auth/entrar", json={"usuario": "dono@teste.com", "senha": SENHA})
    assert entrada.status_code == 200
    corpo = entrada.json()
    assert corpo["papel"] == "dono" and corpo["organizacao"]["cnpj_formatado"].count(".") == 2


def test_admin_da_plataforma_fica_fora_das_organizacoes(monkeypatch):
    criar_org("x")
    assert (
        _cmd(
            monkeypatch,
            ["criar-usuario", "--usuario", "adm", "--nome", "Adm", "--admin-plataforma"],
            SENHA,
        )
        == 0
    )
    with pytest.raises(SystemExit):
        _cmd(
            monkeypatch,
            [
                "criar-usuario",
                "--usuario",
                "adm2",
                "--nome",
                "A",
                "--admin-plataforma",
                "--organizacao",
                "x",
                "--papel",
                "dono",
            ],
            SENHA,
        )
    with pytest.raises(SystemExit):
        _cmd(
            monkeypatch,
            ["adicionar-membro", "--usuario", "adm", "--organizacao", "x", "--papel", "dono"],
        )


def test_comando_recusa_cnpj_invalido_senha_curta_e_repetidos(monkeypatch):
    with pytest.raises(SystemExit) as erro_cnpj:
        _cmd(
            monkeypatch,
            [
                "criar-organizacao",
                "--nome",
                "X",
                "--nome-curto",
                "x",
                "--cnpj",
                "11.111.111/1111-11",
            ],
        )
    assert "CNPJ" in str(erro_cnpj.value)
    criar_org("existe")
    with pytest.raises(SystemExit):
        _cmd(
            monkeypatch,
            [
                "criar-organizacao",
                "--nome",
                "X",
                "--nome-curto",
                "existe",
                "--cnpj",
                cnpj_de_teste(),
            ],
        )

    with pytest.raises(SystemExit) as curta:
        _cmd(
            monkeypatch,
            [
                "criar-usuario",
                "--usuario",
                "a",
                "--nome",
                "A",
                "--organizacao",
                "existe",
                "--papel",
                "dono",
            ],
            "curta",
        )
    assert "pelo menos" in str(curta.value)

    _cmd(
        monkeypatch,
        [
            "criar-usuario",
            "--usuario",
            "b",
            "--nome",
            "B",
            "--organizacao",
            "existe",
            "--papel",
            "operador",
        ],
        SENHA,
    )
    with pytest.raises(SystemExit) as repetido:
        _cmd(
            monkeypatch,
            [
                "criar-usuario",
                "--usuario",
                "b",
                "--nome",
                "B",
                "--organizacao",
                "existe",
                "--papel",
                "operador",
            ],
            SENHA,
        )
    assert "já existe" in str(repetido.value)


def test_redefinir_senha_pelo_comando(monkeypatch, client):
    entrar(client, "esquecido", "operador")
    nova = "outra-senha-longa-456"
    _cmd(monkeypatch, ["redefinir-senha", "--usuario", "esquecido"], nova)
    client.cookies.clear()
    assert (
        client.post(
            "/api/v1/auth/entrar", json={"usuario": "esquecido", "senha": SENHA}
        ).status_code
        == 401
    )
    assert (
        client.post("/api/v1/auth/entrar", json={"usuario": "esquecido", "senha": nova}).status_code
        == 200
    )


def test_comando_nao_aceita_senha_por_argumento():
    with pytest.raises(SystemExit):
        cli.main(
            [
                "criar-usuario",
                "--usuario",
                "c",
                "--nome",
                "C",
                "--organizacao",
                "x",
                "--papel",
                "dono",
                "--senha",
                "x",
            ]
        )
