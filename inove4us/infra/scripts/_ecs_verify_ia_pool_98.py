"""Idempotência do pool + CREDITS_GRANTED (RDS privado via ECS)."""
from __future__ import annotations

import boto3

from _ecs_repor_credito import run_python, service_network

CODE = r"""
import json
from institutional_ia_credits import (
    CREDITO_IA_INSTITUTIONAL_POOL,
    backfill_linked_professors,
    grant_institutional_ia_pool,
)
from webhook_routes import _handle_credits_granted, _release_hub_idempotency

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
bf = backfill_linked_professors()
g21 = grant_institutional_ia_pool(21, INST)
g22 = grant_institutional_ia_pool(22, INST)
key = "prompt98-credits-granted-retry-delta0"
payload = {"subject_id": "inovador@inove4us.com.br", "credits_added": 0}
r1 = _handle_credits_granted(payload, idempotency_key=key)
r2 = _handle_credits_granted(payload, idempotency_key=key)
_release_hub_idempotency(key)
print(json.dumps({
    "pool": CREDITO_IA_INSTITUTIONAL_POOL,
    "backfill": {k: bf[k] for k in ("candidates", "granted", "skipped", "pool")},
    "grant_21": g21,
    "grant_22": g22,
    "credits_granted_first": r1,
    "credits_granted_retry": r2,
}, default=str, ensure_ascii=False))
"""


def main() -> None:
    ecs = boto3.client("ecs", region_name="us-east-2")
    network, td = service_network(ecs)
    print("taskdef", td)
    run_python(ecs, td, network, CODE)


if __name__ == "__main__":
    main()
