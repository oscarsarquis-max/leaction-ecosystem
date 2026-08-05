"""PDF worker loop + lightweight health HTTP endpoint."""

from __future__ import annotations

import logging
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.config import get_settings
from app.worker.jobs import claim_next, recover_abandoned
from app.worker.process_pdf import process_report_pdf_export

class _CtxFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "job_id"):
            record.job_id = "-"
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s %(levelname)s %(name)s "
        "job_id=%(job_id)s correlation_id=%(correlation_id)s %(message)s"
    ),
)
logging.getLogger().addFilter(_CtxFilter())
logger = logging.getLogger("qmind.worker")

_ready = False
_stop = threading.Event()


class _HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/health", "/ready"):
            self.send_response(404)
            self.end_headers()
            return
        if self.path == "/ready" and not _ready:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'{"status":"starting"}')
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"qmind-pdf-worker"}')


def _start_health(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health", daemon=True)
    thread.start()
    return server


def run() -> int:
    global _ready
    settings = get_settings()
    # Prefer hostname for lease ownership when WORKER_ID not overridden meaningfully
    if settings.worker_id == "pdf-worker":
        settings = settings.model_copy(update={"worker_id": f"pdf-worker@{socket.gethostname()}"})

    health = _start_health(settings.worker_health_port)
    logger.info(
        "worker_starting poll=%ss lease=%ss max_attempts=%s",
        settings.worker_poll_interval_seconds,
        settings.worker_lease_seconds,
        settings.worker_max_attempts,
        extra={"job_id": "-", "correlation_id": "-"},
    )

    def _handle_signal(signum, _frame) -> None:
        logger.info(
            "worker_signal signum=%s",
            signum,
            extra={"job_id": "-", "correlation_id": "-"},
        )
        _stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Recover abandoned leases before first claim
    try:
        n = recover_abandoned(settings)
        if n:
            logger.warning(
                "recovered_abandoned count=%s",
                n,
                extra={"job_id": "-", "correlation_id": "-"},
            )
    except Exception:
        logger.exception(
            "recover_abandoned_failed",
            extra={"job_id": "-", "correlation_id": "-"},
        )
    _ready = True

    idle_recover_every = max(30.0, settings.worker_lease_seconds / 2)
    last_recover = time.monotonic()

    while not _stop.is_set():
        try:
            if time.monotonic() - last_recover >= idle_recover_every:
                recover_abandoned(settings)
                last_recover = time.monotonic()

            job = claim_next(settings)
            if job is None:
                _stop.wait(settings.worker_poll_interval_seconds)
                continue

            log = logging.LoggerAdapter(
                logger,
                {"job_id": str(job.id), "correlation_id": str(job.correlation_id)},
            )
            log.info(
                "claimed job_type=%s attempt=%s/%s org=%s",
                job.job_type,
                job.attempt_count,
                job.max_attempts,
                job.organization_id,
            )
            if job.job_type == "report_pdf_export":
                status = process_report_pdf_export(job, settings)
                log.info("finished status=%s", status)
            else:
                from app.worker.jobs import mark_failed_or_retry

                mark_failed_or_retry(
                    settings,
                    job,
                    error_code="unsupported_job_type",
                    error_safe_message=f"Unsupported job_type={job.job_type}",
                )
        except Exception:
            logger.exception(
                "worker_loop_error",
                extra={"job_id": "-", "correlation_id": "-"},
            )
            _stop.wait(settings.worker_poll_interval_seconds)

    health.shutdown()
    logger.info("worker_stopped", extra={"job_id": "-", "correlation_id": "-"})
    return 0


if __name__ == "__main__":
    sys.exit(run())
