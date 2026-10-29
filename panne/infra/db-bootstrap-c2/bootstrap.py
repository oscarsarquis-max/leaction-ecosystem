"""CURSOR-027-C2-B1 idempotent PostgreSQL bootstrap for Panne.

Administrative DDL uses a dedicated connection created with autocommit=True.
Never toggles autocommit on an already-used connection.
Never logs passwords, secret JSON, or SQL with credentials.
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


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"missing required env {name}")
    return value


def _secret_ids() -> dict[str, str]:
    return {
        "prod_migrator": _require_env("PANNE_SECRET_PROD_MIGRATOR"),
        "prod_runtime": _require_env("PANNE_SECRET_PROD_RUNTIME"),
        "demo_migrator": _require_env("PANNE_SECRET_DEMO_MIGRATOR"),
        "demo_runtime": _require_env("PANNE_SECRET_DEMO_RUNTIME"),
    }

EXPECTED = {
    "prod_migrator": {"username": "panne_prod_migrator", "dbname": "panne"},
    "prod_runtime": {"username": "panne_prod_runtime", "dbname": "panne"},
    "demo_migrator": {"username": "panne_demo_migrator", "dbname": "panne_demo"},
    "demo_runtime": {"username": "panne_demo_runtime", "dbname": "panne_demo"},
}

PANNE_APP_ROLES = (
    "panne_prod_migrator",
    "panne_prod_runtime",
    "panne_demo_migrator",
    "panne_demo_runtime",
)

# PostgreSQL 16+/17: GRANT role TO member WITH ADMIN FALSE, INHERIT FALSE, SET TRUE
MEMBERSHIP_GRANT_SQL = "GRANT {} TO {} WITH ADMIN FALSE, INHERIT FALSE, SET TRUE"

SYNC_TAG_KEY = "SyncStatus"
SYNC_TAG_VALUE = "postgres_role_bootstrapped"
SSLMODE = os.environ.get("PANNE_PG_SSLMODE", "require")
PROBE_TABLE = "c2b2_migrator_probe"

def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    sys.exit(code)


def sqlstate_of(exc: BaseException) -> str | None:
    state = getattr(exc, "sqlstate", None) or getattr(exc, "pgcode", None)
    if state:
        return str(state)
    diag = getattr(exc, "diag", None)
    if diag is not None:
        ds = getattr(diag, "sqlstate", None)
        if ds:
            return str(ds)
    return None


def log_exc(stage: str, exc: BaseException) -> None:
    """Sanitized exception log — no credentials, no secret bodies."""
    state = sqlstate_of(exc)
    cls = type(exc).__name__
    # Message may contain object names; strip password-like fragments defensively.
    raw = str(exc).replace("\n", " ")[:240]
    for token in ("password", "Password", "PASSWORD", "secret", "Secret"):
        if token in raw:
            raw = f"{cls} (message redacted)"
            break
    log(f"ERROR: stage={stage} class={cls} sqlstate={state or 'n/a'} detail={raw}")


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


def connect(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    *,
    autocommit: bool = False,
):
    """Open a new connection. Prefer autocommit=True for DDL that cannot run in a txn."""
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        sslmode=SSLMODE,
        connect_timeout=30,
        autocommit=autocommit,
    )
    return conn


def db_exists(conn, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        return cur.fetchone() is not None


def role_exists(conn, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,))
        return cur.fetchone() is not None


def fetch_role_attrs(conn, username: str) -> tuple[bool, bool, bool, bool, bool, bool] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolcanlogin
            FROM pg_roles WHERE rolname = %s
            """,
            (username,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return tuple(bool(x) for x in row)  # type: ignore[return-value]


def assert_role_attrs_safe(username: str, attrs: tuple[bool, bool, bool, bool, bool, bool]) -> None:
    rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolcanlogin = attrs
    if rolsuper or rolcreatedb or rolcreaterole or rolreplication or rolbypassrls or not rolcanlogin:
        fail(
            "role attributes unsafe or invalid: "
            f"{username} super={rolsuper} createdb={rolcreatedb} createrole={rolcreaterole} "
            f"replication={rolreplication} bypassrls={rolbypassrls} canlogin={rolcanlogin}"
        )


def is_direct_member(conn, member: str, role: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_auth_members am
            JOIN pg_roles r ON r.oid = am.member
            JOIN pg_roles m ON m.oid = am.roleid
            WHERE r.rolname = %s AND m.rolname = %s
            """,
            (member, role),
        )
        return cur.fetchone() is not None


def has_set_membership(conn, member: str, role: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_auth_members am
            JOIN pg_roles r ON r.oid = am.member
            JOIN pg_roles m ON m.oid = am.roleid
            WHERE r.rolname = %s AND m.rolname = %s AND am.set_option IS TRUE
            """,
            (member, role),
        )
        return cur.fetchone() is not None


def grant_set_membership(admin, role: str, member: str) -> None:
    """Temporary SET-capable membership without ADMIN or INHERIT (PG16+/17)."""
    with admin.cursor() as cur:
        cur.execute(
            sql.SQL(MEMBERSHIP_GRANT_SQL).format(sql.Identifier(role), sql.Identifier(member))
        )
    log(f"membership_granted_set role={role} member={member}")


def revoke_membership(admin, role: str, member: str) -> None:
    with admin.cursor() as cur:
        cur.execute(
            sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(role), sql.Identifier(member))
        )
    log(f"membership_revoked role={role} member={member}")


