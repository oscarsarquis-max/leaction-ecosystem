"""CURSOR-027-C3-H3 authorized migration — img6 digest, explicit entryPoint, no ConfigParser URL.

demo: cursor-027-c3-h3-migrate-demo-authorized-once
prod: cursor-027-c3-h3-migrate-prod-authorized-once
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from run_scan_gate import fetch_payload
from scan_gate import ScanGateError, assert_allowed, evaluate_scan_payload

AUTHORIZED = {
    "demo": "cursor-027-c3-h3-migrate-demo-authorized-once",
    "prod": "cursor-027-c3-h3-migrate-prod-authorized-once",
}
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
SG = {"demo": "sg-0f41648d1720bca80", "prod": "sg-0b4dcda30650d419e"}
SECRET = {"demo": "panne/demo/db/migrator", "prod": "panne/prod/db/migrator"}
ENTRYPOINT = ["python", "-u", "/app/migrate_runner.py"]
COMMAND: list[str] = []
DO_NOT_RUN = {
    "sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e",
    "sha256:1d618254b703ccc24998d4c0da0221eceb3418d4c63c0cc9d91c290643fe90d2",
    "sha256:50f4b9ec1cd91748dcc27f76aed4485a139f29c786b82f4ba49f0efae2b44c0c",
    "sha256:b0447b633d2f7510ff85bc82e0cdc5387ffe8e148492d6993ff1e4137f605186",
    "sha256:b8053869cc40d0d7ac63c4b8cfa3407bfa2ec571b715ee5a3bf9d4c125002eb9",
    "sha256:b4625c5ca416cd014d89f3e65d849fa740edc5f1ea8a16352981c3bd84e4dc2a",  # C3/H2 img
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def require_env_pair() -> tuple[str, str]:
    env = os.environ.get("PANNE_MIGRATE_ENV", "")
    if env not in AUTHORIZED:
        fail("PANNE_MIGRATE_ENV must be demo|prod")
    run_id = os.environ.get("AUTHORIZED_RUN_ID", "")
    if run_id != AUTHORIZED[env]:
        fail(f"AUTHORIZED_RUN_ID mismatch need={AUTHORIZED[env]}")
    return env, run_id


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
    if set(ids) != {SG["demo"], SG["prod"]}:
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


def register_td(image_uri: str, env: str) -> str:
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
                    {"name": "PANNE_MIGRATE_ENV", "value": env},
                    {"name": "PANNE_MIGRATOR_SECRET_ID", "value": SECRET[env]},
                    {"name": "PANNE_PG_SSLMODE", "value": "require"},
                    {"name": "PANNE_ENV", "value": "prod"},
                    {"name": "PANNE_ALEMBIC_CWD", "value": "/app"},
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
                        "awslogs-stream-prefix": f"c3h3-{env}",
                    },
                },
            }
        ],
    )
    arn = resp["taskDefinition"]["taskDefinitionArn"]
    cdef = resp["taskDefinition"]["containerDefinitions"][0]
    if cdef.get("entryPoint") != ENTRYPOINT:
        fail("entryPoint mismatch")
    if "uvicorn" in json.dumps(cdef.get("entryPoint")).lower():
        fail("uvicorn in entryPoint")
    env_blob = json.dumps(cdef.get("environment", []))
    if "PANNE_MASTER_SECRET_ID" in env_blob or "rds!db-" in env_blob:
        fail("master in TD env")
    log(f"task_definition_registered={arn}")
    log(f"entryPoint={ENTRYPOINT} command={COMMAND}")
    return arn


def close_all(ecs, td_arn: str | None, task_arn: str | None) -> None:
    if task_arn:
        try:
            ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="c3h3-close")
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
    env, run_id = require_env_pair()
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    tag = os.environ.get("PANNE_IMAGE_TAG", "")
    if not digest.startswith("sha256:") or not tag:
        fail("PANNE_IMAGE_DIGEST and PANNE_IMAGE_TAG required")
    if "img6" not in tag and "c3-h3" not in tag:
        fail("H3 migrate requires img6 tag")

    required_digest = os.environ.get("PANNE_REQUIRED_DIGEST", "")
    if required_digest and digest != required_digest:
        fail("digest mismatch vs PANNE_REQUIRED_DIGEST")

    snap = os.environ.get("PANNE_REQUIRED_SNAPSHOT_ID", "")
    if not snap:
        fail("PANNE_REQUIRED_SNAPSHOT_ID required")

    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    evidence = Path(
        os.environ.get(
            "PANNE_C3_EVIDENCE",
            rf"c:\Projetos\panne\documentacao\infraestrutura\_c3h3-{env}-run.json",
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

    # Compromised H2 stream must already be gone before migrate
    logs = boto3.client("logs", region_name=REGION)
    bad = "c3h2-demo/panne-db-migration/0501b07f068a41a6ba256277b65dabce"
    try:
        logs.describe_log_streams(
            logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=bad
        )
        streams = [
            s["logStreamName"]
            for s in logs.describe_log_streams(
                logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=bad
            ).get("logStreams")
            or []
            if s["logStreamName"] == bad
        ]
        if streams:
            fail("compromised H2 log stream still exists — stop before migrate")
    except ClientError:
        pass
    log("compromised_stream_absent=true")

    scan_meta = assert_scan_clean(digest)
    prove_rds_sg_steady()
    prove_task_role_no_master_no_write()

    td_arn = None
    task_arn = None
    exit_code = 2
    try:
        td_arn = register_td(image_uri, env)
        resp = ecs.run_task(
            cluster=CLUSTER,
            taskDefinition=td_arn,
            launchType="FARGATE",
            platformVersion="LATEST",
            clientToken=run_id,
            count=1,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": SUBNETS,
                    "securityGroups": [SG[env]],
                    "assignPublicIp": "DISABLED",
                }
            },
        )
        if resp.get("failures"):
            fail(f"run_task_failures={resp['failures']}")
        task_arn = resp["tasks"][0]["taskArn"]
        log(f"task_arn={task_arn}")
        evidence.write_text(
            json.dumps(
                {
                    "authorizedRunId": run_id,
                    "clientToken": run_id,
                    "env": env,
                    "digest": digest,
                    "tag": tag,
                    "snapshot": snap,
                    "taskDefinition": td_arn,
                    "taskArn": task_arn,
                    "entryPoint": ENTRYPOINT,
                    "scan": scan_meta,
                    "masterUsed": False,
                    "gate": "CURSOR-027-C3-H3",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        ecs.get_waiter("tasks_stopped").wait(
            cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 120}
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
        stream = f"c3h3-{env}/panne-db-migration/{task_arn.rsplit('/', 1)[-1]}"
        try:
            ev = logs.get_log_events(
                logGroupName="/ecs/panne/db-migrations", logStreamName=stream, limit=250
            )
            for e in ev.get("events") or []:
                msg = e.get("message", "")
                low = msg.lower()
                if (
                    "://" in msg
                    or "secretstring" in low
                    or "%2" in msg
                    or (low.startswith("password=") or "=password" in low)
                ):
                    print("log: (redacted-sensitive)", flush=True)
                else:
                    print(msg, flush=True)
        except ClientError as exc:
            log(f"log_fetch_warning={exc.response['Error']['Code']}")
    finally:
        close_all(ecs, td_arn, task_arn)

    if exit_code != 0:
        fail(f"migrate_exit={exit_code}", code=exit_code)
    log(f"authorized_c3h3_{env}_success")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScanGateError as exc:
        log(f"ERROR: scan_gate {exc}")
        raise SystemExit(1) from exc
