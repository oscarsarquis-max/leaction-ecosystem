from app import create_app
from app.database.models import Tenant, TenantFramework, User, TenantUser, AssessmentSubmission, db
from app.core.tenant_framework_resolver import resolve_framework_for_tenant

app = create_app()
with app.app_context():
    for email in ["gestor@leactionengenharia.com.br", "vitor@vrsengenharia.com.br", "engenharia@paneldx.com.br"]:
        u = User.query.filter_by(email=email).first()
        if not u:
            print(f"\n{email}: USER NOT FOUND")
            continue
        memberships = TenantUser.query.filter_by(user_id=u.id).all()
        for m in memberships:
            t = db.session.get(Tenant, m.tenant_id)
            fw = resolve_framework_for_tenant(m.tenant_id)
            subs = AssessmentSubmission.query.filter_by(tenant_id=m.tenant_id, user_id=u.id).all()
            print(f"\n{email} | role={m.role} | tenant={t.name} | resolved_fw={fw.id if fw else None}")
            for s in subs:
                print(f"  sub {s.id} status={s.status} fw={s.framework_id} score={s.score_global} report={bool(s.report_data)}")
            links = TenantFramework.query.filter_by(tenant_id=m.tenant_id).all()
            for l in links:
                print(f"  link fw={l.framework_id} status={l.status}")
