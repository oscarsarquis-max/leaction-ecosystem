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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
