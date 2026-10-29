"""CURSOR-027-C2-H1 single authorized ECS run — no master, no retry.

Requires AUTHORIZED_RUN_ID=cursor-027-c2-h1-hardening-authorized-once
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

AUTHORIZED_RUN_ID = "cursor-027-c2-h1-hardening-authorized-once"
CLIENT_TOKEN = AUTHORIZED_RUN_ID

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-bootstrap"
REPO = "panne/backend"
RDS_ID = "actionhub-prod"
RDS_SG = "sg-04269196534d71e08"
BOOT_SG = "sg-0c7a0ce1c81ed4cf6"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE_NAME = "panne-db-bootstrap-task-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/{TASK_ROLE_NAME}"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
DO_NOT_RUN = {
    "sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e",
    "sha256:1d618254b703ccc24998d4c0da0221eceb3418d4c63c0cc9d91c290643fe90d2",
    "sha256:50f4b9ec1cd91748dcc27f76aed4485a139f29c786b82f4ba49f0efae2b44c0c",
    "sha256:b0447b633d2f7510ff85bc82e0cdc5387ffe8e148492d6993ff1e4137f605186",  # img4
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def require_authorized() -> None:
    if os.environ.get("AUTHORIZED_RUN_ID", "") != AUTHORIZED_RUN_ID:
        fail(f"AUTHORIZED_RUN_ID mismatch (need {AUTHORIZED_RUN_ID})")


def list_tasks(ecs, desired: str) -> list[str]:
    arns: list[str] = []
    for page in ecs.get_paginator("list_tasks").paginate(
        cluster=CLUSTER, family=FAMILY, desiredStatus=desired
    ):
        arns.extend(page.get("taskArns") or [])
    return arns


def assert_no_active_tasks(ecs) -> None:
    running = list_tasks(ecs, "RUNNING")
    pending = list_tasks(ecs, "PENDING")
    if running or pending:
        fail(f"tasks active running={running} pending={pending}")


def assert_scan_clean(digest: str) -> dict:
    if digest in DO_NOT_RUN or not digest.startswith("sha256:"):
        fail(f"digest forbidden or invalid: {digest[:32]}")
    payload = fetch_payload(REPO, digest, REGION)
    decision = evaluate_scan_payload(payload, allow_high_with_override=False)
    assert_allowed(decision)
    if decision.critical or decision.high:
        fail(f"scan not green c={decision.critical} h={decision.high}")
    ecr = boto3.client("ecr", region_name=REGION)
    indep = ecr.describe_image_scan_findings(
        repositoryName=REPO, imageId={"imageDigest": digest}
    )
    counts = (indep.get("imageScanFindings") or {}).get("findingSeverityCounts") or {}
    if int(counts.get("CRITICAL") or 0) or int(counts.get("HIGH") or 0):
        fail(f"independent recount blocked {counts}")
    if (indep.get("imageScanStatus") or {}).get("status") != "COMPLETE":
        fail("scan not COMPLETE")
    log(f"scan_gate_ok digest={digest} counts={counts or '{}'}")
    return {"decision": decision.__dict__, "counts": counts}


def put_task_role_panne_only() -> None:
    """Never include master secret."""
    iam = boto3.client("iam")
    doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadPanneAppSecretsOnly",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                "Resource": [
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/prod/db/*",
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:panne/demo/db/*",
                ],
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
        RoleName=TASK_ROLE_NAME,
        PolicyName="panne-db-bootstrap-inline",
        PolicyDocument=json.dumps(doc),
    )
    raw = json.dumps(doc)
    if "rds!db-" in raw:
        fail("master leaked into policy document")
    log("task_role_panne_only=true master_absent=true")


def set_bootstrap_inbound(*, enable: bool) -> None:
    ec2 = boto3.client("ec2", region_name=REGION)
    perm = [
        {
            "IpProtocol": "tcp",
            "FromPort": 5432,
            "ToPort": 5432,
            "UserIdGroupPairs": [
                {
                    "GroupId": BOOT_SG,
                    "Description": "Panne DB bootstrap/harden task to actionhub-prod:5432",
                }
            ],
        }
    ]
    if enable:
        try:
            ec2.authorize_security_group_ingress(GroupId=RDS_SG, IpPermissions=perm)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
                raise
        log("inbound_bootstrap_enabled")
    else:
        try:
            ec2.revoke_security_group_ingress(GroupId=RDS_SG, IpPermissions=perm)
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
        if perm.get("IpRanges"):
            fail(f"unexpected CIDR {perm.get('IpRanges')}")
        for pair in perm.get("UserIdGroupPairs") or []:
            ids.append(pair["GroupId"])
    if BOOT_SG in ids:
        fail("bootstrap SG still inbound")
    if set(ids) - {"sg-0b4dcda30650d419e", "sg-0f41648d1720bca80"}:
        fail(f"unexpected inbound {ids}")
    iam = boto3.client("iam")
    pol = iam.get_role_policy(RoleName=TASK_ROLE_NAME, PolicyName="panne-db-bootstrap-inline")
    if "rds!db-" in json.dumps(pol["PolicyDocument"]):
        fail("master still in task role")
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
                        "awslogs-stream-prefix": "c2h1",
                    },
                },
            }
        ],
    )
    arn = resp["taskDefinition"]["taskDefinitionArn"]
    # Guard: no master in registered TD
    env_names = {
        e["name"]
        for e in resp["taskDefinition"]["containerDefinitions"][0].get("environment", [])
    }
    if "PANNE_MASTER_SECRET_ID" in env_names:
        fail("master env present in task definition")
    log(f"task_definition_registered={arn}")
    return arn


def run_once(ecs, td_arn: str) -> str:
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
        fail(f"run_task_failed code={exc.response['Error']['Code']} (no retry)")
    if resp.get("failures"):
        fail(f"run_task_failures={resp['failures']}")
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
    exit_code = desc["tasks"][0]["containers"][0].get("exitCode")
    log(f"task_stopped exit={exit_code} reason={desc['tasks'][0].get('stoppedReason')}")
    if exit_code is None:
        fail("exit_code_missing")
    return int(exit_code)


def fetch_logs(task_arn: str) -> None:
    logs = boto3.client("logs", region_name=REGION)
    stream = f"c2h1/panne-db-bootstrap/{task_arn.rsplit('/', 1)[-1]}"
    try:
        ev = logs.get_log_events(
            logGroupName="/ecs/panne/db-bootstrap", logStreamName=stream, limit=150
        )
        for e in ev.get("events") or []:
            print(e.get("message", ""), flush=True)
    except ClientError as exc:
        log(f"log_fetch_warning={exc.response['Error']['Code']}")


def close_all(ecs, td_arn: str | None, task_arn: str | None) -> None:
    if task_arn:
        try:
            ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c2h1-close")
        except ClientError:
            pass
    set_bootstrap_inbound(enable=False)
    put_task_role_panne_only()
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
    for banned in ("img1", "img2", "img3", "img4"):
        if banned in tag:
            fail(f"forbidden tag fragment {banned}")

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    evidence = Path(
        os.environ.get(
            "PANNE_H1_EVIDENCE",
            r"c:\Projetos\panne\documentacao\infraestrutura\_c2h1-run.json",
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
        put_task_role_panne_only()
        set_bootstrap_inbound(enable=True)
        # CIDR check
        sg = boto3.client("ec2", region_name=REGION).describe_security_groups(GroupIds=[RDS_SG])[
            "SecurityGroups"
        ][0]
        for perm in sg.get("IpPermissions") or []:
            if perm.get("IpRanges"):
                fail("CIDR present after reopen")

        td_arn = register_td(image_uri)
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
                    "masterUsed": False,
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
        fail(f"harden_exit={exit_code}", code=exit_code)
    log("authorized_h1_success")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScanGateError as exc:
        log(f"ERROR: scan_gate {exc}")
        raise SystemExit(1) from exc
