"""Revalidate Demo 026 seed under FORCE RLS + tenant set_config. img7b only. No mutate."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

AUTHORIZED_RUN_ID = "cursor-027-homolog-validate-seed-tenant-once"
REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
REPO = "panne/backend"
IMG7B_DIGEST = "sha256:01c691ebd21fae0dbaf64c5cf2fad35e49bd2fa49f433d60f4be8a329abc0236"
IMG7B_TAG = "backend-027-homolog-seed-142b356-img7b"
DO_NOT_USE = {
    "sha256:68a679b59d7fa3c1b5972b41fb66a17ad3d2a1b8d8d21b78652e2e4939cbf844",
    "sha256:9eb41c33433e03d27dc750ac3ade1957bc5f5604127cd25799d96cb812e41096",
    "sha256:4dbe9a3d68837730045e58d6f1969eb2538165010ee362ea8e27562fae9f485b",
}
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"
SECRET = "panne/demo/db/migrator"

# Inline validator: FORCE preserved, NO BYPASSRLS, no seed mutate.
VALIDATE_PY = r"""
import json, os, sys
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from app.seed.ids import seed_uuid

ORG_A, ORG_B = "panne-demonstracao", "padaria-horizonte-demo"
ISSUER, SUBJ = "https://panne.local/fake", "demo-owner"
oa, ob, ou = seed_uuid("org", ORG_A), seed_uuid("org", ORG_B), seed_uuid("user", SUBJ)
est = seed_uuid("est", str(oa), "CENTRAL")

def fail(m):
    print("ERROR:", m, flush=True); raise SystemExit(1)

sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION","us-east-2"))
sec = json.loads(sm.get_secret_value(SecretId=os.environ["PANNE_MIGRATOR_SECRET_ID"])["SecretString"])
assert sec["username"]=="panne_demo_migrator" and sec["dbname"]=="panne_demo"
url = URL.create("postgresql+psycopg", username=sec["username"], password=sec["password"],
                 host=sec["host"], port=int(sec["port"]), database=sec["dbname"])
eng = create_engine(url, future=True, connect_args={"sslmode":"require"})

def set_t(c, oid=None, uid=None, sub=""):
    c.execute(text("SELECT set_config('app.current_organization_id', :v, true)"), {"v": "" if oid is None else str(oid)})
    c.execute(text("SELECT set_config('app.current_user_id', :v, true)"), {"v": "" if uid is None else str(uid)})
    c.execute(text("SELECT set_config('app.current_issuer', :v, true)"), {"v": ISSUER if sub else ""})
    c.execute(text("SELECT set_config('app.current_subject', :v, true)"), {"v": sub})

with eng.connect() as c:
    forced = c.execute(text("SELECT COUNT(*) FROM pg_class x JOIN pg_namespace n ON n.oid=x.relnamespace WHERE n.nspname='public' AND x.relkind='r' AND x.relforcerowsecurity")).scalar()
    bypass = c.execute(text("SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user")).scalar()
    if forced < 40: fail(f"FORCE RLS weak {forced}")
    if bypass: fail("BYPASSRLS set")
    print(f"force_rls_intact={forced} nobypassrls=true", flush=True)
    c.commit()

    with eng.connect() as c2:
        set_t(c2); blind=c2.execute(text("SELECT COUNT(*) FROM organization")).scalar(); c2.commit()
        if blind: fail(f"blind leak {blind}")
        print("isolation_blind_ok", flush=True)

    with eng.connect() as c2:
        set_t(c2, oa, ou, SUBJ)
        slug=c2.execute(text("SELECT slug FROM organization WHERE id=:i"), {"i": oa}).scalar()
        if slug != ORG_A: fail(f"orgA {slug}")
        ing=int(c2.execute(text("SELECT COUNT(*) FROM ingredient WHERE organization_id=:o"), {"o": oa}).scalar() or 0)
        ordn=int(c2.execute(text("SELECT COUNT(*) FROM production_order WHERE organization_id=:o"), {"o": oa}).scalar() or 0)
        estn=int(c2.execute(text("SELECT COUNT(*) FROM establishment WHERE organization_id=:o"), {"o": oa}).scalar() or 0)
        code=c2.execute(text("SELECT code FROM establishment WHERE id=:i"), {"i": est}).scalar()
        c2.commit()
        if ing < 5 or ordn < 1 or estn < 1 or code != "CENTRAL":
            fail(f"counts ing={ing} orders={ordn} est={estn} central={code}")
        print(f"tenant_a_ok gaps=0 ingredients={ing} orders={ordn} establishments={estn}", flush=True)

    with eng.connect() as c2:
        set_t(c2, ob, ou, SUBJ)
        slugb=c2.execute(text("SELECT slug FROM organization WHERE id=:i"), {"i": ob}).scalar()
        leak_e=int(c2.execute(text("SELECT COUNT(*) FROM establishment WHERE organization_id=:o"), {"o": oa}).scalar() or 0)
        leak_i=int(c2.execute(text("SELECT COUNT(*) FROM ingredient WHERE organization_id=:o"), {"o": oa}).scalar() or 0)
        leak_o=int(c2.execute(text("SELECT COUNT(*) FROM production_order WHERE organization_id=:o"), {"o": oa}).scalar() or 0)
        estb=int(c2.execute(text("SELECT COUNT(*) FROM establishment WHERE organization_id=:o"), {"o": ob}).scalar() or 0)
        c2.commit()
        if slugb != ORG_B: fail(f"orgB {slugb}")
        if leak_e or leak_i or leak_o: fail(f"leak e={leak_e} i={leak_i} o={leak_o}")
        if estb < 1: fail("orgB empty")
        print(f"isolation_b_ok no_leak=true est_b={estb}", flush=True)

    with eng.connect() as c2:
        forced2 = c2.execute(text("SELECT COUNT(*) FROM pg_class x JOIN pg_namespace n ON n.oid=x.relnamespace WHERE n.nspname='public' AND x.relkind='r' AND x.relforcerowsecurity")).scalar()
        if forced2 != forced: fail("FORCE RLS changed during validate")
        print("validate_complete force_preserved=true mutate=false", flush=True)
