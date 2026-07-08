import logging

from sqlalchemy.orm import Session

from indicator_parser import INDICATOR_CATALOG, extract_codigo_e_nome
from models import Indicadores

logger = logging.getLogger(__name__)

INDICADOR_DEFINICOES = {
    "P001": {
        "nome_indicador": "Business Value per Sprint",
        "formula_original": "(IR×4 + RS×3 + EO×2 + RC×1) / 50",
    },
    "P003": {
        "nome_indicador": "Velocidade de Desbloqueio",
        "formula_original": "TR / TB — Bloqueios resolvidos < 4h / Total de bloqueios",
    },
    "P004": {
        "nome_indicador": "Predictability",
        "formula_original": "PE / PP — Story Points entregues / Story Points planejados",
    },
    "P005": {
        "nome_indicador": "SLA Compliance",
        "formula_original": "CEMP / TCMP — Iniciativas concluídas no prazo / total concluídas com prazo",
    },
    "P007": {
        "nome_indicador": "Taxa de Retrabalho",
        "formula_original": "1 - (IR / IE)  |  IE = itens entregues (Completed/Resolved), IR = reabertos após entrega",
    },
    "A001": {
        "nome_indicador": "Backlog Health",
        "formula_original": "CA / I3S — HUs com AcceptanceCriteria / total nas próximas N sprints",
    },
    "A002": {
        "nome_indicador": "Feature Delivery Rate",
        "formula_original": "fd (Features Done no trimestre) / fp (Features criadas no trimestre)",
    },
    "A009": {
        "nome_indicador": "Test Coverage",
        "formula_original": "STA / SDP — HUs com teste vinculado / total HUs concluídas",
    },
    "A010": {
        "nome_indicador": "Defect Detection Efficiency",
        "formula_original": "Bugs Detectados em Teste / Total de Bugs",
    },
}


def build_catalog_entry(cod_indicador: str) -> dict:
    meta = INDICATOR_CATALOG[cod_indicador]
    definicao = INDICADOR_DEFINICOES[cod_indicador]
    return {
        "cod_indicador": cod_indicador,
        "nome_indicador": definicao["nome_indicador"],
        "nome_grupo": meta["nome_grupo"],
        "dimensao": meta["dimensao"],
        "nivel_avaliacao": meta["nivel_avaliacao"],
        "formula_original": definicao["formula_original"],
        "subpapeis_aplicaveis": meta.get("subpapeis_aplicaveis"),
    }


def seed_indicadores_catalog(engine) -> int:
    with Session(engine) as session:
        if session.query(Indicadores).count() > 0:
            return 0

        for cod_indicador in INDICATOR_CATALOG:
            session.add(Indicadores(**build_catalog_entry(cod_indicador)))

        session.commit()
        total = len(INDICATOR_CATALOG)
        logger.info("Catálogo de indicadores inicializado com %s registos.", total)
        return total


def find_indicador_by_cod(session: Session, cod_indicador: str) -> Indicadores | None:
    return (
        session.query(Indicadores)
        .filter(Indicadores.cod_indicador == cod_indicador.upper())
        .first()
    )


def resolve_indicador_id(session: Session, payload: dict) -> int | None:
    try:
        cod_indicador, _ = extract_codigo_e_nome(payload)
    except ValueError:
        return None

    indicador = find_indicador_by_cod(session, cod_indicador)
    return indicador.id if indicador else None
