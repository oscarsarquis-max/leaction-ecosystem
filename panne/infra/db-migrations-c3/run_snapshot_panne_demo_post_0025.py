"""Read-only post-0025 photo: head, RLS/FORCE, counts, policies, A-D sale basis."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"
OUT_DIR = Path(__file__).resolve().parents[2] / "documentacao" / "evidencias" / "cursor-028-release"

PROBE = r'''
import json
from datetime import datetime, timezone
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

REGION = "us-east-2"
RELAX = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel FROM pg_class c
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
    SELECT c.relname AS rel FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""

def eng(secret_id, expect_db, expect_user):
    sm = boto3.client("secretsmanager", region_name=REGION)
    sec = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    assert sec["dbname"] == expect_db and sec["username"] == expect_user
    url = URL.create("postgresql+psycopg", username=sec["username"], password=sec["password"],
                     host=sec["host"], port=int(sec["port"]), database=sec["dbname"])
    return create_engine(url, connect_args={"sslmode":"require"})

e = eng("panne/demo/db/migrator", "panne_demo", "panne_demo_migrator")
payload = {"captured_at": datetime.now(timezone.utc).isoformat(), "database": "panne_demo", "read_only": True}
with e.connect() as c:
    c.execute(text(RELAX)); c.commit()
    try:
        payload["alembic_head"] = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
        payload["current_database"] = c.execute(text("SELECT current_database()")).scalar()
        rls = [dict(r) for r in c.execute(text("""
            SELECT c.relname AS table,
                   c.relrowsecurity AS rls,
                   c.relforcerowsecurity AS force_rls
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r'
              AND c.relname IN (
                'practiced_price','pricing_markup_policy','pricing_economic_audit',
                'technical_product','organization'
              )
            ORDER BY 1
        """)).mappings()]
        payload["rls"] = rls
        payload["counts"] = [dict(r) for r in c.execute(text("""
            SELECT o.slug,
              (SELECT count(*) FROM technical_product tp WHERE tp.organization_id=o.id) AS produtos,
              (SELECT count(*) FROM ingredient i WHERE i.organization_id=o.id) AS ingredientes,
              (SELECT count(*) FROM formulation f WHERE f.organization_id=o.id) AS receitas,
              (SELECT count(*) FROM production_order po WHERE po.organization_id=o.id) AS ordens,
              (SELECT count(*) FROM supplier s WHERE s.organization_id=o.id) AS fornecedores,
              (SELECT count(*) FROM supplier_item_price sip
                 JOIN supplier_item si ON si.id=sip.supplier_item_id
                WHERE si.organization_id=o.id) AS precos_compra,
              (SELECT count(*) FROM costing_calculation cc WHERE cc.organization_id=o.id) AS calculos,
              (SELECT count(*) FROM practiced_price pp WHERE pp.organization_id=o.id) AS precos_venda,
              (SELECT count(*) FROM pricing_markup_policy p WHERE p.organization_id=o.id) AS politicas
            FROM organization o ORDER BY slug
        """)).mappings()]
        payload["ad_prices"] = [dict(r) for r in c.execute(text("""
            SELECT tp.code, pp.amount::text, pp.status, pp.sale_basis_quantity::text,
                   pp.valid_from::text, pp.valid_to::text
            FROM practiced_price pp
            JOIN technical_product tp ON tp.id=pp.technical_product_id
            JOIN organization o ON o.id=pp.organization_id
            WHERE o.slug='panne-demonstracao'
              AND tp.code IN ('PAO-FR','PAO-INT','MANTEIGA-PT','FOCACCIA')
            ORDER BY tp.code, pp.valid_from
        """)).mappings()]
        payload["policies"] = [dict(r) for r in c.execute(text("""
            SELECT p.code, p.kind, p.value::text, p.scope_level, p.status, o.slug
            FROM pricing_markup_policy p
            JOIN organization o ON o.id=p.organization_id
            ORDER BY o.slug, p.code
        """)).mappings()]
    finally:
        c.execute(text(RESTORE)); c.commit()
e.dispose()

e2 = eng("panne/prod/db/migrator", "panne", "panne_prod_migrator")
panne = {"database": "panne"}
with e2.connect() as c:
    panne["current_database"] = c.execute(text("SELECT current_database()")).scalar()
    assert panne["current_database"] == "panne"
    panne["alembic_version_table"] = c.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
    panne["organization_table"] = c.execute(text("SELECT to_regclass('public.organization')")).scalar()
e2.dispose()

print("SNAPSHOT_JSON_BEGIN", flush=True)
print(json.dumps({"demo": payload, "panne_intact": panne}, ensure_ascii=False, default=str), flush=True)
print("SNAPSHOT_JSON_END", flush=True)
print("OK", flush=True)
'''


def current_demo_image() -> str:
    digest = __import__("os").environ.get("PANNE_IMAGE_DIGEST", "")
    if digest.startswith("sha256:"):
        return f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{digest}"
    ecs = boto3.client("ecs", region_name=REGION)
    svc = ecs.describe_services(cluster=CLUSTER, services=["panne-demo-api"])["services"][0]
    td = ecs.describe_task_definition(taskDefinition=svc["taskDefinition"])["taskDefinition"]
    for c in td["containerDefinitions"]:
        if c.get("name") == "panne-demo-api":
            return str(c["image"])
    raise SystemExit("demo image not found")


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "post"
    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    image = current_demo_image()
    prefix = f"c028-post0025-{phase}"
    print(f"phase={phase}", flush=True)
    print(f"ecs_image={image}", flush=True)
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
                "image": image,
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
        startedBy=f"cursor-028-post0025-{phase}",
    )
    if run.get("failures"):
        print(run["failures"], flush=True)
        return 1
    task_arn = run["tasks"][0]["taskArn"]
    print("task", task_arn, flush=True)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 50}
    )
    tid = task_arn.rsplit("/", 1)[-1]
    stream_prefix = f"{prefix}/panne-db-migration/{tid}"
    messages: list[str] = []
    for s in logs.describe_log_streams(
        logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=stream_prefix
    ).get("logStreams") or []:
        for e in logs.get_log_events(
            logGroupName="/ecs/panne/db-migrations",
            logStreamName=s["logStreamName"],
            startFromHead=True,
        ).get("events") or []:
            messages.append(e["message"])
            print(e["message"], flush=True)
    try:
        ecs.deregister_task_definition(taskDefinition=td_arn)
    except Exception:
        pass
    text_out = "\n".join(messages)
    begin = text_out.find("SNAPSHOT_JSON_BEGIN")
    end = text_out.find("SNAPSHOT_JSON_END")
    if begin < 0 or end <= begin:
        print("ERROR: snapshot JSON missing", flush=True)
        return 2
    raw = text_out[begin + len("SNAPSHOT_JSON_BEGIN") : end].strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"panne-demo-post0025-{phase}.json"
    out.write_text(raw + "\n", encoding="utf-8")
    print("wrote", out.name, flush=True)
    data = json.loads(raw)
    demo = data["demo"]
    print("head", demo.get("alembic_head"), flush=True)
    print("counts", json.dumps(demo.get("counts"), ensure_ascii=False), flush=True)
    print("policies", json.dumps(demo.get("policies"), ensure_ascii=False), flush=True)
    print("panne_intact", json.dumps(data.get("panne_intact"), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
