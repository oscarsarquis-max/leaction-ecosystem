"""Print only secret identity fields (no password) for migrator secrets."""
import boto3
import json

sm = boto3.client("secretsmanager", region_name="us-east-2")
for sid in ["panne/demo/db/migrator", "panne/prod/db/migrator", "panne/demo/db/runtime", "panne/prod/db/runtime"]:
    try:
        sec = json.loads(sm.get_secret_value(SecretId=sid)["SecretString"])
        print(f"{sid} user={sec.get('username')} db={sec.get('dbname')} host_set={bool(sec.get('host'))}")
    except Exception as exc:
        print(f"{sid} ERR {type(exc).__name__}")
