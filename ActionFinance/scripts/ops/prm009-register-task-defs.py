"""Register PRM_009 task definitions. Does not print secret values."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REGION = "us-east-2"
ACCOUNT = "253137917703"
TMP = pathlib.Path(os.environ["TEMP"])
AF_IMAGE = (
    f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/actionfinance@"
    "sha256:1b3fb96889e2ea02053b570710211f3b4390044a170c2a8d30aaec241dbcffaf"
)
SPIDER_IMAGE = (
    f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/spider-sandbox-backend@"
    "sha256:8709085a9f96daedbab22ce3b200b4c5d20a02c5998eb93077935239ab99569a"
)
PAY_SECRET = (TMP / "prm009-pay-provider.secret").read_text(encoding="utf-8").strip()
AF_SPIDER_SECRET = (TMP / "prm009-af-spider.secret").read_text(encoding="utf-8").strip()


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    return json.loads(text)


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


def upsert_secret(container: dict, name: str, value_from: str) -> None:
    secrets = container.setdefault("secrets", [])
    for item in secrets:
        if item["name"] == name:
            item["valueFrom"] = value_from
            return
    secrets.append({"name": name, "valueFrom": value_from})


def update_runtime_secret() -> str:
    described = aws_json(["secretsmanager", "describe-secret", "--secret-id", "actionfinance/runtime"])
    arn = described["ARN"]
    current = aws_json(["secretsmanager", "get-secret-value", "--secret-id", "actionfinance/runtime"])
    data = json.loads(current["SecretString"])
    data["spider_secret"] = AF_SPIDER_SECRET
    secret_file = TMP / "prm009-runtime-put.json"
    secret_file.write_text(json.dumps(data), encoding="utf-8")
    try:
        subprocess.check_call(
            [
                "aws",
                "secretsmanager",
                "put-secret-value",
                "--region",
                REGION,
                "--secret-id",
                "actionfinance/runtime",
                "--secret-string",
                f"file://{secret_file}",
            ],
            stdout=subprocess.DEVNULL,
        )
    finally:
        if secret_file.exists():
            secret_file.unlink()
    print("runtime_secret_keys", sorted(data.keys()))
    return arn


def main() -> int:
    runtime_arn = update_runtime_secret()
    web = json.loads((TMP / "af-web-td.json").read_text(encoding="utf-8"))
    migrate = json.loads((TMP / "af-mig-td.json").read_text(encoding="utf-8"))
    spider = json.loads((TMP / "spider-td.json").read_text(encoding="utf-8"))

    web_c = web["containerDefinitions"][0]
    web_c["image"] = AF_IMAGE
    upsert_env(web_c, "ACTIONFINANCE_RECEIPT_SYNC_ENABLED", "true")
    upsert_env(web_c, "ACTIONFINANCE_INTEGRATION_HOMOLOG", "false")
    upsert_env(web_c, "ACTIONFINANCE_DEMO_AUTH_ENABLED", "false")
    upsert_env(web_c, "ACTIONFINANCE_SPIDER_BASE_URL", "https://api.spider.actionhub.com.br")
    upsert_env(web_c, "ACTIONFINANCE_SPIDER_MONITOR_BASE_URL", "https://monitor.spider.actionhub.com.br")
    upsert_secret(web_c, "ACTIONFINANCE_SPIDER_SECRET", f"{runtime_arn}:spider_secret::")

    mig_c = migrate["containerDefinitions"][0]
    mig_c["image"] = AF_IMAGE
    upsert_env(mig_c, "ACTIONFINANCE_RECEIPT_SYNC_ENABLED", "false")
    upsert_env(mig_c, "ACTIONFINANCE_INTEGRATION_HOMOLOG", "false")

    spider_c = spider["containerDefinitions"][0]
    spider_c["image"] = SPIDER_IMAGE
    upsert_env(
        spider_c,
        "SPIDER_MONITOR_ALLOWED_COMPANIES",
        "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c,624023a4-57e3-415c-b7d0-925ca1acd3b7",
    )
    upsert_env(spider_c, "SPIDER_ACTIONHUB_PAY_EDGE_URL", "https://actionhub.com.br")
    upsert_env(spider_c, "SPIDER_ACTIONHUB_PAY_EDGE_SECRET", PAY_SECRET)
    upsert_env(spider_c, "SPIDER_ACTIONFINANCE_APPLICATION_SECRET", AF_SPIDER_SECRET)
    upsert_env(spider_c, "SPIDER_ACTIONHUB_PAY_EDGE_URL", "https://actionhub.com.br")

    register("actionfinance-web", web)
    register("actionfinance-migrate", migrate)
    register("spider-sandbox-backend", spider)
    return 0


if __name__ == "__main__":
    sys.exit(main())
