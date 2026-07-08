import json
import logging
import os
import threading

from flask import Flask, jsonify, request
from sqlalchemy import create_engine

from catalog_service import seed_indicadores_catalog
from config import DATABASE_URL, JSON_PROCESSED_DIR
from db_migrations import ensure_schema_indexes, upgrade_schema
from ingest_service import backfill_medicoes_from_processados, process_json_ingestion
from models import Base

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = Flask(__name__)
_watcher_started = False
logger = logging.getLogger(__name__)


def parse_json_payload() -> tuple[str, str]:
    if request.files:
        upload = request.files.get("file") or next(iter(request.files.values()), None)
        if upload is None or upload.filename == "":
            raise ValueError("Nenhum ficheiro JSON enviado")
        raw_content = upload.read().decode("utf-8")
        return upload.filename, raw_content

    payload = request.get_json(silent=True)
    if payload is None:
        raise ValueError("Corpo da requisição vazio ou JSON inválido")

    return "api/ingest", json.dumps(payload, ensure_ascii=False)


@app.route("/api/ingest", methods=["POST"])
def ingest():
    try:
        nome_arquivo, raw_content = parse_json_payload()
    except (ValueError, json.JSONDecodeError) as exc:
        return jsonify({"erro": str(exc)}), 400

    try:
        resultado = process_json_ingestion(
            engine,
            nome_arquivo=nome_arquivo,
            raw_content=raw_content,
        )
    except Exception as exc:
        logger.exception("Erro ao ingerir payload")
        return jsonify({"erro": "Falha ao gravar medição na base de dados", "detalhe": str(exc)}), 500

    medicao = resultado.medicao
    if medicao is None:
        return jsonify({"erro": "Medição não foi criada durante a ingestão"}), 500

    if not resultado.sucesso:
        return (
            jsonify(
                {
                    "erro": resultado.mensagem or medicao.detalhe_status,
                    "id": medicao.id,
                    "status_import": medicao.status_import,
                    "detalhe_status": medicao.detalhe_status,
                }
            ),
            400,
        )

    indicador = medicao.indicador
    return (
        jsonify(
            {
                "id": medicao.id,
                "indicador_id": medicao.indicador_id,
                "nome_arquivo": medicao.nome_arquivo,
                "status_import": medicao.status_import,
                "data_referencia": medicao.data_referencia.isoformat()
                if medicao.data_referencia
                else None,
                "data_importacao": medicao.data_importacao.isoformat(),
                "cod_indicador": indicador.cod_indicador if indicador else None,
                "nome_indicador": indicador.nome_indicador if indicador else None,
                "nome_grupo": indicador.nome_grupo if indicador else None,
            }
        ),
        201,
    )


@app.route("/health", methods=["GET"])
def health():
    from config import JSON_FAILED_DIR, JSON_IMPORT_DIR, JSON_PROCESSED_DIR

    return jsonify(
        {
            "status": "ok",
            "watcher": {
                "import_dir": str(JSON_IMPORT_DIR),
                "processed_dir": str(JSON_PROCESSED_DIR),
                "failed_dir": str(JSON_FAILED_DIR),
            },
        }
    )


@app.route("/health/ia", methods=["GET"])
def health_ia():
    from ai.bedrock_client import BEDROCK_MODEL_ID, BEDROCK_REGION, testar_conexao

    try:
        resultado = testar_conexao()
        return jsonify(
            {
                "status": "ok",
                "provider": "aws-bedrock",
                "model_id": BEDROCK_MODEL_ID,
                "region": BEDROCK_REGION,
                "resposta": resultado["resposta"],
            }
        )
    except Exception as exc:
        logger.exception("Falha no health check de IA")
        return (
            jsonify(
                {
                    "status": "erro",
                    "provider": "aws-bedrock",
                    "model_id": BEDROCK_MODEL_ID,
                    "region": BEDROCK_REGION,
                    "detalhe": str(exc),
                }
            ),
            503,
        )


def init_db():
    upgrade_schema(engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema_indexes(engine)
    seed_indicadores_catalog(engine)
    imported = backfill_medicoes_from_processados(engine, JSON_PROCESSED_DIR)
    if imported:
        logger.info("%s medições importadas do backfill em processados/.", imported)


def should_start_watcher() -> bool:
    if os.environ.get("DISABLE_JSON_WATCHER") == "1":
        return False

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True

    if not app.debug:
        return True

    return False


def start_watcher_background() -> None:
    global _watcher_started

    if _watcher_started or not should_start_watcher():
        return

    from config import JSON_IMPORT_DIR
    from watcher import start_watcher

    thread = threading.Thread(
        target=lambda: start_watcher(blocking=True),
        name="json-import-watcher",
        daemon=True,
    )
    thread.start()
    _watcher_started = True
    logger.info("Watcher de importação JSON iniciado em: %s", JSON_IMPORT_DIR)


def bootstrap_services() -> None:
    init_db()
    start_watcher_background()


if __name__ == "__main__":
    bootstrap_services()
    app.run(host="0.0.0.0", port=5000, debug=True)
