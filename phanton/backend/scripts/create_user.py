#!/usr/bin/env python
"""Cria usuário Phanton (admin ou restricted_tester).

Uso:
  cd C:\\Projetos\\phanton\\backend
  .\\venv\\Scripts\\python.exe scripts\\create_user.py --username andrea --password '***' --role restricted_tester
  .\\venv\\Scripts\\python.exe scripts\\create_user.py --username oscar --password '***' --role admin

Roles: admin | restricted_tester
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria usuário Phanton")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--role",
        required=True,
        choices=["admin", "restricted_tester"],
    )
    args = parser.parse_args()

    from auth import User
    from auth_api import create_user
    from database import Base, SessionLocal, engine

    # Garante tabela users (além do SQL 04_auth.sql)
    Base.metadata.create_all(bind=engine, tables=[User.__table__])

    db = SessionLocal()
    try:
        row = create_user(
            db,
            username=args.username,
            password=args.password,
            role=args.role,
        )
        print(f"OK id={row.id} username={row.username} role={row.role}")
        from hub_client import nivel_from_legacy_role, sync_usuario_hub

        email = row.email or (
            row.username if "@" in row.username else f"{row.username}@phanton.local"
        )
        ok, err = sync_usuario_hub(
            email=email,
            nome=row.nome or row.username,
            nivel=row.nivel or nivel_from_legacy_role(row.role or ""),
            funcao=row.funcao,
        )
        if not ok:
            print(f"AVISO: sync Hub falhou: {err}", file=sys.stderr)
        return 0
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
