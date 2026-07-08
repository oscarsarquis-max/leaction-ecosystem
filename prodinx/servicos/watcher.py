import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from catalog_service import seed_indicadores_catalog
from config import (
    DATABASE_URL,
    JSON_FAILED_DIR,
    JSON_IMPORT_DIR,
    JSON_PROCESSED_DIR,
)
from db_migrations import ensure_schema_indexes, upgrade_schema
from ingest_service import backfill_medicoes_from_processados, load_json_file, process_json_ingestion
from medicao_service import STATUS_SUCESSO
from models import Base

BASE_DIR = Path(__file__).resolve().parent
IMPORT_DIR = JSON_IMPORT_DIR
PROCESSED_DIR = JSON_PROCESSED_DIR
FAILED_DIR = JSON_FAILED_DIR
LOG_FILE = BASE_DIR / "importacao.log"

STABILITY_CHECKS = 3
STABILITY_INTERVAL_SECONDS = 0.5

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

logger = logging.getLogger("prodinx.importacao")


def setup_logging() -> None:
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def ensure_directories() -> None:
    for directory in (IMPORT_DIR, PROCESSED_DIR, FAILED_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def wait_for_file_ready(file_path: Path) -> None:
    previous_size = -1

    for _ in range(STABILITY_CHECKS):
        if not file_path.exists():
            raise FileNotFoundError(f"Ficheiro não encontrado: {file_path}")

        current_size = file_path.stat().st_size
        if current_size > 0 and current_size == previous_size:
            return

        previous_size = current_size
        time.sleep(STABILITY_INTERVAL_SECONDS)

    if previous_size <= 0:
        raise ValueError("Ficheiro ainda não contém dados válidos")


def build_destination_path(target_dir: Path, source_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = target_dir / f"{source_path.stem}_{timestamp}{source_path.suffix}"
    counter = 1

    while destination.exists():
        destination = target_dir / f"{source_path.stem}_{timestamp}_{counter}{source_path.suffix}"
        counter += 1

    return destination


def move_file(source_path: Path, target_dir: Path) -> Path:
    destination = build_destination_path(target_dir, source_path)
    shutil.move(str(source_path), str(destination))
    return destination


def is_import_candidate(file_path: Path) -> bool:
    file_path = Path(file_path).resolve()
    import_dir = IMPORT_DIR.resolve()

    if file_path.suffix.lower() != ".json":
        return False

    if not file_path.is_file():
        return False

    return file_path.parent == import_dir


def process_json_file(file_path: Path) -> None:
    file_path = Path(file_path)

    if not is_import_candidate(file_path):
        return

    logger.info("Processamento iniciado: %s", file_path.name)

    try:
        wait_for_file_ready(file_path)
        raw_content = load_json_file(file_path)
        resultado = process_json_ingestion(
            engine,
            nome_arquivo=file_path.name,
            raw_content=raw_content,
        )

        if not file_path.exists():
            logger.warning("Ficheiro removido durante processamento: %s", file_path.name)
            return

        if resultado.sucesso and resultado.medicao.status_import == STATUS_SUCESSO:
            destination = move_file(file_path, PROCESSED_DIR)
            indicador = resultado.medicao.indicador
            logger.info(
                "Importação concluída: %s -> %s (medicao id=%s, indicador=%s, id_colaborador=%s)",
                file_path.name,
                destination.name,
                resultado.medicao.id,
                indicador.cod_indicador if indicador else "—",
                resultado.medicao.id_colaborador,
            )
            return

        destination = move_file(file_path, FAILED_DIR)
        logger.error(
            "Falha na importação: %s -> %s | %s",
            file_path.name,
            destination.name,
            resultado.mensagem or resultado.medicao.detalhe_status,
        )
    except Exception as exc:
        logger.exception("Erro não tratado ao processar %s", file_path.name)
        if file_path.exists():
            try:
                destination = move_file(file_path, FAILED_DIR)
                logger.error(
                    "Ficheiro movido para falhas após erro inesperado: %s -> %s | %s",
                    file_path.name,
                    destination.name,
                    exc,
                )
            except Exception as move_exc:
                logger.error(
                    "Não foi possível mover %s para falhas: %s",
                    file_path.name,
                    move_exc,
                )


def process_existing_files() -> None:
    for file_path in sorted(IMPORT_DIR.glob("*.json")):
        try:
            process_json_file(file_path)
        except Exception as exc:
            logger.exception("Erro ao processar ficheiro existente %s: %s", file_path.name, exc)


class JsonImportHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        try:
            process_json_file(Path(event.src_path))
        except Exception as exc:
            logger.exception("Erro no evento on_created: %s", exc)

    def on_moved(self, event):
        if event.is_directory:
            return
        try:
            process_json_file(Path(event.dest_path))
        except Exception as exc:
            logger.exception("Erro no evento on_moved: %s", exc)


def start_watcher(blocking: bool = True) -> Observer | None:
    setup_logging()
    ensure_directories()
    upgrade_schema(engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema_indexes(engine)
    seed_indicadores_catalog(engine)
    imported = backfill_medicoes_from_processados(engine, PROCESSED_DIR)
    if imported:
        logger.info("%s medições importadas do backfill em processados/.", imported)
    process_existing_files()

    handler = JsonImportHandler()
    observer = Observer()
    observer.schedule(handler, str(IMPORT_DIR), recursive=False)
    observer.start()

    logger.info("Watcher ativo em: %s", IMPORT_DIR)

    if blocking:
        try:
            while observer.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Watcher interrompido pelo utilizador")
        finally:
            observer.stop()
            observer.join()

    return observer


if __name__ == "__main__":
    start_watcher(blocking=True)
