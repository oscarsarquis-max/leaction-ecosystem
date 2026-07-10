"""Inspeciona submissions no banco (uso operacional)."""
from __future__ import annotations

from app import create_app
from app.database.models import AssessmentSubmission, Tenant, TenantUser, User, db

app = create_app()
with app.app_context():
    subs = (
        AssessmentSubmission.query.order_by(AssessmentSubmission.created_at.desc())
        .limit(15)
        .all()
    )
    print("=== Submissions ===")
    for s in subs:
        u = db.session.get(User, s.user_id)
        t = db.session.get(Tenant, s.tenant_id)
        resp_count = len(s.responses) if hasattr(s, "responses") else "?"
        print(
            f"{s.id} | {s.status} | score={s.score_global} | report={bool(s.report_data)} | "
            f"fw={s.framework_id} | user={u.email if u else '?'} | tenant={t.name if t else '?'}"
        )

    print("\n=== Leads ===")
    leads = TenantUser.query.filter_by(role="led").limit(20).all()
    for m in leads:
        u = db.session.get(User, m.user_id)
        t = db.session.get(Tenant, m.tenant_id)
        if u:
            print(f"{u.email} | tenant={t.name if t else m.tenant_id}")
