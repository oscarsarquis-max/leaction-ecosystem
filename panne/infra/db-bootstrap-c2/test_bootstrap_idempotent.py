"""Local integration tests for idempotent bootstrap (throwaway Postgres only)."""
from __future__ import annotations

import os
import subprocess
import time
import unittest
import uuid

import psycopg
from psycopg import sql as pgsql

# Force non-TLS for local docker Postgres
os.environ["PANNE_PG_SSLMODE"] = "disable"

from bootstrap import (  # noqa: E402
    bootstrap_postgres,
    connect,
    db_exists,
    ensure_database,
    fetch_role_attrs,
    role_exists,
)


CONTAINER = f"panne-c2b1-pg-{uuid.uuid4().hex[:8]}"
PORT = 55433
DSN_ADMIN = f"postgresql://postgres:diag@127.0.0.1:{PORT}/postgres"
HOST = "127.0.0.1"


def _secrets() -> dict:
    return {
        "prod_migrator": {
            "username": "panne_prod_migrator",
            "password": "prod_mig_pw_test",
            "dbname": "panne",
        },
        "prod_runtime": {
            "username": "panne_prod_runtime",
            "password": "prod_rt_pw_test",
            "dbname": "panne",
        },
        "demo_migrator": {
            "username": "panne_demo_migrator",
            "password": "demo_mig_pw_test",
            "dbname": "panne_demo",
        },
        "demo_runtime": {
            "username": "panne_demo_runtime",
            "password": "demo_rt_pw_test",
            "dbname": "panne_demo",
        },
    }


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _wait_ready() -> None:
    for _ in range(40):
        try:
            with psycopg.connect(DSN_ADMIN, connect_timeout=2) as c:
                with c.cursor() as cur:
                    cur.execute("SELECT 1")
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError("local postgres not ready")


def setUpModule() -> None:
    _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER,
            "-e",
            "POSTGRES_PASSWORD=diag",
            "-p",
            f"{PORT}:5432",
            "postgres:17-alpine",
        ]
    )
    _wait_ready()
    # Create stand-in maintenance DB name matching production check path when required
    with psycopg.connect(DSN_ADMIN, autocommit=True) as c:
        with c.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'actionhub_prod'")
            if cur.fetchone() is None:
                cur.execute("CREATE DATABASE actionhub_prod")


def tearDownModule() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], check=False, capture_output=True)


