"""Inspeciona jornada e diagnóstico de um utilizador pelo e-mail."""
from __future__ import annotations

import sys

from app import create_app
from app.core.tenant_framework_resolver import resolve_framework_for_tenant
from app.database.models import AssessmentSubmission, Tenant, TenantUser, User, db
from app.services.assessment_service import AssessmentService
from app.services.client_journey_service import build_journey_payload

if __name__ == "__main__":
    email = (sys.argv[1] if len(sys.argv) > 1 else "gestor@leactionengenharia.com.br").lower()
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"USER NOT FOUND: {email}")
            sys.exit(1)
        print(f"User: {user.email} id={user.id}")
        for m in TenantUser.query.filter_by(user_id=user.id).all():
            t = db.session.get(Tenant, m.tenant_id)
            fw = resolve_framework_for_tenant(m.tenant_id)
            journey = build_journey_payload(t) if t else None
            subs = AssessmentSubmission.query.filter_by(tenant_id=m.tenant_id, user_id=user.id).all()
            print(f"\n--- membership role={m.role} tenant={t.name if t else m.tenant_id} ---")
            print(f"resolved_framework={fw.id if fw else None}")
            if journey:
                print(f"journey status={journey.get('status_ia')}")
                print(f"latest_submission_id={journey.get('latest_submission_id')}")
                print(f"context_filled={journey.get('context_filled')}")
                print(f"flags={journey.get('flags')}")
            for s in subs:
                print(
                    f"  submission {s.id} | {s.status} | score={s.score_global} | "
                    f"report={bool(s.report_data)} | fw={s.framework_id}"
                )
