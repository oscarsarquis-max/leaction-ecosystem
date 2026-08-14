"""inove4us School — API B2B (Torre de Controle).

Independente do inove4us B2C (professores). Não importa código de outras apps.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Preenche só chaves ausentes — nunca sobrescreve env já injetada (PM2/ECS).
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _version() -> str:
    root = Path(__file__).resolve().parents[1]
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _git_sha() -> str:
    for key in ("GIT_SHA", "SOURCE_COMMIT", "GITHUB_SHA", "COMMIT_SHA"):
        val = (os.getenv(key) or "").strip()
        if val:
            return val[:12]
    root = Path(__file__).resolve().parents[1]
    try:
        return (root / "GIT_SHA").read_text(encoding="utf-8").strip()[:12] or "unknown"
    except OSError:
        return "unknown"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-school-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    if (os.getenv("INOVE4US_SCHOOL_ENV") or os.getenv("FLASK_ENV") or "").lower() == "production":
        app.config["SESSION_COOKIE_SECURE"] = True
    app.config["ACTIONHUB_WEBHOOK_SECRET"] = (
        os.getenv("ACTIONHUB_WEBHOOK_SECRET")
        or os.getenv("ACTION_HUB_APP_SECRET")
        or ""
    ).strip()

    origins = [
        o.strip()
        for o in (os.getenv("CORS_ORIGINS") or "http://localhost:5175").split(",")
        if o.strip()
    ]
    CORS(app, origins=origins, supports_credentials=True)

    from metodologias_api import bp as metodologias_bp
    from dashboard_api import bp as dashboard_bp
    from pei_api import bp as pei_bp
    from cms_api import bp as cms_bp
    from auth_api import bp as auth_bp
    from equipe_api import bp as equipe_bp
    from secretaria_routes import bp as secretaria_academica_bp
    from webhook_actionhub_routes import bp as actionhub_webhook_bp
    from webhook_b2c_routes import bp as b2c_webhook_bp
    from billing_routes import billing_bp
    from curadoria_routes import bp as curadoria_bp
    from pei_documental_routes import bp as pei_documental_bp
    from tracking_routes import tracking_bp
    from avisos_api import bp as avisos_bp
    from roteiro_api import bp as roteiro_bp
    from gatekeeper_routes import register_gatekeeper

    app.register_blueprint(metodologias_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(pei_bp)
    app.register_blueprint(cms_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(equipe_bp)
    # Secretaria Acadêmica — superfície unificada (/api/secretaria/*)
    app.register_blueprint(secretaria_academica_bp)
    app.register_blueprint(billing_bp)
    # Curadoria bottom-up (professor → pedagogo)
    app.register_blueprint(curadoria_bp)
    # PEI canônico: AEE + pei_alunos + Adaptações na Prática (legado Ciclo Vivo removido)
    app.register_blueprint(pei_documental_bp)
    # Action-Sponge — sensor CRM (origem inove4us-school)
    app.register_blueprint(tracking_bp)
    # Quadro de Avisos → Mesa do Professor
    app.register_blueprint(avisos_bp)
    app.register_blueprint(roteiro_bp)
    # S2S Outbox — sem sessão de gestor / RBAC
    app.register_blueprint(actionhub_webhook_bp)
    # Ponte interna School ← B2C (JWT HS256)
    app.register_blueprint(b2c_webhook_bp)
    register_gatekeeper(app)

    @app.get("/api/health")
    def health():
        db_ok = False
        try:
            from db import ping

            db_ok = ping()
        except Exception:
            db_ok = False
        return jsonify(
            {
                "ok": True,
                "app": "inove4us-school",
                "product": "inove4us School",
                "audience": "b2b",
                "version": _version(),
                "git_sha": _git_sha(),
                "db": "inove4us_school" if db_ok else "unreachable",
            }
        )

    @app.get("/api/meta")
    def meta():
        """Contrato público mínimo — sem dados de gestão."""
        return jsonify(
            {
                "app": "inove4us-school",
                "role": "torre_de_controle",
                "login": "gestores (Diretor | Coordenador)",
                "bridge_to_b2c": "school_professores_vinculo.professor_b2c_id",
                "tables_prefix": "school_",
                "dev_instituicao_id": os.getenv(
                    "DEV_INSTITUICAO_ID",
                    "a1111111-1111-4111-8111-111111111111",
                ),
                "lexico_pedagogico": {
                    "vetores": [
                        {
                            "id": "dia_a_dia",
                            "nome": "Dia a Dia",
                            "subtitulo": "ciclo rápido",
                        },
                        {
                            "id": "desafio",
                            "nome": "Desafio",
                            "subtitulo": "método inove4us",
                        },
                    ],
                    "familias": [
                        "Indutivas",
                        "Agilidade",
                        "Contextuais",
                        "Dedutivas",
                    ],
                },
            }
        )

    # SPA React (Vite) — em produção o dist fica em SPA_DIR / frontend/dist
    root = Path(__file__).resolve().parents[1]
    spa_dir = Path(os.environ.get("SPA_DIR") or (root / "frontend" / "dist"))
    if spa_dir.is_dir():

        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def spa_fallback(path: str):
            if path.startswith("api/"):
                return jsonify({"error": "Not found"}), 404
            target = spa_dir / path
            if path and target.is_file():
                return send_from_directory(spa_dir, path)
            return send_from_directory(spa_dir, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5012"))
    # Windows + Start-Process com log redirecionado: o reloader mata o PID e o Vite
    # devolve 500 (ECONNRESET) no /api/auth/login.
    use_reloader = os.getenv("FLASK_USE_RELOADER", "0" if os.name == "nt" else "1")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True,
        use_reloader=use_reloader.strip().lower() in ("1", "true", "yes"),
    )
