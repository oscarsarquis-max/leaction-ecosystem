"""Enable Spider sandbox telemetry on the running family. No secret values printed."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess

REGION = "us-east-2"
CLUSTER = "spider-sandbox"
FAMILY = "spider-sandbox-backend"
SERVICE = "spider-sandbox-backend"
TMP = pathlib.Path(os.environ["TEMP"])


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def upsert_env(container: dict, name: str, value: str) -> None:
    env = container.setdefault("environment", [])
    for item in env:
        if item["name"] == name:
            item["value"] = value
            return
    env.append({"name": name, "value": value})


def main() -> int:
    td = aws_json(["ecs", "describe-task-definition", "--task-definition", FAMILY])["taskDefinition"]
    container = td["containerDefinitions"][0]
    upsert_env(container, "SPIDER_TELEMETRY_ENABLED", "true")
    keep = (
        "family",
        "taskRoleArn",
        "executionRoleArn",
        "networkMode",
        "containerDefinitions",
        "volumes",
        "placementConstraints",
        "requiresCompatibilities",
        "cpu",
        "memory",
        "runtimePlatform",
    )
    body = {key: td[key] for key in keep if key in td}
    path = TMP / "prm009-prova001-spider-td.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    try:
        registered = aws_json(
            ["ecs", "register-task-definition", "--cli-input-json", f"file://{path}"]
        )
    finally:
        if path.exists():
            path.unlink()
    revision = registered["taskDefinition"]["revision"]
    aws_json(
        [
            "ecs",
            "update-service",
            "--cluster",
            CLUSTER,
            "--service",
            SERVICE,
            "--task-definition",
            f"{FAMILY}:{revision}",
            "--force-new-deployment",
        ]
    )
    print(f"registered {FAMILY}:{revision}")
    print("telemetry_env=true")
    print("service_updated=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
