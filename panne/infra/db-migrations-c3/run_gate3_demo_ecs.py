"""One-shot GATE3 append-only on panne_demo. Refuses DB panne."""
from __future__ import annotations

import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"

BOOT = r"""
import json, os, sys
from urllib.parse import quote
import boto3
sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-2"))
sec = json.loads(sm.get_secret_value(SecretId="panne/demo/db/migrator")["SecretString"])
assert sec["username"] == "panne_demo_migrator"
assert sec["dbname"] == "panne_demo"
if sec["dbname"] == "panne":
    raise SystemExit("refused production database")
pwd = quote(sec["password"], safe="")
url = f"postgresql+psycopg://{sec['username']}:{pwd}@{sec['host']}:{int(sec['port'])}/{sec['dbname']}"
os.environ["PANNE_PATCH_URL"] = url
os.environ["PANNE_ENV"] = "demo"
os.execv(sys.executable, [sys.executable, "-u", "/app/scripts/gate3_append_demo_economy.py"])
"""


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", flush=True)
    raise SystemExit(code)


def main() -> int:
    if os.environ.get("PANNE_MIGRATE_ENV") != "demo":
        fail("PANNE_MIGRATE_ENV must be demo")
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    if not digest.startswith("sha256:"):
        fail("PANNE_IMAGE_DIGEST required")
    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{digest}"
    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    for desired in ("RUNNING", "PENDING"):
        arns = []
        for page in ecs.get_paginator("list_tasks").paginate(
            cluster=CLUSTER, family=FAMILY, desiredStatus=desired
        ):
            arns.extend(page.get("taskArns") or [])
        if arns:
            fail(f"migration family already active {desired}={arns}")

    td = ecs.register_task_definition(
        family=FAMILY,
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="512",
        memory="1024",
        executionRoleArn=EXEC_ROLE,
        taskRoleArn=TASK_ROLE,
        runtimePlatform={"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"},
        containerDefinitions=[
            {
                "name": "panne-db-migration",
                "image": image_uri,
                "essential": True,
                "readonlyRootFilesystem": True,
                "entryPoint": ["python", "-u", "-c"],
                "command": [BOOT],
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "PANNE_ENV", "value": "demo"},
                    {"name": "PANNE_FISCAL_LIVE", "value": "0"},
                    {"name": "PANNE_OCR_LIVE", "value": "0"},
                ],
                "linuxParameters": {
                    "tmpfs": [
                        {
                            "containerPath": "/tmp",
                            "size": 128,
                            "mountOptions": ["rw", "noexec", "nosuid", "nodev"],
                        }
                    ]
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/panne/db-migrations",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "c028-gate3",
                    },
                },
            }
        ],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
    print(f"task_definition_registered={td_arn}", flush=True)
    task_arn = None
    exit_code = 1
    try:
        run = ecs.run_task(
            cluster=CLUSTER,
            taskDefinition=td_arn,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": SUBNETS,
                    "securityGroups": [SG_DEMO],
                    "assignPublicIp": "DISABLED",
                }
            },
            startedBy="cursor-028-gate3",
        )
        if run.get("failures"):
            fail(f"run_task failures={run['failures']}")
        task_arn = run["tasks"][0]["taskArn"]
        print(f"task_started={task_arn}", flush=True)
        ecs.get_waiter("tasks_stopped").wait(
            cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 15, "MaxAttempts": 80}
        )
        desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
        containers = desc.get("containers") or []
        exit_code = int((containers[0].get("exitCode") if containers else None) or 1)
        tid = task_arn.rsplit("/", 1)[-1]
        for s in logs.describe_log_streams(
            logGroupName="/ecs/panne/db-migrations",
            logStreamNamePrefix=f"c028-gate3/panne-db-migration/{tid}",
        ).get("logStreams") or []:
            for e in logs.get_log_events(
                logGroupName="/ecs/panne/db-migrations",
                logStreamName=s["logStreamName"],
                startFromHead=True,
            ).get("events") or []:
                print(e["message"], flush=True)
        print(f"task_stopped exit={exit_code}", flush=True)
    finally:
        if task_arn:
            try:
                ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c028-gate3-close")
            except ClientError:
                pass
        try:
            ecs.deregister_task_definition(taskDefinition=td_arn)
        except ClientError:
            pass
    print(json.dumps({"digest": digest, "exit_code": exit_code, "task": task_arn}), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
