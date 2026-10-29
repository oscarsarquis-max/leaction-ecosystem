"""Restore AWS panne_demo from local dump (S3) using postgres alpine + pg_restore.

Demo only. Proves DB panne identity untouched. Does not run populate_demo_economy.py.
"""
from __future__ import annotations

import boto3

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"
# Official postgres client image (has pg_restore)
IMG = "public.ecr.aws/docker/library/postgres:16-alpine"

SHELL = r'''
set -euo pipefail
apk add --no-cache aws-cli jq python3 py3-pip >/tmp/apk.log
pip3 install --break-system-packages --quiet boto3 psycopg[binary] sqlalchemy >/tmp/pip.log
python3 - <<'PY'
import json, os, subprocess
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

REGION = "us-east-2"
BUCKET = "panne-demo-frontend-253137917703"
KEY = "ops/cursor-028-custos/panne_demo_custos.dump"
sm = boto3.client("secretsmanager", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

# Prove panne intact BEFORE
sec_p = json.loads(sm.get_secret_value(SecretId="panne/prod/db/migrator")["SecretString"])
assert sec_p["dbname"] == "panne" and sec_p["username"] == "panne_prod_migrator"
url_p = URL.create(
    "postgresql+psycopg",
    username=sec_p["username"],
    password=sec_p["password"],
    host=sec_p["host"],
    port=int(sec_p["port"]),
    database=sec_p["dbname"],
)
e_p = create_engine(url_p, connect_args={"sslmode": "require"})
with e_p.connect() as c:
    assert c.execute(text("SELECT current_database()")).scalar() == "panne"
    org = c.execute(text("SELECT to_regclass('public.organization')")).scalar()
print("panne_intact_before", {"database": "panne", "organization_table": org}, flush=True)
e_p.dispose()

sec = json.loads(sm.get_secret_value(SecretId="panne/demo/db/migrator")["SecretString"])
assert sec["dbname"] == "panne_demo" and sec["username"] == "panne_demo_migrator"
dump = "/tmp/panne_demo_custos.dump"
s3.download_file(BUCKET, KEY, dump)
print("dump_bytes", os.path.getsize(dump), flush=True)

env = os.environ.copy()
env["PGPASSWORD"] = sec["password"]
cmd = [
    "pg_restore",
    "-h", sec["host"],
    "-p", str(sec["port"]),
    "-U", sec["username"],
    "-d", sec["dbname"],
    "--clean",
    "--if-exists",
    "--no-owner",
    "--no-acl",
    dump,
]
print("RESTORE_BEGIN", flush=True)
p = subprocess.run(cmd, env=env, capture_output=True, text=True)
print("stderr_tail", (p.stderr or "")[-6000:], flush=True)
print("restore_rc", p.returncode, flush=True)
# pg_restore returns 1 when some benign errors occur with --clean
if p.returncode not in (0, 1):
    raise SystemExit(p.returncode)

url = URL.create(
    "postgresql+psycopg",
    username=sec["username"],
    password=sec["password"],
    host=sec["host"],
    port=int(sec["port"]),
    database=sec["dbname"],
)
e = create_engine(url, connect_args={"sslmode": "require"})
RELAX = """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relforcerowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
RESTORE = """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
with e.connect() as c:
    c.execute(text(RELAX)); c.commit()
    try:
        rows = c.execute(text("""
            SELECT o.slug,
              (SELECT count(*) FROM technical_product tp WHERE tp.organization_id=o.id) AS produtos,
              (SELECT count(*) FROM ingredient i WHERE i.organization_id=o.id) AS ingredientes,
              (SELECT count(*) FROM supplier_item_price sip JOIN supplier_item si ON si.id=sip.supplier_item_id WHERE si.organization_id=o.id) AS precos_compra,
              (SELECT count(*) FROM costing_calculation cc WHERE cc.organization_id=o.id) AS calculos,
              (SELECT count(*) FROM practiced_price pp WHERE pp.organization_id=o.id) AS precos_venda
            FROM organization o ORDER BY slug
        """)).mappings().all()
        codes = list(
            c.execute(
                text(
                    "SELECT code FROM technical_product tp JOIN organization o ON o.id=tp.organization_id WHERE o.slug='panne-demonstracao' ORDER BY 1"
                )
            ).scalars()
        )
        print("SNAPSHOT_JSON_BEGIN", flush=True)
        print(json.dumps({"counts": [dict(r) for r in rows], "product_codes": codes}, ensure_ascii=False), flush=True)
        print("SNAPSHOT_JSON_END", flush=True)
    finally:
        c.execute(text(RESTORE)); c.commit()
e.dispose()

e_p = create_engine(url_p, connect_args={"sslmode": "require"})
with e_p.connect() as c:
    assert c.execute(text("SELECT current_database()")).scalar() == "panne"
print("panne_intact_after_ok", flush=True)
print("OK", flush=True)
PY
'''


def main() -> int:
    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    prefix = "c028-restore-demo"
    td = ecs.register_task_definition(
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
                "image": IMG,
                "essential": True,
                "entryPoint": ["sh", "-c"],
                "command": [SHELL],
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/panne/db-migrations",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": prefix,
                    },
                },
            }
        ],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
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
        startedBy="cursor-028-custos-restore-demo",
    )
    if run.get("failures"):
        print(run["failures"])
        return 1
    task_arn = run["tasks"][0]["taskArn"]
    print("task", task_arn)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 10, "MaxAttempts": 120}
    )
    desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
    print("exit", desc["containers"][0].get("exitCode"), "reason", desc["containers"][0].get("reason"))
    tid = task_arn.rsplit("/", 1)[-1]
    stream_prefix = f"{prefix}/panne-db-migration/{tid}"
    for s in logs.describe_log_streams(
        logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=stream_prefix
    ).get("logStreams") or []:
        for e in logs.get_log_events(
            logGroupName="/ecs/panne/db-migrations",
            logStreamName=s["logStreamName"],
            startFromHead=True,
        ).get("events") or []:
            print(e["message"])
    try:
        ecs.deregister_task_definition(taskDefinition=td_arn)
    except Exception:
        pass
    return 0 if desc["containers"][0].get("exitCode") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
