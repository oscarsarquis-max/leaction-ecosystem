"""Read-only FORCE RLS proof without relaxing policies."""
from __future__ import annotations

import os

import boto3

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"

PROBE = r'''
import json, boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
sm = boto3.client("secretsmanager", region_name="us-east-2")
sec = json.loads(sm.get_secret_value(SecretId="panne/demo/db/migrator")["SecretString"])
assert sec["dbname"] == "panne_demo" and sec["username"] == "panne_demo_migrator"
url = URL.create("postgresql+psycopg", username=sec["username"], password=sec["password"],
                 host=sec["host"], port=int(sec["port"]), database=sec["dbname"])
e = create_engine(url, connect_args={"sslmode":"require"})
with e.connect() as c:
    rows = [dict(r) for r in c.execute(text("""
        SELECT c.relname AS table, c.relrowsecurity AS rls, c.relforcerowsecurity AS force_rls
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind='r'
          AND c.relname IN (
            'practiced_price','pricing_markup_policy','pricing_economic_audit',
            'technical_product','organization'
          )
        ORDER BY 1
    """)).mappings()]
    forced = [r["table"] for r in rows if r["rls"] and r["force_rls"]]
    unforced = [r["table"] for r in rows if r["rls"] and not r["force_rls"]]
print("FORCE_JSON", json.dumps({"rows": rows, "forced": forced, "unforced": unforced}), flush=True)
print("OK" if not unforced else "FORCE_GAP", flush=True)
e.dispose()
'''


def main() -> int:
    digest = os.environ["PANNE_IMAGE_DIGEST"]
    image = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{digest}"
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
        containerDefinitions=[{
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
            "linuxParameters": {"tmpfs": [{"containerPath": "/tmp", "size": 64, "mountOptions": ["rw", "noexec", "nosuid", "nodev"]}]},
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {"awslogs-group": "/ecs/panne/db-migrations", "awslogs-region": REGION, "awslogs-stream-prefix": "c028-force"},
            },
        }],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
    run = ecs.run_task(
        cluster=CLUSTER,
        taskDefinition=td_arn,
        launchType="FARGATE",
        networkConfiguration={"awsvpcConfiguration": {"subnets": SUBNETS, "securityGroups": [SG_DEMO], "assignPublicIp": "DISABLED"}},
        startedBy="cursor-028-force",
    )
    if run.get("failures"):
        print(run["failures"])
        return 1
    task_arn = run["tasks"][0]["taskArn"]
    ecs.get_waiter("tasks_stopped").wait(cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 40})
    tid = task_arn.rsplit("/", 1)[-1]
    for s in logs.describe_log_streams(logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=f"c028-force/panne-db-migration/{tid}").get("logStreams") or []:
        for e in logs.get_log_events(logGroupName="/ecs/panne/db-migrations", logStreamName=s["logStreamName"], startFromHead=True).get("events") or []:
            print(e["message"], flush=True)
    try:
        ecs.deregister_task_definition(taskDefinition=td_arn)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
