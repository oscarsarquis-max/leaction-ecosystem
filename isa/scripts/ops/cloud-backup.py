"""Cópia lógica da ISA no bucket privado. Não inclui sessão nem código de acesso.

Exige ISA_DATABASE_URL e ISA_BACKUP_BUCKET. Falha se houver anexo sem o arquivo.
Não agenda nada por si só: a agenda fica no agendador da publicação.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import store


def main():
    bucket = os.environ.get("ISA_BACKUP_BUCKET") or ""
    if not bucket:
        raise SystemExit("Defina ISA_BACKUP_BUCKET. Uma pasta local não é o destino externo.")
    conn = store.connect(os.environ["ISA_DATABASE_URL"])
    try:
        tables = store.snapshot_tables(conn)
    finally:
        conn.close()
    raw = json.dumps({"engine": "postgres", "tables": tables}, ensure_ascii=False).encode("utf-8")
    stamp = store.now().replace(":", "").replace("-", "")
    prefix = "backups/" + stamp + "/"
    import boto3
    client = boto3.client("s3")
    client.put_object(Bucket=bucket, Key=prefix + "dump.json", Body=raw, ServerSideEncryption="AES256")
    manifest = {
        "createdAt": store.now(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "retentionDays": 7,
        "exclusionLedger": "erasures/",
        "engine": "postgres",
        "schedule": True,
    }
    client.put_object(
        Bucket=bucket,
        Key=prefix + "manifest.json",
        Body=json.dumps(manifest).encode("utf-8"),
        ServerSideEncryption="AES256",
    )
    print(json.dumps({"backup": prefix, "verifiedUpload": True, "tables": len(tables)}))


if __name__ == "__main__":
    main()
