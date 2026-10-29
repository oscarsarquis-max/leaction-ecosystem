"""Evaluate ECR scan via boto3 (fail-closed). Exit 0 only if allowed."""
from __future__ import annotations

import json
import sys
import time

import boto3

from scan_gate import ScanGateError, assert_allowed, evaluate_scan_payload


def fetch_payload(repo: str, digest: str, region: str, max_wait_s: int = 900) -> dict:
    client = boto3.client("ecr", region_name=region)
    deadline = time.time() + max_wait_s
    started = False
    while True:
        try:
            resp = client.describe_image_scan_findings(
                repositoryName=repo, imageId={"imageDigest": digest}
            )
        except client.exceptions.ScanNotFoundException:
            if not started:
                try:
                    client.start_image_scan(repositoryName=repo, imageId={"imageDigest": digest})
                    started = True
                except Exception as exc:  # noqa: BLE001
                    # LimitExceeded / Unsupported may occur; keep waiting / retry start
                    if "LimitExceeded" in type(exc).__name__ or "LimitExceeded" in str(exc):
                        pass
                    elif not started:
                        raise ScanGateError(f"start_image_scan failed: {type(exc).__name__}") from exc
            if time.time() >= deadline:
                raise ScanGateError("scan incomplete status=NOT_FOUND")
            time.sleep(15)
            continue

        status = (resp.get("imageScanStatus") or {}).get("status", "")
        if status.upper() == "COMPLETE":
            return {
                "imageScanStatus": resp.get("imageScanStatus"),
                "imageScanFindings": {
                    "findingSeverityCounts": (resp.get("imageScanFindings") or {}).get(
                        "findingSeverityCounts", {}
                    ),
                    "findings": (resp.get("imageScanFindings") or {}).get("findings", []),
                },
            }
        if status.upper() in {"FAILED", "UNSUPPORTED", "ERROR"}:
            raise ScanGateError(f"scan failed status={status}")
        if time.time() >= deadline:
            raise ScanGateError(f"scan incomplete after wait status={status or 'unknown'}")
        time.sleep(15)


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: run_scan_gate.py <repo> <digest> <region> [--block-high]", file=sys.stderr)
        return 2
    repo, digest, region = sys.argv[1], sys.argv[2], sys.argv[3]
    block_high = "--allow-high" not in sys.argv
    try:
        payload = fetch_payload(repo, digest, region)
        decision = evaluate_scan_payload(payload, allow_high_with_override=not block_high)
        assert_allowed(decision)
        print(json.dumps({"allow": True, **decision.__dict__, "counts": payload["imageScanFindings"]["findingSeverityCounts"]}))
        return 0
    except ScanGateError as exc:
        print(json.dumps({"allow": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
