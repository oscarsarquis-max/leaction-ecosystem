"""Add Monitor CloudFront /v1/canonical/* to the same ALB origin as /v1/console/*. No secrets printed."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

REGION = "us-east-1"
DIST = "E2E4ORTD4DHI1D"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def main() -> int:
    cfg = aws_json(["cloudfront", "get-distribution-config", "--id", DIST])
    etag = cfg["ETag"]
    dist = cfg["DistributionConfig"]
    behaviors = dist.setdefault("CacheBehaviors", {"Quantity": 0, "Items": []})
    items = behaviors.setdefault("Items", [])
    if any(item.get("PathPattern") == "/v1/canonical/*" for item in items):
        print("canonical_behavior_present=1")
        return 0
    source = next(item for item in items if item.get("PathPattern") == "/v1/console/*")
    added = copy.deepcopy(source)
    added["PathPattern"] = "/v1/canonical/*"
    items.append(added)
    behaviors["Quantity"] = len(items)
    print("canonical_behavior_added=1")
    path_cfg = Path.home() / "AppData" / "Local" / "Temp" / "prm009-prova001-cf-canonical.json"
    path_cfg.write_text(json.dumps(dist), encoding="utf-8")
    subprocess.check_output(
        [
            "aws",
            "cloudfront",
            "update-distribution",
            "--id",
            DIST,
            "--if-match",
            etag,
            "--distribution-config",
            f"file://{path_cfg}",
            "--region",
            REGION,
            "--query",
            "Distribution.Status",
            "--output",
            "text",
        ]
    )
    path_cfg.unlink(missing_ok=True)
    print("cloudfront_updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
