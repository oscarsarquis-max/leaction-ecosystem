#!/usr/bin/env python3
"""Clone spider-sandbox-backend:14 into a Monitor-JPA revision and optionally update ECS.

Does not print secret values. Canonical persistence stays memory.
"""
from __future__ import annotations

import argparse
import json
import sys

import boto3

REGION = "us-east-2"
FAMILY = "spider-sandbox-backend"
SOURCE_REVISION = 14
CLUSTER = "spider-sandbox"
SERVICE = "spider-sandbox-backend"
SECRET_NAME = "spider-sandbox/postgres"
JDBC_USER_ENV = "SPIDER_MONITOR_JDBC_USERNAME"
JDBC_PASS_ENV = "SPIDER_MONITOR_JDBC_PASSWORD"
JDBC_URL_ENV = "SPIDER_MONITOR_JDBC_URL"
MODE_ENV = "SPIDER_MONITOR_PERSISTENCE_MODE"
CANONICAL_ENV = "SPIDER_CANONICAL_PERSISTENCE_MODE"


def _log(message: str) -> None:
    print(message, flush=True)


def _secret_keys(sm) -> tuple[str, dict]:
    raw = sm.get_secret_value(SecretId=SECRET_NAME)
    arn = raw["ARN"]
    payload = json.loads(raw["SecretString"])
    keys = sorted(payload.keys())
    required = ("host", "port", "dbname", "username", "password")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise SystemExit(f"secret missing keys: {missing}")
    _log(f"secret={SECRET_NAME} keys={keys}")
    return arn, payload


def _jdbc_url(payload: dict) -> str:
    return (
        f"jdbc:postgresql://{payload['host']}:{payload['port']}/"
        f"{payload['dbname']}?ssl=true&sslmode=require"
    )


def _upsert_env(environment: list[dict], name: str, value: str) -> None:
    for item in environment:
        if item.get("name") == name:
            item["value"] = value
            return
    environment.append({"name": name, "value": value})


def _upsert_secret(secrets: list[dict], name: str, value_from: str) -> None:
    for item in secrets:
        if item.get("name") == name:
            item["valueFrom"] = value_from
            return
    secrets.append({"name": name, "valueFrom": value_from})


def clone_task(ecs, sm, image: str) -> dict:
    source = ecs.describe_task_definition(taskDefinition=f"{FAMILY}:{SOURCE_REVISION}")[
        "taskDefinition"
    ]
    container = json.loads(json.dumps(source["containerDefinitions"][0]))
    environment = list(container.get("environment") or [])
    secrets = list(container.get("secrets") or [])
    arn, payload = _secret_keys(sm)
    _upsert_env(environment, CANONICAL_ENV, "memory")
    _upsert_env(environment, MODE_ENV, "jpa")
    _upsert_env(environment, JDBC_URL_ENV, _jdbc_url(payload))
    _upsert_secret(secrets, JDBC_USER_ENV, f"{arn}:username::")
    _upsert_secret(secrets, JDBC_PASS_ENV, f"{arn}:password::")
    container["image"] = image
    container["environment"] = environment
    container["secrets"] = secrets
    _log("source_revision=" + str(source["revision"]))
    _log("image=" + image)
    _log("env_names=" + ",".join(sorted(item["name"] for item in environment)))
    _log("secret_names=" + ",".join(sorted(item["name"] for item in secrets)))
    return {
        "family": source["family"],
        "taskRoleArn": source["taskRoleArn"],
        "executionRoleArn": source["executionRoleArn"],
        "networkMode": source["networkMode"],
        "containerDefinitions": [container],
        "requiresCompatibilities": source.get("requiresCompatibilities") or ["FARGATE"],
        "cpu": source["cpu"],
        "memory": source["memory"],
        "volumes": source.get("volumes") or [],
        "tags": [
            {"key": item["key"], "value": item["value"]}
            for item in ecs.list_tags_for_resource(resourceArn=source["taskDefinitionArn"]).get(
                "tags", []
            )
            if item.get("key")
        ],
    }


def register(ecs, payload: dict) -> str:
    kwargs = dict(payload)
    tags = kwargs.pop("tags", [])
    if tags:
        kwargs["tags"] = tags
    registered = ecs.register_task_definition(**kwargs)
    arn = registered["taskDefinition"]["taskDefinitionArn"]
    revision = registered["taskDefinition"]["revision"]
    _log(f"registered={FAMILY}:{revision}")
    _log("arn=" + arn)
    return arn


def update_service(ecs, task_arn: str) -> None:
    ecs.update_service(
        cluster=CLUSTER,
        service=SERVICE,
        taskDefinition=task_arn,
        desiredCount=1,
        deploymentConfiguration={
            "deploymentCircuitBreaker": {"enable": True, "rollback": True},
            "maximumPercent": 100,
            "minimumHealthyPercent": 0,
        },
    )
    _log(f"service_updated cluster={CLUSTER} service={SERVICE} desired=1")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Immutable image URI or repo@sha256")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--update-service", action="store_true")
    args = parser.parse_args()
    session = boto3.session.Session(region_name=REGION)
    ecs = session.client("ecs")
    sm = session.client("secretsmanager")
    payload = clone_task(ecs, sm, args.image)
    if not args.register:
        _log("dry-run (pass --register to create a revision)")
        return 0
    arn = register(ecs, payload)
    if args.update_service:
        update_service(ecs, arn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
