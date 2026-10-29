"""ECS one-shot: print alembic heads for panne_demo (+ optional panne via prod migrator not used).
Demo migrator only. Never prints secrets.
"""
from __future__ import annotations

import json
import time

import boto3

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
DIGEST = "sha256:f9405c5d444af1052aee758488111561247a21241c3bcada7540301827266ac6"
IMG = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{DIGEST}"
EXEC_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role"
SUBNETS = ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"]
SG_DEMO = "sg-0f41648d1720bca80"

# Inline probe — uses migrator secret, prints only db+version
PROBE = r"""
import json, os
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
sm = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"])
sec = json.loads(sm.get_secret_value(SecretId=os.environ["PANNE_MIGRATOR_SECRET_ID"])["SecretString"])
assert sec["dbname"] == "panne_demo" and sec["username"] == "panne_demo_migrator"
url = URL.create("postgresql+psycopg", username=sec["username"], password=sec["password"],
                 host=sec["host"], port=int(sec["port"]), database=sec["dbname"])
eng = create_engine(url, connect_args={"sslmode":"require"})
with eng.connect() as c:
    rows = [r[0] for r in c.execute(text("SELECT version_num FROM alembic_version")).fetchall()]
    print(f"PROBE_OK db=panne_demo versions={rows}", flush=True)
eng.dispose()
"""


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
                    {"name": "PANNE_MIGRATOR_SECRET_ID", "value": "panne/demo/db/migrator"},
                    {"name": "PANNE_PG_SSLMODE", "value": "require"},
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
                        "awslogs-stream-prefix": "c028c-probe",
                    },
                },
            }
        ],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
    print("td", td_arn, flush=True)
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
        startedBy="cursor-028-c-probe",
    )
    if run.get("failures"):
        raise SystemExit(f"failures={run['failures']}")
    task_arn = run["tasks"][0]["taskArn"]
    print("task", task_arn, flush=True)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task_arn], WaiterConfig={"Delay": 6, "MaxAttempts": 40}
    )
    desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
    exit_code = desc["containers"][0].get("exitCode")
    print("exit", exit_code, flush=True)
    # fetch logs
    tid = task_arn.rsplit("/", 1)[-1]
    prefix = f"c028c-probe/panne-db-migration/{tid}"
    streams = logs.describe_log_streams(
        logGroupName="/ecs/panne/db-migrations", logStreamNamePrefix=prefix
    ).get("logStreams") or []
    for s in streams:
        ev = logs.get_log_events(
            logGroupName="/ecs/panne/db-migrations", logStreamName=s["logStreamName"], startFromHead=True
        )
        for e in ev.get("events") or []:
            print(e["message"], flush=True)
    try:
        ecs.deregister_task_definition(taskDefinition=td_arn)
    except Exception:
        pass
    if exit_code != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
