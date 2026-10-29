"""Fail-closed ECR image scan gate for Panne bootstrap/deploy.

Any uncertainty blocks execution. CRITICAL > 0 always blocks.
HIGH > 0 requires explicit documented override (not automatic pass).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


class ScanGateError(Exception):
    """Scan cannot authorize execution."""


@dataclass(frozen=True)
class ScanDecision:
    allow: bool
    reason: str
    critical: int
    high: int
    status: str


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        raise ScanGateError("severity count must not be boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ScanGateError(f"invalid severity count type={type(value).__name__}")


def evaluate_scan_payload(
    payload: dict[str, Any] | None,
    *,
    allow_high_with_override: bool = False,
) -> ScanDecision:
    if payload is None:
        raise ScanGateError("scan payload is None")
    if not isinstance(payload, dict):
        raise ScanGateError("scan payload is not an object")

    status_block = payload.get("imageScanStatus")
    if not isinstance(status_block, dict):
        raise ScanGateError("imageScanStatus missing or invalid")
    status = status_block.get("status")
    if not isinstance(status, str) or not status:
        raise ScanGateError("imageScanStatus.status missing")
    status_u = status.upper()
    if status_u in {"IN_PROGRESS", "PENDING", "SCANNING"}:
        raise ScanGateError(f"scan incomplete status={status}")
    if status_u not in {"COMPLETE", "ACTIVE", "SUPPORTED", "SUCCESS"}:
        # AWS uses COMPLETE for finished scans
        if status_u != "COMPLETE":
            # Accept only COMPLETE as finished success; anything else unknown => block
            if status_u not in {"COMPLETE"}:
                raise ScanGateError(f"unknown or failed scan status={status}")

    # Normalize: AWS describe-image-scan-findings uses COMPLETE
    if status_u != "COMPLETE":
        raise ScanGateError(f"scan not complete status={status}")

    findings = payload.get("imageScanFindings")
    if not isinstance(findings, dict):
        raise ScanGateError("imageScanFindings missing or invalid")

    counts = findings.get("findingSeverityCounts")
    if counts is None:
        # Empty findings object with no counts key => treat as zero only if findings list present
        if "findings" not in findings:
            raise ScanGateError("findingSeverityCounts missing")
        counts = {}
    if not isinstance(counts, dict):
        raise ScanGateError("findingSeverityCounts invalid")

    critical = _as_int(counts.get("CRITICAL"))
    high = _as_int(counts.get("HIGH"))

    if critical > 0:
        return ScanDecision(
            allow=False,
            reason=f"CRITICAL={critical} blocks execution",
            critical=critical,
            high=high,
            status=status_u,
        )
    if high > 0 and not allow_high_with_override:
        return ScanDecision(
            allow=False,
            reason=f"HIGH={high} requires documented override",
            critical=critical,
            high=high,
            status=status_u,
        )
    return ScanDecision(
        allow=True,
        reason="scan complete with no CRITICAL (HIGH override ok or zero)",
        critical=critical,
        high=high,
        status=status_u,
    )


def evaluate_scan_json_text(text: str, **kwargs: Any) -> ScanDecision:
    if text is None:
        raise ScanGateError("scan json text is None")
    if not isinstance(text, str) or not text.strip():
        raise ScanGateError("scan json text empty")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScanGateError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ScanGateError("JSON root is not an object")
    return evaluate_scan_payload(payload, **kwargs)


def fetch_and_evaluate(
    aws_invoke: Callable[[], str],
    **kwargs: Any,
) -> ScanDecision:
    """aws_invoke must return stdout JSON text or raise on CLI/API failure."""
    try:
        text = aws_invoke()
    except Exception as exc:  # noqa: BLE001 — fail-closed on any transport error
        raise ScanGateError(f"aws scan command failed: {type(exc).__name__}") from exc
    return evaluate_scan_json_text(text, **kwargs)


def assert_allowed(decision: ScanDecision) -> None:
    if not decision.allow:
        raise ScanGateError(decision.reason)
