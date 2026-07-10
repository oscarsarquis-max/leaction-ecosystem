#!/usr/bin/env python3
"""Cria executor VRS (mestre@vrsengenharia.com.br) em produção."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy import func
from werkzeug.security import generate_password_hash

from app import create_app
from app.core.rbac.constants import ROLE_EXECUTOR
from app.database.models import Tenant, TenantUser, User, db
from app.models.operational_models import OperationalSite

TENANT_ID = "6a1b4bf1-d85b-4248-bbb9-452df146854c"
EMAIL = "mestre@vrsengenharia.com.br"
NAME = "Mestre VRS"
TEST_PASSWORD = os.getenv("VRS_TEST_PASSWORD", "VrsEngenharia2026!")
SATELLITE_SITE_ID = "c335f3b2-a636-489c-92c0-a63ec710a1a2"


def main() -> int:
    app = create_app()
    with app.app_context():
        tenant = Tenant.query.get(TENANT_ID)
        if not tenant:
            print(f"Tenant {TENANT_ID} não encontrado.")
            return 1

        site = OperationalSite.query.filter_by(
            tenant_id=tenant.id, satellite_site_id=SATELLITE_SITE_ID, is_active=True
        ).first()
        if not site:
            print("Canteiro operacional VRS (satélite) não encontrado.")
            return 1

        email = EMAIL.lower().strip()
        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            user = User(
                name=NAME,
                email=email,
                password_hash=generate_password_hash(TEST_PASSWORD),
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()
        else:
            user.name = NAME
            user.password_hash = generate_password_hash(TEST_PASSWORD)
            user.is_active = True

        membership = TenantUser.query.filter_by(tenant_id=tenant.id, user_id=user.id).first()
        if not membership:
            membership = TenantUser(
                tenant_id=tenant.id,
                user_id=user.id,
                role=ROLE_EXECUTOR,
                operational_site_id=site.id,
            )
            db.session.add(membership)
        else:
            membership.role = ROLE_EXECUTOR
            membership.operational_site_id = site.id

        db.session.commit()

        print("\n==> Executor VRS criado")
        print(f"    tenant:   {tenant.name} ({tenant.id})")
        print(f"    canteiro: {site.name} ({site.id})")
        print(f"    email:    {email}")
        print(f"    senha:    {TEST_PASSWORD}")
        print(f"    papel:    {ROLE_EXECUTOR}")
        print("\nFluxo: login -> Portal -> Diário de Obra (redirecionamento automático)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
