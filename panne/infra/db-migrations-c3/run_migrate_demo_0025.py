"""One-shot Alembic upgrade of panne_demo to 0025. Never touches DB panne / prod."""
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
REPO = "panne/backend"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"
SECRET_DEMO = "panne/demo/db/migrator"
ENTRYPOINT = ["python", "-u", "/app/migrate_runner.py"]
DO_NOT_RUN = {
    "sha256:f9405c5d444af1052aee758488111561247a21241c3bcada7540301827266ac6",
}


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", flush=True)
    raise SystemExit(code)


def main() -> int:
    if os.environ.get("PANNE_MIGRATE_ENV") != "demo":
        fail("PANNE_MIGRATE_ENV must be demo")
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    if not digest.startswith("sha256:"):
        fail("PANNE_IMAGE_DIGEST required")
    if digest in DO_NOT_RUN:
        fail("forbidden digest")
    if os.environ.get("PANNE_MIGRATE_ENV") == "prod":
        fail("prod forbidden")

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    ecs = boto3.client("ecs", region_name=REGION)
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
                "entryPoint": ENTRYPOINT,
                "command": [],
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "PANNE_MIGRATE_ENV", "value": "demo"},
                    {"name": "PANNE_MIGRATOR_SECRET_ID", "value": SECRET_DEMO},
                    {"name": "PANNE_PG_SSLMODE", "value": "require"},
                    {"name": "PANNE_ENV", "value": "prod"},
                    {"name": "PANNE_ALEMBIC_CWD", "value": "/app"},
                    {"name": "PANNE_MIGRATE_ALLOW_SEEDED", "value": "1"},
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
                        "awslogs-stream-prefix": "c028-demo-pack-mig",
                    },
                },
            }
        ],
        tags=[
            {"key": "Project", "value": "panne"},
            {"key": "Env", "value": "demo"},
            {"key": "Cursor", "value": "028-DEMO-PACK"},
        ],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
    cdef = td["taskDefinition"]["containerDefinitions"][0]
    if cdef.get("entryPoint") != ENTRYPOINT:
        fail("entryPoint mismatch")
    migrate_vals = [e["value"] for e in cdef.get("environment", []) if e["name"] == "PANNE_MIGRATE_ENV"]
    if migrate_vals != ["demo"]:
        fail("migrate env not demo")
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
            startedBy="cursor-028-demo-pack-migrate",
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
        print(f"task_stopped exit={exit_code}", flush=True)
    finally:
        if task_arn:
            try:
                ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c028-demo-pack-close")
            except ClientError:
                pass
        try:
            ecs.deregister_task_definition(taskDefinition=td_arn)
            print(f"task_definition_deregistered={td_arn}", flush=True)
        except ClientError:
            pass
    print(json.dumps({"digest": digest, "exit_code": exit_code, "task": task_arn}), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
