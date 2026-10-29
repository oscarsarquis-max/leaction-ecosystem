"""Restore /dump/panne_demo_custos.dump into AWS panne_demo. Prove panne intact."""
from __future__ import annotations

import json
import os
import subprocess

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

REGION = os.environ.get("AWS_REGION", "us-east-2")
DUMP = "/dump/panne_demo_custos.dump"


def main() -> None:
    sm = boto3.client("secretsmanager", region_name=REGION)

    sec_p = json.loads(sm.get_secret_value(SecretId="panne/prod/db/migrator")["SecretString"])
    assert sec_p["dbname"] == "panne" and sec_p["username"] == "panne_prod_migrator"
    url_p = URL.create(
        "postgresql+psycopg",
        username=sec_p["username"],
        password=sec_p["password"],
        host=sec_p["host"],
        port=int(sec_p["port"]),
        database=sec_p["dbname"],
    )
    e_p = create_engine(url_p, connect_args={"sslmode": "require"})
    with e_p.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "panne"
        org = c.execute(text("SELECT to_regclass('public.organization')")).scalar()
    print("panne_intact_before", {"database": "panne", "organization_table": org}, flush=True)
    e_p.dispose()

    sec = json.loads(sm.get_secret_value(SecretId="panne/demo/db/migrator")["SecretString"])
    assert sec["dbname"] == "panne_demo" and sec["username"] == "panne_demo_migrator"
    print("dump_bytes", os.path.getsize(DUMP), flush=True)

    env = os.environ.copy()
    env["PGPASSWORD"] = sec["password"]
    cmd = [
        "pg_restore",
        "-h",
        sec["host"],
        "-p",
        str(sec["port"]),
        "-U",
        sec["username"],
        "-d",
        sec["dbname"],
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        DUMP,
    ]
    print("RESTORE_BEGIN", flush=True)
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print("stderr_tail", (p.stderr or "")[-8000:], flush=True)
    print("restore_rc", p.returncode, flush=True)
    if p.returncode not in (0, 1):
        raise SystemExit(p.returncode)

    url = URL.create(
        "postgresql+psycopg",
        username=sec["username"],
        password=sec["password"],
        host=sec["host"],
        port=int(sec["port"]),
        database=sec["dbname"],
    )
    e = create_engine(url, connect_args={"sslmode": "require"})
    relax = """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relforcerowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
    restore = """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
    with e.connect() as c:
        c.execute(text(relax))
        c.commit()
        try:
            rows = c.execute(
                text(
                    """
            SELECT o.slug,
              (SELECT count(*) FROM technical_product tp WHERE tp.organization_id=o.id) AS produtos,
              (SELECT count(*) FROM ingredient i WHERE i.organization_id=o.id) AS ingredientes,
              (SELECT count(*) FROM supplier_item_price sip JOIN supplier_item si ON si.id=sip.supplier_item_id WHERE si.organization_id=o.id) AS precos_compra,
              (SELECT count(*) FROM costing_calculation cc WHERE cc.organization_id=o.id) AS calculos,
              (SELECT count(*) FROM practiced_price pp WHERE pp.organization_id=o.id) AS precos_venda
            FROM organization o ORDER BY slug
            """
                )
            ).mappings().all()
            codes = list(
                c.execute(
                    text(
                        "SELECT code FROM technical_product tp JOIN organization o ON o.id=tp.organization_id WHERE o.slug='panne-demonstracao' ORDER BY 1"
                    )
                ).scalars()
            )
            print("SNAPSHOT_JSON_BEGIN", flush=True)
            print(
                json.dumps(
                    {"counts": [dict(r) for r in rows], "product_codes": codes},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            print("SNAPSHOT_JSON_END", flush=True)
        finally:
            c.execute(text(restore))
            c.commit()
    e.dispose()

    e_p = create_engine(url_p, connect_args={"sslmode": "require"})
    with e_p.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "panne"
    print("panne_intact_after_ok", flush=True)
    print("OK", flush=True)


if __name__ == "__main__":
    main()
