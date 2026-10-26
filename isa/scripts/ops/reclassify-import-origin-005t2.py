"""Reclassifica origem de importação real. Sem --apply, só lista. Não apaga registros."""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import store

NEW = "extrato-bb-arquivo"
LEGACY = ("arquivo-teste", "exemplo-sintetico")
ACTION = "reclassificar-origem-005t2"
SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def require_production():
    if os.environ.get("ISA_ENV") != "production":
        raise SystemExit("Esta reclassificação só roda em produção. No laboratório, exemplo-sintetico é verdadeiro.")


def _person(owner):
    return hashlib.sha256((owner or "").encode()).hexdigest()[:8]


def _load(text):
    if isinstance(text, dict):
        return dict(text)
    if not text:
        return {}
    value = json.loads(text)
    return dict(value) if isinstance(value, dict) else {}


def _legacy_value(payload):
    for key in ("source", "origin"):
        if payload.get(key) in LEGACY:
            return payload[key]
    return None


def verify_backup(path):
    target = (path or "").strip()
    if not target:
        raise SystemExit("Informe a cópia verificada de hoje.")
    try:
        manifest, digest = _read_backup(target)
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit("A cópia informada não pôde ser conferida. " + type(exc).__name__)
    if not manifest.get("sha256") or manifest.get("sha256") != digest:
        raise SystemExit("A cópia não confere com o manifesto.")
    created = datetime.fromisoformat(manifest["createdAt"])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if created.astimezone(SAO_PAULO).date() != datetime.now(SAO_PAULO).date():
        raise SystemExit("A cópia verificada não é de hoje.")


