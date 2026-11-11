#!/usr/bin/env python3
"""Copy the ActionHub Pay credential into the production secret.

Reads the live sandbox task environment and writes a new production secret.
Does not print the credential.
"""
from __future__ import annotations

import json
import sys

import boto3

REGION = "us-east-2"
CLUSTER = "spider-sandbox"
SERVICE = "spider-sandbox-backend"
SOURCE_ENV = "SPIDER_ACTIONHUB_PAY_EDGE_SECRET"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: install-pay-secret.py <secret-id>")
    secret_id = sys.argv[1]
    ecs = boto3.client("ecs", region_name=REGION)
    sm = boto3.client("secretsmanager", region_name=REGION)
    described = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])["services"][0]
    task_arn = described["taskDefinition"]
    task = ecs.describe_task_definition(taskDefinition=task_arn)["taskDefinition"]
    value = None
    for item in task["containerDefinitions"][0].get("environment") or []:
        if item.get("name") == SOURCE_ENV and item.get("value"):
            value = item["value"]
            break
    if not value:
        raise SystemExit("source pay credential missing")
    sm.put_secret_value(SecretId=secret_id, SecretString=value)
    print("production pay secret installed")


if __name__ == "__main__":
    main()
