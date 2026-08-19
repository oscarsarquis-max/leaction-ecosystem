"""Deterministic input fingerprint for Problem Analysis stale detection."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.improvement_cases.problem_schemas import ProblemContextInput, dump_jsonable


def _canonical(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _canonical(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canonical(v) for v in obj]
    return obj


def fingerprint_problem_context_input(payload: ProblemContextInput) -> str:
    """
    Hash of facts that affect interpretation.

    Excludes request_id, correlation_id, requested_at, source.
    Includes schema_version, problem texts, and profile facts sent to OI.
    """
    data = dump_jsonable(payload)
    material = {
        "schema_version": data["schema_version"],
        "organization_profile": data["organization_profile"],
        "problem": data["problem"],
    }
    encoded = json.dumps(
        _canonical(material),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
