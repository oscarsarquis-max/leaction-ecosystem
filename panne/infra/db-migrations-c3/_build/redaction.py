"""Central redaction for Panne migration/rotation runners.

Never log passwords, URLs with userinfo, secret JSON, or percent-encoded credentials.
"""
from __future__ import annotations

import re
import sys
import traceback
from typing import Any, Iterable

# Patterns that must never appear in outputs (generic; no live secrets).
_URL_USERINFO = re.compile(
    r"(?i)\b(?:postgresql(?:\+\w+)?|postgres|mysql|mongodb|redis|amqp)://[^\s\"']+",
    re.MULTILINE,
)
_USERINFO_GENERIC = re.compile(
    r"(?i)\b[a-z0-9_.+-]+://[^/\s\"']*:[^/\s\"']+@",
)
_PASSWORD_ASSIGN = re.compile(
    r"(?i)\b(password|passwd|pwd|secretstring|secret_string)\s*[=:]\s*\S+",
)
_PERCENT_SEQ = re.compile(r"(?:%[0-9A-Fa-f]{2}){2,}")
_JSON_PASSWORD = re.compile(
    r'(?i)"password"\s*:\s*"[^"]*"',
)
_DSN_KV = re.compile(
    r"(?i)\b(password|pwd)\s*=\s*[^\s;]+",
)


def redact_text(text: str, extra_tokens: Iterable[str] | None = None) -> str:
    if not text:
        return text
    out = text
    for tok in extra_tokens or ():
        if tok and len(tok) >= 4:
            out = out.replace(tok, "<redacted>")
    out = _URL_USERINFO.sub("<redacted-url>", out)
    out = _USERINFO_GENERIC.sub("<redacted-url>", out)
    out = _JSON_PASSWORD.sub('"password":"<redacted>"', out)
    out = _PASSWORD_ASSIGN.sub(r"\1=<redacted>", out)
    out = _DSN_KV.sub(r"\1=<redacted>", out)
    # Percent-encoded blobs often are passwords in URLs; scrub long runs.
    out = _PERCENT_SEQ.sub("<redacted-pct>", out)
    return out


def redact_exc(exc: BaseException, extra_tokens: Iterable[str] | None = None) -> str:
    parts = [type(exc).__name__]
    msg = redact_text(str(exc).replace("\n", " "), extra_tokens)[:200]
    if msg:
        parts.append(msg)
    state = getattr(exc, "sqlstate", None) or getattr(exc, "pgcode", None)
    if state:
        parts.append(f"sqlstate={state}")
    return " ".join(parts)


def sanitized_traceback(exc: BaseException, extra_tokens: Iterable[str] | None = None) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=8))
    # Drop locals-like dumps if present
    lines = []
    for line in tb.splitlines():
        if "locals" in line.lower() and "=" in line:
            continue
        lines.append(redact_text(line, extra_tokens))
    return "\n".join(lines)


class RedactingStream:
    """Wrap stdout/stderr so library prints cannot leak credentials."""

    def __init__(self, wrapped: Any, extra_tokens: Iterable[str] | None = None):
        self._wrapped = wrapped
        self._extra = list(extra_tokens or [])

    def write(self, s: str) -> int:
        if not s:
            return 0
        data = redact_text(s, self._extra)
        return self._wrapped.write(data)

    def flush(self) -> None:
        self._wrapped.flush()

    def fileno(self) -> int:
        return self._wrapped.fileno()

    def isatty(self) -> bool:
        return False

    def add_tokens(self, *tokens: str) -> None:
        for t in tokens:
            if t and len(t) >= 4 and t not in self._extra:
                self._extra.append(t)


def install_stdio_redaction(extra_tokens: Iterable[str] | None = None) -> RedactingStream:
    err = RedactingStream(sys.__stderr__, extra_tokens)
    out = RedactingStream(sys.__stdout__, extra_tokens)
    sys.stdout = out  # type: ignore[assignment]
    sys.stderr = err  # type: ignore[assignment]
    return err


def log_safe(msg: str, extra_tokens: Iterable[str] | None = None) -> None:
    print(redact_text(msg, extra_tokens), flush=True)
