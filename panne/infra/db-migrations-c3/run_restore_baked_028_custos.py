"""Run baked restore image against AWS panne_demo."""
from __future__ import annotations

import boto3

REGION = "us-east-2"
ACCOUNT = "253137917703"
CLUSTER = "paneldx-cluster"
FAMILY = "panne-db-migration"
IMG = "253137917703.dkr.ecr.us-east-2.amazonaws.com/panne/backend@sha256:884f00eed22e0d5062e9f1da031009f07d43ece52e7ad857b5265f132eb3a92a"


def main() -> int:
    ecs = boto3.client("ecs", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)
    prefix = "c028-restore-baked"
    td = ecs.register_task_definition(
        family=FAMILY,
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="1024",
        memory="2048",
        executionRoleArn=f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role",
        taskRoleArn=f"arn:aws:iam::{ACCOUNT}:role/panne-db-migration-task-role",
        runtimePlatform={"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"},
        containerDefinitions=[
            {
                "name": "panne-db-migration",
                "image": IMG,
                "essential": True,
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
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
    print("TD", td_arn)
    run = ecs.run_task(
        cluster=CLUSTER,
        taskDefinition=td_arn,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": ["subnet-0a1da7a0765588962", "subnet-0693afdb3330b683a"],
                "securityGroups": ["sg-0f41648d1720bca80"],
                "assignPublicIp": "DISABLED",
            }
        },
        startedBy="cursor-028-custos-restore-baked",
    )
    if run.get("failures"):
        print(run["failures"])
        return 1
    task = run["tasks"][0]["taskArn"]
    print("task", task)
    ecs.get_waiter("tasks_stopped").wait(
        cluster=CLUSTER, tasks=[task], WaiterConfig={"Delay": 10, "MaxAttempts": 120}
    )
    desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task])["tasks"][0]
    print("exit", desc["containers"][0].get("exitCode"))
    tid = task.rsplit("/", 1)[-1]
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