def _read_backup(target):
    if target.startswith("backups/") or target.startswith("s3://"):
        return _read_s3(target)
    folder = os.path.abspath(target)
    with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as handle:
        manifest = json.loads(handle.read())
    digest = hashlib.sha256()
    with open(os.path.join(folder, "dump.json"), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return manifest, digest.hexdigest()


def _read_s3(target):
    bucket = os.environ.get("ISA_BACKUP_BUCKET") or ""
    prefix = target
    if target.startswith("s3://"):
        rest = target[5:]
        bucket, _, prefix = rest.partition("/")
    if not bucket:
        raise SystemExit("A cópia informada está no bucket e ISA_BACKUP_BUCKET não está definido.")
    if not prefix.endswith("/"):
        prefix += "/"
    import boto3
    client = boto3.client("s3")
    manifest = json.loads(client.get_object(Bucket=bucket, Key=prefix + "manifest.json")["Body"].read())
    digest = hashlib.sha256()
    body = client.get_object(Bucket=bucket, Key=prefix + "dump.json")["Body"]
    for chunk in body.iter_chunks():
        digest.update(chunk)
    return manifest, digest.hexdigest()


def _add(counts, table, origin):
    key = (table, origin or "")
    counts[key] = counts.get(key, 0) + 1


def origin_counts(conn):
    counts = {}
    for row in store.rows(conn, "SELECT origin FROM batch"):
        _add(counts, "batch", row["origin"])
    for row in store.rows(conn, "SELECT source FROM movement"):
        _add(counts, "movement", row["source"])
    for table in ("occurrence", "ledger_entry", "statement_note"):
        for row in store.rows(conn, "SELECT payload_json FROM " + table):
            payload = _load(row["payload_json"])
            if "source" in payload:
                _add(counts, table, payload.get("source") or "")
            if table == "statement_note" and "origin" in payload:
                _add(counts, "statement_note.origin", payload.get("origin") or "")
    return counts


def control_sums(conn):
    found = {}
    for row in store.rows(conn, "SELECT owner_id, COUNT(*) AS n, COALESCE(SUM(amount_cents), 0) AS total FROM movement GROUP BY owner_id"):
        found[row["owner_id"]] = {"count": int(row["n"]), "amountCents": int(row["total"])}
    return found


def _public_counts(counts):
    return [
        {"tabela": table, "origem": origin, "quantidade": counts[(table, origin)]}
        for table, origin in sorted(counts)
    ]


def _public_control(sums):
    return [
        {"pessoa": _person(owner), "quantidade": item["count"], "centavos": item["amountCents"]}
        for owner, item in sorted(sums.items(), key=lambda pair: _person(pair[0]))
    ]


def _would_change(conn):
    total = 0
    total += store.one(conn, "SELECT COUNT(*) AS n FROM batch WHERE origin IN (?, ?)", LEGACY)["n"]
    total += store.one(conn, "SELECT COUNT(*) AS n FROM movement WHERE source IN (?, ?)", LEGACY)["n"]
    for table in ("occurrence", "ledger_entry", "statement_note"):
        for row in store.rows(conn, "SELECT payload_json FROM " + table):
            if _legacy_value(_load(row["payload_json"])):
                total += 1
    return int(total)


def _owners(conn):
    found = set()
    for table, column in (("batch", "origin"), ("movement", "source")):
        for row in store.rows(conn, "SELECT owner_id FROM " + table + " WHERE " + column + " IN (?, ?)", LEGACY):
            found.add(row["owner_id"])
    for table in ("occurrence", "ledger_entry", "statement_note"):
        for row in store.rows(conn, "SELECT owner_id, payload_json FROM " + table):
            if _legacy_value(_load(row["payload_json"])):
                found.add(row["owner_id"])
    return found


def _rewrite(payload, ledger):
    old = _legacy_value(payload)
    if not old:
        return None
    for key in ("source", "origin"):
        if payload.get(key) in LEGACY:
            payload[key] = NEW
    if "originLegacy" not in payload:
        payload["originLegacy"] = old
    if ledger:
        payload["simulated"] = False
    return old


def _apply_owner(conn, owner):
    changed = 0
    for row in store.rows(conn, "SELECT id, origin FROM batch WHERE owner_id = ? AND origin IN (?, ?)", (owner, *LEGACY)):
        conn.execute("UPDATE batch SET origin = ? WHERE id = ? AND owner_id = ?", (NEW, row["id"], owner))
        store.log(conn, owner, "batch", row["id"], ACTION, {"origin": row["origin"]}, {"origin": NEW})
        changed += 1
    for row in store.rows(conn, "SELECT id, source FROM movement WHERE owner_id = ? AND source IN (?, ?)", (owner, *LEGACY)):
        conn.execute("UPDATE movement SET source = ? WHERE id = ? AND owner_id = ?", (NEW, row["id"], owner))
        store.log(conn, owner, "movement", row["id"], ACTION, {"source": row["source"]}, {"source": NEW})
        changed += 1
    for table, ledger in (("occurrence", False), ("ledger_entry", True), ("statement_note", False)):
        for row in store.rows(conn, "SELECT id, payload_json FROM " + table + " WHERE owner_id = ?", (owner,)):
            payload = _load(row["payload_json"])
            old = _rewrite(payload, ledger)
            if not old:
                continue
            conn.execute("UPDATE " + table + " SET payload_json = ? WHERE id = ? AND owner_id = ?", (json.dumps(payload), row["id"], owner))
            after = {"source": payload.get("source") or "", "origin": payload.get("origin") or "", "originLegacy": payload.get("originLegacy")}
            if ledger:
                after["simulated"] = False
            store.log(conn, owner, table, row["id"], ACTION, {"origin": old}, after)
            changed += 1
    return changed


def apply(conn):
    changed = 0
    for owner in sorted(_owners(conn)):
        conn.execute("BEGIN IMMEDIATE")
        try:
            changed += _apply_owner(conn, owner)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    require_production()
    verify_backup(args.backup)
    url = os.environ.get("ISA_DATABASE_URL") or ""
    if not url:
        raise SystemExit("Defina ISA_DATABASE_URL.")
    conn = store.connect(url, bootstrap=False)
    try:
        before_counts = origin_counts(conn)
        before_sums = control_sums(conn)
        would = _would_change(conn)
        changed = apply(conn) if args.apply else 0
        after_counts = origin_counts(conn)
        after_sums = control_sums(conn)
    finally:
        conn.close()
    if before_sums != after_sums:
        print(json.dumps({"erro": "soma de controle diferente", "antes": _public_control(before_sums), "depois": _public_control(after_sums)}, ensure_ascii=False))
        raise SystemExit(4)
    print(json.dumps({
        "modo": "aplicado" if args.apply else "simulacao",
        "wouldChange": would,
        "changed": changed,
        "before": _public_counts(before_counts),
        "after": _public_counts(after_counts),
        "controleAntes": _public_control(before_sums),
        "controleDepois": _public_control(after_sums),
        "iguais": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
