"""Comandos de administração do Gestão (rodam dentro do contêiner).

    python -m app.cli criar-usuario --usuario oscar --nome "Oscar" --papel dono
    python -m app.cli redefinir-senha --usuario oscar
    python -m app.cli listar-usuarios

A senha é sempre lida do stdin (sem eco no terminal; ou uma linha, quando vem por pipe).
Nunca é aceita por argumento, nem gravada em arquivo ou log.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db.session import get_engine
from app.domain.auth import gerar_hash_senha, normalizar_usuario
from app.domain.papeis import PAPEIS
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


def criar_usuario(args: argparse.Namespace) -> int:
    nome_usuario = normalizar_usuario(args.usuario)
    if not nome_usuario:
        raise SystemExit("informe --usuario")
    senha = ler_senha()
    try:
        senha_hash = gerar_hash_senha(senha)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    with _sessao() as db:
        if db.scalar(select(Usuario).where(Usuario.usuario == nome_usuario)) is not None:
            raise SystemExit(f"o usuário '{nome_usuario}' já existe")
        db.add(
            Usuario(
                usuario=nome_usuario,
                nome=args.nome.strip()[:120] or nome_usuario,
                senha_hash=senha_hash,
                papel=args.papel,
            )
        )
        db.commit()
    print(f"usuário '{nome_usuario}' criado com o papel '{args.papel}'")
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


def listar_usuarios(_args: argparse.Namespace) -> int:
    with _sessao() as db:
        for u in db.scalars(select(Usuario).order_by(Usuario.usuario)):
            print(f"{u.usuario}\t{u.papel}\t{'ativo' if u.ativo else 'inativo'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="comando", required=True)

    novo = sub.add_parser("criar-usuario")
    novo.add_argument("--usuario", required=True)
    novo.add_argument("--nome", required=True)
    novo.add_argument("--papel", required=True, choices=PAPEIS)
    novo.set_defaults(func=criar_usuario)

    senha = sub.add_parser("redefinir-senha")
    senha.add_argument("--usuario", required=True)
    senha.set_defaults(func=redefinir_senha)

    lista = sub.add_parser("listar-usuarios")
    lista.set_defaults(func=listar_usuarios)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
