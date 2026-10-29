"""Allow CloudFront /v1/canonical with the existing origin secret. Does not open the ACL."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

REGION = "us-east-2"
NAME = "spider-sandbox-api"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def main() -> int:
    listed = aws_json(["wafv2", "list-web-acls", "--scope", "REGIONAL"])
    acl = next(item for item in listed.get("WebACLs", []) if item.get("Name") == NAME)
    detail = aws_json(
        ["wafv2", "get-web-acl", "--scope", "REGIONAL", "--id", acl["Id"], "--name", NAME]
    )
    web = detail["WebACL"]
    token = detail["LockToken"]
    rules = web.get("Rules") or []
    target = next(rule for rule in rules if rule.get("Name") == "allow-cloudfront-console")
    statement = target["Statement"]["AndStatement"]
    parts = statement["Statements"]
    path_part = next(
        part
        for part in parts
        if part.get("ByteMatchStatement", {}).get("FieldToMatch", {}).get("UriPath") is not None
        or "UriPath" in str(part.get("ByteMatchStatement", {}).get("FieldToMatch", {}))
    )
    already_or = any("OrStatement" in part for part in parts)
    if already_or:
        print("waf_canonical_already=1")
        return 0

    def as_text(value: str) -> str:
        try:
            text = base64.b64decode(value).decode("utf-8")
            if text.isprintable():
                return text
        except Exception:
            pass
        return value

    def b64(value: str) -> str:
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    search = as_text(path_part["ByteMatchStatement"].get("SearchString", ""))
    if search != "/v1/console":
        raise SystemExit("unexpected path match")
    secret_part = next(part for part in parts if part is not path_part)
    console_match = {
        "ByteMatchStatement": {
            "SearchString": b64("/v1/console"),
            "FieldToMatch": {"UriPath": {}},
            "TextTransformations": [{"Priority": 0, "Type": "NONE"}],
            "PositionalConstraint": "STARTS_WITH",
        }
    }
    canonical_match = {
        "ByteMatchStatement": {
            "SearchString": b64("/v1/canonical"),
            "FieldToMatch": {"UriPath": {}},
            "TextTransformations": [{"Priority": 0, "Type": "NONE"}],
            "PositionalConstraint": "STARTS_WITH",
        }
    }
    statement["Statements"] = [
        {"OrStatement": {"Statements": [console_match, canonical_match]}},
        secret_part,
    ]
    target["VisibilityConfig"]["MetricName"] = "spider-sandbox-api-cf-console-canonical"
    payload = {
        "Name": NAME,
        "Scope": "REGIONAL",
        "Id": acl["Id"],
        "LockToken": token,
        "DefaultAction": web["DefaultAction"],
        "VisibilityConfig": web["VisibilityConfig"],
        "Rules": rules,
    }
    path = Path.home() / "AppData" / "Local" / "Temp" / "prm009-prova001-waf.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        aws_json(["wafv2", "update-web-acl", "--cli-input-json", f"file://{path}"])
    finally:
        path.unlink(missing_ok=True)
    print("waf_canonical_updated=1")
    print("default_action=BLOCK")
    print("paths=/v1/console,/v1/canonical")
    print("ingress=origin-secret-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
