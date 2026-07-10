import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from app.api.admin_users_routes import admin_users_bp
from app.api.client_journey_routes import client_journey_bp
from app.api.assessment_routes import assessment_bp
from app.api.auth_routes import auth_bp
from app.api.framework_routes import framework_bp
from app.api.kaizen_routes import kaizen_bp
from app.api.operational_routes import operational_bp
from app.api.questions_routes import questions_bp
from app.api.td_routes import td_bp
from app.api.users_routes import users_bp
from app.api.seed_routes import seed_bp
from app.api.webhook_routes import webhook_bp
from app.core.gemba_webhook_auth import resolve_gemba_webhook_secret
from app.core.middlewares import load_tenant_context
from app.database.models import db
import app.models.kaizen_models  # noqa: F401 — registra tabelas Gemba-Kaizen
import app.models.operational_models  # noqa: F401 — unidades operacionais e relatórios
import app.models.td_models  # noqa: F401 — Transformação Digital (Plano + Sprints)

BACKEND_DIR = Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(BACKEND_DIR.parent / ".env")

    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost:5432/chamelleon",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEBUG=os.getenv("FLASK_DEBUG", "1") == "1",
        GEMBA_WEBHOOK_API_KEY=resolve_gemba_webhook_secret(),
    )

    db.init_app(app)
    _enable_dev_cors(app)
    app.before_request(load_tenant_context)
    app.register_blueprint(admin_users_bp, url_prefix="/api/admin")
    app.register_blueprint(client_journey_bp, url_prefix="/api/client")
    app.register_blueprint(assessment_bp, url_prefix="/api/assessment")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(questions_bp, url_prefix="/api/questions")
    app.register_blueprint(framework_bp, url_prefix="/api/framework")
    app.register_blueprint(kaizen_bp, url_prefix="/api/kaizen")
    app.register_blueprint(operational_bp, url_prefix="/api/operational")
    app.register_blueprint(td_bp, url_prefix="/api/td")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(seed_bp, url_prefix="/api")
    app.register_blueprint(webhook_bp, url_prefix="/api/webhooks")

    with app.app_context():
        db.create_all()
        _apply_schema_patches()
        from app.core.bootstrap import ensure_published_framework

        ensure_published_framework()

    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    return app


def _enable_dev_cors(app: Flask) -> None:
    """Permite chamadas diretas ao backend em desenvolvimento (sem proxy Vite)."""

    @app.after_request
    def add_cors_headers(response):
        if not app.debug:
            return response
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, X-Tenant-ID, X-User-ID, X-Integration-Key, "
            "X-Gemba-Webhook-Key, X-Gemba-Signature, Authorization"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        return response

    @app.route("/api/<path:_path>", methods=["OPTIONS"])
    def cors_preflight(_path: str):
        return "", 204


