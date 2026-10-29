"""CURSOR-027-C3-H3 â€” migration runner (connection via Alembic attributes; no ConfigParser URL).

Never logs passwords/URLs. Never uses master. FORCE RLS relax/restore as table owner.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

from redaction import (
    install_stdio_redaction,
    log_safe,
    redact_exc,
    redact_text,
    sanitized_traceback,
)

EXPECTED_HEAD = "0025_economic_audit_policy"
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"

RELAX_FORCE_SQL = """
DO $migration$
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
$migration$;
"""

RESTORE_FORCE_SQL = """
DO $migration$
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
$migration$;
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


def alembic_config(alembic_cwd: str) -> Config:
    ini = str(Path(alembic_cwd) / "alembic.ini")
    cfg = Config(ini)
    cfg.set_main_option("script_location", str(Path(alembic_cwd) / "alembic"))
    # Intentionally never set sqlalchemy.url on ConfigParser.
    return cfg


def run_alembic(secret: dict[str, Any], args: list[str], *, alembic_cwd: str) -> None:
    """Run alembic with a live SQLAlchemy connection in config.attributes."""
    engine = make_engine(secret)
    cfg = alembic_config(alembic_cwd)
    try:
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            if args == ["current"]:
                command.current(cfg)
            elif args[:1] == ["upgrade"] and len(args) == 2:
                command.upgrade(cfg, args[1])
            else:
                fail(f"unsupported alembic args {args!r}")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        fail(f"alembic {' '.join(args)} failed: {redact_exc(exc, _TOKENS)}")
    finally:
        engine.dispose()


def current_version(secret: dict[str, Any]) -> str | None:
    engine = make_engine(secret)
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
            if not exists:
                return None
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            if not rows:
                return None
            if len(rows) != 1:
                fail("multiple alembic heads in db")
            return str(rows[0][0])
    finally:
        engine.dispose()


def exec_sql(secret: dict[str, Any], sql: str) -> None:
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    finally:
        engine.dispose()


def relax_and_restore_force(secret: dict[str, Any], *, restore: bool) -> None:
    exec_sql(secret, RESTORE_FORCE_SQL if restore else RELAX_FORCE_SQL)
    log("rls_force_restored" if restore else "rls_force_relaxed")


def upgrade_head_stepwise(secret: dict[str, Any], *, alembic_cwd: str) -> None:
    steps = 0
    while True:
        before = current_version(secret)
        if before == EXPECTED_HEAD:
            log(f"already_at_head={EXPECTED_HEAD}")
            break
        relax_and_restore_force(secret, restore=False)
        try:
            run_alembic(secret, ["upgrade", "+1"], alembic_cwd=alembic_cwd)
        finally:
            relax_and_restore_force(secret, restore=True)
        after = current_version(secret)
        steps += 1
        log(f"step_ok before={before or 'empty'} after={after} n={steps}")
        if after == before:
            fail("alembic upgrade +1 made no progress")
        if after == EXPECTED_HEAD:
            break
        if steps > 40:
            fail("too many migration steps")
    relax_and_restore_force(secret, restore=True)


def preflight(secret: dict[str, Any], expected_user: str, expected_db: str) -> None:
    if str(secret["username"]) != expected_user:
        fail("username mismatch")
    if str(secret["dbname"]) != expected_db:
        fail("dbname mismatch")
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            user, db = conn.execute(text("SELECT current_user, current_database()")).one()
            ssl = conn.execute(text("SHOW ssl")).scalar()
            log(f"preflight user={user} db={db} ssl={ssl}")
            if user != expected_user or db != expected_db:
                fail("session identity mismatch")
            if sslmode() == "require" and str(ssl).lower() not in {"on", "1", "true"}:
                fail("TLS required but ssl is off")
            owner = conn.execute(
                text(
                    "SELECT pg_catalog.pg_get_userbyid(d.datdba) "
                    "FROM pg_database d WHERE d.datname = current_database()"
                )
            ).scalar()
            if owner != expected_user:
                fail("owner mismatch")
            bypass = conn.execute(
                text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
            ).scalar()
            log(f"migrator_bypassrls={bypass}")
            if bypass:
                fail("migrator must remain NOBYPASSRLS")
            log("preflight_ok")
    finally:
        engine.dispose()


