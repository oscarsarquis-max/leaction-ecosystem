"""Local H1 harden tests — databases owned by non-superuser migrator roles."""
from __future__ import annotations

import ast
import os
import subprocess
import time
import unittest
import uuid

import psycopg
from psycopg import sql as pgsql

os.environ["PANNE_PG_SSLMODE"] = "disable"
# Prevent accidental master env in harden main import path
os.environ.pop("PANNE_MASTER_SECRET_ID", None)

from harden import (  # noqa: E402
    ENVIRONMENTS,
    harden_all,
    harden_environment,
)


CONTAINER = f"panne-c2h1-{uuid.uuid4().hex[:8]}"
PORT = 55437
HOST = "127.0.0.1"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _wait() -> None:
    for _ in range(40):
        try:
            with psycopg.connect(
                f"postgresql://postgres:diag@127.0.0.1:{PORT}/postgres", connect_timeout=2
            ):
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError("pg not ready")


def _secrets() -> dict:
    return {
        "prod_migrator": {
            "username": "panne_prod_migrator",
            "password": "prod_mig_pw",
            "dbname": "panne",
        },
        "prod_runtime": {
            "username": "panne_prod_runtime",
            "password": "prod_rt_pw",
            "dbname": "panne",
        },
        "demo_migrator": {
            "username": "panne_demo_migrator",
            "password": "demo_mig_pw",
            "dbname": "panne_demo",
        },
        "demo_runtime": {
            "username": "panne_demo_runtime",
            "password": "demo_rt_pw",
            "dbname": "panne_demo",
        },
    }


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
    _wait()
    secrets = _secrets()
    with psycopg.connect(
        f"postgresql://postgres:diag@127.0.0.1:{PORT}/postgres", autocommit=True
    ) as conn:
        with conn.cursor() as cur:
            for key, s in secrets.items():
                cur.execute(
                    pgsql.SQL(
                        "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOREPLICATION NOBYPASSRLS PASSWORD {}"
                    ).format(pgsql.Identifier(s["username"]), pgsql.Literal(s["password"]))
                )
            cur.execute("CREATE DATABASE panne OWNER panne_prod_migrator")
            cur.execute("CREATE DATABASE panne_demo OWNER panne_demo_migrator")
            # Partial prior grants similar to B2 residue
            cur.execute("GRANT CONNECT, TEMPORARY ON DATABASE panne TO panne_prod_migrator, panne_prod_runtime")
            cur.execute("GRANT CONNECT, TEMPORARY ON DATABASE panne_demo TO panne_demo_migrator, panne_demo_runtime")


def tearDownModule() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], check=False, capture_output=True)


class HardenSourceGuardTests(unittest.TestCase):
    def test_no_master_or_role_ddl(self) -> None:
        src = open(
            os.path.join(os.path.dirname(__file__), "harden.py"), encoding="utf-8"
        ).read()
        self.assertNotIn("CREATE ROLE", src)
        self.assertNotIn("ALTER ROLE", src)
        self.assertNotIn("CREATE DATABASE", src)
        self.assertNotIn("ALTER DEFAULT PRIVILEGES FOR ROLE", src)
        # Master may only appear as an explicit refusal guard
        self.assertIn('os.environ.get("PANNE_MASTER_SECRET_ID")', src)
        self.assertNotIn("get_secret(sm, MASTER", src)
        self.assertNotIn("rds!db-", src)

    def test_default_privileges_without_for_role_in_sql(self) -> None:
        src = open(
            os.path.join(os.path.dirname(__file__), "harden.py"), encoding="utf-8"
        ).read()
        self.assertIn("ALTER DEFAULT PRIVILEGES IN SCHEMA public", src)
        self.assertNotIn("ALTER DEFAULT PRIVILEGES FOR ROLE", src)


