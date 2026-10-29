"""CURSOR-027-C3-H3 — single authorized demo migrator password rotation (ECS).

AuthorizedRunId: cursor-027-c3-h3-rotate-demo-migrator-authorized-once
Temporarily grants PutSecretValue on panne/demo/db/migrator only; revokes after.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from run_scan_gate import fetch_payload
from scan_gate import ScanGateError, assert_allowed, evaluate_scan_payload

AUTHORIZED_RUN_ID = "cursor-027-c3-h3-rotate-demo-migrator-authorized-once"
REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
REPO = "panne/backend"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE_NAME = "panne-db-migration-task-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/{TASK_ROLE_NAME}"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
DEMO_SG = "sg-0f41648d1720bca80"
RDS_SG = "sg-04269196534d71e08"
EXPECTED_DIGEST = "PLACEHOLDER_SET_BY_ENV"


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def require_authorized() -> None:
    if os.environ.get("AUTHORIZED_RUN_ID") != AUTHORIZED_RUN_ID:
        fail(f"AUTHORIZED_RUN_ID mismatch need={AUTHORIZED_RUN_ID}")


def migrator_read_policy() -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadPanneMigratorSecretsOnly",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                "Resource": [
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/demo/db/migrator-*",
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/prod/db/migrator-*",
                ],
            },
            {
                "Sid": "MigrationLogsOnly",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                "Resource": [
                    f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/ecs/panne/db-migrations",
                    f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/ecs/panne/db-migrations:log-stream:*",
                ],
            },
        ],
    }


def migrator_rotate_policy() -> dict:
    doc = migrator_read_policy()
    doc["Statement"].append(
        {
            "Sid": "RotateDemoMigratorSecretOnly",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:PutSecretValue",
                "secretsmanager:UpdateSecretVersionStage",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
            ],
            "Resource": [
                f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/demo/db/migrator-*"
            ],
        }
    )
    # Remove prod from rotate statement; keep prod read in first statement only.
    raw = json.dumps(doc)
    if "rds!db-" in raw:
        fail("master leaked into policy")
    if "panne/prod/db/migrator" in json.dumps(doc["Statement"][-1]):
        fail("prod secret must not be writable")
    return doc


def put_task_role(doc: dict) -> None:
    iam = boto3.client("iam")
    iam.put_role_policy(
        RoleName=TASK_ROLE_NAME,
        PolicyName="panne-db-migration-inline",
        PolicyDocument=json.dumps(doc),
    )
    if "rds!db-" in json.dumps(doc):
        fail("master in policy")
    log("task_role_policy_applied")


def assert_no_tasks(ecs) -> None:
    for desired in ("RUNNING", "PENDING"):
        arns = []
        for page in ecs.get_paginator("list_tasks").paginate(
            cluster=CLUSTER, family=FAMILY, desiredStatus=desired
        ):
            arns.extend(page.get("taskArns") or [])
        if arns:
            fail(f"tasks active {desired}={arns}")


def prove_sg() -> None:
    ec2 = boto3.client("ec2", region_name=REGION)
    sg = ec2.describe_security_groups(GroupIds=[RDS_SG])["SecurityGroups"][0]
    ids = []
    for perm in sg.get("IpPermissions") or []:
        if perm.get("IpRanges"):
            fail("unexpected CIDR")
        for pair in perm.get("UserIdGroupPairs") or []:
            ids.append(pair["GroupId"])
    if set(ids) != {"sg-0b4dcda30650d419e", "sg-0f41648d1720bca80"}:
        fail(f"unexpected inbound {ids}")
    log("rds_sg_steady=true")


def register_td(image_uri: str) -> str:
    ecs = boto3.client("ecs", region_name=REGION)
    resp = ecs.register_task_definition(
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
                "entryPoint": ["python", "-u", "/app/rotate_demo_migrator.py"],
                "command": [],
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "AUTHORIZED_RUN_ID", "value": AUTHORIZED_RUN_ID},
                    {"name": "PANNE_PG_SSLMODE", "value": "require"},
                    {
                        "name": "ROTATE_CLIENT_TOKEN",
                        "value": AUTHORIZED_RUN_ID,
                    },
                ],
                "linuxParameters": {
                    "tmpfs": [
                        {
                            "containerPath": "/tmp",
                            "size": 64,
                            "mountOptions": ["rw", "noexec", "nosuid", "nodev"],
                        }
                    ]
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/panne/db-migrations",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "c3h3-rotate",
                    },
                },
            }
        ],
    )
    arn = resp["taskDefinition"]["taskDefinitionArn"]
    ep = resp["taskDefinition"]["containerDefinitions"][0].get("entryPoint")
    if "rotate_demo_migrator.py" not in json.dumps(ep):
        fail("entryPoint mismatch")
    if "uvicorn" in json.dumps(ep).lower():
        fail("uvicorn in entryPoint")
    log(f"task_definition_registered={arn}")
    return arn


def main() -> int:
    require_authorized()
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    tag = os.environ.get("PANNE_IMAGE_TAG", "")
    if not digest.startswith("sha256:") or not tag:
        fail("PANNE_IMAGE_DIGEST/TAG required")
    if "img6" not in tag and "c3-h3" not in tag:
        fail("rotation must use H3 img6 tag")

    payload = fetch_payload(REPO, digest, REGION)
    decision = evaluate_scan_payload(payload, allow_high_with_override=False)
    assert_allowed(decision)
    if decision.critical or decision.high:
        fail("scan not green")

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    ecs = boto3.client("ecs", region_name=REGION)
    assert_no_tasks(ecs)
    prove_sg()

    td_arn = None
    task_arn = None
    exit_code = 2
    try:
        put_task_role(migrator_rotate_policy())
        td_arn = register_td(image_uri)
        resp = ecs.run_task(
            cluster=CLUSTER,
            taskDefinition=td_arn,
            launchType="FARGATE",
            platformVersion="LATEST",
            clientToken=AUTHORIZED_RUN_ID,
            count=1,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": SUBNETS,
                    "securityGroups": [DEMO_SG],
                    "assignPublicIp": "DISABLED",
                }
            },
        )
        if resp.get("failures"):
            fail(f"run_task_failures={resp['failures']}")
        task_arn = resp["tasks"][0]["taskArn"]
        log(f"task_arn={task_arn}")
        Path(
            os.environ.get(
                "PANNE_H3_ROTATE_EVIDENCE",
                r"c:\Projetos\panne\documentacao\infraestrutura\_c3h3-rotate-run.json",
            )
        ).write_text(
            json.dumps(
                {
                    "authorizedRunId": AUTHORIZED_RUN_ID,
                    "digest": digest,
                    "tag": tag,
                    "taskDefinition": td_arn,
                    "taskArn": task_arn,
                    "secret": "panne/demo/db/migrator",
                    "masterUsed": False,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        ecs.get_waiter("tasks_stopped").wait(
            cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 60}
        )
        exit_code = None
        for _ in range(10):
            desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])
            exit_code = desc["tasks"][0]["containers"][0].get("exitCode")
            if exit_code is not None:
                break
            import time

            time.sleep(2)
        if exit_code is None:
            fail("exit_code_missing_after_stop")
        exit_code = int(exit_code)
        log(f"task_stopped exit={exit_code}")
        # Fetch logs sanitized
        logs = boto3.client("logs", region_name=REGION)
        stream = f"c3h3-rotate/panne-db-migration/{task_arn.rsplit('/', 1)[-1]}"
        try:
            ev = logs.get_log_events(
                logGroupName="/ecs/panne/db-migrations", logStreamName=stream, limit=100
            )
            for e in ev.get("events") or []:
                msg = e.get("message", "")
                if "password" in msg.lower() or "postgresql" in msg.lower() or "%2" in msg:
                    print("log: (redacted)", flush=True)
                else:
                    print(msg, flush=True)
        except ClientError as exc:
            log(f"log_fetch_warning={exc.response['Error']['Code']}")
    finally:
        if task_arn:
            try:
                ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c3h3-rotate-close")
            except ClientError:
                pass
        if td_arn:
            try:
                ecs.deregister_task_definition(taskDefinition=td_arn)
                log(f"task_definition_deregistered={td_arn}")
            except ClientError:
                pass
        put_task_role(migrator_read_policy())
        log("task_role_write_revoked=true")
        assert_no_tasks(ecs)
        prove_sg()
        pol = boto3.client("iam").get_role_policy(
            RoleName=TASK_ROLE_NAME, PolicyName="panne-db-migration-inline"
        )
        if "PutSecretValue" in json.dumps(pol["PolicyDocument"]):
            fail("write permission still present")
        log("closure_proved=true")

    if exit_code != 0:
        fail(f"rotate_exit={exit_code}", code=exit_code)
    log("authorized_h3_rotate_success")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScanGateError as exc:
        log(f"ERROR: scan_gate {exc}")
        raise SystemExit(1) from exc
