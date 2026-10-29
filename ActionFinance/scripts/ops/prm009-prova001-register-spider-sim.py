"""Point spider-sandbox-backend at the prova001 simulation image. Keep telemetry on."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess

REGION = "us-east-2"
CLUSTER = "spider-sandbox"
FAMILY = "spider-sandbox-backend"
IMAGE = (
    "253137917703.dkr.ecr.us-east-2.amazonaws.com/spider-sandbox-backend@"
    "sha256:51b05e39350327cdfa8fb9d2c5762689ab314abbc598ebab289488cb10a380ea"
)
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
    container["image"] = IMAGE
    upsert_env(container, "SPIDER_TELEMETRY_ENABLED", "true")
    upsert_env(container, "SPIDER_CANONICAL_SIGNAL_HTTP_ENABLED", "true")
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
    path = TMP / "prm009-prova001-spider-sim-td.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    try:
        registered = aws_json(["ecs", "register-task-definition", "--cli-input-json", f"file://{path}"])
    finally:
        path.unlink(missing_ok=True)
    revision = registered["taskDefinition"]["revision"]
    aws_json(
        [
            "ecs",
            "update-service",
            "--cluster",
            CLUSTER,
            "--service",
            FAMILY,
            "--task-definition",
            f"{FAMILY}:{revision}",
            "--force-new-deployment",
        ]
    )
    print(f"registered {FAMILY}:{revision}")
    print("image_digest sha256:51b05e39350327cdfa8fb9d2c5762689ab314abbc598ebab289488cb10a380ea")
    print("telemetry_env=true")
    print("signal_http_env=true")
    print("ram_store_will_reset=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
