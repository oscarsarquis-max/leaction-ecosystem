"""Deploy panne demo API (img7b only). No accidental digests."""
from __future__ import annotations

import json

import boto3

ACCOUNT = "253137917703"
REGION = "us-east-2"
DIGEST = "sha256:01c691ebd21fae0dbaf64c5cf2fad35e49bd2fa49f433d60f4be8a329abc0236"
DO_NOT_USE = {
    "sha256:68a679b59d7fa3c1b5972b41fb66a17ad3d2a1b8d8d21b78652e2e4939cbf844",
    "sha256:9eb41c33433e03d27dc750ac3ade1957bc5f5604127cd25799d96cb812e41096",
    "sha256:4dbe9a3d68837730045e58d6f1969eb2538165010ee362ea8e27562fae9f485b",
}
assert DIGEST not in DO_NOT_USE
IMG = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/panne/backend@{DIGEST}"
TG = "arn:aws:elasticloadbalancing:us-east-2:253137917703:targetgroup/panne-demo-api-tg/fa655a2489eee5d5"
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
            {"key": "Image", "value": "img7b"},
        ],
    )
    td_arn = td["taskDefinition"]["taskDefinitionArn"]
    image = td["taskDefinition"]["containerDefinitions"][0]["image"]
    assert DIGEST in image
    for bad in DO_NOT_USE:
        assert bad not in image
    print("TD", td_arn)

    def next_prio(listener: str) -> int:
        rules = elbv2.describe_rules(ListenerArn=listener)["Rules"]
        used = {int(r["Priority"]) for r in rules if r.get("Priority") not in (None, "default")}
        prio = 50
        while prio in used:
            prio += 1
        return prio

    # idempotent host rules
    existing_https = elbv2.describe_rules(ListenerArn=HTTPS)["Rules"]
    has_api = False
    for r in existing_https:
        for c in r.get("Conditions") or []:
            vals = (c.get("HostHeaderConfig") or {}).get("Values") or c.get("Values") or []
            if "api.demo.panne.ia.br" in vals:
                has_api = True
    if not has_api:
        prio = next_prio(HTTPS)
        r = elbv2.create_rule(
            ListenerArn=HTTPS,
            Priority=prio,
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": ["api.demo.panne.ia.br"]},
                }
            ],
            Actions=[{"Type": "forward", "TargetGroupArn": TG}],
            Tags=[{"Key": "Project", "Value": "panne"}, {"Key": "Env", "Value": "demo"}],
        )
        print("HTTPS_RULE", r["Rules"][0]["RuleArn"], "prio", prio)
    else:
        print("HTTPS_RULE exists")

    existing_http = elbv2.describe_rules(ListenerArn=HTTP)["Rules"]
    has_http = False
    for r in existing_http:
        for c in r.get("Conditions") or []:
            vals = (c.get("HostHeaderConfig") or {}).get("Values") or c.get("Values") or []
            if "api.demo.panne.ia.br" in vals:
                has_http = True
    if not has_http:
        prio2 = next_prio(HTTP)
        r2 = elbv2.create_rule(
            ListenerArn=HTTP,
            Priority=prio2,
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": ["api.demo.panne.ia.br"]},
                }
            ],
            Actions=[
                {
                    "Type": "redirect",
                    "RedirectConfig": {
                        "Protocol": "HTTPS",
                        "Port": "443",
                        "StatusCode": "HTTP_301",
                    },
                }
            ],
        )
        print("HTTP_RULE", r2["Rules"][0]["RuleArn"])
    else:
        print("HTTP_RULE exists")

    svc_name = "panne-demo-api"
    existing = ecs.describe_services(cluster="paneldx-cluster", services=[svc_name])["services"]
    if existing and existing[0]["status"] != "INACTIVE":
        ecs.update_service(
            cluster="paneldx-cluster",
            service=svc_name,
            taskDefinition=td_arn,
            desiredCount=1,
            forceNewDeployment=True,
        )
        print("SERVICE_UPDATED", svc_name)
    else:
        s = ecs.create_service(
            cluster="paneldx-cluster",
            serviceName=svc_name,
            taskDefinition=td_arn,
            desiredCount=1,
            launchType="FARGATE",
            platformVersion="1.4.0",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-0a1da7a0765588962",
                        "subnet-0693afdb3330b683a",
                    ],
                    "securityGroups": ["sg-0f41648d1720bca80"],
                    "assignPublicIp": "DISABLED",
                }
            },
            loadBalancers=[
                {
                    "targetGroupArn": TG,
                    "containerName": "panne-demo-api",
                    "containerPort": 5080,
                }
            ],
            healthCheckGracePeriodSeconds=60,
            tags=[{"key": "Project", "value": "panne"}, {"key": "Env", "value": "demo"}],
            propagateTags="SERVICE",
        )
        print("SERVICE_CREATED", s["service"]["serviceArn"])


if __name__ == "__main__":
    main()
