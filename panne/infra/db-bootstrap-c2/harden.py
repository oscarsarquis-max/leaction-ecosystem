"""CURSOR-027-C2-H1 — schema harden + isolation using migrator/runtime only.

Never uses the RDS master secret. Never creates or alters login roles or databases.
Never grants master membership. Default privileges use current_user (no FOR ROLE clause).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import boto3
import psycopg
from psycopg import sql

REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
SSLMODE = os.environ.get("PANNE_PG_SSLMODE", "require")
SYNC_TAG_KEY = "SyncStatus"
SYNC_TAG_VALUE = "postgres_role_bootstrapped"
PROBE = "c2h1_migrator_probe"

ENVIRONMENTS = (
    {
        "name": "prod",
        "dbname": "panne",
        "migrator": "panne_prod_migrator",
        "runtime": "panne_prod_runtime",
        "foreign": ("panne_demo_migrator", "panne_demo_runtime"),
        "mig_key": "prod_migrator",
        "rt_key": "prod_runtime",
    },
    {
        "name": "demo",
        "dbname": "panne_demo",
        "migrator": "panne_demo_migrator",
        "runtime": "panne_demo_runtime",
        "foreign": ("panne_prod_migrator", "panne_prod_runtime"),
        "mig_key": "demo_migrator",
        "rt_key": "demo_runtime",
    },
)

PANNE_ROLES = (
    "panne_prod_migrator",
    "panne_prod_runtime",
    "panne_demo_migrator",
    "panne_demo_runtime",
)


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    sys.exit(code)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"missing required env {name}")
    return value


def log_exc(stage: str, exc: BaseException) -> None:
    state = getattr(exc, "sqlstate", None) or getattr(exc, "pgcode", None)
    raw = str(exc).replace("\n", " ")[:240]
    for token in ("password", "Password", "PASSWORD", "secret", "Secret"):
        if token in raw:
            raw = f"{type(exc).__name__} (message redacted)"
            break
    log(f"ERROR: stage={stage} class={type(exc).__name__} sqlstate={state or 'n/a'} detail={raw}")


def get_secret(sm: Any, secret_id: str) -> dict[str, Any]:
    resp = sm.get_secret_value(SecretId=secret_id)
    raw = resp.get("SecretString")
    if not raw:
        fail(f"secret empty or binary: {secret_id}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        fail(f"secret not object: {secret_id}")
    return data


def tag_secret_synced(sm: Any, secret_id: str) -> None:
    sm.tag_resource(
        SecretId=secret_id,
        Tags=[{"Key": SYNC_TAG_KEY, "Value": SYNC_TAG_VALUE}],
    )
    log(f"secret_tag_updated={secret_id} {SYNC_TAG_KEY}={SYNC_TAG_VALUE}")


def connect(host: str, port: int, dbname: str, user: str, password: str, *, autocommit: bool = True):
    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        sslmode=SSLMODE,
        connect_timeout=30,
        autocommit=autocommit,
    )


def assert_session(conn, *, expect_user: str, expect_db: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT current_user, current_database()")
        user, db = cur.fetchone()
    if user != expect_user:
        fail(f"current_user={user} expected={expect_user}")
    if db != expect_db:
        fail(f"current_database={db} expected={expect_db}")
    log(f"session_ok user={user} db={db}")


def assert_owner(conn, dbname: str, owner: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s",
            (dbname,),
        )
        row = cur.fetchone()
    if not row:
        fail(f"database missing: {dbname}")
    if row[0] != owner:
        fail(f"database {dbname} unexpected owner={row[0]} expected={owner}")
    log(f"owner_ok db={dbname} owner={owner}")


def assert_no_app_objects(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT n.nspname, c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
              AND c.relname NOT LIKE 'pg_%'
            """
        )
        rows = cur.fetchall()
        # allow nothing except empty public
        unexpected = [f"{n}.{r}" for n, r in rows if not r.startswith("c2h1_")]
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'unaccent'")
        if cur.fetchone():
            fail("unaccent_extension_present")
        cur.execute("SELECT to_regclass('public.alembic_version')")
        if cur.fetchone()[0] is not None:
            fail("alembic_version_present")
    if unexpected:
        fail(f"unexpected_public_objects={unexpected}")
    log("no_app_objects=true")


