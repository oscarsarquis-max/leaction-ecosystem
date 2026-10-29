"""CURSOR-027-C2-B2 membership / ownership tests (throwaway Postgres 17)."""
from __future__ import annotations

import os
import subprocess
import time
import unittest
import uuid
from unittest import mock

import psycopg
from psycopg import sql as pgsql
from psycopg.errors import InsufficientPrivilege

os.environ["PANNE_PG_SSLMODE"] = "disable"

from bootstrap import (  # noqa: E402
    MEMBERSHIP_GRANT_SQL,
    assert_no_master_panne_memberships,
    bootstrap_postgres,
    clear_master_panne_memberships,
    connect,
    db_exists,
    ensure_database,
    grant_set_membership,
    has_set_membership,
    is_direct_member,
    revoke_membership,
)


CONTAINER = f"panne-c2b2-mem-{uuid.uuid4().hex[:8]}"
PORT = 55435
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
    admin = connect(HOST, PORT, "postgres", "postgres", "diag", autocommit=True)
    try:
        with admin.cursor() as cur:
            cur.execute("CREATE DATABASE actionhub_prod")
            cur.execute(
                "CREATE ROLE rds_like_master LOGIN CREATEDB CREATEROLE NOSUPERUSER "
                "NOREPLICATION NOBYPASSRLS PASSWORD 'masterpw'"
            )
            cur.execute("GRANT CONNECT, CREATE ON DATABASE actionhub_prod TO rds_like_master")
            cur.execute("GRANT CONNECT, CREATE ON DATABASE postgres TO rds_like_master")
    finally:
        admin.close()


def tearDownModule() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], check=False, capture_output=True)


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


def _super():
    return connect(HOST, PORT, "postgres", "postgres", "diag", autocommit=True)


def _rds_like():
    return connect(HOST, PORT, "actionhub_prod", "rds_like_master", "masterpw", autocommit=True)


def _cleanup_panne() -> None:
    s = _super()
    try:
        with s.cursor() as cur:
            for db in ("panne", "panne_demo"):
                cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db,))
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
                cur.execute(
                    """
                    SELECT 1 FROM pg_auth_members am
                    JOIN pg_roles r ON r.oid=am.member
                    JOIN pg_roles m ON m.oid=am.roleid
                    WHERE r.rolname='rds_like_master' AND m.rolname=%s
                    """,
                    (role,),
                )
                if cur.fetchone():
                    cur.execute(
                        pgsql.SQL("REVOKE {} FROM rds_like_master CASCADE").format(
                            pgsql.Identifier(role)
                        )
                    )
                cur.execute(
                    """
                    SELECT 1 FROM pg_auth_members am
                    JOIN pg_roles r ON r.oid=am.member
                    JOIN pg_roles m ON m.oid=am.roleid
                    WHERE r.rolname='postgres' AND m.rolname=%s
                    """,
                    (role,),
                )
                if cur.fetchone():
                    cur.execute(
                        pgsql.SQL("REVOKE {} FROM postgres CASCADE").format(pgsql.Identifier(role))
                    )
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
                if cur.fetchone():
                    cur.execute(pgsql.SQL("DROP ROLE {}").format(pgsql.Identifier(role)))
    finally:
        s.close()