eng.dispose()
"""


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def main() -> int:
    if os.environ.get("AUTHORIZED_RUN_ID") != AUTHORIZED_RUN_ID:
        fail(f"AUTHORIZED_RUN_ID mismatch need={AUTHORIZED_RUN_ID}")
    digest = os.environ.get("PANNE_IMAGE_DIGEST", "")
    if digest != IMG7B_DIGEST:
        fail(f"only img7b allowed got={digest}")
    if digest in DO_NOT_USE:
        fail("DO_NOT_USE digest")

    ecr = boto3.client("ecr", region_name=REGION)
    scan = ecr.describe_image_scan_findings(
        repositoryName=REPO, imageId={"imageDigest": digest}
    )
    if (scan.get("imageScanStatus") or {}).get("status") != "COMPLETE":
        fail("img7b scan not COMPLETE")
    counts = (scan.get("imageScanFindings") or {}).get("findingSeverityCounts") or {}
    if int(counts.get("CRITICAL") or 0) or int(counts.get("HIGH") or 0):
        fail(f"img7b scan not green {counts}")
    log(f"img7b_ok digest={digest} scan={counts or '{}'}")

    ecs = boto3.client("ecs", region_name=REGION)
    image_uri = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{REPO}@{digest}"
    td_arn = None
    task_arn = None
    try:
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
                    "entryPoint": ["python", "-u", "-c"],
                    "command": [VALIDATE_PY],
                    "environment": [
                        {"name": "AWS_REGION", "value": REGION},
                        {"name": "AWS_DEFAULT_REGION", "value": REGION},
                        {"name": "PANNE_MIGRATOR_SECRET_ID", "value": SECRET},
                        {"name": "PANNE_ENV", "value": "demo"},
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
                            "awslogs-stream-prefix": "homolog-validate-tenant",
                        },
                    },
                }
            ],
        )
        td_arn = resp["taskDefinition"]["taskDefinitionArn"]
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
                {"key": "Purpose", "value": "validate-seed-tenant-no-mutate"},
            ],
        )
        if run.get("failures"):
            fail(str(run["failures"]))
        task_arn = run["tasks"][0]["taskArn"]
        log(f"task_started={task_arn}")
        for _ in range(60):
            desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
            if desc.get("lastStatus") == "STOPPED":
                break
            time.sleep(5)
        exit_code = (desc.get("containers") or [{}])[0].get("exitCode")
        log(f"exitCode={exit_code}")
        if exit_code != 0:
            fail("validate failed")
    finally:
        if task_arn:
            try:
                ecs.stop_task(cluster=CLUSTER, task=task_arn, reason="validate-close")
            except ClientError:
                pass
        if td_arn:
            try:
                ecs.deregister_task_definition(taskDefinition=td_arn)
            except ClientError:
                pass

    Path(
        r"c:\Projetos\panne\documentacao\infraestrutura\_homolog-validate-tenant-run.json"
    ).write_text(
        json.dumps(
            {
                "authorized_run_id": AUTHORIZED_RUN_ID,
                "image": IMG7B_TAG,
                "digest": IMG7B_DIGEST,
                "mutate": False,
                "force_rls": "preserved",
                "bypassrls": False,
                "do_not_use_images_excluded": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log("validate_seed_tenant_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
