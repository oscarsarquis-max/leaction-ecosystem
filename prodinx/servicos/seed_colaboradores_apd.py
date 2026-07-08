#!/usr/bin/env python3
"""
Seed APD Técnica — colaboradores e medições com discrepâncias individuais vs. baseline de equipe.

Cenários para validação do motor de IA:
  José (Dev)     — E005 baixo, P007 alto (score baixo); equipe com A002 altíssimo.
  Saulo (Dev)    — S001 e C006 (Review Response Time) péssimos; equipe saudável.
  Samuel (PO)    — E001 excelente; P001 e P002 (equipe) terríveis.
  Francisco (SM) — C003 excelente; P004 (equipe) péssimo.

Uso:
    cd servicos
    python seed_colaboradores_apd.py
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from config import DATABASE_URL
from db_migrations import upgrade_schema
from models import Colaboradores, Indicadores, Medicoes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED_ARQUIVO_PREFIXO = "seed_apd_"


def ultimo_dia_mes_anterior(hoje: date | None = None) -> date:
    hoje = hoje or date.today()
    primeiro_do_mes = date(hoje.year, hoje.month, 1)
    return primeiro_do_mes - timedelta(days=1)


DATA_REFERENCIA = ultimo_dia_mes_anterior()
PERIODO_APD = {
    "inicio": DATA_REFERENCIA.replace(day=1).isoformat(),
    "fim": DATA_REFERENCIA.isoformat(),
}

COLABORADORES_APD = [
    {
        "matricula": "F178992",
        "nome": "José PINHEIRO de Moura Júnior",
        "papel": "Técnica",
        "subpapel": "Dev",
        "funcao": "Dev",
        "codsetor": "APD",
    },
    {
        "matricula": "F178841",
        "nome": "SAULO Gabriel Bandeira de Oliveira",
        "papel": "Técnica",
        "subpapel": "Dev",
        "funcao": "Dev",
        "codsetor": "APD",
    },
    {
        "matricula": "F170046",
        "nome": "SAMUEL Pinheiro de Barcellos Vieira",
        "papel": "Gestão Técnica",
        "subpapel": "PO",
        "funcao": "PO",
        "codsetor": "APD",
    },
    {
        "matricula": "F179117",
        "nome": "FRANCISCO Gleriston Rodrigues Cavalcante",
        "papel": "Gestão Técnica",
        "subpapel": "Scrum Master",
        "funcao": "Scrum Master",
        "codsetor": "APD",
    },
]

INDICADORES_APD = {
    "S001": {
        "nome_indicador": "Carga Cognitiva Individual",
        "dimensao": "Satisfação",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "S002": {
        "nome_indicador": "eNPS do Processo",
        "dimensao": "Satisfação",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "P001": {
        "nome_indicador": "Business Value per Sprint",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "P002": {
        "nome_indicador": "Product Market Fit",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "P004": {
        "nome_indicador": "Predictability",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "P007": {
        "nome_indicador": "Taxa de Retrabalho",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": ["Dev", "Tester"],
    },
    "P008": {
        "nome_indicador": "Change Failure Rate",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "A002": {
        "nome_indicador": "Feature Delivery Rate",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "A009": {
        "nome_indicador": "Test Coverage",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "A010": {
        "nome_indicador": "Defect Detection Efficiency (DDE)",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": ["Dev", "Tester"],
    },
    "C002": {
        "nome_indicador": "Cross-team Alignment",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "C003": {
        "nome_indicador": "Team Health Check",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "C006": {
        "nome_indicador": "Review Response Time",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": ["Dev", "Tester", "Arquiteto"],
    },
    "E001": {
        "nome_indicador": "Requirement Lead Time",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "E005": {
        "nome_indicador": "Focus Time (Deep Work)",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
    "E006": {
        "nome_indicador": "Flow Efficiency",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
        "nome_grupo": "Técnica",
        "subpapeis_aplicaveis": None,
    },
}

# Baseline de equipe saudável — contraste acentuado com métricas individuais problemáticas.
BASELINE_EQUIPE_SAUDAVEL = {
    "S002": 0.86,
    "P002": 0.88,
    "P004": 0.90,
    "P008": 0.89,
    "A002": 0.93,
    "A010": 0.82,
    "C002": 0.87,
    "E006": 0.88,
}

# Baseline individual neutro — preenche indicadores sem override de cenário.
BASELINE_INDIVIDUAL_SAUDAVEL = {
    "S001": 0.72,
    "P001": 0.68,
    "P007": 0.75,
    "A009": 0.70,
    "C003": 0.74,
    "C006": 0.71,
    "E001": 0.69,
    "E005": 0.65,
}

# Overrides de cenário IA — apenas os indicadores com discrepância intencional.
OVERRIDES_JOSE_INDIVIDUAL = {
    "E005": 0.04,
    "P007": 0.07,
    "A009": 0.42,
    "S001": 0.48,
}

OVERRIDES_JOSE_EQUIPE = {
    "A002": 0.96,
    "A010": 0.38,
    "P008": 0.91,
}

OVERRIDES_SAULO_INDIVIDUAL = {
    "S001": 0.08,
    "C006": 0.05,
    "E005": 0.32,
    "P007": 0.55,
}

OVERRIDES_SAULO_EQUIPE: dict[str, float] = {
    "A010": 0.91,
}

OVERRIDES_SAMUEL_INDIVIDUAL = {
    "E001": 0.94,
    "P001": 0.10,
    "S001": 0.52,
    "C003": 0.58,
}

OVERRIDES_SAMUEL_EQUIPE = {
    "P002": 0.09,
    "P004": 0.92,
}

OVERRIDES_FRANCISCO_INDIVIDUAL = {
    "C003": 0.96,
    "S001": 0.54,
    "E001": 0.62,
}

OVERRIDES_FRANCISCO_EQUIPE = {
    "P004": 0.07,
    "A002": 0.91,
}

CENARIOS_POR_MATRICULA = {
    "F178992": {
        "overrides_individual": OVERRIDES_JOSE_INDIVIDUAL,
        "overrides_equipe": OVERRIDES_JOSE_EQUIPE,
        "cenario": "Dev rápido sem foco · alto retrabalho · equipe com A002 altíssimo",
    },
    "F178841": {
        "overrides_individual": OVERRIDES_SAULO_INDIVIDUAL,
        "overrides_equipe": OVERRIDES_SAULO_EQUIPE,
        "cenario": "Dev sobrecarregado · C006 (Review Response) péssimo · equipe saudável",
    },
    "F170046": {
        "overrides_individual": OVERRIDES_SAMUEL_INDIVIDUAL,
        "overrides_equipe": OVERRIDES_SAMUEL_EQUIPE,
        "cenario": "PO com E001 excelente · P001/P002 terríveis",
    },
    "F179117": {
        "overrides_individual": OVERRIDES_FRANCISCO_INDIVIDUAL,
        "overrides_equipe": OVERRIDES_FRANCISCO_EQUIPE,
        "cenario": "SM com C003 excelente · P004 (Predictability) péssimo",
    },
}


def indicador_aplica_ao_subpapel(subpapel: str, meta: dict) -> bool:
    aplicaveis = meta.get("subpapeis_aplicaveis")
    if not aplicaveis:
        return True
    return subpapel in aplicaveis


def montar_medicoes_completas(
    subpapel: str,
    *,
    overrides_individual: dict[str, float] | None = None,
    overrides_equipe: dict[str, float] | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Garante score para todos os indicadores APD aplicáveis ao subpapel."""
    individual: dict[str, float] = {}
    equipe: dict[str, float] = {}

    for cod, meta in INDICADORES_APD.items():
        if not indicador_aplica_ao_subpapel(subpapel, meta):
            continue

        if meta["nivel_avaliacao"] == "Individual":
            individual[cod] = BASELINE_INDIVIDUAL_SAUDAVEL.get(cod, 0.70)
        else:
            equipe[cod] = BASELINE_EQUIPE_SAUDAVEL.get(cod, 0.85)

    if overrides_individual:
        individual.update(overrides_individual)
    if overrides_equipe:
        equipe.update(overrides_equipe)

    return individual, equipe


