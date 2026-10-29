"""First remote apply of consolidated demo economy to AWS panne_demo only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from urllib.parse import quote

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

REGION = os.environ.get("AWS_REGION", "us-east-2")


def _url_from_secret(secret_id: str, expect_db: str, expect_user: str) -> tuple[str, dict]:
    sm = boto3.client("secretsmanager", region_name=REGION)
    sec = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    assert sec["dbname"] == expect_db and sec["username"] == expect_user
    pwd = quote(sec["password"], safe="")
    url = f"postgresql+psycopg://{sec['username']}:{pwd}@{sec['host']}:{int(sec['port'])}/{sec['dbname']}"
    return url, {"dbname": sec["dbname"], "username": sec["username"], "host": sec["host"].split(".")[0] + ".…"}


def photograph(url: str) -> dict:
    e = create_engine(url, future=True)
    with e.connect() as c:
        # relax RLS briefly for migrator snapshot
        c.execute(
            text(
                """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relforcerowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
            )
        )
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
            return {"counts": [dict(r) for r in rows], "product_codes": codes}
        finally:
            c.execute(
                text(
                    """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
                )
            )
            c.commit()


def set_force_rls(url: str, *, force: bool) -> None:
    e = create_engine(url, future=True)
    with e.connect() as c:
        if force:
            c.execute(
                text(
                    """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
                )
            )
        else:
            c.execute(
                text(
                    """
DO $migration$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname AS rel FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind='r' AND c.relforcerowsecurity
 LOOP EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel); END LOOP; END $migration$;
"""
                )
            )
        c.commit()
    e.dispose()


def main() -> None:
    # Ensure /app (tests helpers + app sources) is importable for seed scripts
    if "/app" not in sys.path:
        sys.path.insert(0, "/app")
    os.environ["PYTHONPATH"] = "/app:/opt/panne/backend:" + os.environ.get("PYTHONPATH", "")

    # Prove panne intact
    url_p, meta_p = _url_from_secret("panne/prod/db/migrator", "panne", "panne_prod_migrator")
    e_p = create_engine(url_p, future=True)
    with e_p.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "panne"
        org = c.execute(text("SELECT to_regclass('public.organization')")).scalar()
    print("panne_intact_before", {**meta_p, "organization_table": org}, flush=True)
    e_p.dispose()

    url, meta = _url_from_secret("panne/demo/db/migrator", "panne_demo", "panne_demo_migrator")
    print("target", meta, flush=True)
    before = photograph(url)
    print("BEFORE_JSON", json.dumps(before, ensure_ascii=False), flush=True)

    print("RELAX_RLS", flush=True)
    set_force_rls(url, force=False)
    try:
        env = os.environ.copy()
        env["PANNE_PATCH_URL"] = url
        env["PYTHONPATH"] = "/app:/opt/panne/backend"
        print("POPULATE_BEGIN", flush=True)
        p1 = subprocess.run(
            [sys.executable, "/opt/panne/scripts/populate_demo_economy.py"],
            env=env,
            capture_output=True,
            text=True,
            cwd="/opt/panne",
        )
        print("populate_stdout", p1.stdout[-8000:], flush=True)
        print("populate_stderr", (p1.stderr or "")[-4000:], flush=True)
        print("populate_rc", p1.returncode, flush=True)
        if p1.returncode != 0:
            raise SystemExit(p1.returncode)

        print("FLOUR_NORMALIZE_BEGIN", flush=True)
        p2 = subprocess.run(
            [sys.executable, "/opt/panne/scripts/normalize_flour_package_prices.py"],
            env=env,
            capture_output=True,
            text=True,
            cwd="/opt/panne",
        )
        print("flour_stdout", p2.stdout[-4000:], flush=True)
        print("flour_stderr", (p2.stderr or "")[-2000:], flush=True)
        print("flour_rc", p2.returncode, flush=True)
        if p2.returncode != 0:
            raise SystemExit(p2.returncode)
    finally:
        print("RESTORE_RLS", flush=True)
        set_force_rls(url, force=True)

    after = photograph(url)
    print("AFTER_JSON", json.dumps(after, ensure_ascii=False), flush=True)

    e_p = create_engine(url_p, future=True)
    with e_p.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "panne"
    print("panne_intact_after_ok", flush=True)
    print("OK", flush=True)


if __name__ == "__main__":
    main()
