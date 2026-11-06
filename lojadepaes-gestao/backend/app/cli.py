"""Comandos de administração do Gestão (rodam dentro do contêiner).

    python -m app.cli criar-organizacao --nome "Loja de Pães – Boulangerie" --nome-curto boulangerie \
        --cnpj 00.000.000/0000-00 --fonte-loja --email-contato contato@exemplo.com
    python -m app.cli criar-usuario --usuario login@exemplo.com --nome "Nome" --organizacao boulangerie \
        --papel dono --email-contato contato@exemplo.com
    python -m app.cli criar-usuario --usuario oscar --nome "Oscar" --admin-plataforma
    python -m app.cli adicionar-membro --usuario login@exemplo.com --organizacao outra --papel operador
    python -m app.cli redefinir-senha --usuario login@exemplo.com
    python -m app.cli listar-organizacoes
    python -m app.cli listar-usuarios
    python -m app.cli carregar-catalogo [--arquivo caminho.yaml]
    python -m app.cli importar-produtos-loja --organizacao boulangerie
    python -m app.cli importar-produtos-loja --organizacao boulangerie --executar --confirm boulangerie

A senha é sempre lida do stdin (sem eco no terminal; ou uma linha, quando vem por pipe).
Nunca é aceita por argumento, nem gravada em arquivo ou log. Nenhum comando envia e-mail.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db.session import get_engine
from app.domain import cnpj as cnpj_dom
from app.domain.auth import gerar_hash_senha, normalizar_usuario
from app.domain.catalogo import CAMINHO_PADRAO, CatalogoInvalido
from app.domain.catalogo import carregar_catalogo as _carregar
from app.domain.normalizacao import normalizar
from app.domain.papeis import PAPEIS
from app.models.estoque import Local
from app.models.organizacao import Membro, Organizacao
from app.models.usuarios import Usuario


def ler_senha(confirmar: bool = True) -> str:
    if sys.stdin.isatty():
        senha = getpass.getpass("Senha: ")
        if confirmar and getpass.getpass("Repita a senha: ") != senha:
            raise SystemExit("as senhas não conferem")
        return senha
    linha = sys.stdin.readline()
    return linha.rstrip("\r\n")


def _sessao():
    from sqlalchemy.orm import Session

    return Session(get_engine(), expire_on_commit=False)


def _organizacao(db, nome_curto: str) -> Organizacao:
    org = db.scalar(select(Organizacao).where(Organizacao.nome_curto == nome_curto.strip().lower()))
    if org is None:
        raise SystemExit(f"a organização '{nome_curto}' não existe")
    return org


def criar_organizacao(args: argparse.Namespace) -> int:
    try:
        cnpj = cnpj_dom.normalizar(args.cnpj)
    except cnpj_dom.CnpjInvalido as exc:
        raise SystemExit(str(exc)) from None
    nome_curto = args.nome_curto.strip().lower()
    if not nome_curto:
        raise SystemExit("informe --nome-curto")
    with _sessao() as db:
        if db.scalar(select(Organizacao).where(Organizacao.nome_curto == nome_curto)) is not None:
            raise SystemExit(f"a organização '{nome_curto}' já existe")
        if db.scalar(select(Organizacao).where(Organizacao.cnpj == cnpj)) is not None:
            raise SystemExit("já existe uma organização com esse CNPJ")
        org = Organizacao(
            nome=args.nome.strip(),
            nome_curto=nome_curto,
            cnpj=cnpj,
            fonte_loja=args.fonte_loja,
            email_contato=(args.email_contato or "").strip() or None,
        )
        db.add(org)
        db.flush()
        from app.domain.gigio.padroes import semear

        semear(db, org.id)
        db.add(
            Local(
                organizacao_id=org.id,
                nome="Despensa",
                nome_normalizado=normalizar("Despensa"),
                padrao=True,
            )
        )
        db.commit()
    print(
        f"organização '{nome_curto}' criada (CNPJ {cnpj_dom.formatar(cnpj)}); local padrão: Despensa"
    )
    return 0


def criar_usuario(args: argparse.Namespace) -> int:
    nome_usuario = normalizar_usuario(args.usuario)
    if not nome_usuario:
        raise SystemExit("informe --usuario")
    if not args.admin_plataforma and not args.organizacao:
        raise SystemExit("informe --organizacao (e --papel) ou --admin-plataforma")
    if args.organizacao and not args.papel:
        raise SystemExit("informe --papel")
    if args.admin_plataforma and args.organizacao:
        raise SystemExit(
            "o admin da plataforma fica fora das organizações: não combine com --organizacao"
        )
    senha = ler_senha()
    try:
        senha_hash = gerar_hash_senha(senha)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    with _sessao() as db:
        if db.scalar(select(Usuario).where(Usuario.usuario == nome_usuario)) is not None:
            raise SystemExit(f"o usuário '{nome_usuario}' já existe")
        org = _organizacao(db, args.organizacao) if args.organizacao else None
        usuario = Usuario(
            usuario=nome_usuario,
            nome=args.nome.strip()[:120] or nome_usuario,
            senha_hash=senha_hash,
            admin_plataforma=args.admin_plataforma,
            email_contato=(args.email_contato or "").strip() or None,
        )
        db.add(usuario)
        db.flush()
        if org is not None:
            db.add(Membro(usuario_id=usuario.id, organizacao_id=org.id, papel=args.papel))
        db.commit()
    destino = (
        f"organização '{args.organizacao}' com o papel '{args.papel}'"
        if args.organizacao
        else "admin da plataforma"
    )
    print(f"usuário '{nome_usuario}' criado: {destino}")
    return 0


def adicionar_membro(args: argparse.Namespace) -> int:
    nome_usuario = normalizar_usuario(args.usuario)
    with _sessao() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.usuario == nome_usuario))
        if usuario is None:
            raise SystemExit(f"o usuário '{nome_usuario}' não existe")
        if usuario.admin_plataforma:
            raise SystemExit("o admin da plataforma fica fora das organizações")
        org = _organizacao(db, args.organizacao)
        if db.scalar(
            select(Membro).where(Membro.usuario_id == usuario.id, Membro.organizacao_id == org.id)
        ):
            raise SystemExit("essa pessoa já é membro dessa organização")
        db.add(Membro(usuario_id=usuario.id, organizacao_id=org.id, papel=args.papel))
        db.commit()
    print(f"'{nome_usuario}' agora é '{args.papel}' em '{args.organizacao}'")
    return 0


def redefinir_senha(args: argparse.Namespace) -> int:
    nome_usuario = normalizar_usuario(args.usuario)
    senha = ler_senha()
    try:
        senha_hash = gerar_hash_senha(senha)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    with _sessao() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.usuario == nome_usuario))
        if usuario is None:
            raise SystemExit(f"o usuário '{nome_usuario}' não existe")
        usuario.senha_hash = senha_hash
        db.commit()
    print(f"senha de '{nome_usuario}' redefinida")
    return 0


def listar_organizacoes(_args: argparse.Namespace) -> int:
    with _sessao() as db:
        for o in db.scalars(select(Organizacao).order_by(Organizacao.nome_curto)):
            fonte = "fonte da Loja" if o.fonte_loja else "-"
            print(
                f"{o.nome_curto}\t{cnpj_dom.formatar(o.cnpj)}\t{'ativa' if o.ativo else 'inativa'}\t{fonte}\t{o.nome}"
            )
    return 0


def listar_usuarios(_args: argparse.Namespace) -> int:
    with _sessao() as db:
        for u in db.scalars(select(Usuario).order_by(Usuario.usuario)):
            vinculos = db.execute(
                select(Organizacao.nome_curto, Membro.papel)
                .join(Membro, Membro.organizacao_id == Organizacao.id)
                .where(Membro.usuario_id == u.id)
                .order_by(Organizacao.nome_curto)
            ).all()
            onde = ", ".join(f"{org}:{papel}" for org, papel in vinculos) or "-"
            marca = "admin_plataforma" if u.admin_plataforma else "-"
            print(f"{u.usuario}\t{marca}\t{onde}\t{'ativo' if u.ativo else 'inativo'}")
    return 0


def importar_produtos_loja(args: argparse.Namespace) -> int:
    """Traz os produtos publicados da Loja. Sem --executar, só mostra o plano."""
    from sqlalchemy.orm import Session

    from app.db.escopo import ativar_escopo
    from app.db.session import get_loja_engine
    from app.domain.auth import Principal
    from app.domain.contexto import Contexto
    from app.domain.importacao_loja import importar_vitrine

    if args.executar and args.confirm != args.organizacao:
        raise SystemExit("para gravar, repita o nome curto em --confirm")
    with _sessao() as db, Session(get_loja_engine()) as loja:
        org = _organizacao(db, args.organizacao)
        ativar_escopo(db, org.id)
        ctx = Contexto(
            principal=Principal(None, "cli", "cli", False, None, org.id, ""),
            organizacao=org,
            papel="dono",
            db=db,
        )
        resultado = importar_vitrine(ctx, loja, executar=args.executar)
        loja.rollback()
        if args.executar:
            db.commit()
    print("nome\tfamília\tfoto\tjá existe")
    for linha in resultado.linhas:
        foto = "sim" if linha.tem_foto else "não"
        existe = "sim" if linha.ja_existe else "não"
        extra = f"\t{linha.motivo}" if linha.motivo else ""
        print(f"{linha.nome}\t{linha.familia}\t{foto}\t{existe}{extra}")
    print(
        f"{resultado.familias_criadas} famílias criadas, "
        f"{resultado.produtos_criados} produtos criados, "
        f"{resultado.ja_existiam} já importados, "
        f"{len(resultado.nao_criados)} não criados"
    )
    return 0


def carregar_catalogo(args: argparse.Namespace) -> int:
    """Carrega o catálogo de referência de ingredientes (YAML versionado). Idempotente; nunca apaga."""
    caminho = args.arquivo or CAMINHO_PADRAO
    try:
        with _sessao() as db:
            r = _carregar(db, caminho)
            db.commit()
    except CatalogoInvalido as exc:
        print(f"catálogo inválido ({caminho}):", file=sys.stderr)
        for erro in exc.erros:
            print(f"  - {erro}", file=sys.stderr)
        return 1
    print(f"catálogo de ingredientes - versão {r.versao}")
    print(f"{r.inseridos} inseridos, {r.alterados} alterados, {r.iguais} iguais")
    if r.fora_do_arquivo:
        print(f"{r.fora_do_arquivo} no banco que não estão no arquivo (mantidos; nada é apagado)")
    return 0


CASOS_ENSAIO = (
    {
        "catalogo": "Pão de Canela (Cinnamon Bread)",
        "titulo": "Pão de Canela sobre a Massa sovada",
        "familia": "Pão Sovado",
        "base": (
            ("Farinha de trigo", 500),
            ("Água", 300),
            ("Água residual do fermento", 30),
            ("Leite em pó", 50),
            ("Fermento", 5),
            ("Sal", 10),
            ("Açúcar", 20),
            ("Gordura", 40),
        ),
    },
    {
        "catalogo": "Focaccia Alta (Italian Focaccia)",
        "titulo": "Focaccia Alta",
        "familia": "Focaccia",
        "base": (),
    },
)


def _descricoes_publicas() -> dict[str, str]:
    """Só o texto público. Preço e identificador não entram no ensaio."""
    import json
    import urllib.request

    pedido = urllib.request.Request(
        "https://lojadepaes.com.br/api/v1/catalog/products",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(pedido, timeout=20) as resposta:
        corpo = json.loads(resposta.read().decode())
    return {
        str(item.get("name") or ""): str(item.get("short_description") or "").strip()
        for item in corpo.get("items") or []
    }


def _contagens(db) -> dict[str, int]:
    from sqlalchemy import text

    tabelas = (
        "organizacoes",
        "produtos",
        "receitas",
        "receita_linhas",
        "gigio_sugestao",
        "padrao_padaria",
        "ingredientes",
    )
    return {
        tabela: int(db.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one())
        for tabela in tabelas
    }


def gigio_ensaio(args: argparse.Namespace) -> int:
    if not args.sem_gravar:
        raise SystemExit("gigio-ensaio só roda com --sem-gravar: não grava no banco")
    from app.domain.gigio.servico import ensaiar

    descricoes = _descricoes_publicas()
    with _sessao() as db:
        org = _organizacao(db, args.organizacao)
        antes = _contagens(db)
        print("contagem_antes")
        for tabela, total in antes.items():
            print(f"  {tabela}={total}")
        for caso in CASOS_ENSAIO:
            descricao = descricoes.get(caso["catalogo"])
            if not descricao:
                raise SystemExit(f"não achei a descrição pública de {caso['catalogo']}")
            resultado = ensaiar(
                db,
                org.id,
                titulo=caso["titulo"],
                familia=caso["familia"],
                descricao=descricao,
                base=[{"nome": nome, "quantidade_g": gramas} for nome, gramas in caso["base"]],
            )
            db.rollback()
            print(f"== {resultado['titulo']}")
            print(f"modelo={resultado['modelo']}")
            print(f"tokens_entrada={resultado['tokens_entrada']} tokens_saida={resultado['tokens_saida']}")
            print(f"farinha_contida_g={resultado['farinha_contida_g']}")
            print(f"rendimento_g={resultado['rendimento_g']} perda_pct={resultado['perda_pct']}")
            print("descricao=" + descricao)
            print("linhas")
            for linha in resultado["linhas"]:
                faixa = ""
                if linha.get("faixa_min") is not None and linha.get("faixa_max") is not None:
                    faixa = f"{linha['faixa_min']}–{linha['faixa_max']} %"
                print(
                    " | ".join(
                        [
                            str(linha.get("nome")),
                            "" if linha.get("percentual") is None else f"{linha['percentual']} %",
                            f"{linha.get('quantidade')} {linha.get('unidade')}",
                            faixa or "—",
                            str(linha.get("confianca")),
                            str(linha.get("motivo") or ""),
                        ]
                    )
                )
            print("modo_de_fazer")
            for passo in resultado["modo_de_fazer"]:
                print(f"- {passo}")
            if resultado["observacoes"]:
                print("observacoes=" + resultado["observacoes"])
            if resultado["avisos"]:
                print("avisos")
                for aviso in resultado["avisos"]:
                    print(f"- {aviso}")
        db.rollback()
        depois = _contagens(db)
    print("contagem_depois")
    for tabela, total in depois.items():
        print(f"  {tabela}={total}")
    if antes != depois:
        print("ERRO a contagem mudou")
        return 1
    print("gravou=0")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="comando", required=True)

    org = sub.add_parser("criar-organizacao")
    org.add_argument("--nome", required=True)
    org.add_argument("--nome-curto", required=True)
    org.add_argument("--cnpj", required=True)
    org.add_argument("--fonte-loja", action="store_true")
    org.add_argument("--email-contato")
    org.set_defaults(func=criar_organizacao)

    novo = sub.add_parser("criar-usuario")
    novo.add_argument("--usuario", required=True)
    novo.add_argument("--nome", required=True)
    novo.add_argument("--organizacao")
    novo.add_argument("--papel", choices=PAPEIS)
    novo.add_argument("--admin-plataforma", action="store_true")
    novo.add_argument("--email-contato")
    novo.set_defaults(func=criar_usuario)

    membro = sub.add_parser("adicionar-membro")
    membro.add_argument("--usuario", required=True)
    membro.add_argument("--organizacao", required=True)
    membro.add_argument("--papel", required=True, choices=PAPEIS)
    membro.set_defaults(func=adicionar_membro)

    senha = sub.add_parser("redefinir-senha")
    senha.add_argument("--usuario", required=True)
    senha.set_defaults(func=redefinir_senha)

    sub.add_parser("listar-organizacoes").set_defaults(func=listar_organizacoes)
    sub.add_parser("listar-usuarios").set_defaults(func=listar_usuarios)

    loja = sub.add_parser("importar-produtos-loja")
    loja.add_argument("--organizacao", required=True)
    loja.add_argument("--executar", action="store_true")
    loja.add_argument("--confirm", default="")
    loja.set_defaults(func=importar_produtos_loja)

    ensaio = sub.add_parser("gigio-ensaio")
    ensaio.add_argument("--sem-gravar", action="store_true")
    ensaio.add_argument("--organizacao", default="boulangerie")
    ensaio.set_defaults(func=gigio_ensaio)

    cat = sub.add_parser("carregar-catalogo")
    cat.add_argument("--arquivo", help="outro YAML (padrão: o catálogo versionado em app/catalogo)")
    cat.set_defaults(func=carregar_catalogo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
