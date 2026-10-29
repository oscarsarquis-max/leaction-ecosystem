"""CURSOR-027 homolog — one-shot Demo 026 seed on panne_demo only.

Mutate (seed write): temporary NO FORCE as table owner (same dance as migrate), then restore.
Validate: FORCE RLS stays ON; NO BYPASSRLS; tenant context via app.current_* (app model).
Never logs passwords/URLs. Never touches logical panne / production.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import sessionmaker

from redaction import install_stdio_redaction, log_safe, redact_exc

EXPECTED_DB = "panne_demo"
EXPECTED_USER = "panne_demo_migrator"
EXPECTED_HEAD = "0020_inventory_procurement"
DEFAULT_ANCHOR = "2026-08-24"
ORG_A_SLUG = "panne-demonstracao"
ORG_B_SLUG = "padaria-horizonte-demo"
ISSUER = "https://panne.local/fake"
OWNER_SUBJECT = "demo-owner"
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"

RELAX_FORCE_SQL = """
DO $seed$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$seed$;
"""

RESTORE_FORCE_SQL = """
DO $seed$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$seed$;
"""

_TOKENS: list[str] = []


def log(msg: str) -> None:
    log_safe(msg, _TOKENS)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"missing required env {name}")
    return value


def sslmode() -> str:
    return os.environ.get("PANNE_PG_SSLMODE", "require")


def refuse_master() -> None:
    if os.environ.get("PANNE_MASTER_SECRET_ID"):
        fail("PANNE_MASTER_SECRET_ID must not be set")
    for key, val in os.environ.items():
        if key.startswith("AWS_"):
            continue
        if "PANNE_MASTER" in key.upper():
            fail(f"forbidden master-related env {key}")
        if "rds!db-" in str(val):
            fail(f"forbidden master secret reference in {key}")


def get_secret(sm: Any, secret_id: str) -> dict[str, Any]:
    resp = sm.get_secret_value(SecretId=secret_id)
    raw = resp.get("SecretString")
    if not raw:
        fail(f"secret empty: {secret_id}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        fail("secret not object")
    for key in ("username", "password", "host", "port", "dbname"):
        if key not in data or data[key] in (None, ""):
            fail(f"secret missing field {key}")
    pwd = str(data["password"])
    if pwd not in _TOKENS:
        _TOKENS.append(pwd)
    return data


def make_url(secret: dict[str, Any]) -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=str(secret["username"]),
        password=str(secret["password"]),
        host=str(secret["host"]),
        port=int(secret["port"]),
        database=str(secret["dbname"]),
    )


def make_engine(secret: dict[str, Any]) -> Engine:
    connect_args: dict[str, Any] = {}
    mode = sslmode()
    if mode and mode != "disable":
        connect_args["sslmode"] = mode
    return create_engine(
        make_url(secret),
        pool_pre_ping=True,
        future=True,
        connect_args=connect_args,
    )


def exec_sql(secret: dict[str, Any], sql: str) -> None:
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    finally:
        engine.dispose()


def relax_and_restore_force(secret: dict[str, Any], *, restore: bool) -> None:
    """Only for seed mutate (owner inserts). Always restore before validate."""
    exec_sql(secret, RESTORE_FORCE_SQL if restore else RELAX_FORCE_SQL)
    log("rls_force_restored" if restore else "rls_force_relaxed_for_mutate")


def deterministic_ids() -> tuple[UUID, UUID, UUID]:
    from app.seed.ids import seed_uuid

    org_a = seed_uuid("org", ORG_A_SLUG)
    org_b = seed_uuid("org", ORG_B_SLUG)
    owner = seed_uuid("user", OWNER_SUBJECT)
    return org_a, org_b, owner


def set_tenant(conn: Any, *, organization_id: UUID | None, user_id: UUID | None, subject: str = "") -> None:
    conn.execute(
        text("SELECT set_config('app.current_organization_id', :v, true)"),
        {"v": "" if organization_id is None else str(organization_id)},
    )
    conn.execute(
        text("SELECT set_config('app.current_user_id', :v, true)"),
        {"v": "" if user_id is None else str(user_id)},
    )
    conn.execute(text("SELECT set_config('app.current_issuer', :v, true)"), {"v": ISSUER if subject else ""})
    conn.execute(text("SELECT set_config('app.current_subject', :v, true)"), {"v": subject})


def assert_force_rls_and_nobypass(secret: dict[str, Any]) -> None:
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            forced = int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity
                        """
                    )
                ).scalar()
                or 0
            )
            if forced < 40:
                fail(f"FORCE RLS not intact forced_tables={forced}")
            bypass = conn.execute(
                text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
            ).scalar()
            if bypass:
                fail("current role must remain NOBYPASSRLS")
            log(f"force_rls_intact forced_tables={forced} nobypassrls=true")
    finally:
        engine.dispose()