class IntransRegressionTests(unittest.TestCase):
    def test_cannot_toggle_autocommit_in_intrans(self) -> None:
        from psycopg.errors import ProgrammingError

        conn = psycopg.connect(DSN_ADMIN, autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            with self.assertRaises(ProgrammingError) as ctx:
                conn.autocommit = True
            self.assertIn("autocommit", str(ctx.exception).lower())
        finally:
            conn.close()

    def test_create_database_on_autocommit_from_start(self) -> None:
        admin = connect(HOST, PORT, "postgres", "postgres", "diag", autocommit=True)
        try:
            self.assertTrue(admin.autocommit)
            name = f"c2b2_tmp_{uuid.uuid4().hex[:8]}"
            mig = f"c2b2_mig_{uuid.uuid4().hex[:6]}"
            with admin.cursor() as cur:
                cur.execute(
                    pgsql.SQL(
                        "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                    ).format(pgsql.Identifier(mig))
                )
            ensure_database(admin, name, mig, "postgres")
            self.assertTrue(db_exists(admin, name))
            with admin.cursor() as cur:
                cur.execute(pgsql.SQL("DROP DATABASE {} WITH (FORCE)").format(pgsql.Identifier(name)))
                cur.execute(pgsql.SQL("DROP ROLE {}").format(pgsql.Identifier(mig)))
        finally:
            admin.close()


class IdempotentBootstrapTests(unittest.TestCase):
    def _master(self) -> tuple[str, str]:
        return "postgres", "diag"

    def test_empty_state(self) -> None:
        user, pw = self._master()
        # Drop roles/dbs if leftover from prior method
        self._cleanup_partial()
        bootstrap_postgres(
            HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
        )
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            self.assertTrue(db_exists(admin, "panne"))
            self.assertTrue(db_exists(admin, "panne_demo"))
            for r in (
                "panne_prod_migrator",
                "panne_prod_runtime",
                "panne_demo_migrator",
                "panne_demo_runtime",
            ):
                self.assertTrue(role_exists(admin, r))
                attrs = fetch_role_attrs(admin, r)
                assert attrs is not None
                self.assertFalse(attrs[0])  # super
        finally:
            admin.close()

    def test_roles_exist_dbs_missing_then_rerun(self) -> None:
        user, pw = self._master()
        self._cleanup_partial()
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            for name, secret_key in [
                ("panne_prod_migrator", "prod_migrator"),
                ("panne_prod_runtime", "prod_runtime"),
                ("panne_demo_migrator", "demo_migrator"),
                ("panne_demo_runtime", "demo_runtime"),
            ]:
                s = _secrets()[secret_key]
                with admin.cursor() as cur:
                    cur.execute(
                        pgsql.SQL(
                            "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                            "NOREPLICATION NOBYPASSRLS PASSWORD {}"
                        ).format(pgsql.Identifier(name), pgsql.Literal(s["password"]))
                    )
        finally:
            admin.close()
        bootstrap_postgres(
            HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
        )
        # second full rerun must be idempotent
        bootstrap_postgres(
            HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
        )

    def test_already_correct_rerun(self) -> None:
        user, pw = self._master()
        bootstrap_postgres(
            HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
        )
        bootstrap_postgres(
            HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
        )

    def test_dangerous_role_attrs_stops(self) -> None:
        user, pw = self._master()
        self._cleanup_partial()
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            with admin.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN CREATEDB NOSUPERUSER "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
        finally:
            admin.close()
        with self.assertRaises(SystemExit):
            bootstrap_postgres(
                HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
            )

    def test_unexpected_owner_stops(self) -> None:
        user, pw = self._master()
        self._cleanup_partial()
        # create roles first with safe attrs
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            for name in (
                "panne_prod_migrator",
                "panne_prod_runtime",
                "panne_demo_migrator",
                "panne_demo_runtime",
            ):
                if not role_exists(admin, name):
                    with admin.cursor() as cur:
                        cur.execute(
                            pgsql.SQL(
                                "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                                "NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                            ).format(pgsql.Identifier(name))
                        )
            with admin.cursor() as cur:
                cur.execute("CREATE DATABASE panne OWNER postgres")
        finally:
            admin.close()
        with self.assertRaises(SystemExit):
            bootstrap_postgres(
                HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
            )

    def test_partial_failure_mid_demo_then_resume(self) -> None:
        """Simulate prod OK / demo DB missing — resume completes demo."""
        user, pw = self._master()
        self._cleanup_partial()
        secrets = _secrets()
        bootstrap_postgres(
            HOST, PORT, user, pw, secrets, maintenance_db="actionhub_prod", require_actionhub=True
        )
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            # Force "partial" by dropping demo DB only (roles remain)
            with admin.cursor() as cur:
                cur.execute("DROP DATABASE panne_demo WITH (FORCE)")
            self.assertFalse(db_exists(admin, "panne_demo"))
            self.assertTrue(db_exists(admin, "panne"))
        finally:
            admin.close()
        bootstrap_postgres(
            HOST, PORT, user, pw, secrets, maintenance_db="actionhub_prod", require_actionhub=True
        )
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            self.assertTrue(db_exists(admin, "panne_demo"))
        finally:
            admin.close()

    def test_no_temp_probe_left(self) -> None:
        user, pw = self._master()
        bootstrap_postgres(
            HOST, PORT, user, pw, _secrets(), maintenance_db="actionhub_prod", require_actionhub=True
        )
        for db in ("panne", "panne_demo"):
            conn = connect(HOST, PORT, db, "panne_prod_migrator" if db == "panne" else "panne_demo_migrator",
                           _secrets()["prod_migrator"]["password"] if db == "panne" else _secrets()["demo_migrator"]["password"],
                           autocommit=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'c2%'"
                    )
                    self.assertEqual(cur.fetchall(), [])
            finally:
                conn.close()

    def _cleanup_partial(self) -> None:
        user, pw = self._master()
        admin = connect(HOST, PORT, "actionhub_prod", user, pw, autocommit=True)
        try:
            with admin.cursor() as cur:
                for db in ("panne", "panne_demo"):
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
                    if cur.fetchone():
                        cur.execute(
                            pgsql.SQL("DROP DATABASE {} WITH (FORCE)").format(pgsql.Identifier(db))
                        )
                for role in (
                    "panne_prod_migrator",
                    "panne_prod_runtime",
                    "panne_demo_migrator",
                    "panne_demo_runtime",
                ):
                    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                    if cur.fetchone():
                        cur.execute(pgsql.SQL("DROP ROLE {}").format(pgsql.Identifier(role)))
        finally:
            admin.close()


if __name__ == "__main__":
    unittest.main()
