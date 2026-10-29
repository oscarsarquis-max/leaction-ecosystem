"""Register AF web and migrate with the cadastros candidate image. Does not print secrets. Does not touch Spider."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REGION = "us-east-2"
ACCOUNT = "253137917703"
KEEP = (
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


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return json.loads(raw.decode("utf-16"))
    return json.loads(raw.decode("utf-8"))


def register(family: str, image: str) -> int:
    current = aws_json(["ecs", "describe-task-definition", "--task-definition", family])["taskDefinition"]
    previous = current["revision"]
    previous_image = current["containerDefinitions"][0]["image"]
    body = {key: current[key] for key in KEEP if key in current}
    body["containerDefinitions"][0]["image"] = image
    path = pathlib.Path(os.environ["TEMP"]) / f"af-reg-cadastros-017-{family}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    try:
        result = aws_json(["ecs", "register-task-definition", "--cli-input-json", f"file://{path}"])
    finally:
        if path.exists():
            path.unlink()
    revision = result["taskDefinition"]["revision"]
    print(f"previous={family}:{previous}")
    print(f"previousImage={previous_image}")
    print(f"registered={family}:{revision}")
    print(f"image={image}")
    return revision


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("sha256:"):
        print("usage: register-af-cadastros-017.py sha256:<digest>")
        return 2
    image = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/actionfinance@{sys.argv[1]}"
    register("actionfinance-web", image)
    register("actionfinance-migrate", image)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