def preflight(secret: dict[str, Any]) -> bool:
    """Identity/TLS/head checks. Returns True if Demo 026 already present (tenant context)."""
    if str(secret["username"]) != EXPECTED_USER:
        fail("username mismatch")
    if str(secret["dbname"]) != EXPECTED_DB:
        fail("dbname mismatch")
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            user, db = conn.execute(text("SELECT current_user, current_database()")).one()
            ssl = conn.execute(text("SHOW ssl")).scalar()
            log(f"preflight user={user} db={db} ssl={ssl}")
            if user != EXPECTED_USER or db != EXPECTED_DB:
                fail("session identity mismatch")
            if sslmode() == "require" and str(ssl).lower() not in {"on", "1", "true"}:
                fail("TLS required but ssl is off")
            head = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if head != EXPECTED_HEAD:
                fail(f"alembic head mismatch got={head}")
            log(f"alembic_head={head}")
            bypass = conn.execute(
                text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
            ).scalar()
            if bypass:
                fail("migrator must remain NOBYPASSRLS")
    finally:
        engine.dispose()

    assert_force_rls_and_nobypass(secret)

    org_a, _org_b, owner = deterministic_ids()
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                set_tenant(conn, organization_id=org_a, user_id=owner, subject=OWNER_SUBJECT)
                slug = conn.execute(
                    text("SELECT slug FROM organization WHERE id = :id"),
                    {"id": org_a},
                ).scalar()
                trans.commit()
            except Exception:
                trans.rollback()
                raise
        if slug == ORG_A_SLUG:
            log("already_seeded=true (tenant-visible)")
            return True
        if slug is not None:
            fail(f"unexpected org slug at deterministic id: {slug}")
        log("already_seeded=false")
        return False
    finally:
        engine.dispose()


def run_seed(secret: dict[str, Any], *, anchor: str) -> dict[str, Any]:
    from app.seed.demo import seed_demo
    from app.seed.ids import as_date
    from app.seed.target import describe_target

    host = str(secret["host"]).lower()
    os.environ["PANNE_ENV"] = "demo"
    os.environ["PANNE_SEED_ALLOW_RDS"] = "1"
    os.environ["PANNE_SEED_RDS_HOST"] = host
    url_obj = make_url(secret)
    url = url_obj.render_as_string(hide_password=False)
    if url_obj.password and url_obj.password not in _TOKENS:
        _TOKENS.append(str(url_obj.password))
    target = describe_target(url, "demo")
    if target["database"] != EXPECTED_DB:
        fail("seed target database mismatch")
    log(f"seed_target database={target['database']} host={target['host']} env=demo")

    engine = make_engine(secret)
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    try:
        world = seed_demo(session, anchor=as_date(anchor))
        session.commit()
        gaps = list(world.gaps or [])
        slug = world.organization.slug if world.organization else ""
        log(f"seed_demo_ok org={slug} gaps={len(gaps)}")
        if gaps:
            fail(f"seed gaps non-empty: {gaps}")
        return {"org": slug, "gaps": gaps}
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        fail(f"seed_demo failed: {redact_exc(exc, _TOKENS)}")
    finally:
        session.close()
        engine.dispose()


