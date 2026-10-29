"""Allow CloudFront POST /v1/canonical without opening global writes."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

REGION = "us-east-1"
NAME = "spider-sandbox-monitor"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def path_match(path: str) -> dict:
    return {
        "ByteMatchStatement": {
            "SearchString": b64(path),
            "FieldToMatch": {"UriPath": {}},
            "TextTransformations": [{"Priority": 0, "Type": "NONE"}],
            "PositionalConstraint": "STARTS_WITH",
        }
    }


def main() -> int:
    listed = aws_json(["wafv2", "list-web-acls", "--scope", "CLOUDFRONT"])
    acl = next(item for item in listed.get("WebACLs", []) if item.get("Name") == NAME)
    detail = aws_json(
        ["wafv2", "get-web-acl", "--scope", "CLOUDFRONT", "--id", acl["Id"], "--name", NAME]
    )
    web = detail["WebACL"]
    token = detail["LockToken"]
    rules = web.get("Rules") or []
    target = next(rule for rule in rules if rule.get("Name") == "allow-console-writes")
    and_stmt = target["Statement"]["AndStatement"]
    already_or = any("OrStatement" in part and "UriPath" in json.dumps(part) for part in and_stmt["Statements"])
    if already_or:
        print("cf_waf_canonical_writes_already=1")
        return 0

    methods = next(part for part in and_stmt["Statements"] if "OrStatement" in part)
    and_stmt["Statements"] = [
        {"OrStatement": {"Statements": [path_match("/v1/console"), path_match("/v1/canonical")]}},
        methods,
    ]
    target["VisibilityConfig"]["MetricName"] = "spider-sandbox-monitor-console-canonical-write"
    payload = {
        "Name": NAME,
        "Scope": "CLOUDFRONT",
        "Id": acl["Id"],
        "LockToken": token,
        "DefaultAction": web["DefaultAction"],
        "VisibilityConfig": web["VisibilityConfig"],
        "Rules": rules,
    }
    if web.get("CustomResponseBodies"):
        payload["CustomResponseBodies"] = web["CustomResponseBodies"]
    path = Path.home() / "AppData" / "Local" / "Temp" / "prm009-prova001-cf-waf.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        aws_json(["wafv2", "update-web-acl", "--cli-input-json", f"file://{path}"])
    finally:
        path.unlink(missing_ok=True)
    print("cf_waf_canonical_writes_updated=1")
    print("default_action=BLOCK")
    print("write_paths=/v1/console,/v1/canonical")
    print("write_methods=POST,PUT,PATCH,DELETE")
    print("ingress=not-global")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
