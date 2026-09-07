"""Task def :30 — Bedrock Sonnet 4.6 (desbloqueia 🧩 adaptar-pei). Sem print de secrets."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REGION = "us-east-2"
FAMILY = "inove4us-prod"
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
MODEL = "us.anthropic.claude-sonnet-4-6"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    return json.loads(raw)


def main() -> int:
    td = aws_json(["ecs", "describe-task-definition", "--task-definition", f"{FAMILY}:29"])[
        "taskDefinition"
    ]
    for key in list(td):
        if key in DROP:
            td.pop(key)
    ctn = td["containerDefinitions"][0]
    env = {e["name"]: e["value"] for e in ctn.get("environment", [])}
    env["BEDROCK_MODEL_ID"] = MODEL
    env["PEI_BEDROCK_MODEL_ID"] = MODEL
    env["BEDROCK_REGION"] = env.get("AWS_REGION") or "us-east-2"
    ctn["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
    out = Path.home() / "AppData" / "Local" / "Temp" / "inove-td-fase0-82-bedrock.json"
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
            "inove4us-prod",
            "--service",
            "inove4us-prod",
            "--task-definition",
            f"{FAMILY}:{new_rev}",
            "--force-new-deployment",
        ]
    )["service"]
    print(
        json.dumps(
            {
                "new_revision": new_rev,
                "image": registered["containerDefinitions"][0]["image"],
                "bedrock_model": MODEL,
                "desired": svc.get("desiredCount"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
