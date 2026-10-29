"""CURSOR-027-C2-B2 single authorized ECS run — no retry loop.

Requires AUTHORIZED_RUN_ID=cursor-027-c2-b2-owner-authorized-once
Uses ECS RunTask clientToken for idempotency. Never calls RunTask twice.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from run_scan_gate import fetch_payload
from scan_gate import ScanGateError, assert_allowed, evaluate_scan_payload

AUTHORIZED_RUN_ID = "cursor-027-c2-b2-owner-authorized-once"
# ECS clientToken max 64 ASCII chars — same logical token.
CLIENT_TOKEN = AUTHORIZED_RUN_ID

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-bootstrap"
REPO = "panne/backend"
RDS_ID = "actionhub-prod"
RDS_SG = "sg-04269196534d71e08"
BOOT_SG = "sg-0c7a0ce1c81ed4cf6"
MASTER_SECRET_ARN = (
    "arn:aws:secretsmanager:us-east-2:253137917703:secret:"
    "rds!db-bb7070d9-83f7-4e09-81b7-31aca7a0c2c0-DUzARr"
)
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-bootstrap-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
DO_NOT_RUN = {
    "sha256:1d618254b703ccc24998d4c0da0221eceb3418d4c63c0cc9d91c290643fe90d2",  # img2
    "sha256:50f4b9ec1cd91748dcc27f76aed4485a139f29c786b82f4ba49f0efae2b44c0c",  # img3
    "sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e",  # C2 vuln
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def require_authorized() -> None:
    got = os.environ.get("AUTHORIZED_RUN_ID", "")
    if got != AUTHORIZED_RUN_ID:
        fail(
            f"AUTHORIZED_RUN_ID mismatch or missing (need {AUTHORIZED_RUN_ID})"
        )


def list_bootstrap_tasks(ecs, desired: str) -> list[str]:
    arns: list[str] = []
    for status in (desired,):
        paginator = ecs.get_paginator("list_tasks")
        for page in paginator.paginate(
            cluster=CLUSTER, family=FAMILY, desiredStatus=status
        ):
            arns.extend(page.get("taskArns") or [])
    return arns


def assert_no_active_tasks(ecs) -> None:
    running = list_bootstrap_tasks(ecs, "RUNNING")
    pending = list_bootstrap_tasks(ecs, "PENDING")
    if running or pending:
        fail(f"bootstrap tasks already active running={running} pending={pending}")


def assert_scan_clean(digest: str) -> dict:
    if digest in DO_NOT_RUN or not digest.startswith("sha256:"):
        fail(f"digest forbidden or invalid: {digest[:24]}")
    payload = fetch_payload(REPO, digest, REGION)
    decision = evaluate_scan_payload(payload, allow_high_with_override=False)
    assert_allowed(decision)
    if decision.critical != 0 or decision.high != 0:
        fail(f"scan not green critical={decision.critical} high={decision.high}")
    # Independent recount
    ecr = boto3.client("ecr", region_name=REGION)
    indep = ecr.describe_image_scan_findings(
        repositoryName=REPO, imageId={"imageDigest": digest}
    )
    counts = (indep.get("imageScanFindings") or {}).get("findingSeverityCounts") or {}
    if int(counts.get("CRITICAL") or 0) != 0 or int(counts.get("HIGH") or 0) != 0:
        fail(f"independent scan recount blocked counts={counts}")
    status = (indep.get("imageScanStatus") or {}).get("status")
    if status != "COMPLETE":
        fail(f"independent scan status={status}")
    log(f"scan_gate_ok digest={digest} counts={counts or '{}'}")
    return {"decision": decision.__dict__, "counts": counts}


def put_task_role_policy(*, with_master: bool) -> None:
    iam = boto3.client("iam")
    resources_read = [
        f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/prod/db/*",
        f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/demo/db/*",
    ]
    if with_master:
        resources_read.insert(
            0,
            f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:rds!db-bb7070d9-83f7-4e09-81b7-31aca7a0c2c0-*",
        )
    doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadSecrets",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                "Resource": resources_read,
            },
            {
                "Sid": "TagPanneSecretSyncStatus",
                "Effect": "Allow",
                "Action": ["secretsmanager:TagResource"],
                "Resource": [
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/prod/db/*",
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/demo/db/*",
                ],
            },
            {
                "Sid": "BootstrapLogsOnly",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                "Resource": [
                    f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/ecs/panne/db-bootstrap",
                    f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/ecs/panne/db-bootstrap:log-stream:*",
                ],
            },
        ],
    }
    iam.put_role_policy(
        RoleName="panne-db-bootstrap-task-role",
        PolicyName="panne-db-bootstrap-inline",
        PolicyDocument=json.dumps(doc),
    )
    log(f"task_role_policy with_master={with_master}")


def set_bootstrap_inbound(*, enable: bool) -> None:
    ec2 = boto3.client("ec2", region_name=REGION)
    if enable:
        try:
            ec2.authorize_security_group_ingress(
                GroupId=RDS_SG,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 5432,
                        "ToPort": 5432,
                        "UserIdGroupPairs": [
                            {
                                "GroupId": BOOT_SG,
                                "Description": "Panne DB bootstrap task to actionhub-prod:5432",
                            }
                        ],
                    }
                ],
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
                raise
        log("inbound_bootstrap_enabled")
    else:
        try:
            ec2.revoke_security_group_ingress(
                GroupId=RDS_SG,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 5432,
                        "ToPort": 5432,
                        "UserIdGroupPairs": [{"GroupId": BOOT_SG}],
                    }
                ],
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in {
                "InvalidPermission.NotFound",
                "InvalidGroup.NotFound",
            }:
                raise
        log("inbound_bootstrap_revoked")


def prove_closed() -> None:
    ec2 = boto3.client("ec2", region_name=REGION)
    sg = ec2.describe_security_groups(GroupIds=[RDS_SG])["SecurityGroups"][0]
    ids = []
    for perm in sg.get("IpPermissions") or []:
        for pair in perm.get("UserIdGroupPairs") or []:
            ids.append(pair["GroupId"])
        if perm.get("IpRanges"):
            fail(f"unexpected CIDR on RDS SG: {perm.get('IpRanges')}")
    if BOOT_SG in ids:
        fail("bootstrap SG still on RDS inbound")
    if set(ids) - { "sg-0b4dcda30650d419e", "sg-0f41648d1720bca80" }:
        fail(f"unexpected inbound SGs: {ids}")
    iam = boto3.client("iam")
    pol = iam.get_role_policy(
        RoleName="panne-db-bootstrap-task-role", PolicyName="panne-db-bootstrap-inline"
    )
    raw = json.dumps(pol["PolicyDocument"])
    if "rds!db-" in raw:
        fail("master secret still in task role policy")
    log("closure_proved=true")


def register_td(image_uri: str) -> str:
    ecs = boto3.client("ecs", region_name=REGION)
    resp = ecs.register_task_definition(
        family=FAMILY,
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="256",
        memory="512",
        executionRoleArn=EXEC_ROLE,
        taskRoleArn=TASK_ROLE,
        runtimePlatform={"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"},
        containerDefinitions=[
            {
                "name": "panne-db-bootstrap",
                "image": image_uri,
                "essential": True,
                "readonlyRootFilesystem": True,
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "PANNE_MASTER_SECRET_ID", "value": MASTER_SECRET_ARN},
                    {"name": "PANNE_SECRET_PROD_MIGRATOR", "value": "panne/prod/db/migrator"},
                    {"name": "PANNE_SECRET_PROD_RUNTIME", "value": "panne/prod/db/runtime"},
                    {"name": "PANNE_SECRET_DEMO_MIGRATOR", "value": "panne/demo/db/migrator"},
                    {"name": "PANNE_SECRET_DEMO_RUNTIME", "value": "panne/demo/db/runtime"},
                    {"name": "PANNE_PG_SSLMODE", "value": "require"},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/panne/db-bootstrap",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "c2b2",
                    },
                },
            }
        ],
    )
    arn = resp["taskDefinition"]["taskDefinitionArn"]
    log(f"task_definition_registered={arn}")
    return arn


def run_once(ecs, td_arn: str) -> str:
    """Single RunTask with fixed clientToken. Never retry."""
    try:
        resp = ecs.run_task(
            cluster=CLUSTER,
            taskDefinition=td_arn,
            launchType="FARGATE",
            platformVersion="LATEST",
            clientToken=CLIENT_TOKEN,
            count=1,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": SUBNETS,
                    "securityGroups": [BOOT_SG],
                    "assignPublicIp": "DISABLED",
                }
            },
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        # Idempotent replay / conflict — fail closed, inspect rather than re-run.
        fail(f"run_task_failed code={code} (no retry)")

    failures = resp.get("failures") or []
    if failures:
        fail(f"run_task_failures={failures}")
    tasks = resp.get("tasks") or []
    if not tasks:
        fail("run_task returned no tasks")
    task_arn = tasks[0]["taskArn"]
    log(f"task_arn={task_arn}")
    return task_arn


def wait_stopped(ecs, task_arn: str) -> int:
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 100}
    )
    desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])
    task = desc["tasks"][0]
    exit_code = task["containers"][0].get("exitCode")
    log(f"task_stopped exit={exit_code} reason={task.get('stoppedReason')}")
    if exit_code is None:
        fail("exit_code_missing")
    return int(exit_code)


def fetch_logs(task_arn: str) -> None:
    logs = boto3.client("logs", region_name=REGION)
    stream = f"c2b2/panne-db-bootstrap/{task_arn.rsplit('/', 1)[-1]}"
    try:
        ev = logs.get_log_events(
            logGroupName="/ecs/panne/db-bootstrap", logStreamName=stream, limit=120
        )
        for e in ev.get("events") or []:
            print(e.get("message", ""), flush=True)
    except ClientError as exc:
        log(f"log_fetch_warning={exc.response['Error']['Code']}")


def close_all(ecs, td_arn: str | None, task_arn: str | None) -> None:
    if task_arn:
        try:
            ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c2b2-close")
        except ClientError:
            pass
    set_bootstrap_inbound(enable=False)
    put_task_role_policy(with_master=False)
    if td_arn:
        try:
            ecs.deregister_task_definition(taskDefinition=td_arn)
            log(f"task_definition_deregistered={td_arn}")
        except ClientError as exc:
            log(f"deregister_warning={exc.response['Error']['Code']}")
    assert_no_active_tasks(ecs)
    prove_closed()


def main() -> int:
    require_authorized()
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    tag = os.environ.get("PANNE_IMAGE_TAG", "")
    if not digest.startswith("sha256:") or not tag:
        fail("PANNE_IMAGE_DIGEST and PANNE_IMAGE_TAG required")
    if "img2" in tag or "img3" in tag:
        fail("img2/img3 tags forbidden")

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    evidence = Path(
        os.environ.get(
            "PANNE_B2_EVIDENCE",
            r"c:\Projetos\panne\documentacao\infraestrutura\_c2b2-run.json",
        )
    )

    ecs = boto3.client("ecs", region_name=REGION)
    rds = boto3.client("rds", region_name=REGION)

    assert_no_active_tasks(ecs)
    status = rds.describe_db_instances(DBInstanceIdentifier=RDS_ID)["DBInstances"][0][
        "DBInstanceStatus"
    ]
    if status != "available":
        fail(f"rds_not_available status={status}")

    scan_meta = assert_scan_clean(digest)

    td_arn: str | None = None
    task_arn: str | None = None
    exit_code = 2
    try:
        put_task_role_policy(with_master=True)
        set_bootstrap_inbound(enable=True)
        # Confirm no CIDR after enable
        prove_no_cidr = boto3.client("ec2", region_name=REGION).describe_security_groups(
            GroupIds=[RDS_SG]
        )["SecurityGroups"][0]
        for perm in prove_no_cidr.get("IpPermissions") or []:
            if perm.get("IpRanges"):
                fail("CIDR present after reopen")

        td_arn = register_td(image_uri)
        # Mechanical single shot
        task_arn = run_once(ecs, td_arn)
        evidence.write_text(
            json.dumps(
                {
                    "authorizedRunId": AUTHORIZED_RUN_ID,
                    "clientToken": CLIENT_TOKEN,
                    "digest": digest,
                    "tag": tag,
                    "taskDefinition": td_arn,
                    "taskArn": task_arn,
                    "scan": scan_meta,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        exit_code = wait_stopped(ecs, task_arn)
        fetch_logs(task_arn)
    finally:
        close_all(ecs, td_arn, task_arn)

    if exit_code != 0:
        fail(f"bootstrap_exit={exit_code}", code=exit_code)
    log("authorized_run_success")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScanGateError as exc:
        log(f"ERROR: scan_gate {exc}")
        raise SystemExit(1) from exc
