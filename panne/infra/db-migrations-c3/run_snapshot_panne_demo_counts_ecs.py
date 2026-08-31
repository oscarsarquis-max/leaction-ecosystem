"""Roda snapshot_panne_demo_counts via ECS (RDS só na VPC). Read-only."""
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

# Imagem já implantada na demo API (somente para executar Python+SQLAlchemy na VPC).
def current_demo_image() -> str:
    ecs = boto3.client("ecs", region_name=REGION)
    svc = ecs.describe_services(cluster=CLUSTER, services=["panne-demo-api"])["services"][0]
    td_arn = svc["taskDefinition"]
    td = ecs.describe_task_definition(taskDefinition=td_arn)["taskDefinition"]
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
METRICS = [
    ("produtos", "technical_product"),
    ("ingredientes", "ingredient"),
    ("receitas", "formulation"),
    ("ordens", "production_order"),
    ("planos", "production_plan"),
    ("fornecedores", "supplier"),
    ("lotes", "inventory_lot"),
    ("saldos", "inventory_balance"),
    ("movimentos", "inventory_movement"),
    ("entradas_fiscais", "fiscal_inbound_document"),
    ("usuarios_demo", "app_user"),
]
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
    return create_engine(url, connect_args={"sslmode":"require"}), sec["host"].split(".")[0]

def exists(c, name):
    return bool(c.execute(text("SELECT to_regclass(:n)"), {"n": f"public.{name}"}).scalar())

def count_by_org(c, table):
    if not exists(c, table):
        return {"__missing__": 1}
    if table == "app_user":
        q = text("""SELECT om.organization_id::text AS organization_id, COUNT(DISTINCT om.user_id)::int AS n
                    FROM organization_membership om GROUP BY om.organization_id""")
        return {r["organization_id"]: int(r["n"]) for r in c.execute(q).mappings()}
    q = text(f"SELECT organization_id::text AS organization_id, COUNT(*)::int AS n FROM {table} GROUP BY organization_id")
    return {r["organization_id"]: int(r["n"]) for r in c.execute(q).mappings()}

e, host_prefix = eng("panne/demo/db/migrator", "panne_demo", "panne_demo_migrator")
payload = {
  "phase": "pre",
  "captured_at": datetime.now(timezone.utc).isoformat(),
  "database": "panne_demo",
  "username": "panne_demo_migrator",
  "host_sanitized": host_prefix + ".…",
  "read_only": True,
  "organizations": [],
  "totals": {},
  "alembic_head": None,
  "notes": [
    "usuarios_demo = memberships distintas",
    "receitas = formulation",
    "produtos = technical_product",
    "entradas_fiscais = fiscal_inbound_document",
  ],
}
with e.connect() as c:
    c.execute(text(RELAX)); c.commit()
    try:
        payload["alembic_head"] = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
        orgs = [dict(r) for r in c.execute(text(
            "SELECT id::text AS organization_id, slug, display_name FROM organization ORDER BY slug"
        )).mappings()]
        maps = {label: count_by_org(c, table) for label, table in METRICS}
        for org in orgs:
            oid = org["organization_id"]
            counts = {}
            for label, _t in METRICS:
                m = maps[label]
                counts[label] = None if "__missing__" in m else int(m.get(oid, 0))
            payload["organizations"].append({**org, "counts": counts})
        totals = {}
        for label, _t in METRICS:
            m = maps[label]
            totals[label] = None if "__missing__" in m else int(sum(m.values()))
        payload["totals"] = totals
    finally:
        c.execute(text(RESTORE)); c.commit()
e.dispose()

