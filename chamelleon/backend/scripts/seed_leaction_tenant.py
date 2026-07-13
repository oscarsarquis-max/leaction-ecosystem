#!/usr/bin/env python3
"""Seed tenant LEACTION para testes de campo (construção civil + Diário de Obra)."""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy import func
from werkzeug.security import generate_password_hash

from app import create_app
from app.core.dev_users import DEV_FRAMEWORK_CONSTRUCAO_ID
from app.core.rbac.constants import ROLE_EXECUTOR, ROLE_LED
from app.database.models import Tenant, TenantFramework, TenantUser, User, db
from app.models.operational_models import INDUSTRY_CONSTRUCAO, OperationalSite
from app.services.operational_service import OperationalService
from app.services.satellite_client import SatelliteClient

TENANT_NAME = "LEACTION"
FRAMEWORK_ID = DEV_FRAMEWORK_CONSTRUCAO_ID
TEST_PASSWORD = os.getenv("LEACTION_TEST_PASSWORD", "LeAction2026!")

USERS = [
    {
        "email": "gestor@leactionengenharia.com.br",
        "name": "Gestor LeAction",
        # Lead da empresa: administra o tenant (jornada, plano TD, operacional).
        "role": ROLE_LED,
    },
    {
        "email": "executor@leactionengenharia.com.br",
        "name": "Executor LeAction",
        "role": ROLE_EXECUTOR,
    },
]

SITE_NAME = "Canteiro LeAction — Teste Campo"
SITE_LOCATION = "Eusébio, CE"


def _get_or_create_tenant() -> Tenant:
    tenant = Tenant.query.filter(func.lower(Tenant.name) == TENANT_NAME.lower()).first()
    if tenant:
        return tenant
    tenant = Tenant(
        name=TENANT_NAME,
        journey_status="DIAGNOSTICO OK",
        has_active_project=True,
        context_data={"sector": "construcao civil", "source": "seed_leaction_tenant"},
    )
    db.session.add(tenant)
    db.session.flush()
    return tenant


def _ensure_framework(tenant: Tenant) -> None:
    exists = TenantFramework.query.filter_by(
        tenant_id=tenant.id, framework_id=FRAMEWORK_ID
    ).first()
    if not exists:
        db.session.add(
            TenantFramework(tenant_id=tenant.id, framework_id=FRAMEWORK_ID, status="active")
        )


def _upsert_user(tenant: Tenant, spec: dict) -> User:
    email = spec["email"].lower().strip()
    user = User.query.filter(func.lower(User.email) == email).first()
    if not user:
        user = User(
            name=spec["name"],
            email=email,
            password_hash=generate_password_hash(TEST_PASSWORD),
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.name = spec["name"]
        user.password_hash = generate_password_hash(TEST_PASSWORD)
        user.is_active = True

    membership = TenantUser.query.filter_by(tenant_id=tenant.id, user_id=user.id).first()
    if not membership:
        db.session.add(
            TenantUser(tenant_id=tenant.id, user_id=user.id, role=spec["role"])
        )
    else:
        membership.role = spec["role"]
    return user


def _get_or_create_site(tenant: Tenant, manager: User) -> OperationalSite:
    site = (
        OperationalSite.query.filter_by(tenant_id=tenant.id, name=SITE_NAME, is_active=True)
        .order_by(OperationalSite.created_at.desc())
        .first()
    )
    if site:
        site.manager_id = manager.id
        return site

    site = OperationalSite(
        tenant_id=tenant.id,
        name=SITE_NAME,
        location=SITE_LOCATION,
        industry_type=INDUSTRY_CONSTRUCAO,
        manager_id=manager.id,
        is_active=True,
    )
    db.session.add(site)
    db.session.flush()
    return site


def _link_users_to_site(tenant: Tenant, site: OperationalSite) -> None:
    for spec in USERS:
        user = User.query.filter(db.func.lower(User.email) == spec["email"]).first()
        if not user:
            continue
        membership = TenantUser.query.filter_by(tenant_id=tenant.id, user_id=user.id).first()
        if membership:
            membership.operational_site_id = site.id


def _sync_satellite(tenant: Tenant, site: OperationalSite) -> str | None:
    if site.satellite_site_id:
        return site.satellite_site_id
    try:
        satellite = SatelliteClient().create_rdo_site(
            {
                "tenant_id": str(tenant.id),
                "name": site.name,
                "location": site.location,
                "rt_engineer_name": "Gestor LeAction",
            }
        )
        satellite_id = str(satellite.get("id") or "").strip()
        if satellite_id:
            site.satellite_site_id = satellite_id
            return satellite_id
    except Exception as exc:
        return f"ERRO_SYNC: {exc}"
    return None


def main() -> int:
    app = create_app()
    with app.app_context():
        tenant = _get_or_create_tenant()
        _ensure_framework(tenant)

        from app.services.okr_service import ensure_canonical_okrs_for_tenant

        ensure_canonical_okrs_for_tenant(tenant.id, commit=False)

        created_users: list[User] = []
        for spec in USERS:
            created_users.append(_upsert_user(tenant, spec))

        gestor = next(u for u in created_users if "gestor@" in u.email)
        site = _get_or_create_site(tenant, gestor)
        _link_users_to_site(tenant, site)
        db.session.commit()

        sync_result = _sync_satellite(tenant, site)
        db.session.commit()

        print("\n==> Tenant LEACTION pronto para testes")
        print(f"    tenant_id: {tenant.id}")
        print(f"    framework: {FRAMEWORK_ID}")
        print(f"    canteiro:  {site.name} ({site.id})")
        print(f"    satellite: {site.satellite_site_id or sync_result}")
        print("\nCredenciais (senha igual para ambos):")
        print(f"    Senha: {TEST_PASSWORD}")
        for spec in USERS:
            print(f"    {spec['role']:10} {spec['email']}")
        print("\nFluxo:")
        print("  Lead/Gestor -> login -> jornada, plano TD, gestão operacional")
        print("  Executor    -> login -> Portal -> Diário de Obra")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