def schema_fingerprint(secret: dict[str, Any]) -> str:
    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT c.relname, COUNT(a.attnum)
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                    WHERE n.nspname = 'public' AND c.relkind = 'r'
                    GROUP BY c.relname
                    ORDER BY c.relname
                    """
                )
            ).fetchall()
            digest_src = "|".join(f"{n}:{c}" for n, c in rows)
            return hashlib.sha256(digest_src.encode()).hexdigest()
    finally:
        engine.dispose()


def validate_structure(secret: dict[str, Any], runtime_user: str) -> None:
    relax_and_restore_force(secret, restore=False)
    try:
        engine = make_engine(secret)
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
                if len(rows) != 1 or rows[0][0] != EXPECTED_HEAD:
                    fail("alembic head mismatch")
                log(f"alembic_head={rows[0][0]}")
                if not conn.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname='unaccent'")
                ).fetchone():
                    fail("unaccent missing")
                log("unaccent_ok")
                org_n = conn.execute(text("SELECT COUNT(*) FROM organization")).scalar()
                user_n = conn.execute(text("SELECT COUNT(*) FROM app_user")).scalar()
                # Demo semeada: org/user != 0 Ã© esperado. SÃ³ falha em ambiente "vazio" esperado.
                if os.environ.get("PANNE_MIGRATE_ALLOW_SEEDED") == "1":
                    log(f"seeded_demo org={org_n} user={user_n} allowed=1")
                elif org_n or user_n:
                    fail("unexpected seed data")
                else:
                    log("no_demo_org_user=true")
                perm_n = conn.execute(text("SELECT COUNT(*) FROM permission")).scalar()
                if perm_n is None or int(perm_n) < 50:
                    fail("permission catalog too small")
                log(f"permission_catalog={perm_n}")
                table_n = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema='public' AND table_type='BASE TABLE'
                        """
                    )
                ).scalar()
                log(f"public_tables={table_n}")
                if table_n is None or int(table_n) < 50:
                    fail("unexpectedly few tables")
                can_create = conn.execute(
                    text("SELECT has_schema_privilege(:u, 'public', 'CREATE')"),
                    {"u": runtime_user},
                ).scalar()
                if can_create:
                    fail("runtime must not have CREATE on public")
                log("runtime_no_schema_create=true")
        finally:
            engine.dispose()
    finally:
        relax_and_restore_force(secret, restore=True)

    engine = make_engine(secret)
    try:
        with engine.connect() as conn:
            missing_force = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname='public' AND c.relkind='r'
                      AND c.relrowsecurity AND NOT c.relforcerowsecurity
                    """
                )
            ).scalar()
            if missing_force:
                fail("tables with RLS but without FORCE")
            log("rls_force_ok")
    finally:
        engine.dispose()
    log(f"schema_fingerprint={schema_fingerprint(secret)}")


def validate_runtime_ops(runtime_secret: dict[str, Any] | None) -> None:
    if not runtime_secret:
        log("runtime_ops_skipped=no_runtime_secret")
        return
    engine = make_engine(runtime_secret)
    try:
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM permission")).scalar()
            log(f"runtime_select_permission={n}")
            try:
                conn.execute(text("CREATE TABLE c3_runtime_ddl_probe(id int)"))
                conn.commit()
                fail("runtime DDL unexpectedly allowed")
            except Exception:  # noqa: BLE001
                conn.rollback()
                log("runtime_ddl_denied_ok")
    finally:
        engine.dispose()


def main() -> None:
    install_stdio_redaction(_TOKENS)
    refuse_master()
    env_name = require_env("PANNE_MIGRATE_ENV")
    alembic_cwd = os.environ.get("PANNE_ALEMBIC_CWD", "/app")

    runtime_secret: dict[str, Any] | None = None
    if env_name == "demo":
        secret_id = require_env("PANNE_MIGRATOR_SECRET_ID")
        expected_user, expected_db = "panne_demo_migrator", "panne_demo"
        runtime_user = "panne_demo_runtime"
        if "demo" not in secret_id:
            fail("demo env requires demo migrator secret")
        if sslmode() != "require":
            fail("demo requires PANNE_PG_SSLMODE=require")
        import boto3

        secret = get_secret(boto3.client("secretsmanager", region_name=REGION), secret_id)
        log(f"secret_loaded id={secret_id} user={secret['username']} db={secret['dbname']}")
    elif env_name == "prod":
        secret_id = require_env("PANNE_MIGRATOR_SECRET_ID")
        expected_user, expected_db = "panne_prod_migrator", "panne"
        runtime_user = "panne_prod_runtime"
        if "prod" not in secret_id or "demo" in secret_id:
            fail("prod env requires prod migrator secret")
        if sslmode() != "require":
            fail("prod requires PANNE_PG_SSLMODE=require")
        import boto3

        secret = get_secret(boto3.client("secretsmanager", region_name=REGION), secret_id)
        log(f"secret_loaded id={secret_id} user={secret['username']} db={secret['dbname']}")
    elif env_name == "local":
        expected_user = require_env("PANNE_LOCAL_MIGRATOR_USER")
        expected_db = require_env("PANNE_LOCAL_DB")
        runtime_user = os.environ.get("PANNE_LOCAL_RUNTIME_USER", "panne_local_runtime")
        os.environ.setdefault("PANNE_PG_SSLMODE", "disable")
        secret = {
            "username": expected_user,
            "password": require_env("PANNE_LOCAL_MIGRATOR_PASSWORD"),
            "host": os.environ.get("PANNE_LOCAL_HOST", "127.0.0.1"),
            "port": int(os.environ.get("PANNE_LOCAL_PORT", "55434")),
            "dbname": expected_db,
        }
        _TOKENS.append(str(secret["password"]))
        if os.environ.get("PANNE_LOCAL_RUNTIME_PASSWORD"):
            runtime_secret = {
                "username": runtime_user,
                "password": os.environ["PANNE_LOCAL_RUNTIME_PASSWORD"],
                "host": secret["host"],
                "port": secret["port"],
                "dbname": expected_db,
            }
            _TOKENS.append(str(runtime_secret["password"]))
    else:
        fail(f"invalid PANNE_MIGRATE_ENV={env_name}")

    preflight(secret, expected_user, expected_db)

    before = current_version(secret)
    log(f"alembic_current_before={before or 'empty'}")
    log("alembic_upgrade_head_stepwise")
    upgrade_head_stepwise(secret, alembic_cwd=alembic_cwd)
    after = current_version(secret)
    log(f"alembic_current_after={after}")
    log("alembic_upgrade_idempotent")
    upgrade_head_stepwise(secret, alembic_cwd=alembic_cwd)

    validate_structure(secret, runtime_user)
    validate_runtime_ops(runtime_secret)
    log(
        f"migrate_success env={env_name} head={EXPECTED_HEAD} "
        f"fingerprint={schema_fingerprint(secret)}"
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            log(f"ERROR: unhandled {redact_exc(exc, _TOKENS)}")
            # Never emit raw traceback to stdout; sanitized only at DEBUG-like path.
            _ = sanitized_traceback(exc, _TOKENS)
        except Exception:  # noqa: BLE001
            print("ERROR: unhandled (redaction failed)", flush=True)
        raise SystemExit(1) from None
