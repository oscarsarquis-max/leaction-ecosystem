"""Registra nova task def Inove apontando para a imagem fase0-82. Sem print de secrets."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REGION = "us-east-2"
FAMILY = "inove4us-prod"
IMAGE = "253137917703.dkr.ecr.us-east-2.amazonaws.com/inove4us:fase0-82"
GIT_SHA = "fase0-82"
CLUSTER = "inove4us-prod"
SERVICE = "inove4us-prod"
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
    src_rev = sys.argv[1] if len(sys.argv) > 1 else "28"
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
    ctn["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
    out = Path.home() / "AppData" / "Local" / "Temp" / "inove-td-fase0-82.json"
    out.write_text(json.dumps(td), encoding="utf-8")
    registered = aws_json(
        ["ecs", "register-task-definition", "--cli-input-json", f"file://{out}"]
    )["taskDefinition"]
    new_arn = registered["taskDefinitionArn"]
    new_rev = registered["revision"]
    new_image = registered["containerDefinitions"][0]["image"]
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
                "new_arn": new_arn,
                "new_image": new_image,
                "service_status": svc.get("status"),
                "desired": svc.get("desiredCount"),
                "running": svc.get("runningCount"),
                "env_git_sha": GIT_SHA,
                "wrote_td_json": str(out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
