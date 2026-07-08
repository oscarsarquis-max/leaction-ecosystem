from datetime import date, datetime, timezone
import traceback

from sqlalchemy.orm import Session

from indicator_parser import extract_codigo_e_nome, enrich_payload_indicador, parse_periodo_date
from models import Medicoes

STATUS_PROCESSANDO = "PROCESSANDO"
STATUS_SUCESSO = "SUCESSO"
STATUS_FALHA = "FALHA"

CODIGO_NAO_CATALOGADO = "Código de indicador não localizado no catálogo mestre."


def create_medicao_processando(
    session: Session,
    *,
    nome_arquivo: str,
    payload: dict,
) -> Medicoes:
    registo = Medicoes(
        indicador_id=None,
        nome_arquivo=nome_arquivo[:100],
        payload=payload,
        data_importacao=datetime.now(timezone.utc),
        data_referencia=None,
        status_import=STATUS_PROCESSANDO,
        detalhe_status=None,
    )
    session.add(registo)
    session.flush()
    return registo


def extract_cod_indicador(payload: dict) -> str:
    cod_indicador, _ = extract_codigo_e_nome(payload)
    return cod_indicador


def extract_data_referencia_inicio(payload: dict, *, fallback: date) -> date:
    periodo = payload.get("periodo")
    if isinstance(periodo, dict) and periodo.get("inicio") is not None:
        try:
            data_referencia = parse_periodo_date(periodo.get("inicio"), "periodo.inicio")
            if data_referencia is not None:
                return data_referencia
        except ValueError:
            pass

    return fallback


def finalize_medicao_sucesso(
    session: Session,
    registo: Medicoes,
    *,
    indicador_id: int,
    data_referencia: date,
    id_colaborador: int | None = None,
    cod_indicador: str | None = None,
) -> None:
    if cod_indicador and isinstance(registo.payload, dict):
        registo.payload = enrich_payload_indicador(cod_indicador, registo.payload)

    registo.indicador_id = indicador_id
    registo.id_colaborador = id_colaborador
    registo.data_referencia = data_referencia
    registo.status_import = STATUS_SUCESSO
    registo.detalhe_status = None


def finalize_medicao_falha(
    session: Session,
    registo: Medicoes,
    mensagem: str,
) -> None:
    registo.status_import = STATUS_FALHA
    registo.detalhe_status = mensagem
    registo.indicador_id = None
    registo.id_colaborador = None


def format_error_detail(erro: Exception | str, *, include_traceback: bool = True) -> str:
    if isinstance(erro, str):
        return erro

    if include_traceback:
        return traceback.format_exc()

    return str(erro)
