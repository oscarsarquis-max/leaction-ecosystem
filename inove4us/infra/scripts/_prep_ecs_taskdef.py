"""Register new ECS task revision: image v2.2.0 + School bridge secrets. No secret prints."""
from __future__ import annotations

import json
import pathlib
import subprocess

AWS = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
REGION = "us-east-2"
IMAGE = "253137917703.dkr.ecr.us-east-2.amazonaws.com/inove4us:v2.2.0"
SHA = "5c47834"
VERSION = "2.2.0"
BRIDGE = pathlib.Path(r"C:\Projetos\leaction-ecosystem\inove4us-school\.env.prod-bridge")
OUT = pathlib.Path(r"C:\Users\Usuario\AppData\Local\Temp\inove-td-register.json")
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
    raw = subprocess.check_output([AWS, *args, "--region", REGION, "--output", "json"])
    return json.loads(raw)


def main() -> None:
    bridge: dict[str, str] = {}
    for line in BRIDGE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            bridge[k.strip()] = v.strip()
    api = bridge["SCHOOL_INTEGRATION_API_KEY"]
    jwt = bridge["SCHOOL_B2C_SHARED_SECRET"]

    td = aws_json(["ecs", "describe-task-definition", "--task-definition", "inove4us-prod:25"])[
        "taskDefinition"
    ]
    for key in list(td):
        if key in DROP:
            td.pop(key)

    ctn = td["containerDefinitions"][0]
    ctn["image"] = IMAGE
    env = {e["name"]: e["value"] for e in ctn.get("environment", [])}
    env["GIT_SHA"] = SHA
    env["APP_VERSION"] = VERSION
    env["INOVE4US_VERSION"] = VERSION
    env["SCHOOL_INTEGRATION_API_KEY"] = api
    env["SCHOOL_B2C_SHARED_SECRET"] = jwt
    ctn["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
    OUT.write_text(json.dumps(td), encoding="utf-8")
    names = sorted(env)
    print("env_names", ",".join(names))
    print("image", IMAGE)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
