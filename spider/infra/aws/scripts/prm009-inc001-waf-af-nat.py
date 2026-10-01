"""Add a narrow WAF allow for AF NAT -> /v1/satellites. Does not print secrets."""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path

REGION = "us-east-2"
SCOPE = "REGIONAL"
ACL_NAME = "spider-sandbox-api"
ACL_ID = "95733f40-5740-45a2-94cf-084e8e59825a"
IP_SET_NAME = "spider-sandbox-af-nat-v4"
AF_NAT = "3.143.92.115/32"
RULE_NAME = "allow-af-nat-satellites"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return json.loads(raw.decode("utf-16"))
    return json.loads(raw.decode("utf-8"))


def ensure_ip_set() -> str:
    listed = aws_json(["wafv2", "list-ip-sets", "--scope", SCOPE])
    for item in listed.get("IPSets", []):
        if item.get("Name") == IP_SET_NAME:
            current = aws_json(
                [
                    "wafv2",
                    "get-ip-set",
                    "--scope",
                    SCOPE,
                    "--name",
                    IP_SET_NAME,
                    "--id",
                    item["Id"],
                ]
            )
            addresses = current["IPSet"].get("Addresses", [])
            if AF_NAT not in addresses:
                subprocess.check_call(
                    [
                        "aws",
                        "wafv2",
                        "update-ip-set",
                        "--region",
                        REGION,
                        "--scope",
                        SCOPE,
                        "--name",
                        IP_SET_NAME,
                        "--id",
                        item["Id"],
                        "--lock-token",
                        current["LockToken"],
                        "--addresses",
                        AF_NAT,
                    ]
                )
            print(f"ip_set={item['Id']} addresses={AF_NAT}")
            return current["IPSet"]["ARN"]
    created = aws_json(
        [
            "wafv2",
            "create-ip-set",
            "--scope",
            SCOPE,
            "--name",
            IP_SET_NAME,
            "--ip-address-version",
            "IPV4",
            "--addresses",
            AF_NAT,
        ]
    )
    print(f"ip_set_created={created['Summary']['Id']}")
    return created["Summary"]["ARN"]


def main() -> None:
    ip_arn = ensure_ip_set()
    acl = aws_json(["wafv2", "get-web-acl", "--scope", SCOPE, "--name", ACL_NAME, "--id", ACL_ID])
    rules = list(acl["WebACL"].get("Rules", []))
    rule = {
        "Name": RULE_NAME,
        "Priority": 2,
        "Action": {"Allow": {}},
        "Statement": {
            "AndStatement": {
                "Statements": [
                    {"IPSetReferenceStatement": {"ARN": ip_arn}},
                    {
                        "ByteMatchStatement": {
                            "SearchString": base64.b64encode(b"/v1/satellites").decode("ascii"),
                            "FieldToMatch": {"UriPath": {}},
                            "TextTransformations": [{"Priority": 0, "Type": "NONE"}],
                            "PositionalConstraint": "STARTS_WITH",
                        }
                    },
                ]
            }
        },
        "VisibilityConfig": {
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "spider-sandbox-api-af-nat-satellites",
        },
    }
    rules = [item for item in rules if item.get("Name") != RULE_NAME]
    rules.append(rule)
    payload = {
        "Name": ACL_NAME,
        "Scope": SCOPE,
        "Id": ACL_ID,
        "LockToken": acl["LockToken"],
        "DefaultAction": acl["WebACL"]["DefaultAction"],
        "VisibilityConfig": acl["WebACL"]["VisibilityConfig"],
        "Rules": rules,
    }
    path = Path(tempfile.gettempdir()) / "prm009-inc001-waf.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        aws_json(["wafv2", "update-web-acl", "--cli-input-json", f"file://{path}"])
    finally:
        path.unlink(missing_ok=True)
    names = sorted(item["Name"] for item in rules)
    print("waf_rules=" + ",".join(names))


if __name__ == "__main__":
    main()
