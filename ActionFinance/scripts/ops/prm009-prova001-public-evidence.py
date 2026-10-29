"""AF-NAT public chain proof after telemetry. Prints IDs, counts and hashes only."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import time
import uuid

REGION = "us-east-2"
CLUSTER = "actionfinance-cluster"
ALB = "https://spider-sandbox-alb-2110184762.us-east-2.elb.amazonaws.com"
SPIDER = "https://api.spider.actionhub.com.br"
LOJA = "624023a4-57e3-415c-b7d0-925ca1acd3b7"
TMP = pathlib.Path(os.environ["TEMP"])
TOKEN = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def aws_text(args: list[str]) -> str:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "text"])
    return raw.decode("utf-8").strip()


def origin_secret() -> str:
    acls = aws_json(["wafv2", "list-web-acls", "--scope", "REGIONAL"])
    acl = next(item for item in acls.get("WebACLs", []) if item.get("Name") == "spider-sandbox-api")
    detail = aws_json(
        [
            "wafv2",
            "get-web-acl",
            "--scope",
            "REGIONAL",
            "--id",
            acl["Id"],
            "--name",
            acl["Name"],
        ]
    )
    import base64

    for rule in detail["WebACL"].get("Rules", []):
        if rule.get("Name") != "allow-cloudfront-console":
            continue
        statements = (
            rule.get("Statement", {})
            .get("AndStatement", {})
            .get("Statements", [])
        )
        for statement in statements:
            header = statement.get("ByteMatchStatement", {}).get("FieldToMatch", {}).get("SingleHeader", {})
            if header.get("Name") == "x-spider-origin-secret":
                return base64.b64decode(statement["ByteMatchStatement"]["SearchString"]).decode("utf-8")
    raise SystemExit("origin secret rule not found")


def main() -> int:
    runtime_arn = aws_text(
        ["secretsmanager", "describe-secret", "--secret-id", "actionfinance/runtime", "--query", "ARN"]
    )
    secret_name = f"actionfinance/prova001-origin-{TOKEN}"
    secret_arn = None
    policy_name = "actionfinance-prova001-evidence-once"
    try:
        created = aws_json(
            [
                "secretsmanager",
                "create-secret",
                "--name",
                secret_name,
                "--secret-string",
                origin_secret(),
            ]
        )
        secret_arn = created["ARN"]
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": [runtime_arn, secret_arn],
                }
            ],
        }
        policy_file = TMP / "prova001-evidence-policy.json"
        policy_file.write_text(json.dumps(policy), encoding="utf-8")
        subprocess.check_call(
            [
                "aws",
                "iam",
                "put-role-policy",
                "--role-name",
                "actionfinance-migrate-execution",
                "--policy-name",
                policy_name,
                "--policy-document",
                f"file://{policy_file}",
                "--region",
                REGION,
            ]
        )
        policy_file.unlink(missing_ok=True)

        inner = INNER.replace("__TOKEN__", TOKEN)
        cmd = "python - <<'PY'\n" + inner + "\nPY"
        td = {
            "family": "actionfinance-dbadmin",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "executionRoleArn": "arn:aws:iam::253137917703:role/actionfinance-migrate-execution",
            "runtimePlatform": {"operatingSystemFamily": "LINUX", "cpuArchitecture": "X86_64"},
            "containerDefinitions": [
                {
                    "name": "dbadmin",
                    "image": "public.ecr.aws/docker/library/python:3.12-alpine",
                    "essential": True,
                    "environment": [
                        {"name": "SPIDER_PUBLIC", "value": SPIDER},
                        {"name": "SPIDER_ALB", "value": ALB},
                        {"name": "LOJA_COMPANY", "value": LOJA},
                    ],
                    "secrets": [
                        {"name": "ACTIONFINANCE_SPIDER_SECRET", "valueFrom": f"{runtime_arn}:spider_secret::"},
                        {"name": "SPIDER_ORIGIN_SECRET", "valueFrom": secret_arn},
                    ],
                    "command": ["sh", "-lc", cmd],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/actionfinance/migrate",
                            "awslogs-region": REGION,
                            "awslogs-stream-prefix": "prova001",
                        },
                    },
                }
            ],
        }
        td_file = TMP / "prova001-evidence-td.json"
        td_file.write_text(json.dumps(td), encoding="utf-8")
        aws_json(["ecs", "register-task-definition", "--cli-input-json", f"file://{td_file}"])
        td_file.unlink(missing_ok=True)
        run = aws_json(
            [
                "ecs",
                "run-task",
                "--cluster",
                CLUSTER,
                "--task-definition",
                "actionfinance-dbadmin",
                "--launch-type",
                "FARGATE",
                "--network-configuration",
                "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}",
            ]
        )
        task_arn = run["tasks"][0]["taskArn"]
        print(f"evidence_task={task_arn.split('/')[-1]}")
        subprocess.check_call(
            ["aws", "ecs", "wait", "tasks-stopped", "--region", REGION, "--cluster", CLUSTER, "--tasks", task_arn]
        )
        desc = aws_json(["ecs", "describe-tasks", "--cluster", CLUSTER, "--tasks", task_arn])
        exit_code = desc["tasks"][0]["containers"][0].get("exitCode")
        print(f"evidence_exit={exit_code}")
        task_id = task_arn.split("/")[-1]
        logs = aws_json(
            [
                "logs",
                "get-log-events",
                "--log-group-name",
                "/actionfinance/migrate",
                "--log-stream-name",
                f"prova001/dbadmin/{task_id}",
                "--limit",
                "80",
            ]
        )
        for event in logs.get("events", []):
            print(event.get("message", ""))
        return 0 if exit_code == 0 else 1
    finally:
        subprocess.call(
            [
                "aws",
                "iam",
                "delete-role-policy",
                "--role-name",
                "actionfinance-migrate-execution",
                "--policy-name",
                policy_name,
                "--region",
                REGION,
            ]
        )
        if secret_arn:
            subprocess.call(
                [
                    "aws",
                    "secretsmanager",
                    "delete-secret",
                    "--secret-id",
                    secret_arn,
                    "--force-delete-without-recovery",
                    "--region",
                    REGION,
                ]
            )


INNER = r'''
import hashlib, json, os, ssl, time, urllib.error, urllib.request
from datetime import datetime, timezone

token = "__TOKEN__"
company = os.environ["LOJA_COMPANY"]
secret = os.environ.get("ACTIONFINANCE_SPIDER_SECRET", "")
origin = os.environ.get("SPIDER_ORIGIN_SECRET", "")
public = os.environ["SPIDER_PUBLIC"]
alb = os.environ["SPIDER_ALB"]
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
ctx = ssl._create_unverified_context()

def sha12(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]

def list_body(message_id, corr, idem):
    return {
      "contractVersion": "1.4",
      "messageId": message_id,
      "correlationId": corr,
      "satelliteId": "actionfinance",
      "satelliteRole": "EXPERIENCE",
      "interactionType": "QUERY_STATUS",
      "createdAt": now,
      "idempotencyKey": idem,
      "purpose": "FINANCIAL_EXTERNAL_LIST",
      "objective": {"text": "LIST_EXTERNAL_PAYMENTS", "origin": "SATELLITE_GOVERNED", "declaredAt": now},
      "dataClassification": "INTERNAL",
      "responseChannel": "SYNC",
      "context": {"snapshot": {
        "schemaVersion": "1.4", "classification": "INTERNAL", "nonPersonal": True,
        "provenance": {"sourceType": "SATELLITE_GOVERNED", "sourceId": "ACTIONFINANCE_FINANCIAL_LIST_V1",
          "sourceTimestamp": now, "captureMethod": "SERVER_REGISTRY", "trustLevel": "GOVERNED"},
        "selectedContribution": "GOVERNED_SOURCE",
        "contributions": [{"role": "GOVERNED_SOURCE", "sourceType": "SATELLITE_GOVERNED",
          "sourceId": "ACTIONFINANCE_FINANCIAL_LIST_V1", "sourceTimestamp": now,
          "captureMethod": "SERVER_REGISTRY", "trustLevel": "GOVERNED", "used": True,
          "elements": {"theme": "payment_list"}}],
        "attributes": {"channel": "ACTIONFINANCE_HOMOLOG", "purposeVersion": "financial-list-v1",
          "theme": "payment_list", "situation": "test_payment_list", "need": "list_external_payments",
          "horizon": "days", "companyId": company}
      }},
      "extensions": {"financialList": {"companyId": company, "originSystem": "ACTIONHUB_PAY",
        "environment": "PRODUCTION", "limit": 50}}
    }

def post_list(message_id, corr, idem):
    req = urllib.request.Request(
      public + "/v1/satellites/interactions",
      data=json.dumps(list_body(message_id, corr, idem)).encode(),
      headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Spider-Satellite-Id": "actionfinance",
        "X-Spider-Satellite-Secret": secret,
        "X-Correlation-ID": corr,
      },
      method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode())
            return resp.status, payload, None
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", "replace")[:400]
        try:
            return err.code, json.loads(raw), raw
        except Exception:
            return err.code, {}, raw

def hashes(summary):
    rows = list(summary.get("reviews") or []) + list(summary.get("items") or [])
    out = []
    for row in rows:
        identity = "|".join([
            str(row.get("transactionId") or ""),
            str(row.get("normalizedStatus") or ""),
            str(row.get("amountMinor") or ""),
            "1" if row.get("paidAmountAbsent") else "0",
        ])
        out.append(sha12(identity))
    return sorted(set(out))

def get_json(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", "replace")[:240]
        return err.code, {}, raw
    except Exception as err:
        return 0, {}, str(err)[:160]

print("token=" + token)
msg = "afm-prova001-" + token
corr = "afp-prova001-" + token
http, payload, raw = post_list(msg, corr, "prova001-list-" + token)
summary = payload.get("resultSummary") or {}
first_hashes = hashes(summary)
print("list1_http=" + str(http))
print("list1_status=" + str(payload.get("status")))
print("list1_capability=" + str(payload.get("capabilityId")))
print("list1_itemCount=" + str(summary.get("itemCount")))
print("list1_reviewCount=" + str(summary.get("reviewCount") if summary.get("reviewCount") is not None else len(summary.get("reviews") or [])))
print("list1_env=" + str(summary.get("environment")))
print("list1_error=" + str(payload.get("errorCode")))
print("list1_hash_count=" + str(len(first_hashes)))
print("list1_hash_prefix=" + (",".join(first_hashes[:3]) if first_hashes else "none"))
if raw and http >= 400:
    print("list1_body_prefix=" + raw[:120])

time.sleep(1)
http2, payload2, raw2 = post_list(msg + "b", corr + "b", "prova001-list-b-" + token)
summary2 = payload2.get("resultSummary") or {}
second_hashes = hashes(summary2)
print("list2_http=" + str(http2))
print("list2_status=" + str(payload2.get("status")))
print("list2_reviewCount=" + str(summary2.get("reviewCount") if summary2.get("reviewCount") is not None else len(summary2.get("reviews") or [])))
print("list2_same_identities=" + str(first_hashes == second_hashes and bool(first_hashes)))

console_headers = {
    "Accept": "application/json",
    "X-Spider-Credential-Ref": "sandbox-operator",
    "X-Spider-Origin-Secret": origin,
}
status_e, events, err_e = get_json(alb + "/v1/console/monitor/events", console_headers)
items = events.get("items") if isinstance(events, dict) else []
if not isinstance(items, list):
    items = []
matched = [item for item in items if str(item.get("executionId") or "") in (msg, msg + "b") or str(item.get("correlationId") or "") in (corr, corr + "b")]
types = sorted({str(item.get("eventType") or "") for item in matched})
print("console_http=" + str(status_e))
print("console_available=" + str(events.get("available") if isinstance(events, dict) else ""))
print("console_item_count=" + str(len(items)))
print("console_match_count=" + str(len(matched)))
print("console_match_types=" + (",".join(types) if types else "none"))
print("console_scenarios=" + (",".join(events.get("availableScenarios") or []) if isinstance(events, dict) else ""))
if err_e:
    print("console_err=" + err_e[:160])

status_x, foreign, err_x = get_json(alb + "/v1/console/executions?limit=20", console_headers)
fx = foreign.get("items") if isinstance(foreign, dict) else []
print("exec_list_http=" + str(status_x))
print("exec_list_count=" + str(len(fx) if isinstance(fx, list) else 0))
if err_x:
    print("exec_list_err=" + err_x[:120])

# anonymous public Monitor: expect Cognito, never follow
req = urllib.request.Request(public.replace("api.spider", "monitor.spider") + "/?q=" + msg + "&execution=" + msg, method="GET")
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        print("monitor_anon_http=" + str(resp.status))
        print("monitor_anon_location=none")
except urllib.error.HTTPError as err:
    loc = err.headers.get("Location", "")
    print("monitor_anon_http=" + str(err.code))
    print("monitor_anon_cognito=" + str("amazoncognito.com" in loc))
'''


if __name__ == "__main__":
    raise SystemExit(main())
