"""CURSOR-028-D authorized migration — demo only (panne_demo). No prod.

One-shot: AUTHORIZED_RUN_ID=cursor-028-d-migrate-demo-authorized-once
Sets PANNE_MIGRATE_ALLOW_SEEDED=1 because demo already has org/user seed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from run_scan_gate import fetch_payload
from scan_gate import ScanGateError, assert_allowed, evaluate_scan_payload

AUTHORIZED_DEMO = "cursor-028-d-migrate-demo-authorized-once"
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
SECRET_DEMO = "panne/demo/db/migrator"
ENTRYPOINT = ["python", "-u", "/app/migrate_runner.py"]
COMMAND: list[str] = []
DO_NOT_RUN = {
    # 028-C first image: wrong alembic/env.py (localhost:5434)
    "sha256:f9405c5d444af1052aee758488111561247a21241c3bcada7540301827266ac6",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def require_demo_auth() -> None:
    if os.environ.get("PANNE_MIGRATE_ENV") != "demo":
        fail("PANNE_MIGRATE_ENV must be demo (prod frozen for 028-D)")
    if os.environ.get("AUTHORIZED_RUN_ID") != AUTHORIZED_DEMO:
        fail(f"AUTHORIZED_RUN_ID mismatch need={AUTHORIZED_DEMO}")


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
    return {"decision": decision.__dict__, "counts": counts}


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
                "command": COMMAND,
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
                        "awslogs-stream-prefix": "c028d-demo",
                    },
                },
            }
        ],
    )
    arn = resp["taskDefinition"]["taskDefinitionArn"]
    cdef = resp["taskDefinition"]["containerDefinitions"][0]
    if cdef.get("entryPoint") != ENTRYPOINT:
        fail("entryPoint mismatch")
    migrate_vals = [
        e["value"] for e in cdef.get("environment", []) if e["name"] == "PANNE_MIGRATE_ENV"
    ]
    if migrate_vals != ["demo"]:
        fail("migrate env not demo")
    log(f"task_definition_registered={arn}")
    return arn


def close_all(ecs, td_arn: str | None, task_arn: str | None) -> None:
    if task_arn:
        try:
            ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c028d-close")
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


def main() -> int:
    require_demo_auth()
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    tag = os.environ.get("PANNE_IMAGE_TAG", "")
    if not digest.startswith("sha256:") or not tag:
        fail("PANNE_IMAGE_DIGEST and PANNE_IMAGE_TAG required")
    if "028-d" not in tag and "fiscal" not in tag:
        fail("tag must reference 028-d/fiscal for this runner")

    snap = os.environ.get("PANNE_REQUIRED_SNAPSHOT_ID", "")
    if not snap:
        fail("PANNE_REQUIRED_SNAPSHOT_ID required")

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    evidence = Path(
        os.environ.get(
            "PANNE_C028D_EVIDENCE",
            rf"c:\Projetos\panne\documentacao\infraestrutura\_c028d-demo-run.json",
        )
    )

    ecs = boto3.client("ecs", region_name=REGION)
    rds = boto3.client("rds", region_name=REGION)
    assert_no_active_tasks(ecs)
    if rds.describe_db_instances(DBInstanceIdentifier=RDS_ID)["DBInstances"][0][
        "DBInstanceStatus"
    ] != "available":
        fail("rds not available")
    snap_desc = rds.describe_db_snapshots(DBSnapshotIdentifier=snap)["DBSnapshots"][0]
    if snap_desc["Status"] != "available" or snap_desc["DBInstanceIdentifier"] != RDS_ID:
        fail("snapshot not ready")
    log(f"snapshot_ok id={snap}")

    scan_meta = assert_scan_clean(digest)
    prove_rds_sg_steady()
    prove_task_role_no_master_no_write()

    td_arn = None
    task_arn = None
    exit_code = 1
    try:
        td_arn = register_td(image_uri)
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
            propagateTags="TASK_DEFINITION",
        )
        if run.get("failures"):
            fail(f"run_task failures={run['failures']}")
        task_arn = run["tasks"][0]["taskArn"]
        log(f"task_started={task_arn}")
        waiter = ecs.get_waiter("tasks_stopped")
        waiter.wait(cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 15, "MaxAttempts": 80})
        desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
        containers = desc.get("containers") or []
        exit_code = int((containers[0].get("exitCode") if containers else None) or 1)
        log(f"task_stopped exit={exit_code}")
        evidence.write_text(
            json.dumps(
                {
                    "cursor": "028-D",
                    "digest": digest,
                    "tag": tag,
                    "task_arn": task_arn,
                    "exit_code": exit_code,
                    "scan": scan_meta,
                    "snapshot": snap,
                    "fazenda_live": False,
                    "allow_seeded": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    finally:
        close_all(ecs, td_arn, task_arn)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
