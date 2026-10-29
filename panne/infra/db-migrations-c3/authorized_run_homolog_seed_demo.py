"""CURSOR-027 homolog — authorized Demo 026 seed (panne_demo only).

Token: cursor-027-homolog-seed-demo-authorized-once
Never runs prod. Never uses migrate-prod token.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from run_scan_gate import fetch_payload
from scan_gate import assert_allowed, evaluate_scan_payload

AUTHORIZED_RUN_ID = "cursor-027-homolog-seed-demo-authorized-once"
REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
REPO = "panne/backend"
RDS_ID = "actionhub-prod"
RDS_SG = "sg-04269196534d71e08"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"
SG_PROD = "sg-0b4dcda30650d419e"
SECRET = "panne/demo/db/migrator"
ENTRYPOINT = ["python", "-u", "/app/seed_runner.py"]
COMMAND: list[str] = []
DO_NOT_RUN = {
    "sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e",
    "sha256:1d618254b703ccc24998d4c0da0221eceb3418d4c63c0cc9d91c290643fe90d2",
    "sha256:50f4b9ec1cd91748dcc27f76aed4485a139f29c786b82f4ba49f0efae2b44c0c",
    "sha256:b0447b633d2f7510ff85bc82e0cdc5387ffe8e148492d6993ff1e4137f605186",
    "sha256:b8053869cc40d0d7ac63c4b8cfa3407bfa2ec571b715ee5a3bf9d4c125002eb9",
    "sha256:b4625c5ca416cd014d89f3e65d849fa740edc5f1ea8a16352981c3bd84e4dc2a",
    # Accidental rebuilds during validation fix — DO_NOT_USE (kept in ECR, never deploy)
    "sha256:4dbe9a3d68837730045e58d6f1969eb2538165010ee362ea8e27562fae9f485b",  # img7
    "sha256:9eb41c33433e03d27dc750ac3ade1957bc5f5604127cd25799d96cb812e41096",  # img7c
    "sha256:68a679b59d7fa3c1b5972b41fb66a17ad3d2a1b8d8d21b78652e2e4939cbf844",  # img7d
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def assert_auth() -> None:
    if os.environ.get("AUTHORIZED_RUN_ID") != AUTHORIZED_RUN_ID:
        fail(f"AUTHORIZED_RUN_ID mismatch need={AUTHORIZED_RUN_ID}")
    if os.environ.get("PANNE_SEED_ENV") != "demo":
        fail("PANNE_SEED_ENV must be demo")
    if os.environ.get("PANNE_MIGRATE_ENV") == "prod":
        fail("prod migrate env forbidden")
    forbidden = "cursor-027-c3-h3-migrate-prod-authorized-once"
    if os.environ.get("AUTHORIZED_RUN_ID") == forbidden:
        fail("prod migrate token forbidden")


def assert_no_active_tasks(ecs) -> None:
    for desired in ("RUNNING", "PENDING"):
        arns = []
        for page in ecs.get_paginator("list_tasks").paginate(
            cluster=CLUSTER, family=FAMILY, desiredStatus=desired
        ):
            arns.extend(page.get("taskArns") or [])
        if arns:
            fail(f"tasks active {desired}={arns}")


def assert_scan_clean(digest: str) -> dict:
    if digest in DO_NOT_RUN or not digest.startswith("sha256:"):
        fail(f"digest forbidden: {digest[:40]}")
    payload = fetch_payload(REPO, digest, REGION)
    decision = evaluate_scan_payload(payload, allow_high_with_override=False)
    assert_allowed(decision)
    if decision.critical or decision.high:
        fail("scan not green")
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
    return {"counts": counts}


def prove_rds_sg_steady() -> None:
    ec2 = boto3.client("ec2", region_name=REGION)
    sg = ec2.describe_security_groups(GroupIds=[RDS_SG])["SecurityGroups"][0]
    ids = []
    for perm in sg.get("IpPermissions") or []:
        if perm.get("IpRanges"):
            fail("unexpected CIDR")
        for pair in perm.get("UserIdGroupPairs") or []:
            ids.append(pair["GroupId"])
    if set(ids) != {SG_DEMO, SG_PROD}:
        fail(f"unexpected inbound {ids}")
    log("rds_sg_steady=true")


def prove_task_role_no_master_no_write() -> None:
    iam = boto3.client("iam")
    pol = iam.get_role_policy(
        RoleName="panne-db-migration-task-role", PolicyName="panne-db-migration-inline"
    )
    raw = json.dumps(pol["PolicyDocument"])
    if "rds!db-" in raw:
        fail("master in migration task role")
    if "PutSecretValue" in raw:
        fail("secret write still on migration role")
    if "db/runtime" in raw:
        fail("runtime secret on migration role")
    log("task_role_migrator_readonly=true master_absent=true")


def register_td(image_uri: str) -> str:
    ecs = boto3.client("ecs", region_name=REGION)
    resp = ecs.register_task_definition(
        family=FAMILY,
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="1024",
        memory="2048",
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
                "command": COMMAND,
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "PANNE_SEED_ENV", "value": "demo"},
                    {"name": "PANNE_ENV", "value": "demo"},
                    {"name": "PANNE_MIGRATOR_SECRET_ID", "value": SECRET},
                    {"name": "PANNE_SEED_ANCHOR_DATE", "value": "2026-08-24"},
                    {"name": "PANNE_PG_SSLMODE", "value": "require"},
                ],
                "linuxParameters": {
                    "tmpfs": [
                        {
                            "containerPath": "/tmp",
                            "size": 256,
                            "mountOptions": ["rw", "noexec", "nosuid", "nodev"],
                        }
                    ]
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/panne/db-migrations",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "homolog-seed-demo",
                    },
                },
            }
        ],
    )
    arn = resp["taskDefinition"]["taskDefinitionArn"]
    cdef = resp["taskDefinition"]["containerDefinitions"][0]
    if cdef.get("entryPoint") != ENTRYPOINT:
        fail("entryPoint mismatch")
    env_blob = json.dumps(cdef.get("environment", []))
    if "PANNE_MASTER_SECRET_ID" in env_blob or "rds!db-" in env_blob:
        fail("master in TD env")
    if "panne/prod" in env_blob:
        fail("prod secret in TD env")
    log(f"task_definition_registered={arn}")
    return arn


def close_all(ecs, td_arn: str | None, task_arn: str | None) -> None:
    if task_arn:
        try:
            ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="homolog-seed-close")
        except ClientError:
            pass
    if td_arn:
        try:
            ecs.deregister_task_definition(taskDefinition=td_arn)
            log(f"task_definition_deregistered={td_arn}")
        except ClientError:
            pass
    assert_no_active_tasks(ecs)
    prove_rds_sg_steady()
    prove_task_role_no_master_no_write()
    log("closure_proved=true")


def wait_task(ecs, task_arn: str, timeout_s: int = 1800) -> dict:
    start = time.time()
    while time.time() - start < timeout_s:
        desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
        last = desc.get("lastStatus")
        if last == "STOPPED":
            return desc
        time.sleep(10)
    fail("task wait timeout")


def main() -> int:
    assert_auth()
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    tag = os.environ.get("PANNE_IMAGE_TAG", "")
    if not digest.startswith("sha256:") or not tag:
        fail("PANNE_IMAGE_DIGEST and PANNE_IMAGE_TAG required")
    if "seed" not in tag and "img7" not in tag and "homolog" not in tag:
        fail("seed requires homolog/img7/seed image tag")
    # img7 / img7b / img7c all acceptable

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    evidence = Path(
        os.environ.get(
            "PANNE_SEED_EVIDENCE",
            rf"c:\Projetos\panne\documentacao\infraestrutura\_homolog-seed-demo-run.json",
        )
    )

    ecs = boto3.client("ecs", region_name=REGION)
    rds = boto3.client("rds", region_name=REGION)
    assert_no_active_tasks(ecs)
    if rds.describe_db_instances(DBInstanceIdentifier=RDS_ID)["DBInstances"][0][
        "DBInstanceStatus"
    ] != "available":
        fail("rds not available")
    prove_rds_sg_steady()
    prove_task_role_no_master_no_write()
    scan = assert_scan_clean(digest)

    td_arn = None
    task_arn = None
    exit_code = None
    try:
        td_arn = register_td(image_uri)
        run = ecs.run_task(
            cluster=CLUSTER,
            taskDefinition=td_arn,
            launchType="FARGATE",
            platformVersion="1.4.0",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": SUBNETS,
                    "securityGroups": [SG_DEMO],
                    "assignPublicIp": "DISABLED",
                }
            },
            startedBy=AUTHORIZED_RUN_ID[:36],
            tags=[
                {"key": "AuthorizedRunId", "value": AUTHORIZED_RUN_ID},
                {"key": "PanneEnv", "value": "demo"},
                {"key": "Purpose", "value": "homolog-seed-demo-026"},
            ],
        )
        if run.get("failures"):
            fail(f"run_task failures={run['failures']}")
        task_arn = run["tasks"][0]["taskArn"]
        log(f"task_started={task_arn}")
        desc = wait_task(ecs, task_arn)
        containers = desc.get("containers") or []
        exit_code = containers[0].get("exitCode") if containers else None
        reason = containers[0].get("reason") if containers else None
        log(f"task_stopped exitCode={exit_code} reason={reason}")
        if exit_code != 0:
            fail(f"seed task failed exitCode={exit_code}")
    finally:
        close_all(ecs, td_arn, task_arn)

    evidence.write_text(
        json.dumps(
            {
                "authorized_run_id": AUTHORIZED_RUN_ID,
                "image_digest": digest,
                "image_tag": tag,
                "task_arn": task_arn,
                "exit_code": exit_code,
                "scan": scan,
                "env": "demo",
                "database": "panne_demo",
                "prod_migrated": False,
                "prod_seeded": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log(f"evidence={evidence}")
    log("seed_demo_authorized_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
