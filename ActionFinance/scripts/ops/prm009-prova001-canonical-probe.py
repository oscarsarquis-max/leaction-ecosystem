"""POST SUCCESS_MULTI_STEP to public ALB after WAF fix. Prints status only."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import time

REGION = "us-east-2"
CLUSTER = "actionfinance-cluster"
ALB = "https://spider-sandbox-alb-2110184762.us-east-2.elb.amazonaws.com"
TMP = pathlib.Path(os.environ["TEMP"])
TOKEN = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def origin_secret() -> str:
    import base64

    acls = aws_json(["wafv2", "list-web-acls", "--scope", "REGIONAL"])
    acl = next(item for item in acls.get("WebACLs", []) if item.get("Name") == "spider-sandbox-api")
    detail = aws_json(
        ["wafv2", "get-web-acl", "--scope", "REGIONAL", "--id", acl["Id"], "--name", acl["Name"]]
    )
    for rule in detail["WebACL"].get("Rules", []):
        if rule.get("Name") != "allow-cloudfront-console":
            continue
        statements = rule.get("Statement", {}).get("AndStatement", {}).get("Statements", [])
        for statement in statements:
            header = (
                statement.get("ByteMatchStatement", {})
                .get("FieldToMatch", {})
                .get("SingleHeader", {})
            )
            if header.get("Name") == "x-spider-origin-secret":
                return base64.b64decode(statement["ByteMatchStatement"]["SearchString"]).decode(
                    "utf-8"
                )
            for inner in statement.get("OrStatement", {}).get("Statements", []):
                pass
        for statement in statements:
            if "OrStatement" in statement:
                continue
            header = (
                statement.get("ByteMatchStatement", {})
                .get("FieldToMatch", {})
                .get("SingleHeader", {})
            )
            if header.get("Name") == "x-spider-origin-secret":
                return base64.b64decode(statement["ByteMatchStatement"]["SearchString"]).decode(
                    "utf-8"
                )
    raise SystemExit("origin secret rule not found")


INNER = r'''
import json, os, ssl, urllib.error, urllib.request
from datetime import datetime, timezone
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
origin = os.environ.get("SPIDER_ORIGIN_SECRET","")
alb = os.environ["SPIDER_ALB"]
ctx = ssl._create_unverified_context()
exec_id = "exec-prova001-c-" + os.environ.get("TOKEN","x")
idem = "idem-prova001-c-" + os.environ.get("TOKEN","x")
body = {
  "contract": {"schemaVersion":"1.0","contractVersion":"1.0.0"},
  "execution": {"executionId": exec_id, "requestedAt": now, "idempotencyKey": idem},
  "contextRef": {"contextId":"ctx-SUCCESS_MULTI_STEP","intentId":"intent:demo","capabilityId":"capability:mock","productServiceId":"product:mock","journeyId":"journey:mock"},
  "origin": {"channel":"operational-console","originatorId":"console-sandbox","interactionRef":"corr-"+exec_id},
  "trace": {"correlationId":"corr-"+exec_id,"traceparent":"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"},
  "target": {"capability":"mock","operation":"SUCCESS_MULTI_STEP"},
  "payload": {"canonicalData":{"mockScenario":"SUCCESS","scenario":"SUCCESS_MULTI_STEP"}}
}
headers = {
  "Content-Type":"application/json",
  "Accept":"application/json",
  "X-Spider-Credential-Ref":"sandbox-operator",
  "X-Spider-Origin-Secret": origin,
  "Idempotency-Key": idem,
}
req = urllib.request.Request(alb+"/v1/canonical/executions", data=json.dumps(body).encode(), headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
        payload = json.loads(resp.read().decode())
        print("canonical_http="+str(resp.status))
        exe = payload.get("execution") or {}
        print("canonical_state="+str(exe.get("state")))
        print("canonical_execution="+str(exe.get("executionId")))
except urllib.error.HTTPError as err:
    raw = err.read().decode("utf-8","replace")[:240]
    print("canonical_http="+str(err.code))
    print("canonical_body="+raw.replace("\n"," ")[:200])
'''


def main() -> int:
    secret_name = f"actionfinance/prova001-origin-c-{TOKEN}"
    created = aws_json(
        ["secretsmanager", "create-secret", "--name", secret_name, "--secret-string", origin_secret()]
    )
    secret_arn = created["ARN"]
    runtime_arn = subprocess.check_output(
        [
            "aws",
            "secretsmanager",
            "describe-secret",
            "--region",
            REGION,
            "--secret-id",
            "actionfinance/runtime",
            "--query",
            "ARN",
            "--output",
            "text",
        ]
    ).decode().strip()
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": [secret_arn, runtime_arn],
            }
        ],
    }
    policy_file = TMP / "prova001-c-policy.json"
    policy_file.write_text(json.dumps(policy), encoding="utf-8")
    try:
        subprocess.check_call(
            [
                "aws",
                "iam",
                "put-role-policy",
                "--role-name",
                "actionfinance-migrate-execution",
                "--policy-name",
                "actionfinance-prova001-c-once",
                "--policy-document",
                f"file://{policy_file}",
                "--region",
                REGION,
            ]
        )
        cmd = "python - <<'PY'\n" + INNER + "\nPY"
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
                        {"name": "SPIDER_ALB", "value": ALB},
                        {"name": "TOKEN", "value": TOKEN},
                    ],
                    "secrets": [{"name": "SPIDER_ORIGIN_SECRET", "valueFrom": secret_arn}],
                    "command": ["sh", "-lc", cmd],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/actionfinance/migrate",
                            "awslogs-region": REGION,
                            "awslogs-stream-prefix": "prova001c",
                        },
                    },
                }
            ],
        }
        td_file = TMP / "prova001-c-td.json"
        td_file.write_text(json.dumps(td), encoding="utf-8")
        aws_json(["ecs", "register-task-definition", "--cli-input-json", f"file://{td_file}"])
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
        subprocess.check_call(
            ["aws", "ecs", "wait", "tasks-stopped", "--region", REGION, "--cluster", CLUSTER, "--tasks", task_arn]
        )
        desc = aws_json(["ecs", "describe-tasks", "--cluster", CLUSTER, "--tasks", task_arn])
        print("probe_exit=" + str(desc["tasks"][0]["containers"][0].get("exitCode")))
        task_id = task_arn.split("/")[-1]
        logs = aws_json(
            [
                "logs",
                "get-log-events",
                "--log-group-name",
                "/actionfinance/migrate",
                "--log-stream-name",
                f"prova001c/dbadmin/{task_id}",
                "--limit",
                "40",
            ]
        )
        for event in logs.get("events", []):
            print(event.get("message", ""))
    finally:
        policy_file.unlink(missing_ok=True)
        subprocess.call(
            [
                "aws",
                "iam",
                "delete-role-policy",
                "--role-name",
                "actionfinance-migrate-execution",
                "--policy-name",
                "actionfinance-prova001-c-once",
                "--region",
                REGION,
            ]
        )
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
