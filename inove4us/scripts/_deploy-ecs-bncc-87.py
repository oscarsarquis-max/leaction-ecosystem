"""Deploy Inove ECS with BNCC seletor (git 6b548ad+). Sem print de secrets.

Uso (depois do docker push da tag = git SHA):
  python scripts/_deploy-ecs-bncc-87.py
  python scripts/_deploy-ecs-bncc-87.py 30
  python scripts/_deploy-ecs-bncc-87.py 30 abc1234
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REGION = "us-east-2"
FAMILY = "inove4us-prod"
GIT_SHA = (
    sys.argv[2]
    if len(sys.argv) > 2
    else subprocess.check_output(["git", "-C", r"C:\Projetos", "rev-parse", "--short", "HEAD"], text=True).strip()
)
IMAGE = f"253137917703.dkr.ecr.us-east-2.amazonaws.com/inove4us:{GIT_SHA}"
CLUSTER = "inove4us-prod"
SERVICE = "inove4us-prod"
SCHOOL_API = "https://school.inove4us.com.br"
SCHOOL_WEBHOOK = "https://school.inove4us.com.br/api/webhooks/b2c"
DROP = {
    "status",
    "revision",
    "taskDefinitionArn",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "deregisteredAt",
}


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    return json.loads(raw)


def main() -> int:
    src_rev = sys.argv[1] if len(sys.argv) > 1 else "30"
    td = aws_json(["ecs", "describe-task-definition", "--task-definition", f"{FAMILY}:{src_rev}"])[
        "taskDefinition"
    ]
    old_image = td["containerDefinitions"][0]["image"]
    old_rev = td.get("revision")
    for key in list(td):
        if key in DROP:
            td.pop(key)
    ctn = td["containerDefinitions"][0]
    ctn["image"] = IMAGE
    env = {e["name"]: e["value"] for e in ctn.get("environment", [])}
    env["GIT_SHA"] = GIT_SHA
    env["INOVE4US_SCHOOL_API_URL"] = SCHOOL_API
    env["INOVE4US_SCHOOL_WEBHOOK_URL"] = SCHOOL_WEBHOOK
    env["INOVE_DAILY_SCHEMA_ENSURE"] = "1"
    ctn["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
    out = Path.home() / "AppData" / "Local" / "Temp" / "inove-td-bncc-87.json"
    out.write_text(json.dumps(td), encoding="utf-8")
    registered = aws_json(
        ["ecs", "register-task-definition", "--cli-input-json", f"file://{out}"]
    )["taskDefinition"]
    new_rev = registered["revision"]
    svc = aws_json(
        [
            "ecs",
            "update-service",
            "--cluster",
            CLUSTER,
            "--service",
            SERVICE,
            "--task-definition",
            f"{FAMILY}:{new_rev}",
            "--force-new-deployment",
        ]
    )["service"]
    print(
        json.dumps(
            {
                "rollback_taskdef": f"{FAMILY}:{old_rev}",
                "rollback_image": old_image,
                "new_revision": new_rev,
                "new_image": registered["containerDefinitions"][0]["image"],
                "env_git_sha": GIT_SHA,
                "school_api": SCHOOL_API,
                "desired": svc.get("desiredCount"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
