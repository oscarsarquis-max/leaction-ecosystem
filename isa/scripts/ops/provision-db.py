"""Cria o database isa e o papel isa_app na instância já existente.

A credencial mestre só entra neste processo. O serviço web não a recebe.
Não altera o database actionfinance nem os dados do Finance.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import psycopg
from psycopg import sql

import store


HOST = os.environ.get("ISA_PG_HOST") or "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"


def _admin():
    master = json.loads(os.environ["ISA_MASTER_JSON"])
    return psycopg.connect(
        host=HOST,
        port=5432,
        dbname="postgres",
        user=master["username"],
        password=master["password"],
        autocommit=True,
        connect_timeout=10,
    )


def main():
    password = os.environ["ISA_APP_PASSWORD"]
    admin = _admin()
    try:
        exists = admin.execute("SELECT 1 FROM pg_roles WHERE rolname = 'isa_app'").fetchone()
        if exists:
            admin.execute(sql.SQL("ALTER ROLE isa_app LOGIN PASSWORD {} CONNECTION LIMIT 16").format(sql.Literal(password)))
        else:
            admin.execute(sql.SQL("CREATE ROLE isa_app LOGIN PASSWORD {} CONNECTION LIMIT 16").format(sql.Literal(password)))
        admin.execute("GRANT isa_app TO CURRENT_USER")
        try:
            database = admin.execute("SELECT 1 FROM pg_database WHERE datname = 'isa'").fetchone()
            if not database:
                admin.execute("CREATE DATABASE isa OWNER isa_app")
            admin.execute("ALTER DATABASE isa OWNER TO isa_app")
        finally:
            admin.execute("REVOKE isa_app FROM CURRENT_USER")
    finally:
        admin.close()
    url = os.environ["ISA_DATABASE_URL"]
    conn = store.connect(url)
    try:
        version = store.one(conn, "SELECT MAX(version) AS v FROM schema_migration")
    finally:
        conn.close()
    master = json.loads(os.environ["ISA_MASTER_JSON"])
    finance = psycopg.connect(
        host=HOST,
        port=5432,
        dbname="actionfinance",
        user=master["username"],
        password=master["password"],
        connect_timeout=10,
    )
    try:
        table = finance.execute(
            "SELECT n.nspname, c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY 1, 2 LIMIT 1"
        ).fetchone()
    finally:
        finance.close()
    denied = False
    if table:
        app = psycopg.connect(
            host=HOST,
            port=5432,
            dbname="actionfinance",
            user="isa_app",
            password=password,
            connect_timeout=10,
            autocommit=True,
        )
        try:
            try:
                app.execute(sql.SQL("SELECT 1 FROM {}.{} LIMIT 1").format(sql.Identifier(table[0]), sql.Identifier(table[1])))
            except psycopg.errors.InsufficientPrivilege:
                denied = True
        finally:
            app.close()
    if table and not denied:
        raise SystemExit("isa_app leu uma tabela do Finance. O provisionamento para aqui.")
    print(json.dumps({"database": "isa", "role": "isa_app", "schema": version["v"] if version else 0, "financeSelect": "denied" if denied or not table else "unchecked"}))


if __name__ == "__main__":
    main()
