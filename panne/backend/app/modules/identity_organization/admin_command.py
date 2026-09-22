"""Comando interno da Panne para emitir, consultar e revogar autorização de onboarding.

Não é rota HTTP. O cliente não executa este módulo e não escolhe a condição comercial.
Usa a conexão administrativa (PANNE_DATABASE_URL), nunca o papel de execução e nunca a Demo.

Exemplos, a partir de panne/backend, com o ambiente já apontando para o banco alvo:

  python -m app.modules.identity_organization.admin_command issue --email pessoa@exemplo --condition complimentary --hours 72
  python -m app.modules.identity_organization.admin_command list --email pessoa@exemplo
  python -m app.modules.identity_organization.admin_command revoke --id <autorizacao>

A saída traz só identificadores e o estado. Não imprime e-mail, documento nem segredo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.modules.identity_organization.onboarding import (
    AuthorizationRecord,
    issue_onboarding_authorization,
    list_onboarding_authorizations,
    revoke_onboarding_authorization,
)
from app.modules.identity_organization.services import IdentityResolutionError

_RUNTIME_ROLES = frozenset({"panne_runtime", "panne_prod_runtime", "panne_demo_runtime"})


def assert_admin_target(database_url: str, env_name: str) -> None:
    parsed = urlparse(database_url)
    name = parsed.path.lstrip("/").split("?")[0]
    if env_name == "demo" or name == "panne_demo":
        raise SystemExit("recusado: este comando não opera na Demo")
    if name != "panne":
        raise SystemExit("recusado: o banco lógico precisa ser panne")
    if (parsed.username or "") in _RUNTIME_ROLES:
        raise SystemExit("recusado: use a conexão administrativa, não o papel de execução")


def _public(record: AuthorizationRecord) -> dict[str, object]:
    return {
        "id": str(record.id),
        "status": record.status,
        "commercial_condition": record.commercial_condition,
        "expires_at": record.expires_at.isoformat(),
        "clients_created": record.clients_created,
        "bound": record.bound,
        "organization_id": None if record.organization_id is None else str(record.organization_id),
    }


def _print(records: list[AuthorizationRecord] | AuthorizationRecord) -> None:
    payload = _public(records) if isinstance(records, AuthorizationRecord) else [_public(item) for item in records]
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def _session() -> Session:
    raw = os.environ.get("PANNE_DATABASE_URL", "")
    assert_admin_target(raw, os.environ.get("PANNE_ENV", ""))
    url = raw.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(url, future=True)
    return sessionmaker(bind=engine, future=True)()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Autorização de onboarding emitida pela Panne")
    commands = parser.add_subparsers(dest="command", required=True)
    issue = commands.add_parser("issue")
    issue.add_argument("--email", required=True)
    issue.add_argument("--condition", required=True, choices=("complimentary", "standard"))
    issue.add_argument("--hours", type=int, default=72)
    listed = commands.add_parser("list")
    listed.add_argument("--email", required=True)
    revoked = commands.add_parser("revoke")
    revoked.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    session = _session()
    try:
        if args.command == "issue":
            try:
                created = issue_onboarding_authorization(
                    session,
                    email=args.email,
                    commercial_condition=args.condition,
                    valid_hours=args.hours,
                )
            except IntegrityError:
                session.rollback()
                raise SystemExit("recusado: já existe autorização aberta para esta conta") from None
            session.commit()
            _print(created)
        elif args.command == "list":
            _print(list_onboarding_authorizations(session, args.email))
        else:
            updated = revoke_onboarding_authorization(session, UUID(args.id))
            session.commit()
            _print(updated)
    except IdentityResolutionError as exc:
        session.rollback()
        raise SystemExit(f"recusado: {exc.reason}") from None
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