class Pg17MembershipSyntaxTests(unittest.TestCase):
    def test_granular_syntax_constant(self) -> None:
        self.assertIn("ADMIN FALSE", MEMBERSHIP_GRANT_SQL)
        self.assertIn("INHERIT FALSE", MEMBERSHIP_GRANT_SQL)
        self.assertIn("SET TRUE", MEMBERSHIP_GRANT_SQL)

    def test_grant_set_without_admin_option(self) -> None:
        s = _super()
        try:
            with s.cursor() as cur:
                cur.execute(
                    "CREATE ROLE t_mig LOGIN NOSUPERUSER; CREATE ROLE t_adm LOGIN CREATEDB PASSWORD 'x'"
                )
                cur.execute(
                    "GRANT t_mig TO t_adm WITH ADMIN FALSE, INHERIT FALSE, SET TRUE"
                )
                cur.execute(
                    """
                    SELECT admin_option, inherit_option, set_option
                    FROM pg_auth_members am
                    JOIN pg_roles r ON r.oid=am.member
                    JOIN pg_roles m ON m.oid=am.roleid
                    WHERE r.rolname='t_adm' AND m.rolname='t_mig'
                    """
                )
                admin_opt, inherit_opt, set_opt = cur.fetchone()
                self.assertFalse(admin_opt)
                self.assertFalse(inherit_opt)
                self.assertTrue(set_opt)
                cur.execute("REVOKE t_mig FROM t_adm")
                cur.execute("DROP ROLE t_adm; DROP ROLE t_mig")
        finally:
            s.close()

    def test_cannot_create_owner_without_set_membership(self) -> None:
        s = _super()
        try:
            with s.cursor() as cur:
                cur.execute(
                    "CREATE ROLE t_mig2 LOGIN NOSUPERUSER; "
                    "CREATE ROLE t_adm2 LOGIN CREATEDB PASSWORD 'x'"
                )
        finally:
            s.close()
        adm = connect(HOST, PORT, "postgres", "t_adm2", "x", autocommit=True)
        try:
            with self.assertRaises(InsufficientPrivilege):
                with adm.cursor() as cur:
                    cur.execute("CREATE DATABASE t_fail_own OWNER t_mig2")
        finally:
            adm.close()
            s = _super()
            try:
                with s.cursor() as cur:
                    cur.execute("DROP ROLE IF EXISTS t_adm2; DROP ROLE IF EXISTS t_mig2")
            finally:
                s.close()


