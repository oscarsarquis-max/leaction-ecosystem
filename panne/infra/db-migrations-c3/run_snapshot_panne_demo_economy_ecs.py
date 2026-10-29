"""Read-only economic counts on AWS panne_demo via ECS (no schema/data writes)."""
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


def current_demo_image() -> str:
    ecs = boto3.client("ecs", region_name=REGION)
    svc = ecs.describe_services(cluster=CLUSTER, services=["panne-demo-api"])["services"][0]
    td = ecs.describe_task_definition(taskDefinition=svc["taskDefinition"])["taskDefinition"]
    for c in td["containerDefinitions"]:
        if c.get("name") == "panne-demo-api":
            return str(c["image"])
    raise SystemExit("demo image not found")


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

sm = boto3.client("secretsmanager", region_name=REGION)
sec = json.loads(sm.get_secret_value(SecretId="panne/demo/db/migrator")["SecretString"])
assert sec["dbname"] == "panne_demo" and sec["username"] == "panne_demo_migrator"
url = URL.create(
    "postgresql+psycopg",
    username=sec["username"],
    password=sec["password"],
    host=sec["host"],
    port=int(sec["port"]),
    database=sec["dbname"],
)
e = create_engine(url, connect_args={"sslmode": "require"})
payload = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "database": "panne_demo",
    "read_only": True,
}
with e.connect() as c:
    c.execute(text(RELAX)); c.commit()
    try:
        rows = c.execute(text("""
            SELECT o.slug,
              (SELECT count(*) FROM technical_product tp WHERE tp.organization_id=o.id) AS produtos,
              (SELECT count(*) FROM ingredient i WHERE i.organization_id=o.id) AS ingredientes,
              (SELECT count(*) FROM supplier s WHERE s.organization_id=o.id) AS fornecedores,
              (SELECT count(*) FROM supplier_item si WHERE si.organization_id=o.id) AS skus,
              (SELECT count(*) FROM supplier_item_price sip
                 JOIN supplier_item si ON si.id=sip.supplier_item_id
                WHERE si.organization_id=o.id) AS precos_compra,
              (SELECT count(*) FROM formulation f WHERE f.organization_id=o.id) AS receitas,
              (SELECT count(*) FROM production_order po WHERE po.organization_id=o.id) AS ordens,
              (SELECT count(*) FROM costing_calculation cc WHERE cc.organization_id=o.id) AS calculos,
              (SELECT count(*) FROM practiced_price pp WHERE pp.organization_id=o.id) AS precos_venda
            FROM organization o ORDER BY slug
        """)).mappings().all()
        payload["counts"] = [dict(r) for r in rows]
        codes = c.execute(text("""
            SELECT code FROM technical_product tp
            JOIN organization o ON o.id=tp.organization_id
            WHERE o.slug='panne-demonstracao'
            ORDER BY code
        """)).scalars().all()
        payload["product_codes"] = list(codes)
        calc_codes = c.execute(text("""
            SELECT DISTINCT tp.code
            FROM costing_calculation cc
            LEFT JOIN technical_product tp ON tp.id=cc.technical_product_id
            JOIN organization o ON o.id=cc.organization_id
            WHERE o.slug='panne-demonstracao'
            ORDER BY 1
        """)).scalars().all()
        payload["calc_product_codes"] = list(calc_codes)
    finally:
        c.execute(text(RESTORE)); c.commit()
e.dispose()
print("SNAPSHOT_JSON_BEGIN", flush=True)
print(json.dumps(payload, ensure_ascii=False, default=str), flush=True)
print("SNAPSHOT_JSON_END", flush=True)
print("OK", flush=True)
'''


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "pre"
    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    image = current_demo_image()
    prefix = f"c028-economy-{phase}"
    print(f"phase={phase}")
    print(f"ecs_image={image}")
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
        startedBy=f"cursor-028-economy-{phase}",
    )
    if run.get("failures"):
        print(run["failures"])
        return 1
    task_arn = run["tasks"][0]["taskArn"]
    print("task", task_arn)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 50}
    )
    desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
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
            print(e["message"])
    try:
        ecs.deregister_task_definition(taskDefinition=td_arn)
    except Exception:
        pass
    text_out = "\n".join(messages)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"panne-demo-economy-{phase}.json"
    begin = text_out.find("SNAPSHOT_JSON_BEGIN")
    end = text_out.find("SNAPSHOT_JSON_END")
    if begin >= 0 and end > begin:
        raw = text_out[begin + len("SNAPSHOT_JSON_BEGIN") : end].strip()
        out.write_text(raw + "\n", encoding="utf-8")
        # also copy into release-028 evidence
        alt = Path(r"C:\Projetos\_release-028\panne\documentacao\evidencias\cursor-028-custos-publish")
        alt.mkdir(parents=True, exist_ok=True)
        (alt / out.name).write_text(raw + "\n", encoding="utf-8")
        print("wrote", out.name)
        print(raw)
        return 0
    print("exit", desc.get("containers", [{}])[0].get("exitCode"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
