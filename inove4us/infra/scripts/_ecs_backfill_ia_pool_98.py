"""Backfill pontual do pool IA institucional via ECS (RDS privado)."""
from __future__ import annotations

import boto3

from _ecs_repor_credito import run_python, service_network

CODE = """
import json
from institutional_ia_credits import backfill_linked_professors
print(json.dumps(backfill_linked_professors(), default=str))
"""


def main() -> None:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    print("taskdef", td)
    run_python(ecs, td, network, CODE)


if __name__ == "__main__":
    main()
