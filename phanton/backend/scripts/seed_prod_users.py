"""Cria/atualiza usuários admin + andrea em produção (env senhas)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from auth import User, hash_password
from database import SessionLocal


def upsert(username: str, password: str, role: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(User).filter(User.username == username).one_or_none()
        if row is None:
            import uuid

            row = User(
                id=uuid.uuid4(),
                username=username,
                password_hash=hash_password(password),
                role=role,
            )
            db.add(row)
            print(f"created {username} role={role}")
        else:
            row.password_hash = hash_password(password)
            row.role = role
            print(f"updated {username} role={role}")
        db.commit()
    finally:
        db.close()


def main() -> int:
    admin_pw = (os.getenv("PHANTON_ADMIN_PASSWORD") or "").strip()
    andrea_pw = (os.getenv("PHANTON_ANDREA_PASSWORD") or "").strip()
    if len(admin_pw) < 8 or len(andrea_pw) < 8:
        print("PHANTON_ADMIN_PASSWORD / PHANTON_ANDREA_PASSWORD obrigatórias (>=8)", file=sys.stderr)
        return 1
    upsert("oscar", admin_pw, "admin")
    upsert("andrea", andrea_pw, "restricted_tester")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
