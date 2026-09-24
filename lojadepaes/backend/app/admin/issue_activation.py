"""Emite o link de ativação no servidor. Não é uma rota HTTP pública."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine
from app.domain.activation import issue_activation


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Emite ativação de senha para a conta administrativa provisionada."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="invalida um link ainda válido e emite outro (não usar no deploy repetido)",
    )
    parser.add_argument(
        "--no-send",
        action="store_true",
        help="só persiste o token, sem e-mail (uso interno de teste)",
    )
    args = parser.parse_args(argv)
    reset_engine()
    settings = get_settings()
    with Session(get_engine()) as session:
        result = issue_activation(session, settings, force=args.force, send=not args.no_send)
        session.commit()
    print(result["message"])


if __name__ == "__main__":
    main()
