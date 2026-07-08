"""Aplicação Flask principal do inove4us.

Atua como ponte entre o frontend React e a camada de serviços de IA.
"""

import os
import sys

from dotenv import load_dotenv

# Carrega as variáveis de ambiente do .env logo no topo, ANTES de qualquer
# import que instancie clientes (Boto3/LangChain leem as credenciais da AWS
# e o SQLAlchemy lê as credenciais do PostgreSQL a partir dessas variáveis).
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, jsonify  # noqa: E402
from flask_cors import CORS  # noqa: E402

# Permite importar os pacotes irmãos (services, database) que ficam na raiz do projeto.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from routes.ai_routes import ai_routes  # noqa: E402


def create_app():
    app = Flask(__name__)

    # Libera requisições vindas do frontend React (Vite dev server).
    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173"]}},
    )

    app.register_blueprint(ai_routes, url_prefix="/api")

    @app.get("/")
    def index():
        return jsonify({"name": "inove4us API", "docs": "/api/health"})

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
