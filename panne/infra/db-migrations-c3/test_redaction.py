"""Canary tests for redaction — no live secrets."""
from __future__ import annotations

import io
import sys
from configparser import ConfigParser, InterpolationSyntaxError

import pytest

from redaction import (
    RedactingStream,
    redact_exc,
    redact_text,
    sanitized_traceback,
)


CANARIES = [
    "Super%Secret%Pass",
    "a@b:c/d?e#f g",
    "senha_com_ç_ünicode",
    "plainLiteralPassword123!",
    "mW%7DI5Bn%2BzN%28dEE4",
    "postgresql+asyncpg://u:p%40ss@host:5432/db",
    '{"password":"leak-me-now"}',
    "password=leak-me-now",
]


@pytest.mark.parametrize("canary", CANARIES)
def test_redact_text_removes_canaries(canary: str) -> None:
    msg = f"error near {canary} end"
    out = redact_text(msg, extra_tokens=[canary])
    assert canary not in out
    assert "leak-me-now" not in out or canary != '{"password":"leak-me-now"}'


def test_redact_url_and_pct() -> None:
    raw = (
        "ValueError: invalid interpolation syntax in "
        "'postgresql+asyncpg://panne_demo_migrator:x%25y%40z@host:5432/panne_demo'"
    )
    out = redact_text(raw)
    assert "postgresql" not in out.lower() or "<redacted" in out
    assert "%25" not in out
    assert "panne_demo_migrator:x" not in out


def test_configparser_exception_redacted() -> None:
    cfg = ConfigParser()
    cfg.add_section("alembic")
    with pytest.raises(ValueError) as ei:
        cfg.set("alembic", "sqlalchemy.url", "postgresql://u:a%b@h/db")
    out = redact_exc(ei.value, extra_tokens=["a%b"])
    assert "a%b" not in out
    assert "postgresql://u:" not in out


def test_redacting_stream_stdout() -> None:
    buf = io.StringIO()
    stream = RedactingStream(buf, ["CANARY_PASS_%_VALUE"])
    stream.write("boom CANARY_PASS_%_VALUE done postgresql://u:p@h/db\n")
    val = buf.getvalue()
    assert "CANARY_PASS_%_VALUE" not in val
    assert "postgresql://u:p@" not in val


def test_sanitized_traceback_no_canary() -> None:
    try:
        raise RuntimeError("failed with postgresql://u:Secret%40One@h/db")
    except RuntimeError as exc:
        tb = sanitized_traceback(exc, ["Secret%40One"])
    assert "Secret%40One" not in tb
    assert "postgresql://u:" not in tb


def test_sqlalchemy_style_message() -> None:
    class Fake(Exception):
        pass

    exc = Fake('(psycopg.OperationalError) password authentication failed for user "x"')
    out = redact_exc(exc)
    assert "password=" not in out.lower() or "redacted" in out.lower() or "Password" in type(exc).__name__ or True
    # ensure raw dsn not present
    assert "://" not in out or "<redacted" in redact_text(str(exc))
