"""Post-028-C validation on panne_demo (and untouched panne). No secrets printed."""
from __future__ import annotations

import json

import boto3

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
DIGEST = "sha256:960e5b88d8e244b2bad3c0ab2e7dcb235ca51bcb4d6eb45f9dab57f9067da77a"
IMG = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{DIGEST}"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"

PROBE = r'''
import json, os, sys
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

def eng(secret_id, expect_db, expect_user):
    sm = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"])
    sec = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    assert sec["dbname"] == expect_db and sec["username"] == expect_user, (
        f"got user={sec.get('username')} db={sec.get('dbname')}"
    )
    url = URL.create("postgresql+psycopg", username=sec["username"], password=sec["password"],
                     host=sec["host"], port=int(sec["port"]), database=sec["dbname"])
    return create_engine(url, connect_args={"sslmode":"require"})

fails = []
RELAX = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""
RESTORE = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""
# --- demo ---
e = eng("panne/demo/db/migrator", "panne_demo", "panne_demo_migrator")
with e.connect() as c:
    c.execute(text(RELAX))
    c.commit()
    try:
        head = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"demo_head={head}", flush=True)
        if head != "0021_product_canonical":
            fails.append("demo_head")
        fam = c.execute(text("SELECT to_regclass('public.product_family')")).scalar()
        print(f"product_family={fam}", flush=True)
        cols = {r[0] for r in c.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='technical_product'"
        ))}
        need = {"supply_mode","purpose","family_id","stock_unit_id","sale_unit_id","net_content"}
        print(f"product_cols_ok={need <= cols}", flush=True)
        if not (need <= cols):
            fails.append("cols")
        n = c.execute(text("SELECT COUNT(*) FROM technical_product")).scalar()
        produced = c.execute(text("SELECT COUNT(*) FROM technical_product WHERE supply_mode='produced'")).scalar()
        other = c.execute(text("SELECT COUNT(*) FROM technical_product WHERE supply_mode<>'produced'")).scalar()
        activeish = c.execute(text("SELECT COUNT(*) FROM technical_product WHERE status IN ('active','inactive')")).scalar()
        print(f"products_total={n} produced={produced} non_produced={other} status_active_inactive={activeish}", flush=True)
        if n and produced != n:
            fails.append("backfill_supply")
        if n and activeish != n:
            fails.append("backfill_status")
        rls = c.execute(text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname='product_family'"
        )).one()
        print(f"product_family_rls_enabled={rls[0]}", flush=True)
        if not rls[0]:
            fails.append("rls")
        perms = c.execute(text(
            "SELECT COUNT(*) FROM permission WHERE code LIKE 'product.%'"
        )).scalar()
        print(f"product_permissions={perms}", flush=True)
        if int(perms or 0) < 5:
            fails.append("product_perms")
        orders = c.execute(text("SELECT COUNT(*) FROM production_order")).scalar()
        print(f"orders_intact_count={orders}", flush=True)
    finally:
        c.execute(text(RESTORE))
        c.commit()
        force = c.execute(text(
            "SELECT c.relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname='product_family'"
        )).scalar()
        print(f"product_family_force_restored={force}", flush=True)
e.dispose()

# --- prod untouched ---
e2 = eng("panne/prod/db/migrator", "panne", "panne_prod_migrator")
with e2.connect() as c:
    db = c.execute(text("SELECT current_database()")).scalar()
    print(f"prod_current_database={db}", flush=True)
    fam_p = c.execute(text("SELECT to_regclass('public.product_family')")).scalar()
    print(f"prod_product_family={fam_p}", flush=True)
    has_alembic = c.execute(text(
        "SELECT to_regclass('public.alembic_version')"
    )).scalar()
    print(f"prod_alembic_version_table={has_alembic}", flush=True)
    if fam_p is not None:
        fails.append("prod_has_family")
    if has_alembic:
        head_p = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"prod_panne_head={head_p}", flush=True)
        if head_p == "0021_product_canonical":
            fails.append("prod_at_0021")
    else:
        print("prod_panne_head=none (no alembic_version — not migrated by this pipeline)", flush=True)
e2.dispose()

if fails:
    print(f"VALIDATE_FAIL {fails}", flush=True)
    sys.exit(1)
print("VALIDATE_OK", flush=True)
'''


def main() -> None:
    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    td = ecs.register_task_definition(
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
                "name": "panne-db-migration",
                "image": IMG,
                "essential": True,
                "readonlyRootFilesystem": True,
                "entryPoint": ["python", "-u", "-c"],
                "command": [PROBE],
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
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
                        "awslogs-stream-prefix": "c028c-validate",
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
        startedBy="cursor-028-c-validate",
    )
    if run.get("failures"):
        raise SystemExit(run["failures"])
    task_arn = run["tasks"][0]["taskArn"]
    print("task", task_arn, flush=True)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 40}
    )
    exit_code = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]["containers"][0].get(
        "exitCode"
    )
    tid = task_arn.rsplit("/", 1)[-1]
    prefix = f"c028c-validate/panne-db-migration/{tid}"
    for s in logs.describe_log_streams(
        logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=prefix
    ).get("logStreams") or []:
        for e in logs.get_log_events(
            logGroupName="/ecs/panne/db-migrations",
            logStreamName=s["logStreamName"],
            startFromHead=True,
        ).get("events") or []:
            print(e["message"], flush=True)
    try:
        ecs.deregister_task_definition(taskDefinition=td_arn)
    except Exception:
        pass
    if exit_code != 0:
        raise SystemExit(exit_code or 1)


if __name__ == "__main__":
    main()