# panne intact proof (schema pode estar pré-migração — não falhar por tabelas ausentes)
e2, host2 = eng("panne/prod/db/migrator", "panne", "panne_prod_migrator")
panne = {"database":"panne","username":"panne_prod_migrator","host_sanitized": host2+".…"}
with e2.connect() as c:
    panne["current_database"] = c.execute(text("SELECT current_database()")).scalar()
    assert panne["current_database"] == "panne"
    panne["alembic_version_table"] = c.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
    if panne["alembic_version_table"]:
        panne["alembic_head"] = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
    else:
        panne["alembic_head"] = None
    panne["organization_table"] = c.execute(text("SELECT to_regclass('public.organization')")).scalar()
    if panne["organization_table"]:
        panne["organization_count"] = int(c.execute(text("SELECT COUNT(*) FROM organization")).scalar() or 0)
    else:
        panne["organization_count"] = None
    panne["technical_product_table"] = c.execute(text("SELECT to_regclass('public.technical_product')")).scalar()
    if panne["technical_product_table"]:
        panne["produtos"] = int(c.execute(text("SELECT COUNT(*) FROM technical_product")).scalar() or 0)
    else:
        panne["produtos"] = None
    panne["note"] = "DB panne intacto = identidade correta; ausência de tabelas = não migrado nesta pipeline (não é redução)"
e2.dispose()

print("SNAPSHOT_JSON_BEGIN", flush=True)
print(json.dumps({"demo": payload, "panne_intact": panne}, ensure_ascii=False), flush=True)
print("SNAPSHOT_JSON_END", flush=True)
print("OK", flush=True)
'''


def main() -> int:
    phase = "pre"
    if len(sys.argv) > 1 and sys.argv[1] in {"pre", "post"}:
        phase = sys.argv[1]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = current_demo_image()
    print(f"phase={phase}", flush=True)
    print(f"ecs_image={img}", flush=True)
    print("mode=read_only via_ecs", flush=True)

    # inject phase into probe
    probe = PROBE.replace('"phase": "pre"', f'"phase": "{phase}"', 1)

    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    prefix = f"c028-release-snap-{phase}"
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
                "image": img,
                "essential": True,
                "readonlyRootFilesystem": True,
                "entryPoint": ["python", "-u", "-c"],
                "command": [probe],
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
        startedBy=f"cursor-028-release-snap-{phase}",
    )
    if run.get("failures"):
        print(run["failures"], flush=True)
        return 1
    task_arn = run["tasks"][0]["taskArn"]
    print(f"task={task_arn}", flush=True)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 50}
    )
    desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
    exit_code = desc["containers"][0].get("exitCode")
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

    blob = None
    capturing = False
    buf: list[str] = []
    for m in messages:
        if m.strip() == "SNAPSHOT_JSON_BEGIN":
            capturing = True
            buf = []
            continue
        if m.strip() == "SNAPSHOT_JSON_END":
            capturing = False
            blob = "".join(buf)
            break
        if capturing:
            buf.append(m)

    if not blob:
        print("ERROR: snapshot JSON missing from logs", flush=True)
        return 2

    data = json.loads(blob)
    demo = data["demo"]
    panne = data["panne_intact"]
    demo_path = OUT_DIR / f"panne-demo-counts-{phase}.json"
    panne_path = OUT_DIR / f"panne-prod-intact-{phase}.json"
    demo_path.write_text(json.dumps(demo, ensure_ascii=False, indent=2), encoding="utf-8")
    panne_path.write_text(json.dumps(panne, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "phase": phase,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "ecs_task": task_arn,
        "ecs_image": img,
        "demo_file": demo_path.name,
        "panne_file": panne_path.name,
        "rule": "após deploy: comparar; redução inesperada → stop + rollback app; sem reseed/truncate",
    }
    (OUT_DIR / f"snapshot-meta-{phase}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote={demo_path.name}", flush=True)
    print(f"demo_head={demo.get('alembic_head')}", flush=True)
    print(f"totals={json.dumps(demo.get('totals'), ensure_ascii=False)}", flush=True)
    print(
        f"panne_intact head={panne.get('alembic_head')} orgs={panne.get('organization_count')} produtos={panne.get('produtos')}",
        flush=True,
    )
    if exit_code != 0:
        return int(exit_code or 1)
    print("OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
