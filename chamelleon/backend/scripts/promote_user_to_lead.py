"""Promove utilizador a lead no tenant (operação pontual)."""
from __future__ import annotations

import sys

from app import create_app
from app.core.rbac.constants import ROLE_LED
from app.database.models import TenantUser, User, db

if __name__ == "__main__":
    email = (sys.argv[1] if len(sys.argv) > 1 else "").lower().strip()
    if not email:
        print("Uso: python scripts/promote_user_to_lead.py <email>")
        sys.exit(1)
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"NOT FOUND: {email}")
            sys.exit(1)
        rows = TenantUser.query.filter_by(user_id=user.id).all()
        if not rows:
            print("Sem membership")
            sys.exit(1)
        for m in rows:
            old = m.role
            m.role = ROLE_LED
            print(f"tenant={m.tenant_id} {old} -> {m.role}")
        db.session.commit()
        print("OK")
