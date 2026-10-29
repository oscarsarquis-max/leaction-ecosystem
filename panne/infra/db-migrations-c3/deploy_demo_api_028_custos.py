"""Deploy panne demo API â€” CURSOR-028 custos consolidado (demo only)."""
from __future__ import annotations

import boto3

ACCOUNT = "253137917703"
REGION = "us-east-2"
DIGEST = "sha256:7f04f955a29461b85a9676e53d33a26e23d602329bb078273b518d84bcfd6829"
DO_NOT_USE = {
    "sha256:f9405c5d444af1052aee758488111561247a21241c3bcada7540301827266ac6",
}
assert DIGEST not in DO_NOT_USE
IMG = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{DIGEST}"
HTTPS = "arn:aws:elasticloadbalancing:us-east-2:253137917703:listener/app/paneldx-alb/618ca931d137dc29/b66588a7b2ccb9f1"
HTTP = "arn:aws:elasticloadbalancing:us-east-2:253137917703:listener/app/paneldx-alb/618ca931d137dc29/2b70a9e65d6a42a8"

BOOT = r"""
import json, os
from urllib.parse import quote
import boto3
sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-2"))
sec = json.loads(sm.get_secret_value(SecretId="panne/demo/db/runtime")["SecretString"])
assert sec["username"] == "panne_demo_runtime" and sec["dbname"] == "panne_demo"
pwd = quote(sec["password"], safe="")
url = f"postgresql+asyncpg://{sec['username']}:{pwd}@{sec['host']}:{int(sec['port'])}/{sec['dbname']}"
os.environ["PANNE_DATABASE_URL"] = url
os.environ["PANNE_RUNTIME_DATABASE_URL"] = url
os.environ["PANNE_ENV"] = "demo"
os.environ["PANNE_AUTH_VERIFIER"] = "fake"
os.environ["PANNE_FAKE_ISSUER"] = "https://panne.local/fake"
os.environ["PANNE_DEMO_ANCHOR_DATE"] = "2026-08-24"
os.environ["PANNE_FISCAL_LIVE"] = "0"
os.environ["PANNE_OCR_LIVE"] = "0"
os.environ["ACTION_HUB_API_URL"] = "https://api.actionhub.com.br"
os.environ["HUB_API_URL"] = "https://api.actionhub.com.br"
os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5080"])
"""


def main() -> None:
    ecs = boto3.client("ecs", region_name=REGION)
    elbv2 = boto3.client("elbv2", region_name=REGION)

    td = ecs.register_task_definition(
        family="panne-demo-api",
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="512",
        memory="1024",
        executionRoleArn=f"arn:aws:iam::{ACCOUNT}:role/panne-ecs-task-execution-role",
        taskRoleArn=f"arn:aws:iam::{ACCOUNT}:role/panne-demo-api-task-role",
        runtimePlatform={"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"},
        containerDefinitions=[
            {
                "name": "panne-demo-api",
                "image": IMG,
                "essential": True,
                "readonlyRootFilesystem": True,
                "entryPoint": ["python", "-u", "-c"],
                "command": [BOOT],
                "portMappings": [{"containerPort": 5080, "protocol": "tcp"}],
                "environment": [
                    {"name": "AWS_REGION", "value": REGION},
                    {"name": "AWS_DEFAULT_REGION", "value": REGION},
                    {"name": "PANNE_ENV", "value": "demo"},
                    {"name": "PANNE_HTTP_HOST", "value": "0.0.0.0"},
                    {"name": "PANNE_HTTP_PORT", "value": "5080"},
                    {"name": "PANNE_FISCAL_LIVE", "value": "0"},
                    {"name": "PANNE_OCR_LIVE", "value": "0"},
                    {"name": "ACTION_HUB_API_URL", "value": "https://api.actionhub.com.br"},
                    {"name": "HUB_API_URL", "value": "https://api.actionhub.com.br"},
                ],
                "linuxParameters": {
                    "tmpfs": [
                        {
                            "containerPath": "/tmp",
                            "size": 128,
                            "mountOptions": ["rw", "noexec", "nosuid", "nodev"],
                        }
                    ]
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/panne/demo-api",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "api",
                    },
                },
                "healthCheck": {
                    "command": [
                        "CMD-SHELL",
                        "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:5080/health', timeout=3)\" || exit 1",
                    ],
                    "interval": 30,
                    "timeout": 5,
                    "retries": 3,
                    "startPeriod": 40,
                },
            }
        ],
        tags=[
            {"key": "Project", "value": "panne"},
            {"key": "Env", "value": "demo"},
            {"key": "Image", "value": "028-custos"},
            {"key": "Cursor", "value": "028-CUSTOS"},
        ],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
    image = td["taskDefinition"]["containerDefinitions"][0]["image"]
    assert DIGEST in image
    print("TD", td_arn)

    for listener, host in ((HTTPS, "api.demo.panne.ia.br"), (HTTP, "api.demo.panne.ia.br")):
        rules = elbv2.describe_rules(ListenerArn=listener)["Rules"]
        has = False
        for r in rules:
            for c in r.get("Conditions") or []:
                vals = (c.get("HostHeaderConfig") or {}).get("Values") or c.get("Values") or []
                if host in vals:
                    has = True
        print(f"listener_rule host={host} exists={has}")

    svc_name = "panne-demo-api"
    services = ecs.describe_services(cluster="paneldx-cluster", services=[svc_name])["services"]
    if not services or services[0].get("status") == "INACTIVE":
        raise SystemExit("demo API service missing")
    upd = ecs.update_service(
        cluster="paneldx-cluster",
        service=svc_name,
        taskDefinition=td_arn,
        forceNewDeployment=True,
    )
    print("SERVICE", upd["service"]["serviceArn"], "td", td_arn)
    print("DEPLOY_API_OK", DIGEST)


if __name__ == "__main__":
    main()



