#!/usr/bin/env python
"""Cria ou atualiza usuário Phanton (senha via CLI ou env).

Uso local:
  python scripts/upsert_user.py --username andrea --password '***' --role restricted_tester

Uso seguro (senha fora do argv):
  set PHANTON_UPSERT_PASSWORD=***
  python scripts/upsert_user.py --username andrea --role restricted_tester --password-from-env

Roles: admin | restricted_tester
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert usuário Phanton")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", default="")
    parser.add_argument(
        "--password-from-env",
        action="store_true",
        help="Lê senha de PHANTON_UPSERT_PASSWORD",
    )
    parser.add_argument(
        "--role",
        required=True,
        choices=["admin", "restricted_tester"],
    )
    args = parser.parse_args()

    password = (args.password or "").strip()
    if args.password_from_env:
        password = (os.getenv("PHANTON_UPSERT_PASSWORD") or "").strip()
    if len(password) < 8:
        print("ERRO: password obrigatória (>=8)", file=sys.stderr)
        return 1

    from auth import User, hash_password
    from database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine, tables=[User.__table__])

    uname = args.username.strip().lower()
    db = SessionLocal()
    try:
        row = db.query(User).filter(User.username == uname).one_or_none()
        if row is None:
            row = User(
                id=uuid.uuid4(),
                username=uname,
                password_hash=hash_password(password),
                role=args.role,
            )
            db.add(row)
            action = "created"
        else:
            row.password_hash = hash_password(password)
            row.role = args.role
            action = "updated"
        db.commit()
        print(f"OK {action} id={row.id} username={row.username} role={row.role}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
