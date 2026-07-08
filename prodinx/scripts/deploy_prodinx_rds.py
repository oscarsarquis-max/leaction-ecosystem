"""Cria base prodinx no RDS PanelDX (AWS) e restaura dump local via ECS Fargate."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REGION = "us-east-2"
CLUSTER = "paneldx-cluster"
S3_BUCKET = "paneldx-cms-assets-2026"
S3_KEY = "temp/prodinx_rds_dump.sql"
TASK_FAMILY = "prodinx-db-migrate"
DB_HOST = "paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com"
DB_USER = "postgres"
DB_PASS = "Cmgv6190!#$"
SUBNETS = ["subnet-0693afdb3330b683a", "subnet-0a1da7a0765588962"]
SECURITY_GROUPS = ["sg-0b8d724a5cc3b8c4e"]
EXECUTION_ROLE = "arn:aws:iam::253137917703:role/ecsTaskExecutionRole"
TASK_ROLE = "arn:aws:iam::253137917703:role/paneldx-backend-task-role"
LOG_GROUP = "/ecs/paneldx-backend-task"

MIGRATE_SCRIPT = r"""set -e
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl >/dev/null
curl -fsSL -o /tmp/dump.sql "$DUMP_URL"
export PGPASSWORD="$PGPASSWORD"
psql -h "$PGHOST" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 -tc \
  "SELECT 1 FROM pg_database WHERE datname='prodinx'" | grep -q 1 \
  || psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "CREATE DATABASE prodinx"
psql -h "$PGHOST" -U "$PGUSER" -d prodinx -v ON_ERROR_STOP=1 -f /tmp/dump.sql
psql -h "$PGHOST" -U "$PGUSER" -d prodinx -c \
  "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;"
echo MIGRATION_OK
"""


def aws(*args: str, capture: bool = True) -> str:
    cmd = ["aws", *args, "--region", REGION]
    result = subprocess.run(cmd, capture_output=capture, text=True, check=False)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"aws {' '.join(args)} failed: {err}")
    return (result.stdout or "").strip()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    dump = repo / "banco_de_dados" / "prodinx_rds_dump.sql"
    if not dump.exists():
        raise FileNotFoundError(f"Dump nao encontrado: {dump}")

    print("==> Upload S3")
    aws("s3", "cp", str(dump), f"s3://{S3_BUCKET}/{S3_KEY}")
    presign = aws(
        "s3", "presign", f"s3://{S3_BUCKET}/{S3_KEY}", "--expires-in", "7200"
    )

    task_def = {
        "family": TASK_FAMILY,
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": "512",
        "memory": "1024",
        "executionRoleArn": EXECUTION_ROLE,
        "taskRoleArn": TASK_ROLE,
        "containerDefinitions": [
            {
                "name": "migrate",
                "image": "postgres:17",
                "essential": True,
                "environment": [
                    {"name": "PGHOST", "value": DB_HOST},
                    {"name": "PGUSER", "value": DB_USER},
                    {"name": "PGPASSWORD", "value": DB_PASS},
                    {"name": "PGSSLMODE", "value": "require"},
                    {"name": "DUMP_URL", "value": presign},
                ],
                "command": ["sh", "-c", MIGRATE_SCRIPT],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": LOG_GROUP,
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "prodinx-migrate",
                    },
                },
            }
        ],
    }

    task_def_path = repo / "scripts" / ".prodinx-task-def.json"
    task_def_path.write_text(json.dumps(task_def), encoding="utf-8")

    print("==> Register task definition")
    task_def_arn = aws(
        "ecs",
        "register-task-definition",
        "--cli-input-json",
        f"file://{task_def_path.as_posix()}",
        "--query",
        "taskDefinition.taskDefinitionArn",
        "--output",
        "text",
    )

    run_task = {
        "cluster": CLUSTER,
        "launchType": "FARGATE",
        "taskDefinition": task_def_arn,
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": SUBNETS,
                "securityGroups": SECURITY_GROUPS,
                "assignPublicIp": "DISABLED",
            }
        },
    }
    run_path = repo / "scripts" / ".prodinx-run-task.json"
    run_path.write_text(json.dumps(run_task), encoding="utf-8")

    print("==> Run migration task")
    task_arn = aws(
        "ecs",
        "run-task",
        "--cli-input-json",
        f"file://{run_path.as_posix()}",
        "--query",
        "tasks[0].taskArn",
        "--output",
        "text",
    )
    print(f"Task: {task_arn}")

    print("==> Aguardando conclusao...")
    for _ in range(60):
        detail = aws(
            "ecs",
            "describe-tasks",
            "--cluster",
            CLUSTER,
            "--tasks",
            task_arn,
            "--query",
            "tasks[0].{status:lastStatus,stop:stoppedReason,exit:containers[0].exitCode}",
            "--output",
            "json",
        )
        info = json.loads(detail)
        status = info.get("status")
        print(f"  status={status}")
        if status == "STOPPED":
            exit_code = info.get("exit")
            if exit_code == 0:
                print("==> Migracao concluida com sucesso.")
                return 0
            raise RuntimeError(f"Task falhou: {info}")
        time.sleep(15)

    raise RuntimeError("Timeout aguardando task ECS")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