def clear_master_panne_memberships(admin, master_user: str) -> None:
    for role in PANNE_APP_ROLES:
        if not role_exists(admin, role):
            continue
        for _ in range(5):
            if not is_direct_member(admin, master_user, role):
                break
            try:
                with admin.cursor() as cur:
                    cur.execute(
                        sql.SQL("REVOKE ADMIN OPTION FOR {} FROM {}").format(
                            sql.Identifier(role), sql.Identifier(master_user)
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                log_exc(f"membership_revoke_admin_option:{role}", exc)
            try:
                revoke_membership(admin, role, master_user)
            except Exception as exc:  # noqa: BLE001
                log_exc(f"membership_residual_revoke:{role}", exc)
                break
        if has_set_membership(admin, master_user, role):
            fail(f"membership_set_still_present role={role}")
        if is_direct_member(admin, master_user, role):
            # CREATEROLE-on-community-PG leaves ADMIN grantor=bootstrap that non-super
            # cannot drop; RDS rds_superuser must be able to clear. Fail closed on SET,
            # and fail closed on any residual when we still have SET or after our grants.
            log(f"ERROR: membership_residual_uncleared role={role} member={master_user}")
            fail(f"membership_residual_still_present role={role}")


def assert_no_master_panne_memberships(admin, master_user: str) -> None:
    for role in PANNE_APP_ROLES:
        if not role_exists(admin, role):
            continue
        if has_set_membership(admin, master_user, role):
            fail(f"membership_set_residual role={role} member={master_user}")
        if is_direct_member(admin, master_user, role):
            fail(f"membership_residual role={role} member={master_user}")
    log("membership_residual_none=true")


def ensure_role(admin, username: str, password: str) -> None:
    """Requires admin connection already in autocommit mode from connect()."""
    if not admin.autocommit:
        fail("ensure_role requires autocommit admin connection")
    if role_exists(admin, username):
        attrs = fetch_role_attrs(admin, username)
        if attrs is None:
            fail(f"role vanished: {username}")
        assert_role_attrs_safe(username, attrs)
        # Existing roles: password/login only — never emit NOSUPERUSER/etc on ALTER.
        with admin.cursor() as cur:
            cur.execute(
                sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                    sql.Identifier(username), sql.Literal(password)
                )
            )
        log(f"role_password_synced={username}")
    else:
        with admin.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(username), sql.Literal(password))
            )
        log(f"role_created={username}")
    attrs_after = fetch_role_attrs(admin, username)
    if attrs_after is None:
        fail(f"role missing after ensure: {username}")
    assert_role_attrs_safe(username, attrs_after)
    log(f"role_attrs_ok={username}")


def ensure_database(admin, dbname: str, owner: str, master_user: str) -> None:
    """CREATE DATABASE with temporary SET membership for owner (RDS-safe)."""
    if not admin.autocommit:
        fail("ensure_database requires autocommit admin connection")
    if db_exists(admin, dbname):
        with admin.cursor() as cur:
            cur.execute(
                """
                SELECT pg_catalog.pg_get_userbyid(datdba), pg_encoding_to_char(encoding)
                FROM pg_database WHERE datname = %s
                """,
                (dbname,),
            )
            current_owner, encoding = cur.fetchone()
            if current_owner != owner:
                fail(f"database {dbname} unexpected owner={current_owner} expected={owner}")
            if encoding.upper() not in {"UTF8", "UTF-8"}:
                fail(f"database {dbname} unexpected encoding={encoding}")
        log(f"database_exists={dbname} owner={owner} encoding={encoding}")
        return

    attrs = fetch_role_attrs(admin, owner)
    if attrs is None:
        fail(f"owner role missing before create database: {owner}")
    assert_role_attrs_safe(owner, attrs)

    # Local/superuser path: creating a DB owned by the connecting user needs no SET ROLE.
    if owner == master_user:
        with admin.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8'").format(
                    sql.Identifier(dbname),
                    sql.Identifier(owner),
                )
            )
        log(f"database_created={dbname} owner={owner}")
        return

    create_error: BaseException | None = None
    revoke_error: BaseException | None = None
    we_granted_set = False
    try:
        if has_set_membership(admin, master_user, owner):
            fail(f"unexpected SET membership before create db={dbname} role={owner}")
        grant_set_membership(admin, owner, master_user)
        we_granted_set = True
        if not has_set_membership(admin, master_user, owner):
            fail(f"membership_set_grant_not_visible role={owner}")
        with admin.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8'").format(
                    sql.Identifier(dbname),
                    sql.Identifier(owner),
                )
            )
        log(f"database_created={dbname} owner={owner}")
    except Exception as exc:  # noqa: BLE001
        create_error = exc
        log_exc(f"ensure_database:{dbname}", exc)
    finally:
        if we_granted_set or has_set_membership(admin, master_user, owner):
            try:
                revoke_membership(admin, owner, master_user)
            except Exception as exc:  # noqa: BLE001
                revoke_error = exc
                log_exc(f"membership_revoke:{owner}", exc)
        if has_set_membership(admin, master_user, owner):
            log(f"ERROR: membership_set_still_present_after_revoke role={owner}")
            if revoke_error is None:
                revoke_error = RuntimeError(f"membership_set_still_present role={owner}")

    if revoke_error is not None:
        fail(f"membership_revoke_failed role={owner}")
    if create_error is not None:
        fail(f"ensure_database_failed db={dbname} class={type(create_error).__name__}")

    if has_set_membership(admin, master_user, owner):
        fail(f"membership_set_absent_check_failed role={owner}")
    log(f"membership_set_absent_confirmed role={owner}")


