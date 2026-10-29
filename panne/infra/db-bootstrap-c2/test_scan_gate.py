"""Unit tests for fail-closed ECR scan gate (no AWS calls)."""
from __future__ import annotations

import json
import unittest

from scan_gate import ScanGateError, evaluate_scan_json_text, evaluate_scan_payload, fetch_and_evaluate


def _payload(status: str, counts: dict | None, include_findings_list: bool = True) -> dict:
    findings: dict = {}
    if counts is not None:
        findings["findingSeverityCounts"] = counts
    if include_findings_list:
        findings["findings"] = []
    return {"imageScanStatus": {"status": status}, "imageScanFindings": findings}


class ScanGateTests(unittest.TestCase):
    def test_zero_critical_allows(self) -> None:
        d = evaluate_scan_payload(_payload("COMPLETE", {}))
        self.assertTrue(d.allow)
        self.assertEqual(d.critical, 0)

    def test_critical_blocks(self) -> None:
        d = evaluate_scan_payload(_payload("COMPLETE", {"CRITICAL": 8, "HIGH": 1}))
        self.assertFalse(d.allow)
        self.assertEqual(d.critical, 8)

    def test_high_blocks_without_override(self) -> None:
        d = evaluate_scan_payload(_payload("COMPLETE", {"HIGH": 2}))
        self.assertFalse(d.allow)

    def test_high_allowed_with_override(self) -> None:
        d = evaluate_scan_payload(
            _payload("COMPLETE", {"HIGH": 2}),
            allow_high_with_override=True,
        )
        self.assertTrue(d.allow)

    def test_missing_status_field(self) -> None:
        with self.assertRaises(ScanGateError):
            evaluate_scan_payload({"imageScanFindings": {"findingSeverityCounts": {}}})

    def test_invalid_json(self) -> None:
        with self.assertRaises(ScanGateError):
            evaluate_scan_json_text("{not-json")

    def test_aws_command_failure(self) -> None:
        def boom() -> str:
            raise RuntimeError("aws failed")

        with self.assertRaises(ScanGateError):
            fetch_and_evaluate(boom)

    def test_scan_in_progress_blocks(self) -> None:
        with self.assertRaises(ScanGateError):
            evaluate_scan_payload(_payload("IN_PROGRESS", {}))

    def test_missing_counts_without_findings_list(self) -> None:
        with self.assertRaises(ScanGateError):
            evaluate_scan_payload(_payload("COMPLETE", None, include_findings_list=False))

    def test_empty_text_blocks(self) -> None:
        with self.assertRaises(ScanGateError):
            evaluate_scan_json_text("   ")


if __name__ == "__main__":
    unittest.main()
