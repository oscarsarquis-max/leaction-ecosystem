"""Preparar organização demonstrativa local (idempotente).

Não grava senhas/tokens. AUTH_MODE=dev.

Uso:
  cd qmind/backend
  .\\.venv\\Scripts\\python.exe scripts\\prepare_demo_org_local.py

Web (gestor): VITE_DEV_USER_SUB=demo-gestor (ou o sub impresso)
SoD (qualidade): X-Dev-User-Sub=demo-qualidade
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8009"
ADMIN_URL = "postgresql+psycopg://admin:password123@localhost:5433/qmind_dev"

DEMO_ORG_NAME = "QMind Demo Oficina Norte"
CONTROL_ORG_NAME = "QMind Controle Isolamento"
GESTOR_SUB = "demo-gestor"
GESTOR_EMAIL = "gestor.demo@example.com"
QM_SUB = "demo-qualidade"
QM_EMAIL = "qualidade.demo@example.com"
CONTROL_SUB = "demo-controle"
CONTROL_EMAIL = "controle.demo@example.com"


def _ok(msg: str) -> None:
    print(f"OK   {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def _dev(sub: str, email: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": email,
        "Content-Type": "application/json",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _ensure_user(sub: str, email: str) -> str:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE idp_sub = :sub"),
            {"sub": sub},
        ).first()
        if row:
            uid = row[0]
        else:
            uid = conn.execute(
                text(
                    """
                    INSERT INTO users (idp_sub, email, status)
                    VALUES (:sub, :email, 'active')
                    RETURNING id
                    """
                ),
                {"sub": sub, "email": email},
            ).scalar_one()
    eng.dispose()
    return str(uid)


def _ensure_membership(org_id: str, user_id: str, roles: list[str]) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT id, roles FROM memberships
                WHERE organization_id = :org AND user_id = :user AND status = 'active'
                """
            ),
            {"org": org_id, "user": user_id},
        ).first()
        if existing:
            conn.execute(
                text("UPDATE memberships SET roles = :roles WHERE id = :id"),
                {"roles": roles, "id": existing[0]},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO memberships (organization_id, user_id, roles, status)
                    VALUES (:org, :user, :roles, 'active')
                    """
                ),
                {"org": org_id, "user": user_id, "roles": roles},
            )
    eng.dispose()


def _find_org_by_name(client: httpx.Client, h: dict, name: str) -> str | None:
    mems = client.get("/api/v1/organizations/me/memberships", headers=h)
    if mems.status_code != 200:
        return None
    for m in mems.json():
        if m.get("organization_name") == name:
            return m["organization_id"]
    return None


def _ensure_org(client: httpx.Client, creator_sub: str, creator_email: str, name: str) -> str:
    h0 = _dev(creator_sub, creator_email)
    # Touch user via any authed call after ensure
    found = _find_org_by_name(client, h0, name)
    if found:
        _ok(f"org existente: {name} ({found})")
        return found
    # Also search via SQL in case creator isn't member yet
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM organizations WHERE name = :n LIMIT 1"),
            {"n": name},
        ).first()
    eng.dispose()
    if row:
        _ok(f"org no banco: {name} ({row[0]})")
        return str(row[0])
    created = client.post(
        "/api/v1/organizations",
        json={"name": name},
        headers=h0,
    )
    if created.status_code != 201:
        _fail(f"criar org {name}: {created.status_code} {created.text}")
    org_id = created.json()["organization"]["id"]
    _ok(f"org criada: {name} ({org_id})")
    return org_id


def main() -> None:
    print(f"Prepare demo -> {BASE}")
    try:
        httpx.get(f"{BASE}/api/v1/health", timeout=5.0)
    except httpx.ConnectError:
        _fail("API não responde em :8009")

    gestor_id = _ensure_user(GESTOR_SUB, GESTOR_EMAIL)
    qm_id = _ensure_user(QM_SUB, QM_EMAIL)
    control_id = _ensure_user(CONTROL_SUB, CONTROL_EMAIL)
    _ok("usuários demo garantidos")

    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        # Bootstrap creator identity in API (upsert via first request)
        client.get("/api/v1/organizations/me/memberships", headers=_dev(GESTOR_SUB, GESTOR_EMAIL))
        client.get("/api/v1/organizations/me/memberships", headers=_dev(CONTROL_SUB, CONTROL_EMAIL))

        demo_org = _ensure_org(client, GESTOR_SUB, GESTOR_EMAIL, DEMO_ORG_NAME)
        control_org = _ensure_org(client, CONTROL_SUB, CONTROL_EMAIL, CONTROL_ORG_NAME)

        _ensure_membership(demo_org, gestor_id, ["org_admin", "consultant_auditor"])
        _ensure_membership(demo_org, qm_id, ["quality_manager"])
        _ensure_membership(control_org, control_id, ["org_admin"])
        # Cross membership must NOT exist for isolation
        _ok("memberships gestor + qualidade na demo; controle isolado")

    print()
    print("=== Demo pronta (fictícia, sem dados sensíveis) ===")
    print(f"Organização: {DEMO_ORG_NAME}")
    print(f"  org_id={demo_org}")
    print(f"  Gestor (edição): sub={GESTOR_SUB} email={GESTOR_EMAIL}")
    print(f"  Qualidade (SoD): sub={QM_SUB} email={QM_EMAIL}")
    print(f"Controle: {CONTROL_ORG_NAME} org_id={control_org} sub={CONTROL_SUB}")
    print()
    print("Web local (gestor):")
    print("  VITE_AUTH_MODE=dev")
    print(f"  VITE_DEV_USER_SUB={GESTOR_SUB}")
    print(f"  VITE_DEV_USER_EMAIL={GESTOR_EMAIL}")
    print("  http://127.0.0.1:5173/assessments")
    print()
    print("Smoke técnico completo:")
    print("  .\\.venv\\Scripts\\python.exe scripts\\smoke_journey_local.py")


if __name__ == "__main__":
    main()
