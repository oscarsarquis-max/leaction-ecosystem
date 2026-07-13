"""Seed CLI — injeta matriz canônica PanelDX de OKRs para um tenant."""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask import g

from app import create_app
from app.database.models import Tenant, db
from app.services.okr_service import OkrService


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed canônico de OKRs PanelDX")
    parser.add_argument(
        "--tenant-id",
        help="UUID do tenant. Se omitido, usa o primeiro tenant encontrado.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.tenant_id:
            tenant = db.session.get(Tenant, uuid.UUID(args.tenant_id))
        else:
            tenant = db.session.query(Tenant).order_by(Tenant.created_at.asc()).first()

        if not tenant:
            print("Nenhum tenant encontrado.")
            return 1

        g.tenant_id = tenant.id
        seeded = OkrService().ensure_canonical_seed()
        data = OkrService().list_dashboard()
        print(
            f"tenant={tenant.id} name={getattr(tenant, 'name', '')} "
            f"seeded={seeded} drivers={len(data['drivers'])}"
        )
        for driver in data["drivers"]:
            print(f"  [{driver['sort_order']}] {driver['name']}")
            for obj in driver.get("objectives") or []:
                print(f"      O: {obj['description'][:80]}...")
                for kr in obj.get("key_results") or []:
                    print(f"        KR: {kr['description']} (alvo={kr['target_value']})")
            for kpi in driver.get("kpis") or []:
                fin = "FIN" if kpi["is_financial"] else "OPS"
                print(f"      KPI[{fin}]: {kpi['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
