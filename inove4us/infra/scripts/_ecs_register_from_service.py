"""Register Inove ECS task from the service's current TD, new image tag. Sem secrets."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REGION = "us-east-2"
CLUSTER = "inove4us-prod"
SERVICE = "inove4us-prod"
FAMILY = "inove4us-prod"
ACCOUNT = "253137917703"
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
    tag = sys.argv[1] if len(sys.argv) > 1 else "latest"
    image = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/inove4us:{tag}"
    svc = aws_json(["ecs", "describe-services", "--cluster", CLUSTER, "--services", SERVICE])
    current = svc["services"][0]["taskDefinition"]
    td = aws_json(["ecs", "describe-task-definition", "--task-definition", current])["taskDefinition"]
    old_rev = td.get("revision")
    old_image = td["containerDefinitions"][0]["image"]
    for key in list(td):
        if key in DROP:
            td.pop(key)
    ctn = td["containerDefinitions"][0]
    ctn["image"] = image
    env = {e["name"]: e["value"] for e in ctn.get("environment", [])}
    env["GIT_SHA"] = tag
    ctn["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
    out = Path.home() / "AppData" / "Local" / "Temp" / f"inove-td-{tag}.json"
    out.write_text(json.dumps(td), encoding="utf-8")
    registered = aws_json(
        ["ecs", "register-task-definition", "--cli-input-json", f"file://{out}"]
    )["taskDefinition"]
    new_rev = registered["revision"]
    aws_json(
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
    )
    print(
        json.dumps(
            {
                "rollback": f"{FAMILY}:{old_rev}",
                "rollback_image": old_image,
                "new_revision": new_rev,
                "new_image": registered["containerDefinitions"][0]["image"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
