"""CURSOR-027-C3-H3 — one-shot demo migrator password substitution (no master).

Never logs passwords, URLs, or secret JSON. Compensates on failure when possible.
"""
from __future__ import annotations

import json
import os
import secrets
import string
import sys
from typing import Any

import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from redaction import install_stdio_redaction, log_safe, redact_exc

REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
SECRET_ID = "panne/demo/db/migrator"
EXPECTED_USER = "panne_demo_migrator"
EXPECTED_DB = "panne_demo"
_TOKENS: list[str] = []


def log(msg: str) -> None:
    log_safe(msg, _TOKENS)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def sslmode() -> str:
    return os.environ.get("PANNE_PG_SSLMODE", "require")


def gen_password(length: int = 48) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#%^*_-+=?"
    # Ensure at least one of each class; avoid characters that break shell/URLs needlessly
    # but include % to keep realism — runner must never put this in ConfigParser.
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#%^*_-+=?" for c in pwd)
        ):
            return pwd


def parse_secret(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        fail("secret not object")
    for key in ("username", "password", "host", "port", "dbname"):
        if key not in data or data[key] in (None, ""):
            fail(f"secret missing field {key}")
    return data


def engine_for(data: dict[str, Any], password: str):
    url = URL.create(
        "postgresql+psycopg",
        username=str(data["username"]),
        password=password,
        host=str(data["host"]),
        port=int(data["port"]),
        database=str(data["dbname"]),
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        future=True,
        connect_args={"sslmode": sslmode(), "connect_timeout": 30},
    )


def assert_session(data: dict[str, Any], password: str) -> None:
    eng = engine_for(data, password)
    try:
        with eng.connect() as conn:
            user, db = conn.execute(text("SELECT current_user, current_database()")).one()
            ssl = conn.execute(text("SHOW ssl")).scalar()
            if user != EXPECTED_USER or db != EXPECTED_DB:
                fail("session identity mismatch")
            if str(ssl).lower() not in {"on", "1", "true"}:
                fail("TLS required")
            owner = conn.execute(
                text(
                    "SELECT pg_catalog.pg_get_userbyid(d.datdba) "
                    "FROM pg_database d WHERE d.datname = current_database()"
                )
            ).scalar()
            if owner != EXPECTED_USER:
                fail("owner mismatch")
            log(f"session_ok user={user} db={db} ssl={ssl} owner={owner}")
    finally:
        eng.dispose()


def alter_own_password(data: dict[str, Any], current_password: str, new_password: str) -> None:
    # Use psycopg sql.Literal so the password is never string-interpolated into logs.
    with psycopg.connect(
        host=str(data["host"]),
        port=int(data["port"]),
        dbname=str(data["dbname"]),
        user=str(data["username"]),
        password=current_password,
        sslmode=sslmode(),
        connect_timeout=30,
        autocommit=True,
    ) as conn:
        conn.execute("SELECT set_config('application_name', 'panne-c3-h3-rotate', true)")
        conn.execute(
            sql.SQL("ALTER ROLE CURRENT_USER PASSWORD {}").format(sql.Literal(new_password))
        )
        log("postgres_password_altered=true")


def main() -> None:
    install_stdio_redaction(_TOKENS)
    if os.environ.get("AUTHORIZED_RUN_ID") != "cursor-027-c3-h3-rotate-demo-migrator-authorized-once":
        fail("AUTHORIZED_RUN_ID mismatch")
    if os.environ.get("PANNE_MASTER_SECRET_ID"):
        fail("master must not be set")
    if sslmode() != "require":
        fail("PANNE_PG_SSLMODE must be require")

    sm = boto3.client("secretsmanager", region_name=REGION)
    cur = sm.get_secret_value(SecretId=SECRET_ID, VersionStage="AWSCURRENT")
    data = parse_secret(cur["SecretString"])
    if str(data["username"]) != EXPECTED_USER or str(data["dbname"]) != EXPECTED_DB:
        fail("secret identity mismatch")
    old_password = str(data["password"])
    _TOKENS.append(old_password)
    log(f"secret_current_loaded id={SECRET_ID} user={EXPECTED_USER} db={EXPECTED_DB}")

    new_password = gen_password()
    _TOKENS.append(new_password)
    pending_payload = dict(data)
    pending_payload["password"] = new_password
    pending_raw = json.dumps(pending_payload)

    # Put AWSPENDING
    try:
        sm.put_secret_value(
            SecretId=SECRET_ID,
            ClientRequestToken=str(
                __import__("uuid").uuid5(
                    __import__("uuid").NAMESPACE_URL,
                    os.environ.get(
                        "ROTATE_CLIENT_TOKEN",
                        "cursor-027-c3-h3-rotate-demo-migrator-authorized-once",
                    ),
                )
            ),
            SecretString=pending_raw,
            VersionStages=["AWSPENDING"],
        )
        log("secret_awspending_created=true")
    except ClientError as exc:
        fail(f"put_pending_failed {redact_exc(exc, _TOKENS)}")

    pg_changed = False
    try:
        assert_session(data, old_password)
        alter_own_password(data, old_password, new_password)
        pg_changed = True
        assert_session(data, new_password)
        log("new_password_login_ok=true")

        # Promote: move AWSCURRENT to new version
        meta = sm.describe_secret(SecretId=SECRET_ID)
        pending_vid = None
        current_vid = None
        for vid, stages in (meta.get("VersionIdsToStages") or {}).items():
            if "AWSPENDING" in stages:
                pending_vid = vid
            if "AWSCURRENT" in stages:
                current_vid = vid
        if not pending_vid or not current_vid:
            fail("missing version ids for stage move")
        sm.update_secret_version_stage(
            SecretId=SECRET_ID,
            VersionStage="AWSCURRENT",
            MoveToVersionId=pending_vid,
            RemoveFromVersionId=current_vid,
        )
        # Drop AWSPENDING label from the new current version if still present.
        try:
            sm.update_secret_version_stage(
                SecretId=SECRET_ID,
                VersionStage="AWSPENDING",
                RemoveFromVersionId=pending_vid,
            )
        except ClientError:
            pass
        log("secret_awscurrent_promoted=true")

        # Confirm old password rejected
        try:
            assert_session(data, old_password)
            fail("old_password_still_valid")
        except SystemExit:
            raise
        except Exception:  # noqa: BLE001
            log("old_password_rejected_ok=true")

        # Confirm current secret works
        cur2 = sm.get_secret_value(SecretId=SECRET_ID, VersionStage="AWSCURRENT")
        data2 = parse_secret(cur2["SecretString"])
        _TOKENS.append(str(data2["password"]))
        assert_session(data2, str(data2["password"]))
        log("rotate_success=true")
    except SystemExit:
        if pg_changed:
            log("ERROR: uncertain_state_after_pg_change — attempting restore")
            try:
                alter_own_password(data, new_password, old_password)
                log("postgres_password_restored=true")
            except Exception as restore_exc:  # noqa: BLE001
                log(f"ERROR: restore_failed {redact_exc(restore_exc, _TOKENS)}")
                fail("credential_state_uncertain", code=3)
        raise
    except Exception as exc:  # noqa: BLE001
        log(f"ERROR: rotate_failed {redact_exc(exc, _TOKENS)}")
        if pg_changed:
            try:
                alter_own_password(data, new_password, old_password)
                log("postgres_password_restored=true")
            except Exception as restore_exc:  # noqa: BLE001
                log(f"ERROR: restore_failed {redact_exc(restore_exc, _TOKENS)}")
                fail("credential_state_uncertain", code=3)
        fail("rotate_aborted", code=1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        log_safe(f"ERROR: unhandled {redact_exc(exc, _TOKENS)}", _TOKENS)
        raise SystemExit(1) from None
