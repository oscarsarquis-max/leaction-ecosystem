"""Garante EventBridge 03:00 America/Sao_Paulo (06:00 UTC) → ECS RunTask do snapshot Inove.

Atualiza o target para a task definition **atual** do serviço (evita tag pinada).
Idempotente. Sem secrets no stdout.
"""

from __future__ import annotations

import json
import subprocess
import sys

REGION = "us-east-2"
CLUSTER = "inove4us-prod"
SERVICE = "inove4us-prod"
CONTAINER = "inove4us"
RULE = "inove4us-prod-conta-snapshot"
ROLE_NAME = "inove4us-prod-snapshot-events"
ACCOUNT = "253137917703"
# 03:00 America/Sao_Paulo = 06:00 UTC (Brasil sem horário de verão).
SCHEDULE = "cron(0 6 * * ? *)"


def aws_json(args: list[str]):
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    return json.loads(raw)


def aws_ok(args: list[str]) -> None:
    subprocess.check_call(["aws", *args, "--region", REGION, "--output", "json"])


def ensure_role() -> str:
    role_arn = f"arn:aws:iam::{ACCOUNT}:role/{ROLE_NAME}"
    try:
        aws_json(["iam", "get-role", "--role-name", ROLE_NAME])
    except subprocess.CalledProcessError:
        assume = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "events.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        aws_json(
            [
                "iam",
                "create-role",
                "--role-name",
                ROLE_NAME,
                "--assume-role-policy-document",
                json.dumps(assume),
            ]
        )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ecs:RunTask"],
                "Resource": f"arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/{CLUSTER}*",
                "Condition": {
                    "ArnEquals": {
                        "ecs:cluster": f"arn:aws:ecs:{REGION}:{ACCOUNT}:cluster/{CLUSTER}"
                    }
                },
            },
            {
                "Effect": "Allow",
                "Action": ["iam:PassRole"],
                "Resource": [
                    f"arn:aws:iam::{ACCOUNT}:role/inove4us-prod-ecs-exec",
                    f"arn:aws:iam::{ACCOUNT}:role/inove4us-prod-ecs-task",
                ],
            },
        ],
    }
    aws_ok(
        [
            "iam",
            "put-role-policy",
            "--role-name",
            ROLE_NAME,
            "--policy-name",
            "ecs-runtask-snapshot",
            "--policy-document",
            json.dumps(policy),
        ]
    )
    return role_arn


def main() -> int:
    svc = aws_json(["ecs", "describe-services", "--cluster", CLUSTER, "--services", SERVICE])
    service = svc["services"][0]
    task_def = service["taskDefinition"]
    net = service["networkConfiguration"]["awsvpcConfiguration"]
    cluster_arn = service["clusterArn"]
    role_arn = ensure_role()

    aws_json(
        [
            "events",
            "put-rule",
            "--name",
            RULE,
            "--schedule-expression",
            SCHEDULE,
            "--state",
            "ENABLED",
            "--description",
            "Sponge: snapshot diário inove4us (03:00 America/Sao_Paulo)",
        ]
    )

    target = {
        "Id": "ecs-snapshot",
        "Arn": cluster_arn,
        "RoleArn": role_arn,
        "EcsParameters": {
            "TaskDefinitionArn": task_def,
            "TaskCount": 1,
            "LaunchType": "FARGATE",
            "NetworkConfiguration": {
                "awsvpcConfiguration": {
                    "Subnets": net["subnets"],
                    "SecurityGroups": net.get("securityGroups") or [],
                    "AssignPublicIp": net.get("assignPublicIp") or "DISABLED",
                }
            },
        },
        "Input": json.dumps(
            {
                "containerOverrides": [
                    {
                        "name": CONTAINER,
                        "command": ["python", "snapshot_conta.py"],
                    }
                ]
            }
        ),
    }
    aws_json(
        [
            "events",
            "put-targets",
            "--rule",
            RULE,
            "--targets",
            json.dumps([target]),
        ]
    )
    print(
        json.dumps(
            {
                "ok": True,
                "rule": RULE,
                "schedule": SCHEDULE,
                "tz": "America/Sao_Paulo 03:00 = UTC 06:00",
                "task_definition": task_def,
                "command": ["python", "snapshot_conta.py"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