def validar_cobertura_medicoes(subpapel: str, individual: dict, equipe: dict) -> list[str]:
    faltantes: list[str] = []
    for cod, meta in INDICADORES_APD.items():
        if not indicador_aplica_ao_subpapel(subpapel, meta):
            continue
        if meta["nivel_avaliacao"] == "Individual" and cod not in individual:
            faltantes.append(f"{cod} (Individual)")
        if meta["nivel_avaliacao"] != "Individual" and cod not in equipe:
            faltantes.append(f"{cod} (Equipe)")
    return faltantes


MEDICOES_POR_MATRICULA = {
    matricula: {
        **dict(
            zip(
                ("individual", "equipe"),
                montar_medicoes_completas(
                    next(c["subpapel"] for c in COLABORADORES_APD if c["matricula"] == matricula),
                    overrides_individual=cfg["overrides_individual"],
                    overrides_equipe=cfg["overrides_equipe"],
                ),
            )
        ),
        "cenario": cfg["cenario"],
    }
    for matricula, cfg in CENARIOS_POR_MATRICULA.items()
}

PESOS_DIMENSOES_TECNICA = {
    "Satisfação": 0.25,
    "Performance": 0.25,
    "Atividade": 0.20,
    "Comunicação": 0.20,
    "Eficiência": 0.10,
}