def apply_database_acls(admin, dbname: str, migrator: str, runtime: str, others: list[str]) -> None:
    if not admin.autocommit:
        fail("apply_database_acls requires autocommit admin connection")
    with admin.cursor() as cur:
        cur.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(dbname)))
        cur.execute(
            sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO {}, {}").format(
                sql.Identifier(dbname),
                sql.Identifier(migrator),
                sql.Identifier(runtime),
            )
        )
        for role in others:
            cur.execute(
                sql.SQL("REVOKE ALL ON DATABASE {} FROM {}").format(
                    sql.Identifier(dbname),
                    sql.Identifier(role),
                )
            )
    log(f"database_grants_ok={dbname}")


def harden_schema(
    host: str,
    port: int,
    master_user: str,
    master_password: str,
    dbname: str,
    migrator: str,
    runtime: str,
) -> None:
    conn = connect(host, port, dbname, master_user, master_password, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
            cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cur.execute(
                sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(migrator))
            )
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(runtime)))
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(sql.Identifier(migrator), sql.Identifier(runtime))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT USAGE, SELECT ON SEQUENCES TO {}"
                ).format(sql.Identifier(migrator), sql.Identifier(runtime))
            )
        log(f"schema_hardened={dbname}")
    finally:
        conn.close()


def validate_isolation(host: str, port: int, secrets: dict[str, dict[str, Any]]) -> None:
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

    rt = secrets["prod_runtime"]
    conn = connect(host, port, "panne", rt["username"], rt["password"], autocommit=False)
    try:
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE c2b2_runtime_should_fail(id int)")
            conn.rollback()
            fail("runtime_created_table_unexpected")
        except Exception:
            conn.rollback()
            log("runtime_ddl_denied_ok=panne")
    finally:
        conn.close()

    for key, dbname in [("prod_migrator", "panne"), ("demo_migrator", "panne_demo")]:
        mig = secrets[key]
        conn = connect(host, port, dbname, mig["username"], mig["password"], autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE TABLE {PROBE_TABLE}(id int)")
                cur.execute(f"DROP TABLE {PROBE_TABLE}")
            log(f"migrator_ddl_ok={dbname}")
        finally:
            conn.close()

    conn = connect(host, port, "panne", rt["username"], rt["password"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW ssl")
            ssl_val = cur.fetchone()[0]
            if SSLMODE == "require" and str(ssl_val).lower() not in {"on", "true", "1"}:
                fail(f"ssl_not_on value={ssl_val}")
            # Also confirm pg_stat_ssl for this backend when available
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


def assert_actionhub_intact(admin) -> None:
    if not db_exists(admin, "actionhub_prod"):
        fail("actionhub_prod missing")
    log("actionhub_prod_intact=true")


def assert_no_probe_objects(host: str, port: int, secrets: dict[str, dict[str, Any]]) -> None:
    for key, dbname in [("prod_migrator", "panne"), ("demo_migrator", "panne_demo")]:
        s = secrets[key]
        conn = connect(host, port, dbname, s["username"], s["password"], autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT to_regclass('public.{PROBE_TABLE}')")
                if cur.fetchone()[0] is not None:
                    fail(f"probe table remains in {dbname}")
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name LIKE 'c2%probe%'
                    """
                )
            log(f"no_probe_objects={dbname}")
        finally:
            conn.close()


def bootstrap_postgres(
    host: str,
    port: int,
    master_user: str,
    master_password: str,
    app_secrets: dict[str, dict[str, Any]],
    *,
    maintenance_db: str = "actionhub_prod",
    require_actionhub: bool = True,
) -> None:
    """Core idempotent bootstrap (testable without AWS)."""
    admin = connect(host, port, maintenance_db, master_user, master_password, autocommit=True)
    try:
        if require_actionhub:
            assert_actionhub_intact(admin)
        else:
            log(f"maintenance_db={maintenance_db} require_actionhub=false")

        clear_master_panne_memberships(admin, master_user)
        assert_no_master_panne_memberships(admin, master_user)

        log(
            "state_probe roles="
            + ",".join(
                f"{EXPECTED[k]['username']}:{'yes' if role_exists(admin, EXPECTED[k]['username']) else 'no'}"
                for k in EXPECTED
            )
        )
        log(
            "state_probe dbs="
            + ",".join(
                f"{name}:{'yes' if db_exists(admin, name) else 'no'}"
                for name in ("panne", "panne_demo")
            )
        )

        ensure_role(admin, app_secrets["prod_migrator"]["username"], app_secrets["prod_migrator"]["password"])
        ensure_role(admin, app_secrets["prod_runtime"]["username"], app_secrets["prod_runtime"]["password"])
        ensure_role(admin, app_secrets["demo_migrator"]["username"], app_secrets["demo_migrator"]["password"])
        ensure_role(admin, app_secrets["demo_runtime"]["username"], app_secrets["demo_runtime"]["password"])

        # One environment at a time: create + revoke membership before the next.
        ensure_database(admin, "panne", "panne_prod_migrator", master_user)
        assert_no_master_panne_memberships(admin, master_user)
        ensure_database(admin, "panne_demo", "panne_demo_migrator", master_user)
        assert_no_master_panne_memberships(admin, master_user)

        apply_database_acls(
            admin,
            "panne",
            "panne_prod_migrator",
            "panne_prod_runtime",
            ["panne_demo_migrator", "panne_demo_runtime"],
        )
        apply_database_acls(
            admin,
            "panne_demo",
            "panne_demo_migrator",
            "panne_demo_runtime",
            ["panne_prod_migrator", "panne_prod_runtime"],
        )
        assert_no_master_panne_memberships(admin, master_user)
    finally:
        # Never leave residual memberships even if mid-flight failure escaped ensure_database.
        try:
            clear_master_panne_memberships(admin, master_user)
        except SystemExit:
            admin.close()
            raise
        except Exception as exc:  # noqa: BLE001
            log_exc("bootstrap_finally_membership_cleanup", exc)
        admin.close()

    harden_schema(
        host, port, master_user, master_password, "panne", "panne_prod_migrator", "panne_prod_runtime"
    )
    harden_schema(
        host,
        port,
        master_user,
        master_password,
        "panne_demo",
        "panne_demo_migrator",
        "panne_demo_runtime",
    )

    validate_isolation(host, port, app_secrets)
    assert_no_probe_objects(host, port, app_secrets)

    verify = connect(host, port, maintenance_db, master_user, master_password, autocommit=True)
    try:
        if require_actionhub:
            assert_actionhub_intact(verify)
        assert_no_master_panne_memberships(verify, master_user)
    finally:
        verify.close()


def main() -> None:
    log("bootstrap_start cycle=027-C2-B2")
    master_secret_id = _require_env("PANNE_MASTER_SECRET_ID")
    secret_ids = _secret_ids()
    sm = boto3.client("secretsmanager", region_name=REGION)

    master = get_secret(sm, master_secret_id)
    master_user = master.get("username") or master.get("Username")
    master_password = master.get("password") or master.get("Password")
    host = master.get("host") or master.get("Host")
    port = int(master.get("port") or master.get("Port") or 5432)
    if not master_user or not master_password:
        fail("master secret missing username/password")

    app_secrets: dict[str, dict[str, Any]] = {}
    for key, sid in secret_ids.items():
        data = get_secret(sm, sid)
        exp = EXPECTED[key]
        if data.get("username") != exp["username"]:
            fail(f"username mismatch secret={sid}")
        if data.get("dbname") != exp["dbname"]:
            fail(f"dbname mismatch secret={sid}")
        if not data.get("password"):
            fail(f"password missing secret={sid}")
        host = host or data.get("host")
        port = int(data.get("port") or port)
        app_secrets[key] = data
        log(f"secret_loaded name={sid} user={exp['username']} db={exp['dbname']}")

    if not host:
        fail("no host in secrets")

    bootstrap_postgres(host, port, master_user, master_password, app_secrets)

    for key, sid in secret_ids.items():
        tag_secret_synced(sm, sid)

    log("bootstrap_success")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        log_exc("unhandled", exc)
        sys.exit(2)
