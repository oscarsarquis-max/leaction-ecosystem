import logging
import re

_SECRET_PATTERN = re.compile(
    r"(postgresql(?:\+\w+)?://)([^:@/]+):([^@/]+)@",
    re.IGNORECASE,
)


class CredentialFilter(logging.Filter):
    """Remove usuário/senha de URLs de conexão e tokens óbvios."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.getMessage())
        record.args = ()
        return True


def _redact(message: str) -> str:
    redacted = _SECRET_PATTERN.sub(r"\1***:***@", message)
    for marker in ("password=", "PASSWORD=", "token=", "TOKEN=", "secret=", "SECRET="):
        if marker in redacted:
            redacted = re.sub(rf"{re.escape(marker)}\S+", f"{marker}***", redacted)
    return redacted


def configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    credential_filter = CredentialFilter()
    for handler in root.handlers:
        handler.addFilter(credential_filter)
    logging.getLogger("lojadepaes").addFilter(credential_filter)
