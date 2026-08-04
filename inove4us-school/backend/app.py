"""inove4us School — API B2B (Torre de Controle).

Independente do inove4us B2C (professores). Não importa código de outras apps.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()


def _version() -> str:
    root = Path(__file__).resolve().parents[1]
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-school-secret")
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
    from comunicacoes_api import bp as comunicacoes_bp
    from secretaria_api import bp as secretaria_bp
    from secretaria_routes import bp as secretaria_academica_bp
    from webhook_actionhub_routes import bp as actionhub_webhook_bp
    from webhook_b2c_routes import bp as b2c_webhook_bp
    from billing_routes import billing_bp
    from curadoria_routes import bp as curadoria_bp
    from pei_ciclo_routes import bp as pei_ciclo_bp

    app.register_blueprint(metodologias_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(pei_bp)
    app.register_blueprint(cms_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(equipe_bp)
    app.register_blueprint(comunicacoes_bp)
    app.register_blueprint(secretaria_bp)
    # Secretaria Acadêmica — CRUD flat + alocação (TEACHER_ALLOCATED)
    app.register_blueprint(secretaria_academica_bp)
    app.register_blueprint(billing_bp)
    # Curadoria bottom-up (professor → pedagogo)
    app.register_blueprint(curadoria_bp)
    # Ciclo Vivo do PEI (adaptação × metodologia + curadoria PEI)
    app.register_blueprint(pei_ciclo_bp)
    # S2S Outbox — sem sessão de gestor / RBAC
    app.register_blueprint(actionhub_webhook_bp)
    # Ponte interna School ← B2C (JWT HS256)
    app.register_blueprint(b2c_webhook_bp)

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

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5012"))
    app.run(host="0.0.0.0", port=port, debug=True)
