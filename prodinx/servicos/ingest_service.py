import json
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from catalog_service import find_indicador_by_cod
from colaborador_service import resolve_id_colaborador_from_payload
from medicao_service import (
    CODIGO_NAO_CATALOGADO,
    STATUS_FALHA,
    STATUS_SUCESSO,
    create_medicao_processando,
    extract_cod_indicador,
    extract_data_referencia_inicio,
    finalize_medicao_falha,
    finalize_medicao_sucesso,
    format_error_detail,
)
from models import Medicoes

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    medicao: Medicoes | None
    sucesso: bool
    mensagem: str | None = None


def build_payload_from_raw(raw_content: str) -> dict:
    if not raw_content.strip():
        return {"_conteudo_bruto": ""}

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        return {"_conteudo_bruto": raw_content}

    if isinstance(parsed, dict):
        return parsed

    return {"_conteudo_bruto": raw_content, "_valor_parseado": parsed}


def _load_medicao(session: Session, medicao_id: int) -> Medicoes:
    registo = session.get(
        Medicoes,
        medicao_id,
        options=[joinedload(Medicoes.indicador)],
    )
    if registo is None:
        raise RuntimeError(f"Medição id={medicao_id} não encontrada após preparação")
    return registo


def _fase_preparacao(engine, *, nome_arquivo: str, raw_content: str) -> int:
    payload = build_payload_from_raw(raw_content)

    with Session(engine) as session:
        registo = create_medicao_processando(
            session,
            nome_arquivo=nome_arquivo,
            payload=payload,
        )
        session.commit()
        return registo.id


def _fase_falha(
    engine,
    medicao_id: int,
    mensagem: str,
    *,
    include_traceback: bool = False,
    erro: Exception | None = None,
) -> Medicoes:
    detalhe = mensagem
    if erro is not None:
        detalhe = format_error_detail(erro, include_traceback=include_traceback)
    elif include_traceback:
        detalhe = mensagem

    with Session(engine) as session:
        registo = _load_medicao(session, medicao_id)
        finalize_medicao_falha(session, registo, detalhe)
        session.commit()
        session.refresh(registo)
        return registo


def _fase_conclusao_sucesso(
    engine,
    medicao_id: int,
    *,
    indicador_id: int,
    data_referencia,
    id_colaborador: int | None = None,
    cod_indicador: str | None = None,
) -> Medicoes:
    with Session(engine) as session:
        registo = _load_medicao(session, medicao_id)
        finalize_medicao_sucesso(
            session,
            registo,
            indicador_id=indicador_id,
            data_referencia=data_referencia,
            id_colaborador=id_colaborador,
            cod_indicador=cod_indicador,
        )
        session.commit()
        session.refresh(registo)
        return registo


def process_json_ingestion(
    engine,
    *,
    nome_arquivo: str,
    raw_content: str,
) -> IngestionResult:
    medicao_id: int | None = None

    try:
        medicao_id = _fase_preparacao(
            engine,
            nome_arquivo=nome_arquivo,
            raw_content=raw_content,
        )

        with Session(engine) as session:
            registo_preparacao = session.get(Medicoes, medicao_id)
            payload = registo_preparacao.payload
            data_importacao_fallback = registo_preparacao.data_importacao.date()

        if "_conteudo_bruto" in payload and "metrica" not in payload:
            if not raw_content.strip():
                medicao = _fase_falha(engine, medicao_id, "Ficheiro JSON vazio")
                return IngestionResult(medicao=medicao, sucesso=False, mensagem="Ficheiro JSON vazio")

            try:
                json.loads(raw_content)
            except json.JSONDecodeError as exc:
                medicao = _fase_falha(
                    engine,
                    medicao_id,
                    f"JSON inválido: {exc.msg}",
                )
                return IngestionResult(medicao=medicao, sucesso=False, mensagem=medicao.detalhe_status)

            medicao = _fase_falha(engine, medicao_id, "O payload JSON deve ser um objeto")
            return IngestionResult(
                medicao=medicao,
                sucesso=False,
                mensagem="O payload JSON deve ser um objeto",
            )

        try:
            cod_indicador = extract_cod_indicador(payload)
            data_referencia = extract_data_referencia_inicio(
                payload,
                fallback=data_importacao_fallback,
            )
        except Exception as exc:
            medicao = _fase_falha(
                engine,
                medicao_id,
                str(exc),
                include_traceback=True,
                erro=exc,
            )
            return IngestionResult(medicao=medicao, sucesso=False, mensagem=medicao.detalhe_status)

        with Session(engine) as session:
            indicador = find_indicador_by_cod(session, cod_indicador)

        if indicador is None:
            medicao = _fase_falha(engine, medicao_id, CODIGO_NAO_CATALOGADO)
            return IngestionResult(
                medicao=medicao,
                sucesso=False,
                mensagem=CODIGO_NAO_CATALOGADO,
            )

        id_colaborador = resolve_id_colaborador_from_payload(engine, payload)

        medicao = _fase_conclusao_sucesso(
            engine,
            medicao_id,
            indicador_id=indicador.id,
            data_referencia=data_referencia,
            id_colaborador=id_colaborador,
            cod_indicador=indicador.cod_indicador,
        )
        return IngestionResult(medicao=medicao, sucesso=True)

    except Exception as exc:
        logger.exception("Erro inesperado ao processar %s", nome_arquivo)
        if medicao_id is not None:
            medicao = _fase_falha(
                engine,
                medicao_id,
                str(exc),
                include_traceback=True,
                erro=exc,
            )
            return IngestionResult(medicao=medicao, sucesso=False, mensagem=medicao.detalhe_status)

        raise


def ingest_json_document(
    engine,
    *,
    nome_arquivo: str,
    raw_content: str,
) -> Medicoes:
    resultado = process_json_ingestion(
        engine,
        nome_arquivo=nome_arquivo,
        raw_content=raw_content,
    )
    if resultado.medicao is None:
        raise RuntimeError("Medição não foi criada durante a ingestão")

    if not resultado.sucesso:
        raise ValueError(resultado.mensagem or resultado.medicao.detalhe_status)

    return resultado.medicao


def ingest_payload(
    payload: dict,
    engine,
    *,
    nome_arquivo: str = "api/ingest",
) -> Medicoes:
    return ingest_json_document(
        engine,
        nome_arquivo=nome_arquivo,
        raw_content=json.dumps(payload, ensure_ascii=False),
    )


def load_json_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def backfill_medicoes_from_processados(engine, processados_dir: Path) -> int:
    if not processados_dir.exists():
        return 0

    with Session(engine) as session:
        existing_names = {
            name
            for (name,) in session.query(Medicoes.nome_arquivo).filter(
                Medicoes.nome_arquivo.isnot(None)
            )
        }

    count = 0
    for file_path in sorted(processados_dir.glob("*.json")):
        if file_path.name in existing_names:
            continue

        resultado = process_json_ingestion(
            engine,
            nome_arquivo=file_path.name,
            raw_content=file_path.read_text(encoding="utf-8"),
        )
        if resultado.sucesso:
            count += 1
            logger.info("Backfill importado: %s", file_path.name)
        else:
            logger.warning(
                "Backfill falhou para %s: %s",
                file_path.name,
                resultado.mensagem,
            )

    return count
