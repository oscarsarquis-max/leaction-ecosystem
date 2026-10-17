"""Restaura uma cópia sintética num database isolado e apaga o ensaio.

Não restaura a instância compartilhada. O database isa_restore_004p2 é removido no fim.
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import psycopg

import store


def _as_admin():
    master = json.loads(os.environ["ISA_MASTER_JSON"])
    host = os.environ.get("ISA_PG_HOST") or "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"
    return psycopg.connect(host=host, port=5432, dbname="postgres", user=master["username"], password=master["password"], autocommit=True, connect_timeout=10)


def _drop_isolated(admin):
    admin.execute("GRANT isa_app TO CURRENT_USER")
    try:
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'isa_restore_004p2' AND pid <> pg_backend_pid()"
        )
        admin.execute("SET ROLE isa_app")
        admin.execute("DROP DATABASE IF EXISTS isa_restore_004p2")
        admin.execute("RESET ROLE")
    finally:
        admin.execute("RESET ROLE")
        admin.execute("REVOKE isa_app FROM CURRENT_USER")


def main():
    admin = _as_admin()
    try:
        _drop_isolated(admin)
        admin.execute("GRANT isa_app TO CURRENT_USER")
        try:
            admin.execute("CREATE DATABASE isa_restore_004p2 OWNER isa_app")
        finally:
            admin.execute("REVOKE isa_app FROM CURRENT_USER")
    finally:
        admin.close()
    live = store.connect(os.environ["ISA_DATABASE_URL"])
    kept = store.ensure_identity(live, "prova-mantida-004p2")
    gone = store.ensure_identity(live, "prova-excluida-004p2")
    store.save_account(live, kept, {"name": "Conta mantida"})
    store.save_entry(live, kept, {"kind": "ganho", "amountCents": 100, "label": "Registro mantido", "date": "2026-10-16", "status": "realizado"})
    store.save_account(live, gone, {"name": "Conta esquecida"})
    store.save_entry(live, gone, {"kind": "gasto", "amountCents": 200, "label": "Registro esquecido", "date": "2026-10-16", "status": "realizado"})
    folder = tempfile.mkdtemp(prefix="isa-restore-")
    try:
        tables = store.snapshot_tables(live)
        with open(os.path.join(folder, "dump.json"), "w", encoding="utf-8") as handle:
            json.dump({"engine": "postgres", "tables": tables}, handle)
        store.forget_owner(live, None, gone)
        restore_url = os.environ["ISA_DATABASE_URL"].rsplit("/", 1)[0] + "/isa_restore_004p2?sslmode=require"
        empty = store.connect(restore_url)
        store.logical_restore(empty, folder)
        kept_row = store.one(empty, "SELECT id FROM ledger_entry WHERE owner_id = ?", (kept,))
        gone_row = store.one(empty, "SELECT id FROM ledger_entry WHERE owner_id = ?", (gone,))
        empty.close()
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        store.forget_owner(live, None, kept)
        live.close()
    admin = _as_admin()
    try:
        _drop_isolated(admin)
    finally:
        admin.close()
    if not kept_row or gone_row:
        raise SystemExit("A restauração isolada não separou o registro mantido do excluído.")
    print(json.dumps({"kept": True, "forgotten": False, "isolatedDatabaseDropped": True}))


if __name__ == "__main__":
    main()