class HardenAsOwnerTests(unittest.TestCase):
    def test_harden_as_migrator_idempotent(self) -> None:
        secrets = _secrets()
        harden_all(HOST, PORT, secrets)
        harden_all(HOST, PORT, secrets)

    def test_runtime_no_create_no_temp(self) -> None:
        secrets = _secrets()
        harden_environment(HOST, PORT, ENVIRONMENTS[0], secrets)
        with psycopg.connect(
            f"postgresql://panne_prod_runtime:prod_rt_pw@127.0.0.1:{PORT}/panne",
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT has_schema_privilege(current_user, 'public', 'CREATE')"
                )
                self.assertFalse(cur.fetchone()[0])
                cur.execute(
                    "SELECT has_database_privilege(current_user, current_database(), 'TEMPORARY')"
                )
                self.assertFalse(cur.fetchone()[0])
                with self.assertRaises(Exception):
                    cur.execute("CREATE TABLE should_fail(id int)")

    def test_runtime_future_table_grants(self) -> None:
        secrets = _secrets()
        harden_environment(HOST, PORT, ENVIRONMENTS[0], secrets)
        with psycopg.connect(
            f"postgresql://panne_prod_migrator:prod_mig_pw@127.0.0.1:{PORT}/panne",
            autocommit=True,
        ) as mig:
            with mig.cursor() as cur:
                cur.execute("CREATE TABLE h1_future(id int PRIMARY KEY)")
                cur.execute("INSERT INTO h1_future(id) VALUES (1)")
        with psycopg.connect(
            f"postgresql://panne_prod_runtime:prod_rt_pw@127.0.0.1:{PORT}/panne",
            autocommit=True,
        ) as rt:
            with rt.cursor() as cur:
                cur.execute("SELECT id FROM h1_future")
                self.assertEqual(cur.fetchone()[0], 1)
                cur.execute("UPDATE h1_future SET id=2")
                cur.execute("DELETE FROM h1_future")
        with psycopg.connect(
            f"postgresql://panne_prod_migrator:prod_mig_pw@127.0.0.1:{PORT}/panne",
            autocommit=True,
        ) as mig:
            with mig.cursor() as cur:
                cur.execute("DROP TABLE h1_future")

    def test_cross_isolation(self) -> None:
        secrets = _secrets()
        harden_all(HOST, PORT, secrets)
        with self.assertRaises(Exception):
            psycopg.connect(
                f"postgresql://panne_prod_runtime:prod_rt_pw@127.0.0.1:{PORT}/panne_demo",
                connect_timeout=3,
            )
        with self.assertRaises(Exception):
            psycopg.connect(
                f"postgresql://panne_demo_runtime:demo_rt_pw@127.0.0.1:{PORT}/panne",
                connect_timeout=3,
            )

    def test_no_master_needed(self) -> None:
        secrets = _secrets()
        # Ensure env does not provide master
        self.assertIsNone(os.environ.get("PANNE_MASTER_SECRET_ID"))
        harden_environment(HOST, PORT, ENVIRONMENTS[1], secrets)

    def test_default_privileges_in_catalog(self) -> None:
        secrets = _secrets()
        harden_environment(HOST, PORT, ENVIRONMENTS[0], secrets)
        with psycopg.connect(
            f"postgresql://panne_prod_migrator:prod_mig_pw@127.0.0.1:{PORT}/panne",
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM pg_default_acl
                    WHERE defaclnamespace = 'public'::regnamespace
                      AND defaclrole = 'panne_prod_migrator'::regrole
                    """
                )
                self.assertGreater(cur.fetchone()[0], 0)

    def test_wrong_user_session_fails(self) -> None:
        secrets = _secrets()
        # Point prod migrator secret at runtime credentials → session assertion fails
        bad = dict(secrets)
        bad["prod_migrator"] = dict(secrets["prod_runtime"])
        bad["prod_migrator"]["username"] = "panne_prod_runtime"
        with self.assertRaises(SystemExit):
            harden_environment(HOST, PORT, ENVIRONMENTS[0], bad)

    def test_partial_preexisting_then_harden(self) -> None:
        # Module setup already applied partial CONNECT/TEMP grants; harden must reconcile.
        secrets = _secrets()
        harden_environment(HOST, PORT, ENVIRONMENTS[0], secrets)
        with psycopg.connect(
            f"postgresql://panne_prod_runtime:prod_rt_pw@127.0.0.1:{PORT}/panne",
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT has_database_privilege(current_user, current_database(), 'TEMPORARY')"
                )
                self.assertFalse(cur.fetchone()[0])


if __name__ == "__main__":
    unittest.main()