class MembershipLifecycleTests(unittest.TestCase):
    def test_master_starts_without_membership(self) -> None:
        _cleanup_panne()
        m = _super()
        try:
            assert_no_master_panne_memberships(m, "postgres")
        finally:
            m.close()

    def test_grant_create_revoke_owner(self) -> None:
        _cleanup_panne()
        m = _rds_like()
        try:
            with m.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
            self.assertFalse(has_set_membership(m, "rds_like_master", "panne_prod_migrator"))
            ensure_database(m, "panne", "panne_prod_migrator", "rds_like_master")
            self.assertTrue(db_exists(m, "panne"))
            self.assertFalse(has_set_membership(m, "rds_like_master", "panne_prod_migrator"))
            with m.cursor() as cur:
                cur.execute(
                    "SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname='panne'"
                )
                self.assertEqual(cur.fetchone()[0], "panne_prod_migrator")
        finally:
            m.close()
            _cleanup_panne()

    def test_fail_before_create_still_revokes(self) -> None:
        _cleanup_panne()
        m = _rds_like()
        try:
            with m.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
            granted = False
            try:
                grant_set_membership(m, "panne_prod_migrator", "rds_like_master")
                granted = True
                raise RuntimeError("fail_before_create")
            except RuntimeError:
                pass
            finally:
                if granted:
                    revoke_membership(m, "panne_prod_migrator", "rds_like_master")
            self.assertFalse(has_set_membership(m, "rds_like_master", "panne_prod_migrator"))
        finally:
            m.close()
            _cleanup_panne()

    def test_fail_after_create_still_revokes(self) -> None:
        _cleanup_panne()
        m = _rds_like()
        try:
            with m.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
            create_error = None
            granted = False
            try:
                grant_set_membership(m, "panne_prod_migrator", "rds_like_master")
                granted = True
                with m.cursor() as cur:
                    cur.execute("CREATE DATABASE panne OWNER panne_prod_migrator ENCODING 'UTF8'")
                raise RuntimeError("fail_after_create")
            except RuntimeError as exc:
                create_error = exc
            finally:
                if granted:
                    revoke_membership(m, "panne_prod_migrator", "rds_like_master")
            self.assertIsNotNone(create_error)
            self.assertTrue(db_exists(m, "panne"))
            self.assertFalse(has_set_membership(m, "rds_like_master", "panne_prod_migrator"))
        finally:
            m.close()
            _cleanup_panne()

    def test_fail_during_revoke_surfaces(self) -> None:
        _cleanup_panne()
        m = _rds_like()
        try:
            with m.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
            with mock.patch(
                "bootstrap.revoke_membership", side_effect=RuntimeError("revoke_boom")
            ):
                with self.assertRaises(SystemExit):
                    ensure_database(m, "panne", "panne_prod_migrator", "rds_like_master")
        finally:
            m.close()
            _cleanup_panne()

    def test_residual_set_membership_cleaned_at_start(self) -> None:
        _cleanup_panne()
        m = _rds_like()
        try:
            with m.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
            grant_set_membership(m, "panne_prod_migrator", "rds_like_master")
            self.assertTrue(has_set_membership(m, "rds_like_master", "panne_prod_migrator"))
            revoke_membership(m, "panne_prod_migrator", "rds_like_master")
            self.assertFalse(has_set_membership(m, "rds_like_master", "panne_prod_migrator"))
        finally:
            m.close()
            _cleanup_panne()

    def test_finally_cleanup_on_ensure_database(self) -> None:
        _cleanup_panne()
        # Superuser path exercises grant/revoke SET without CREATEROLE residual ADMIN.
        s = _super()
        try:
            with s.cursor() as cur:
                cur.execute(
                    "CREATE ROLE panne_prod_migrator WITH LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                )
            ensure_database(s, "panne", "panne_prod_migrator", "postgres")
            self.assertFalse(has_set_membership(s, "postgres", "panne_prod_migrator"))
            self.assertFalse(is_direct_member(s, "postgres", "panne_prod_migrator"))
        finally:
            s.close()
            _cleanup_panne()

    def test_rerun_existing_correct_owner(self) -> None:
        _cleanup_panne()
        bootstrap_postgres(
            HOST, PORT, "postgres", "diag", _secrets(),
            maintenance_db="actionhub_prod", require_actionhub=True,
        )
        bootstrap_postgres(
            HOST, PORT, "postgres", "diag", _secrets(),
            maintenance_db="actionhub_prod", require_actionhub=True,
        )
        s = _super()
        try:
            assert_no_master_panne_memberships(s, "postgres")
            self.assertFalse(is_direct_member(s, "postgres", "panne_prod_runtime"))
        finally:
            s.close()

    def test_existing_wrong_owner_stops(self) -> None:
        _cleanup_panne()
        s = _super()
        try:
            with s.cursor() as cur:
                for role in (
                    "panne_prod_migrator",
                    "panne_prod_runtime",
                    "panne_demo_migrator",
                    "panne_demo_runtime",
                ):
                    cur.execute(
                        pgsql.SQL(
                            "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                            "NOREPLICATION NOBYPASSRLS PASSWORD 'x'"
                        ).format(pgsql.Identifier(role))
                    )
                cur.execute("CREATE DATABASE panne OWNER postgres")
        finally:
            s.close()
        with self.assertRaises(SystemExit):
            bootstrap_postgres(
                HOST, PORT, "postgres", "diag", _secrets(),
                maintenance_db="actionhub_prod", require_actionhub=True,
            )

    def test_runtime_never_receives_membership(self) -> None:
        _cleanup_panne()
        bootstrap_postgres(
            HOST, PORT, "postgres", "diag", _secrets(),
            maintenance_db="actionhub_prod", require_actionhub=True,
        )
        s = _super()
        try:
            self.assertFalse(is_direct_member(s, "postgres", "panne_prod_runtime"))
            self.assertFalse(is_direct_member(s, "postgres", "panne_demo_runtime"))
        finally:
            s.close()

    def test_zero_membership_at_end(self) -> None:
        _cleanup_panne()
        bootstrap_postgres(
            HOST, PORT, "postgres", "diag", _secrets(),
            maintenance_db="actionhub_prod", require_actionhub=True,
        )
        s = _super()
        try:
            assert_no_master_panne_memberships(s, "postgres")
        finally:
            s.close()

    def test_no_admin_option_on_temporary_grant(self) -> None:
        s = _super()
        try:
            with s.cursor() as cur:
                cur.execute("CREATE ROLE t_mig3 LOGIN NOSUPERUSER")
            grant_set_membership(s, "t_mig3", "postgres")
            with s.cursor() as cur:
                cur.execute(
                    """
                    SELECT admin_option FROM pg_auth_members am
                    JOIN pg_roles r ON r.oid=am.member
                    JOIN pg_roles m ON m.oid=am.roleid
                    WHERE r.rolname='postgres' AND m.rolname='t_mig3' AND set_option
                    """
                )
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertFalse(row[0])
            revoke_membership(s, "t_mig3", "postgres")
            with s.cursor() as cur:
                cur.execute("DROP ROLE t_mig3")
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