PESO_INDIVIDUAL = 0.4
PESO_EQUIPE = 0.6

PAYLOAD_EXTRAS_POR_INDICADOR = {
    "P007": {"ie": 24, "ir": 22},
    "P001": {"ir": 1, "sr": 1, "rs": 1, "eo": 1, "rc": 1, "sc": 10},
    "A010": {"btes": 14, "bprod": 3},
}


def combinar_nivel(individual: float | None, equipe: float | None) -> float | None:
    if individual is None and equipe is None:
        return None

    total = 0.0
    peso_aplicado = 0.0

    if individual is not None:
        total += individual * PESO_INDIVIDUAL
        peso_aplicado += PESO_INDIVIDUAL
    if equipe is not None:
        total += equipe * PESO_EQUIPE
        peso_aplicado += PESO_EQUIPE

    if peso_aplicado == 0:
        return None

    return total / peso_aplicado


def estimar_iaps_bloco(
    medicoes_individual: dict[str, float],
    medicoes_equipe: dict[str, float],
) -> float:
    por_dimensao: dict[str, dict[str, float]] = {}

    for cod, score in medicoes_individual.items():
        dim = INDICADORES_APD[cod]["dimensao"]
        por_dimensao.setdefault(dim, {})["individual"] = score * 100

    for cod, score in medicoes_equipe.items():
        dim = INDICADORES_APD[cod]["dimensao"]
        por_dimensao.setdefault(dim, {})["equipe"] = score * 100

    iaps = 0.0
    for dimensao, peso in PESOS_DIMENSOES_TECNICA.items():
        notas = por_dimensao.get(dimensao, {})
        score_dim = combinar_nivel(notas.get("individual"), notas.get("equipe"))
        if score_dim is not None:
            iaps += score_dim * peso

    return round(iaps, 2)


def upsert_colaborador(session: Session, dados: dict) -> Colaboradores:
    colaborador = session.scalar(
        select(Colaboradores).where(Colaboradores.matricula == dados["matricula"])
    )

    if colaborador is None:
        colaborador = Colaboradores(
            matricula=dados["matricula"],
            nome=dados["nome"],
        )
        session.add(colaborador)

    colaborador.nome = dados["nome"]
    colaborador.papel = dados["papel"]
    colaborador.subpapel = dados["subpapel"]
    colaborador.funcao = dados.get("funcao")
    colaborador.codsetor = dados.get("codsetor")
    session.flush()
    return colaborador


def upsert_indicador_apd(session: Session, cod_indicador: str, meta: dict) -> Indicadores:
    indicador = session.scalar(
        select(Indicadores).where(
            Indicadores.cod_indicador == cod_indicador,
            Indicadores.nome_grupo == meta["nome_grupo"],
        )
    )

    if indicador is None:
        indicador = Indicadores(
            cod_indicador=cod_indicador,
            nome_grupo=meta["nome_grupo"],
            nome_indicador=meta["nome_indicador"],
        )
        session.add(indicador)

    indicador.nome_indicador = meta["nome_indicador"]
    indicador.dimensao = meta["dimensao"]
    indicador.nivel_avaliacao = meta["nivel_avaliacao"]
    indicador.subpapeis_aplicaveis = meta.get("subpapeis_aplicaveis")
    indicador.formula_original = meta.get("formula_original")
    session.flush()
    return indicador


def limpar_medicoes_seed(session: Session) -> int:
    resultado = session.execute(
        delete(Medicoes).where(Medicoes.nome_arquivo.like(f"{SEED_ARQUIVO_PREFIXO}%"))
    )
    return resultado.rowcount or 0


