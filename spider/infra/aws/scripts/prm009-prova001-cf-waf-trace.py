"""Trace CloudFront WAF vs POST /v1/canonical. No secrets printed."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request

REGION = "us-east-1"
NAME = "spider-sandbox-monitor"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def main() -> int:
    listed = aws_json(["wafv2", "list-web-acls", "--scope", "CLOUDFRONT"])
    acl = next(item for item in listed.get("WebACLs", []) if item.get("Name") == NAME)
    detail = aws_json(
        ["wafv2", "get-web-acl", "--scope", "CLOUDFRONT", "--id", acl["Id"], "--name", NAME]
    )
    web = detail["WebACL"]
    print("acl=" + NAME)
    print("default=" + next(iter(web.get("DefaultAction") or {}), "?"))
    for rule in web.get("Rules") or []:
        action = rule.get("Action") or rule.get("OverrideAction") or {}
        print("rule prio=%s name=%s action=%s" % (rule.get("Priority"), rule.get("Name"), next(iter(action), "?")))
    writes = next(rule for rule in web["Rules"] if rule["Name"] == "allow-console-writes")
    print("writes_paths=" + json.dumps(writes["Statement"], ensure_ascii=True)[:900])

    req = urllib.request.Request(
        "https://monitor.spider.actionhub.com.br/v1/canonical/executions",
        data=b'{"probe":true}',
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()[:200]
            print("post_http=%s" % resp.status)
            print("post_type=%s" % (resp.headers.get("content-type") or ""))
            print("post_body_prefix=%s" % body[:120].decode("utf-8", "replace"))
    except urllib.error.HTTPError as err:
        body = err.read()[:240]
        print("post_http=%s" % err.code)
        print("post_type=%s" % (err.headers.get("content-type") or ""))
        print("post_server=%s" % (err.headers.get("server") or ""))
        print("post_waf=%s" % (err.headers.get("x-amzn-waf-rule") or err.headers.get("x-amzn-requestid") or ""))
        print("post_body_prefix=%s" % body[:160].decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