def _apply_schema_patches() -> None:
    """Aplica alterações incrementais que db.create_all() não cobre em tabelas existentes."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "assessment_responses" in tables:
        cols = {c["name"] for c in inspector.get_columns("assessment_responses")}
        if "submission_id" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE assessment_responses "
                    "ADD COLUMN submission_id UUID "
                    "REFERENCES assessment_submissions(id) ON DELETE CASCADE"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_assessment_responses_submission_id "
                    "ON assessment_responses (submission_id)"
                )
            )
            db.session.commit()

    if "users" in tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "is_active" not in cols:
            db.session.execute(
                text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
            )
            db.session.commit()

    if "assessment_submissions" in tables:
        cols = {c["name"] for c in inspector.get_columns("assessment_submissions")}
        if "report_data" not in cols:
            db.session.execute(
                text("ALTER TABLE assessment_submissions ADD COLUMN report_data JSONB")
            )
            db.session.commit()

    if "action_plans" in tables:
        cols = {c["name"] for c in inspector.get_columns("action_plans")}
        if "structured_plan" not in cols:
            db.session.execute(
                text("ALTER TABLE action_plans ADD COLUMN structured_plan JSONB")
            )
            db.session.commit()

    if "assessment_items" in tables:
        cols = {c["name"] for c in inspector.get_columns("assessment_items")}
        if "item_metadata" not in cols:
            db.session.execute(
                text("ALTER TABLE assessment_items ADD COLUMN item_metadata JSONB")
            )
            db.session.commit()

    if "assessment_submissions" in tables:
        maturity_columns = {
            "pdom_pres": "JSONB",
            "pdim_pres": "JSONB",
            "pgen_pres": "DOUBLE PRECISION",
            "pdom_fut": "JSONB",
            "pdim_fut": "JSONB",
            "pgen_fut": "DOUBLE PRECISION",
            "pdom_gap": "JSONB",
            "pdim_gap": "JSONB",
            "pgen_gap": "DOUBLE PRECISION",
            "pdom_sect_pres": "JSONB",
            "pdim_sect_pres": "JSONB",
            "pgen_sect_pres": "DOUBLE PRECISION",
            "pdom_sect_fut": "JSONB",
            "pdim_sect_fut": "JSONB",
            "pgen_sect_fut": "DOUBLE PRECISION",
            "pdom_sect_gap": "JSONB",
            "pdim_sect_gap": "JSONB",
            "pgen_sect_gap": "DOUBLE PRECISION",
            "matrix_domain_stats": "JSONB",
            "matrix_meta": "JSONB",
            "diagnostic_status": "VARCHAR(32)",
            "evaluated_at": "TIMESTAMP WITH TIME ZONE",
        }
        cols = {c["name"] for c in inspector.get_columns("assessment_submissions")}
        for col_name, col_type in maturity_columns.items():
            if col_name not in cols:
                db.session.execute(
                    text(f"ALTER TABLE assessment_submissions ADD COLUMN {col_name} {col_type}")
                )
        db.session.commit()

    if "tenants" in tables:
        cols = {c["name"] for c in inspector.get_columns("tenants")}
        tenant_patches = {
            "journey_status": "VARCHAR(32) NOT NULL DEFAULT 'AGUARDANDO CONTEXTO'",
            "has_active_project": "BOOLEAN NOT NULL DEFAULT FALSE",
            "context_data": "JSONB",
        }
        for col_name, col_def in tenant_patches.items():
            if col_name not in cols:
                db.session.execute(
                    text(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_def}")
                )
        db.session.commit()

    if "tenant_users" in tables and "operational_sites" in tables:
        cols = {c["name"] for c in inspector.get_columns("tenant_users")}
        if "operational_site_id" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE tenant_users "
                    "ADD COLUMN operational_site_id UUID "
                    "REFERENCES operational_sites(id) ON DELETE SET NULL"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_tenant_users_operational_site_id "
                    "ON tenant_users (operational_site_id)"
                )
            )
            db.session.commit()

    # --- Módulo operacional (aditivo, sem DROP/TRUNCATE) ---
    if "operational_sites" in tables:
        cols = {c["name"] for c in inspector.get_columns("operational_sites")}
        site_patches = {
            "satellite_site_id": "VARCHAR(64)",
            "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
            "location": "VARCHAR(512)",
            "industry_type": "VARCHAR(64) NOT NULL DEFAULT 'Construcao'",
            "manager_id": "UUID",
        }
        for col_name, col_def in site_patches.items():
            if col_name not in cols:
                db.session.execute(
                    text(f"ALTER TABLE operational_sites ADD COLUMN {col_name} {col_def}")
                )
        if "manager_id" not in cols:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_operational_sites_manager_id "
                    "ON operational_sites (manager_id)"
                )
            )
        if "satellite_site_id" not in cols:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_operational_sites_satellite_site_id "
                    "ON operational_sites (satellite_site_id)"
                )
            )
        db.session.commit()

    if "daily_execution_reports" in tables:
        cols = {c["name"] for c in inspector.get_columns("daily_execution_reports")}
        report_patches = {
            "operational_site_id": "UUID",
            "gemba_event_id": "UUID",
            "report_date": "DATE",
            "sprint_daily_goal": "TEXT",
            "goal_achieved": "BOOLEAN",
            "impediment_details": "TEXT",
            "mitigation_action": "TEXT",
            "preventive_action": "TEXT",
            "raw_payload": "JSONB",
        }
        for col_name, col_def in report_patches.items():
            if col_name not in cols:
                db.session.execute(
                    text(
                        f"ALTER TABLE daily_execution_reports ADD COLUMN {col_name} {col_def}"
                    )
                )
        db.session.commit()

    if "kaizen_tickets" in tables:
        cols = {c["name"] for c in inspector.get_columns("kaizen_tickets")}
        if "escalated_to_sprint_id" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE kaizen_tickets "
                    "ADD COLUMN escalated_to_sprint_id UUID "
                    "REFERENCES td_sprints(id) ON DELETE SET NULL"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_kaizen_tickets_escalated_to_sprint_id "
                    "ON kaizen_tickets (escalated_to_sprint_id)"
                )
            )
            db.session.commit()

    if "td_sprints" in tables:
        cols = {c["name"] for c in inspector.get_columns("td_sprints")}
        sprint_patches = {
            "origin_ref_id": "UUID REFERENCES kaizen_tickets(id) ON DELETE SET NULL",
            "current_state_gap": "TEXT",
            "framework_block_id": "UUID REFERENCES framework_blocks(id) ON DELETE SET NULL",
            "framework_deliverable_id": "UUID REFERENCES framework_deliverables(id) ON DELETE SET NULL",
            "gap_fp": "DOUBLE PRECISION",
        }
        for col_name, col_def in sprint_patches.items():
            if col_name not in cols:
                db.session.execute(
                    text(f"ALTER TABLE td_sprints ADD COLUMN {col_name} {col_def}")
                )
        if "origin_ref_id" not in cols:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_td_sprints_origin_ref_id "
                    "ON td_sprints (origin_ref_id)"
                )
            )
        db.session.commit()
