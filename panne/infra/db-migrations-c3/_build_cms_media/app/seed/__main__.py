"""CLI de seed. Sem dependência nova. Credenciais só do ambiente do processo."""

from __future__ import annotations

import argparse
import os
import time
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.seed import ALEMBIC_HEAD, DEFAULT_ANCHOR, SCENARIO_VERSION
from app.seed.demo import seed_demo
from app.seed.dry_run import inspect_dry_run
from app.seed.ids import as_date
from app.seed.manifest import build_manifest, coverage_report, write_manifest
from app.seed.reference import seed_reference
from app.seed.schema import apply_alembic, current_alembic, recreate_isolated_database
from app.seed.smoke import run_journeys, seed_smoke
from app.seed.target import SeedTargetError, describe_target, sync_url


def _url(explicit: str | None) -> str:
    raw = explicit or os.environ.get("PANNE_SEED_DATABASE_URL") or os.environ.get("PANNE_DATABASE_URL")
    if not raw:
        raise SeedTargetError("informe --database-url ou PANNE_SEED_DATABASE_URL")
    return raw


def _env() -> str:
    return (os.environ.get("PANNE_ENV") or "local").strip().lower()


def _session(url: str):
    engine = create_engine(sync_url(url), future=True)
    return sessionmaker(bind=engine, future=True)(), engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description="Seeds reference/demo/smoke da Panne")
    parser.add_argument("command", choices=["reference", "demo", "smoke", "inspect", "verify", "coverage", "dry-run"])
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--anchor-date", default=DEFAULT_ANCHOR)
    parser.add_argument("--scenario", default="application")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    env = _env()
    if env == "production":
        print("Recusado: ambiente production.")
        return 2
    url = _url(args.database_url)
    try:
        target = describe_target(url, env)
    except SeedTargetError as exc:
        print(f"Recusado: {exc}")
        return 2
    print(f"Alvo resolvido: {target['database']} em {target['host']}:{target['port']} (env={env})")

    if args.command == "inspect":
        print(f"cenário={SCENARIO_VERSION} alembic_esperado={ALEMBIC_HEAD}")
        try:
            print(f"alembic_atual={current_alembic(url)}")
        except Exception as exc:
            print(f"alembic_atual=indisponível ({exc})")
        return 0

    if args.rebuild:
        recreate_isolated_database(url, env)
        apply_alembic(url)

    session, engine = _session(url)
    started = time.perf_counter()
    gaps: list[str] = []
    try:
        if args.command == "reference":
            created = seed_reference(session)
            session.commit()
            print(created)
        elif args.command == "dry-run":
            plan = inspect_dry_run(session, anchor=as_date(args.anchor_date), target=target)
            print(plan)
            if plan.get("mutated"):
                session.rollback()
                return 2
        elif args.command == "demo":
            world = seed_demo(session, anchor=as_date(args.anchor_date))
            session.commit()
            gaps = world.gaps
            print({"org": world.organization.slug, "gaps": gaps})
        elif args.command == "smoke":
            result = seed_smoke(session, scenario=args.scenario, anchor=as_date(args.anchor_date))
            session.commit()
            print(result)
        elif args.command in {"verify", "coverage"}:
            journeys = run_journeys(session)
            print(journeys)
            if args.command == "coverage":
                payload = build_manifest(
                    session,
                    anchor=as_date(args.anchor_date),
                    gaps=gaps,
                    elapsed_s=time.perf_counter() - started,
                    alembic_head=current_alembic(url),
                )
                text = coverage_report(payload)
                out = Path(args.out) if args.out else Path("seed-coverage.md")
                out.write_text(text, encoding="utf-8")
                write_manifest(payload, out.with_suffix(".json"))
                print(text)
        return 0
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
