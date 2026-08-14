"""One-off: list/restore freemium credits via ECS RunTask (RDS privado)."""
from __future__ import annotations

import sys
import time

import boto3

REGION = "us-east-2"
CLUSTER = "inove4us-prod"
SERVICE = "inove4us-prod"
CONTAINER = "inove4us"

# 1 = só listar; 2 = recompor 1 crédito freemium nos e-mails alvo
MODE = sys.argv[1] if len(sys.argv) > 1 else "list"
EMAILS = [a.strip().lower() for a in sys.argv[2:] if a.strip()]


def service_network(ecs):
    svc = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])["services"][0]
    conf = svc["networkConfiguration"]["awsvpcConfiguration"]
    return {
        "awsvpcConfiguration": {
            "subnets": conf["subnets"],
            "securityGroups": conf.get("securityGroups") or [],
            "assignPublicIp": conf.get("assignPublicIp") or "DISABLED",
        }
    }, svc["taskDefinition"]


def run_python(ecs, task_def, network, code: str) -> str:
    # Escape for shell -c via JSON command list
    resp = ecs.run_task(
        cluster=CLUSTER,
        taskDefinition=task_def,
        launchType="FARGATE",
        networkConfiguration=network,
        overrides={
            "containerOverrides": [
                {
                    "name": CONTAINER,
                    "command": ["python", "-c", code],
                }
            ]
        },
    )
    failures = resp.get("failures") or []
    if failures:
        raise RuntimeError(failures)
    task_arn = resp["tasks"][0]["taskArn"]
    print("started", task_arn.split("/")[-1])

    for _ in range(60):
        time.sleep(5)
        desc = ecs.describe_tasks(cluster=CLUSTER, tasks=[task_arn])["tasks"][0]
        last = desc.get("lastStatus")
        print("status", last)
        if last in ("STOPPED",):
            break
    else:
        raise TimeoutError("task não parou a tempo")

    logs = boto3.client("logs", region_name=REGION)
    # Try common log group patterns
    task_id = task_arn.split("/")[-1]
    candidates = [
        f"/ecs/{CLUSTER}",
        f"/ecs/inove4us-prod",
        f"/ecs/inove4us",
    ]
    # Discover from task definition
    td = ecs.describe_task_definition(taskDefinition=task_def)["taskDefinition"]
    for c in td["containerDefinitions"]:
        opts = (c.get("logConfiguration") or {}).get("options") or {}
        if opts.get("awslogs-group"):
            candidates.insert(0, opts["awslogs-group"])
            stream_prefix = opts.get("awslogs-stream-prefix", "ecs")
            stream = f"{stream_prefix}/{CONTAINER}/{task_id}"
            try:
                ev = logs.get_log_events(
                    logGroupName=opts["awslogs-group"],
                    logStreamName=stream,
                    startFromHead=True,
                )
                text = "\n".join(e["message"] for e in ev.get("events", []))
                print("--- logs ---")
                print(text)
                return text
            except Exception as exc:
                print("log_err", opts["awslogs-group"], stream, exc)

    # Fallback: filter log streams
    for group in candidates:
        try:
            streams = logs.describe_log_streams(
                logGroupName=group,
                orderBy="LastEventTime",
                descending=True,
                limit=20,
            )["logStreams"]
            for s in streams:
                name = s["logStreamName"]
                if task_id in name:
                    ev = logs.get_log_events(
                        logGroupName=group, logStreamName=name, startFromHead=True
                    )
                    text = "\n".join(e["message"] for e in ev.get("events", []))
                    print("--- logs ---")
                    print(text)
                    return text
        except Exception as exc:
            print("group_err", group, exc)
    return ""


LIST_CODE = r"""
import os, psycopg2
from psycopg2.extras import RealDictCursor
conn = psycopg2.connect(
    host=os.environ['DB_HOST'], port=int(os.environ.get('DB_PORT') or 5432),
    dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
    password=os.environ['DB_PASS'], sslmode=os.environ.get('DB_SSLMODE') or 'require',
)
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute('''
SELECT id_clie, mail_clie, creditos_ia, plan_tier,
       COALESCE(instituicao_b2b_id::text,'') AS inst
  FROM public.ctdi_clie
 ORDER BY id_clie DESC LIMIT 25
''')
for r in cur.fetchall():
    print(dict(r))
conn.close()
"""


def restore_code(emails: list[str]) -> str:
    emails_repr = repr(emails)
    return f"""
import os, psycopg2
from psycopg2.extras import RealDictCursor
emails = {emails_repr}
conn = psycopg2.connect(
    host=os.environ['DB_HOST'], port=int(os.environ.get('DB_PORT') or 5432),
    dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
    password=os.environ['DB_PASS'], sslmode=os.environ.get('DB_SSLMODE') or 'require',
)
cur = conn.cursor(cursor_factory=RealDictCursor)
if not emails:
    cur.execute('''
        SELECT id_clie, mail_clie, creditos_ia, plan_tier
          FROM public.ctdi_clie
         WHERE COALESCE(plan_tier,'starter') = 'starter'
           AND COALESCE(creditos_ia,0) <= 0
           AND instituicao_b2b_id IS NULL
         ORDER BY id_clie DESC
         LIMIT 10
    ''')
    emails = [str(r['mail_clie']).strip().lower() for r in cur.fetchall() if r.get('mail_clie')]
    print('auto_targets', emails)
for email in emails:
    cur.execute('''
        UPDATE public.ctdi_clie
           SET creditos_ia = 1
         WHERE mail_clie IS NOT NULL
           AND LOWER(TRIM(mail_clie)) = %s
     RETURNING id_clie, mail_clie, creditos_ia, plan_tier
    ''', (email,))
    row = cur.fetchone()
    print('restored' if row else 'missing', dict(row) if row else email)
conn.commit()
conn.close()
print('OK')
"""


def main() -> None:
    ecs = boto3.client("ecs", region_name=REGION)
    network, task_def = service_network(ecs)
    if MODE == "list":
        run_python(ecs, task_def, network, LIST_CODE)
    elif MODE == "restore":
        run_python(ecs, task_def, network, restore_code(EMAILS))
    else:
        raise SystemExit("uso: list | restore [email...]")


if __name__ == "__main__":
    main()