def assert_master_not_member(conn, master_candidates: tuple[str, ...] = ("actionhub_admin",)) -> None:
    with conn.cursor() as cur:
        for master in master_candidates:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (master,))
            if not cur.fetchone():
                continue
            for role in PANNE_ROLES:
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_auth_members am
                    JOIN pg_roles r ON r.oid = am.member
                    JOIN pg_roles m ON m.oid = am.roleid
                    WHERE r.rolname = %s AND m.rolname = %s
                    """,
                    (master, role),
                )
                if cur.fetchone():
                    fail(f"master_membership_residual master={master} role={role}")
    log("master_membership_none=true")


def has_db_privilege(conn, grantee: str, dbname: str, priv: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT has_database_privilege(%s, %s, %s)",
            (grantee, dbname, priv),
        )
        return bool(cur.fetchone()[0])


def has_schema_privilege(conn, grantee: str, schema: str, priv: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT has_schema_privilege(%s, %s, %s)",
            (grantee, schema, priv),
        )
        return bool(cur.fetchone()[0])


def reconcile_database_acls(conn, env: dict[str, Any]) -> None:
    dbname = env["dbname"]
    mig = env["migrator"]
    runtime = env["runtime"]
    with conn.cursor() as cur:
        cur.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(dbname)))
        cur.execute(sql.SQL("REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC").format(sql.Identifier(dbname)))
        cur.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}, {}").format(
                sql.Identifier(dbname), sql.Identifier(mig), sql.Identifier(runtime)
            )
        )
        cur.execute(
            sql.SQL("GRANT TEMPORARY ON DATABASE {} TO {}").format(
                sql.Identifier(dbname), sql.Identifier(mig)
            )
        )
        cur.execute(
            sql.SQL("REVOKE TEMPORARY ON DATABASE {} FROM {}").format(
                sql.Identifier(dbname), sql.Identifier(runtime)
            )
        )
        for foreign in env["foreign"]:
            cur.execute(
                sql.SQL("REVOKE ALL ON DATABASE {} FROM {}").format(
                    sql.Identifier(dbname), sql.Identifier(foreign)
                )
            )
    with conn.cursor() as cur:
        cur.execute("SELECT has_database_privilege('public', current_database(), 'CONNECT')")
        if cur.fetchone()[0]:
            fail(f"public_still_has_connect db={dbname}")
        cur.execute("SELECT has_database_privilege('public', current_database(), 'TEMPORARY')")
        if cur.fetchone()[0]:
            fail(f"public_still_has_temp db={dbname}")
    if not has_db_privilege(conn, mig, dbname, "CONNECT"):
        fail(f"migrator_missing_connect db={dbname}")
    if not has_db_privilege(conn, runtime, dbname, "CONNECT"):
        fail(f"runtime_missing_connect db={dbname}")
    if has_db_privilege(conn, runtime, dbname, "TEMPORARY"):
        fail(f"runtime_still_has_temp db={dbname}")
    for foreign in env["foreign"]:
        if has_db_privilege(conn, foreign, dbname, "CONNECT"):
            fail(f"foreign_connect_present user={foreign} db={dbname}")
    log(f"database_acls_ok={dbname}")


def reconcile_schema_acls(conn, env: dict[str, Any]) -> None:
    mig = env["migrator"]
    runtime = env["runtime"]
    with conn.cursor() as cur:
        cur.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        cur.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(mig)))
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(runtime)))
        cur.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(sql.Identifier(runtime)))
        for foreign in env["foreign"]:
            cur.execute(
                sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(sql.Identifier(foreign))
            )
    if has_schema_privilege(conn, "public", "public", "CREATE"):
        fail("public_schema_create_still_granted")
    if not has_schema_privilege(conn, mig, "public", "CREATE"):
        fail("migrator_missing_schema_create")
    if not has_schema_privilege(conn, runtime, "public", "USAGE"):
        fail("runtime_missing_schema_usage")
    if has_schema_privilege(conn, runtime, "public", "CREATE"):
        fail("runtime_has_schema_create")
    log(f"schema_acls_ok={env['dbname']}")


def reconcile_default_privileges(conn, env: dict[str, Any]) -> None:
    """As current migrator — no FOR ROLE clause."""
    runtime = env["runtime"]
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
            ).format(sql.Identifier(runtime))
        )
        cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO {}"
            ).format(sql.Identifier(runtime))
        )
        cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC"
            )
        )
        cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT EXECUTE ON FUNCTIONS TO {}"
            ).format(sql.Identifier(runtime))
        )
        for foreign in env["foreign"]:
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "REVOKE ALL ON TABLES FROM {}"
                ).format(sql.Identifier(foreign))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "REVOKE ALL ON SEQUENCES FROM {}"
                ).format(sql.Identifier(foreign))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "REVOKE ALL ON FUNCTIONS FROM {}"
                ).format(sql.Identifier(foreign))
            )
    # Catalog check: default ACL rows for current user in public
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT defaclobjtype, defaclacl::text
            FROM pg_default_acl
            WHERE defaclnamespace = 'public'::regnamespace
              AND defaclrole = CURRENT_USER::regrole
            """
        )
        rows = cur.fetchall()
    if not rows:
        fail(f"default_acl_missing db={env['dbname']}")
    blob = " ".join(r[1] or "" for r in rows)
    if runtime not in blob:
        fail(f"default_acl_missing_runtime db={env['dbname']}")
    log(f"default_privileges_ok={env['dbname']} runtime={runtime} entries={len(rows)}")


