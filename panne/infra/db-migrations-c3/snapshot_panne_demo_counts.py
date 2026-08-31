"""CURSOR-028-RELEASE — fotografia quantitativa de panne_demo (somente leitura).

Não imprime senhas/URLs. Não altera dados. Não toca no banco panne (só prova intacto).

Uso local (se SG permitir):
  python snapshot_panne_demo_counts.py --phase pre

Uso pós-deploy:
  python snapshot_panne_demo_counts.py --phase post --compare <pre.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

REGION = "us-east-2"
OUT_DIR = Path(__file__).resolve().parents[2] / "documentacao" / "evidencias" / "cursor-028-release"

# Contagens pedidas — tabelas canônicas por organização.
METRICS: list[tuple[str, str]] = [
    ("produtos", "technical_product"),
    ("ingredientes", "ingredient"),
    ("receitas", "formulation"),
    ("ordens", "production_order"),
    ("planos", "production_plan"),
    ("fornecedores", "supplier"),
    ("lotes", "inventory_lot"),
    ("saldos", "inventory_balance"),
    ("movimentos", "inventory_movement"),
    ("entradas_fiscais", "fiscal_inbound_document"),
    ("usuarios_demo", "app_user"),
]

RELAX = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""

RESTORE = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""


def _engine(secret_id: str, expect_db: str, expect_user: str):
    sm = boto3.client("secretsmanager", region_name=REGION)
    sec = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    assert sec["dbname"] == expect_db and sec["username"] == expect_user, (
        f"identidade inválida user={sec.get('username')} db={sec.get('dbname')}"
    )
    url = URL.create(
        "postgresql+psycopg",
        username=sec["username"],
        password=sec["password"],
        host=sec["host"],
        port=int(sec["port"]),
        database=sec["dbname"],
    )
    return create_engine(url, connect_args={"sslmode": "require"}), {
        "host": sec["host"],
        "port": int(sec["port"]),
        "dbname": sec["dbname"],
        "username": sec["username"],
    }


def _table_exists(conn, name: str) -> bool:
    return bool(conn.execute(text("SELECT to_regclass(:n)"), {"n": f"public.{name}"}).scalar())


def _org_rows(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT id::text AS organization_id, slug, display_name "
            "FROM organization ORDER BY slug"
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def _count_by_org(conn, table: str) -> dict[str, int]:
    if not _table_exists(conn, table):
        return {"__missing__": 1}
    # app_user não tem organization_id direto — conta memberships distintas por org
    if table == "app_user":
        q = text(
            """
            SELECT om.organization_id::text AS organization_id, COUNT(DISTINCT om.user_id)::int AS n
            FROM organization_membership om
            GROUP BY om.organization_id
            """
        )
        return {r["organization_id"]: int(r["n"]) for r in conn.execute(q).mappings()}
    q = text(
        f"""
        SELECT organization_id::text AS organization_id, COUNT(*)::int AS n
        FROM {table}
        GROUP BY organization_id
        """
    )
    return {r["organization_id"]: int(r["n"]) for r in conn.execute(q).mappings()}


def snapshot_demo() -> dict[str, Any]:
    eng, ident = _engine("panne/demo/db/migrator", "panne_demo", "panne_demo_migrator")
    payload: dict[str, Any] = {
        "phase_hint": "pre_or_post",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "database": ident["dbname"],
        "username": ident["username"],
        "host_sanitized": ident["host"].split(".")[0] + ".…",
        "port": ident["port"],
        "read_only": True,
        "organizations": [],
        "totals": {},
        "alembic_head": None,
        "notes": [
            "usuarios_demo = memberships distintas (app_user via organization_membership)",
            "receitas = formulation",
            "produtos = technical_product",
            "entradas_fiscais = fiscal_inbound_document (0 se migration < 0022)",
        ],
    }
    with eng.connect() as conn:
        conn.execute(text(RELAX))
        conn.commit()
        try:
            payload["alembic_head"] = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
            orgs = _org_rows(conn)
            metric_maps: dict[str, dict[str, int]] = {}
            for label, table in METRICS:
                metric_maps[label] = _count_by_org(conn, table)

            for org in orgs:
                oid = org["organization_id"]
                counts = {}
                for label, _table in METRICS:
                    m = metric_maps[label]
                    if "__missing__" in m:
                        counts[label] = None  # tabela ausente
                    else:
                        counts[label] = int(m.get(oid, 0))
                payload["organizations"].append(
                    {
                        "organization_id": oid,
                        "slug": org["slug"],
                        "display_name": org["display_name"],
                        "counts": counts,
                    }
                )

            totals: dict[str, int | None] = {}
            for label, _table in METRICS:
                m = metric_maps[label]
                if "__missing__" in m:
                    totals[label] = None
                else:
                    totals[label] = int(sum(m.values()))
            payload["totals"] = totals
        finally:
            conn.execute(text(RESTORE))
            conn.commit()
    eng.dispose()
    return payload


def prove_panne_intact() -> dict[str, Any]:
    """Prova rápida: banco panne acessível (sem mutação). Schema pode estar pré-migração."""
    eng, ident = _engine("panne/prod/db/migrator", "panne", "panne_prod_migrator")
    out: dict[str, Any] = {
        "database": ident["dbname"],
        "username": ident["username"],
        "host_sanitized": ident["host"].split(".")[0] + ".…",
    }
    with eng.connect() as conn:
        out["current_database"] = conn.execute(text("SELECT current_database()")).scalar()
        assert out["current_database"] == "panne"
        out["alembic_version_table"] = conn.execute(
            text("SELECT to_regclass('public.alembic_version')")
        ).scalar()
        if out["alembic_version_table"]:
            out["alembic_head"] = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        else:
            out["alembic_head"] = None
        out["organization_table"] = conn.execute(
            text("SELECT to_regclass('public.organization')")
        ).scalar()
        if out["organization_table"]:
            out["organization_count"] = int(
                conn.execute(text("SELECT COUNT(*) FROM organization")).scalar() or 0
            )
        else:
            out["organization_count"] = None
        if _table_exists(conn, "technical_product"):
            out["produtos"] = int(
                conn.execute(text("SELECT COUNT(*) FROM technical_product")).scalar() or 0
            )
        else:
            out["produtos"] = None
        out["note"] = (
            "DB panne intacto = identidade correta; ausência de tabelas = não migrado "
            "(não é redução de demo)"
        )
    eng.dispose()
    return out


def compare(pre: dict[str, Any], post: dict[str, Any]) -> dict[str, Any]:
    """Qualquer redução inesperada → fail=True."""
    failures: list[str] = []
    org_diffs: list[dict[str, Any]] = []
    pre_by = {o["organization_id"]: o for o in pre.get("organizations", [])}
    post_by = {o["organization_id"]: o for o in post.get("organizations", [])}
    if set(pre_by) != set(post_by):
        failures.append("organization_set_changed")

    for oid, pre_org in pre_by.items():
        post_org = post_by.get(oid)
        if not post_org:
            failures.append(f"missing_org:{oid}")
            continue
        delta: dict[str, Any] = {}
        for label, _t in METRICS:
            a = pre_org["counts"].get(label)
            b = post_org["counts"].get(label)
            if a is None and b is None:
                continue
            if a is None and b is not None:
                delta[label] = {"pre": a, "post": b, "delta": "table_appeared"}
                continue
            if b is None and a is not None:
                failures.append(f"{pre_org['slug']}:{label}:table_missing")
                delta[label] = {"pre": a, "post": b, "delta": "table_missing"}
                continue
            d = int(b) - int(a)
            delta[label] = {"pre": a, "post": b, "delta": d}
            if d < 0:
                failures.append(f"{pre_org['slug']}:{label}:reduced({a}->{b})")
        org_diffs.append(
            {
                "organization_id": oid,
                "slug": pre_org.get("slug"),
                "deltas": delta,
            }
        )

    # Totais
    total_delta = {}
    for label, _t in METRICS:
        a = pre.get("totals", {}).get(label)
        b = post.get("totals", {}).get(label)
        if isinstance(a, int) and isinstance(b, int):
            total_delta[label] = {"pre": a, "post": b, "delta": b - a}
            if b < a:
                failures.append(f"total:{label}:reduced({a}->{b})")

    return {
        "fail": bool(failures),
        "failures": failures,
        "organization_deltas": org_diffs,
        "total_deltas": total_delta,
        "pre_head": pre.get("alembic_head"),
        "post_head": post.get("alembic_head"),
        "rule": "redução inesperada → interromper publicação e rollback da aplicação",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre", "post"], required=True)
    parser.add_argument("--compare", help="Caminho do JSON pre para comparar no post")
    parser.add_argument("--skip-panne-proof", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"phase={args.phase}", flush=True)
    print("mode=read_only no_reseed no_truncate", flush=True)

    try:
        demo = snapshot_demo()
    except Exception as exc:
        print(f"ERROR demo_snapshot={type(exc).__name__}: {exc}", flush=True)
        return 2

    demo["phase"] = args.phase
    out_path = OUT_DIR / f"panne-demo-counts-{args.phase}.json"
    out_path.write_text(json.dumps(demo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote={out_path.name}", flush=True)
    print(f"demo_head={demo.get('alembic_head')}", flush=True)
    print(f"orgs={len(demo.get('organizations', []))}", flush=True)
    print(f"totals={json.dumps(demo.get('totals'), ensure_ascii=False)}", flush=True)

    if not args.skip_panne_proof:
        try:
            panne = prove_panne_intact()
            panne_path = OUT_DIR / f"panne-prod-intact-{args.phase}.json"
            panne_path.write_text(json.dumps(panne, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                f"panne_intact head={panne.get('alembic_head')} orgs={panne.get('organization_count')} "
                f"produtos={panne.get('produtos')}",
                flush=True,
            )
        except Exception as exc:
            print(f"ERROR panne_proof={type(exc).__name__}: {exc}", flush=True)
            return 3

    if args.phase == "post":
        if not args.compare:
            print("ERROR --compare obrigatório no post", flush=True)
            return 4
        pre = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        result = compare(pre, demo)
        cmp_path = OUT_DIR / "panne-demo-counts-compare.json"
        cmp_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"compare_fail={result['fail']}", flush=True)
        if result["failures"]:
            print(f"failures={json.dumps(result['failures'], ensure_ascii=False)}", flush=True)
        if result["fail"]:
            print("STOP publication — unexpected reduction — rollback app", flush=True)
            return 10

    print("OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