def criar_medicao(
    session: Session,
    *,
    indicador: Indicadores,
    id_colaborador: int,
    score: float,
    sufixo: str,
) -> Medicoes:
    score_percentual = round(score * 100, 4)
    payload = {
        "metrica": f"{indicador.cod_indicador} - {indicador.nome_indicador}",
        "periodo": PERIODO_APD,
        "resumo": {
            "score": score,
            "score_percentual": score_percentual,
        },
        "origem": "seed_colaboradores_apd",
    }

    extras = PAYLOAD_EXTRAS_POR_INDICADOR.get(indicador.cod_indicador)
    if extras:
        payload["resumo"].update(extras)

    medicao = Medicoes(
        indicador_id=indicador.id,
        id_colaborador=id_colaborador,
        nome_arquivo=f"{SEED_ARQUIVO_PREFIXO}{indicador.cod_indicador}_{sufixo}.json",
        payload=payload,
        data_importacao=datetime.now(timezone.utc),
        data_referencia=DATA_REFERENCIA,
        status_import="SUCESSO",
        detalhe_status=None,
    )
    session.add(medicao)
    return medicao


def seed_medicoes_colaborador(
    session: Session,
    colaborador: Colaboradores,
    *,
    medicoes_individual: dict[str, float],
    medicoes_equipe: dict[str, float],
) -> int:
    total = 0
    sufixo_base = colaborador.matricula.lower()

    for cod_indicador, score in medicoes_individual.items():
        indicador = upsert_indicador_apd(session, cod_indicador, INDICADORES_APD[cod_indicador])
        criar_medicao(
            session,
            indicador=indicador,
            id_colaborador=colaborador.id_colaborador,
            score=score,
            sufixo=f"{sufixo_base}_individual",
        )
        total += 1

    for cod_indicador, score in medicoes_equipe.items():
        indicador = upsert_indicador_apd(session, cod_indicador, INDICADORES_APD[cod_indicador])
        criar_medicao(
            session,
            indicador=indicador,
            id_colaborador=colaborador.id_colaborador,
            score=score,
            sufixo=f"{sufixo_base}_equipe",
        )
        total += 1

    return total


def executar_seed() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    upgrade_schema(engine)

    with Session(engine) as session:
        removidas = limpar_medicoes_seed(session)
        logger.info("Medições seed anteriores removidas: %s", removidas)

        colaboradores_por_matricula: dict[str, Colaboradores] = {}
        for dados in COLABORADORES_APD:
            colaborador = upsert_colaborador(session, dados)
            colaboradores_por_matricula[dados["matricula"]] = colaborador
            logger.info(
                "Colaborador %s · %s · papel=%s · subpapel=%s · id=%s",
                colaborador.matricula,
                colaborador.nome,
                colaborador.papel,
                colaborador.subpapel,
                colaborador.id_colaborador,
            )

        for cod_indicador, meta in INDICADORES_APD.items():
            indicador = upsert_indicador_apd(session, cod_indicador, meta)
            logger.info(
                "Indicador %s (%s) · %s · %s",
                indicador.cod_indicador,
                indicador.nome_grupo,
                indicador.dimensao,
                indicador.nivel_avaliacao,
            )

        medicoes_totais = 0
        for matricula, blocos in MEDICOES_POR_MATRICULA.items():
            colaborador = colaboradores_por_matricula[matricula]
            faltantes = validar_cobertura_medicoes(
                colaborador.subpapel,
                blocos["individual"],
                blocos["equipe"],
            )
            if faltantes:
                raise RuntimeError(
                    f"Cobertura incompleta para {colaborador.nome}: {', '.join(faltantes)}"
                )

            criadas = seed_medicoes_colaborador(
                session,
                colaborador,
                medicoes_individual=blocos["individual"],
                medicoes_equipe=blocos["equipe"],
            )
            medicoes_totais += criadas
            iaps_estimado = estimar_iaps_bloco(blocos["individual"], blocos["equipe"])
            logger.info(
                "Medições APD criadas para %s (%s): %s (%s ind + %s eq) · IAPS estimado: %.2f",
                colaborador.nome,
                colaborador.matricula,
                criadas,
                len(blocos["individual"]),
                len(blocos["equipe"]),
                iaps_estimado,
            )
            logger.info("Cenário IA: %s", blocos["cenario"])
            logger.info(
                "Validação API: GET /api/dashboard/metricas?nivel=colaborador&id_colaborador=%s",
                colaborador.id_colaborador,
            )

        session.commit()
        logger.info("Total de medições APD criadas: %s", medicoes_totais)
        logger.info("data_referencia das medições: %s", DATA_REFERENCIA)


if __name__ == "__main__":
    executar_seed()