def validate_tenant_isolation(secret: dict[str, Any]) -> None:
    """FORCE RLS ON. Application tenant GUCs. Prove org A visible; org B cannot see A."""
    from app.seed.ids import seed_uuid

    org_a, org_b, owner = deterministic_ids()
    # Owner is member of org B as viewer in seed — use an org_b-only principal if needed.
    # demo-owner has membership on both; isolation of *data* is by current_organization_id.
    # For cross-org denial, query org_a establishment ids while context is org_b.

    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            # 1) No context → organizational rows hidden
            trans = conn.begin()
            set_tenant(conn, organization_id=None, user_id=None, subject="")
            blind = int(conn.execute(text("SELECT COUNT(*) FROM organization")).scalar() or 0)
            if blind != 0:
                fail(f"blind context must hide orgs got={blind}")
            log("isolation_blind_ok")
            trans.commit()

            # 2) Org A + owner → panne-demonstracao visible with expected shape
            trans = conn.begin()
            set_tenant(conn, organization_id=org_a, user_id=owner, subject=OWNER_SUBJECT)
            slug = conn.execute(
                text("SELECT slug FROM organization WHERE id = :id"), {"id": org_a}
            ).scalar()
            if slug != ORG_A_SLUG:
                fail(f"org A not visible under tenant context slug={slug}")
            other_as_a = conn.execute(
                text("SELECT slug FROM organization WHERE id = :id"), {"id": org_b}
            ).scalar()
            # Owner is also member of B → org B may be visible via membership policy.
            # Data isolation is on organization_id-scoped tables:
            est_a = list(
                conn.execute(
                    text("SELECT id, code FROM establishment WHERE organization_id = :o"),
                    {"o": org_a},
                ).fetchall()
            )
            if len(est_a) < 1:
                fail("org A establishments missing under tenant A")
            ingredients_a = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM ingredient WHERE organization_id = :o"),
                    {"o": org_a},
                ).scalar()
                or 0
            )
            if ingredients_a < 5:
                fail(f"org A ingredients too few count={ingredients_a}")
            orders_a = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM production_order WHERE organization_id = :o"),
                    {"o": org_a},
                ).scalar()
                or 0
            )
            users_visible = int(conn.execute(text("SELECT COUNT(*) FROM app_user")).scalar() or 0)
            if users_visible < 1:
                fail("app_user not visible under tenant A")
            log(
                f"tenant_a_ok slug={slug} other_slug={other_as_a} "
                f"est={len(est_a)} ingredients={ingredients_a} orders={orders_a} users={users_visible}"
            )
            trans.commit()

            # 3) Org B context → must NOT see org A establishments / ingredients / orders
            # Use a user that belongs to B: demo-owner is viewer on B.
            trans = conn.begin()
            set_tenant(conn, organization_id=org_b, user_id=owner, subject=OWNER_SUBJECT)
            slug_b = conn.execute(
                text("SELECT slug FROM organization WHERE id = :id"), {"id": org_b}
            ).scalar()
            if slug_b != ORG_B_SLUG:
                fail(f"org B not visible under tenant B slug={slug_b}")
            leak_est = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM establishment WHERE organization_id = :o"),
                    {"o": org_a},
                ).scalar()
                or 0
            )
            leak_ing = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM ingredient WHERE organization_id = :o"),
                    {"o": org_a},
                ).scalar()
                or 0
            )
            leak_ord = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM production_order WHERE organization_id = :o"),
                    {"o": org_a},
                ).scalar()
                or 0
            )
            if leak_est or leak_ing or leak_ord:
                fail(
                    f"org B context leaked org A data "
                    f"est={leak_est} ingredients={leak_ing} orders={leak_ord}"
                )
            # Positive: B's own establishment (horizonte) visible
            est_b = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM establishment WHERE organization_id = :o"),
                    {"o": org_b},
                ).scalar()
                or 0
            )
            if est_b < 1:
                fail("org B establishments missing under tenant B")
            log(f"isolation_b_ok slug={slug_b} est_b={est_b} no_leak_from_a=true")
            trans.commit()

            # 4) Deterministic UUID sanity
            expected_est = seed_uuid("est", str(org_a), "CENTRAL")
            trans = conn.begin()
            set_tenant(conn, organization_id=org_a, user_id=owner, subject=OWNER_SUBJECT)
            code = conn.execute(
                text("SELECT code FROM establishment WHERE id = :id"),
                {"id": expected_est},
            ).scalar()
            if code != "CENTRAL":
                fail(f"expected CENTRAL establishment got={code}")
            log("deterministic_ids_ok")
            trans.commit()
    finally:
        engine.dispose()


