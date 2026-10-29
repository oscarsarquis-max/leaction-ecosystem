"""Register AF/Spider task definitions with new images. Does not print secret values."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REGION = "us-east-2"
ACCOUNT = "253137917703"
TMP = pathlib.Path(os.environ["TEMP"])
AF_IMAGE = os.environ.get(
    "PRM009_AF_IMAGE",
    f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/actionfinance@"
    "sha256:77ef03baf8b7875a360b8a45eae9c73b32ce2526a6d32a3f9ef0ce5e5b8d9a35",
)
SPIDER_IMAGE = os.environ.get("PRM009_SPIDER_IMAGE", "")
LOJA = "624023a4-57e3-415c-b7d0-925ca1acd3b7"
PADARIA = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c"


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    return json.loads(text)


def describe(family: str) -> dict:
    return aws_json(["ecs", "describe-task-definition", "--task-definition", family])["taskDefinition"]


def register(family: str, payload: dict) -> int:
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
    body = {key: payload[key] for key in keep if key in payload}
    path = TMP / f"prm009-reg-{family}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    try:
        result = aws_json(["ecs", "register-task-definition", "--cli-input-json", f"file://{path}"])
    finally:
        if path.exists():
            path.unlink()
    revision = result["taskDefinition"]["revision"]
    print(f"registered {family}:{revision}")
    return revision


def upsert_env(container: dict, name: str, value: str) -> None:
    env = container.setdefault("environment", [])
    for item in env:
        if item["name"] == name:
            item["value"] = value
            return
    env.append({"name": name, "value": value})


def main() -> int:
    if not SPIDER_IMAGE:
        print("missing PRM009_SPIDER_IMAGE", file=sys.stderr)
        return 2
    web = describe("actionfinance-web")
    migrate = describe("actionfinance-migrate")
    spider = describe("spider-sandbox-backend")

    web_c = web["containerDefinitions"][0]
    web_c["image"] = AF_IMAGE
    upsert_env(web_c, "ACTIONFINANCE_RECEIPT_SYNC_ENABLED", "true")
    upsert_env(web_c, "ACTIONFINANCE_INTEGRATION_HOMOLOG", "false")
    upsert_env(web_c, "ACTIONFINANCE_DEMO_AUTH_ENABLED", "false")
    upsert_env(web_c, "ACTIONFINANCE_FLYWAY_ENABLED", "false")

    mig_c = migrate["containerDefinitions"][0]
    mig_c["image"] = AF_IMAGE
    upsert_env(mig_c, "ACTIONFINANCE_FLYWAY_ENABLED", "true")
    upsert_env(mig_c, "ACTIONFINANCE_RECEIPT_SYNC_ENABLED", "false")

    spider_c = spider["containerDefinitions"][0]
    spider_c["image"] = SPIDER_IMAGE
    upsert_env(spider_c, "SPIDER_MONITOR_ALLOWED_COMPANIES", f"{PADARIA},{LOJA}")
    upsert_env(spider_c, "SPIDER_ACTIONHUB_PAY_EDGE_URL", "https://api.actionhub.com.br")
    upsert_env(spider_c, "SPIDER_TELEMETRY_ENABLED", "true")

    register("actionfinance-web", web)
    register("actionfinance-migrate", migrate)
    register("spider-sandbox-backend", spider)
    print("af_image_digest sha256:77ef03baf8b7875a360b8a45eae9c73b32ce2526a6d32a3f9ef0ce5e5b8d9a35")
    print("spider_image_set 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