def verify_default_privileges_with_probe(host: str, port: int, env: dict[str, Any], secrets: dict) -> None:
    mig = secrets[env["mig_key"]]
    rt = secrets[env["rt_key"]]
    dbname = env["dbname"]
    conn = connect(host, port, dbname, mig["username"], mig["password"], autocommit=True)
    try:
        assert_session(conn, expect_user=env["migrator"], expect_db=dbname)
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE {PROBE}(id int PRIMARY KEY)")
            cur.execute(f"INSERT INTO {PROBE}(id) VALUES (1)")
        log(f"probe_created={dbname}")
    finally:
        conn.close()

    rt_conn = connect(host, port, dbname, rt["username"], rt["password"], autocommit=False)
    try:
        with rt_conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {PROBE}")
            if cur.fetchone()[0] != 1:
                fail("runtime_select_failed")
            cur.execute(f"UPDATE {PROBE} SET id = 2 WHERE id = 1")
            cur.execute(f"INSERT INTO {PROBE}(id) VALUES (3)")
            cur.execute(f"DELETE FROM {PROBE} WHERE id = 3")
        rt_conn.commit()
        try:
            with rt_conn.cursor() as cur:
                cur.execute("CREATE TABLE c2h1_runtime_should_fail(id int)")
            rt_conn.rollback()
            fail("runtime_created_table_unexpected")
        except Exception:
            rt_conn.rollback()
            log(f"runtime_ddl_denied_ok={dbname}")
        log(f"runtime_dml_ok={dbname}")
    finally:
        rt_conn.close()

    conn = connect(host, port, dbname, mig["username"], mig["password"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {PROBE}")
            cur.execute(f"SELECT to_regclass('public.{PROBE}')")
            if cur.fetchone()[0] is not None:
                fail(f"probe_remains={dbname}")
        log(f"probe_removed={dbname}")
    finally:
        conn.close()


def harden_environment(host: str, port: int, env: dict[str, Any], secrets: dict) -> None:
    mig = secrets[env["mig_key"]]
    if mig["username"] != env["migrator"] or mig.get("dbname") != env["dbname"]:
        fail(f"secret_mismatch env={env['name']}")
    conn = connect(host, port, env["dbname"], mig["username"], mig["password"], autocommit=True)
    try:
        assert_session(conn, expect_user=env["migrator"], expect_db=env["dbname"])
        assert_owner(conn, env["dbname"], env["migrator"])
        assert_master_not_member(conn)
        assert_no_app_objects(conn)
        reconcile_database_acls(conn, env)
        reconcile_schema_acls(conn, env)
        reconcile_default_privileges(conn, env)
        log(f"harden_complete={env['dbname']}")
    finally:
        conn.close()
    verify_default_privileges_with_probe(host, port, env, secrets)


def validate_cross_isolation(host: str, port: int, secrets: dict) -> None:
    pairs = [
        ("prod_runtime", "panne_demo", True),
        ("demo_runtime", "panne", True),
        ("prod_migrator", "panne_demo", True),
        ("demo_migrator", "panne", True),
        ("prod_runtime", "panne", False),
        ("demo_runtime", "panne_demo", False),
        ("prod_migrator", "panne", False),
        ("demo_migrator", "panne_demo", False),
    ]
    for key, dbname, must_fail in pairs:
        s = secrets[key]
        conn = None
        try:
            conn = connect(host, port, dbname, s["username"], s["password"], autocommit=True)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            if must_fail:
                fail(f"unexpected_connect_success user={s['username']} db={dbname}")
            log(f"connect_ok user={s['username']} db={dbname}")
        except Exception:
            if not must_fail:
                fail(f"unexpected_connect_failure user={s['username']} db={dbname}")
            log(f"connect_denied_ok user={s['username']} db={dbname}")
        finally:
            if conn is not None and not conn.closed:
                conn.close()


def validate_tls(host: str, port: int, secrets: dict) -> None:
    s = secrets["prod_runtime"]
    conn = connect(host, port, "panne", s["username"], s["password"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW ssl")
            ssl_val = cur.fetchone()[0]
            if SSLMODE == "require" and str(ssl_val).lower() not in {"on", "true", "1"}:
                fail(f"ssl_not_on value={ssl_val}")
            try:
                cur.execute("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
                row = cur.fetchone()
                if row is not None and SSLMODE == "require" and row[0] is not True:
                    fail(f"pg_stat_ssl_unexpected ssl={row[0]}")
            except Exception as exc:  # noqa: BLE001
                log_exc("pg_stat_ssl_optional", exc)
            log(f"tls_ok=ssl_show:{ssl_val}")
    finally:
        conn.close()


def harden_all(host: str, port: int, secrets: dict[str, dict[str, Any]]) -> None:
    log("harden_start cycle=027-C2-H1")
    for env in ENVIRONMENTS:
        harden_environment(host, port, env, secrets)
    # Second pass — idempotent
    for env in ENVIRONMENTS:
        harden_environment(host, port, env, secrets)
    validate_cross_isolation(host, port, secrets)
    validate_tls(host, port, secrets)
    log("harden_success")


def main() -> None:
    # Refuse master env if somehow injected
    if os.environ.get("PANNE_MASTER_SECRET_ID"):
        fail("PANNE_MASTER_SECRET_ID must not be set for H1")

    secret_ids = {
        "prod_migrator": _require_env("PANNE_SECRET_PROD_MIGRATOR"),
        "prod_runtime": _require_env("PANNE_SECRET_PROD_RUNTIME"),
        "demo_migrator": _require_env("PANNE_SECRET_DEMO_MIGRATOR"),
        "demo_runtime": _require_env("PANNE_SECRET_DEMO_RUNTIME"),
    }
    expected_users = {
        "prod_migrator": ("panne_prod_migrator", "panne"),
        "prod_runtime": ("panne_prod_runtime", "panne"),
        "demo_migrator": ("panne_demo_migrator", "panne_demo"),
        "demo_runtime": ("panne_demo_runtime", "panne_demo"),
    }

    sm = boto3.client("secretsmanager", region_name=REGION)
    secrets: dict[str, dict[str, Any]] = {}
    host = None
    port = 5432
    for key, sid in secret_ids.items():
        data = get_secret(sm, sid)
        user, dbname = expected_users[key]
        if data.get("username") != user:
            fail(f"username mismatch secret={sid}")
        if data.get("dbname") != dbname:
            fail(f"dbname mismatch secret={sid}")
        if not data.get("password"):
            fail(f"password missing secret={sid}")
        host = host or data.get("host") or data.get("Host")
        port = int(data.get("port") or data.get("Port") or port)
        secrets[key] = data
        log(f"secret_loaded name={sid} user={user} db={dbname}")

    if not host:
        fail("no host in secrets")

    harden_all(host, port, secrets)

    for key, sid in secret_ids.items():
        tag_secret_synced(sm, sid)

    log("h1_success")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        log_exc("unhandled", exc)
        sys.exit(2)