def prove_prod_untouched() -> None:
    secret_id = os.environ.get("PANNE_PROD_CHECK_SECRET_ID", "").strip()
    if not secret_id:
        log("prod_untouched_check=skipped")
        return
    import boto3

    sm = boto3.client("secretsmanager", region_name=REGION)
    try:
        prod = get_secret(sm, secret_id)
    except Exception as exc:  # noqa: BLE001
        log(f"prod_untouched_check=unavailable ({redact_exc(exc, _TOKENS)})")
        return
    if str(prod.get("dbname")) != "panne":
        fail("prod check secret dbname unexpected")
    engine = make_engine(prod)
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                      SELECT 1 FROM information_schema.tables
                      WHERE table_schema='public' AND table_name='alembic_version'
                    )
                    """
                )
            ).scalar()
            if exists:
                fail("prod panne unexpectedly has alembic_version")
            log("prod_untouched_alembic_absent=true")
    finally:
        engine.dispose()


def main() -> int:
    install_stdio_redaction(_TOKENS)
    refuse_master()
    env = (os.environ.get("PANNE_SEED_ENV") or "").strip().lower()
    if env != "demo":
        fail("PANNE_SEED_ENV must be demo")
    if (os.environ.get("PANNE_ENV") or "").strip().lower() == "production":
        fail("PANNE_ENV=production refused")
    secret_id = require_env("PANNE_MIGRATOR_SECRET_ID")
    if secret_id != "panne/demo/db/migrator":
        fail("only panne/demo/db/migrator allowed")
    anchor = (os.environ.get("PANNE_SEED_ANCHOR_DATE") or DEFAULT_ANCHOR).strip()
    log(f"seed_runner start env=demo secret_id={secret_id} anchor={anchor}")

    import boto3

    sm = boto3.client("secretsmanager", region_name=REGION)
    secret = get_secret(sm, secret_id)
    already = preflight(secret)

    result: dict[str, Any]
    if already:
        log("skip_mutate=true (no duplicate seed)")
        result = {"org": ORG_A_SLUG, "gaps": []}
    else:
        relax_and_restore_force(secret, restore=False)
        try:
            result = run_seed(secret, anchor=anchor)
        finally:
            relax_and_restore_force(secret, restore=True)

    # Validation never relaxes FORCE / never grants BYPASSRLS
    assert_force_rls_and_nobypass(secret)
    validate_tenant_isolation(secret)
    assert_force_rls_and_nobypass(secret)
    prove_prod_untouched()
    log(f"seed_complete org={result.get('org')} gaps={len(result.get('gaps') or [])}")
    log("validation_mode=tenant_context force_rls=preserved")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        install_stdio_redaction(_TOKENS)
        log(f"ERROR: unhandled {redact_exc(exc, _TOKENS)}")
        raise SystemExit(1) from exc
