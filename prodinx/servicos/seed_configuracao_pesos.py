#!/usr/bin/env python3
"""
Seed da tabela configuracao_pesos — pesos IAPS por papel/subpapel.

Uso:
    cd servicos
    python seed_configuracao_pesos.py
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from config import DATABASE_URL
from db_migrations import upgrade_schema
from models import ConfiguracaoPesos

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PESOS_PADRAO = {
    "peso_ind": 0.4,
    "peso_eq": 0.6,
    "peso_satisfacao": 0.25,
    "peso_performance": 0.25,
    "peso_atividade": 0.20,
    "peso_comunicacao": 0.20,
    "peso_eficiencia": 0.10,
}

CONFIGURACOES_PADRAO = [
    {"papel": "Técnica", "subpapel": "Dev"},
    {"papel": "Técnica", "subpapel": "Tester"},
    {"papel": "Técnica", "subpapel": "Arquiteto"},
    {"papel": "Gestão Técnica", "subpapel": "PO"},
    {"papel": "Gestão Técnica", "subpapel": "Scrum Master"},
    {"papel": "Gestão Técnica", "subpapel": "Gerente"},
]


def upsert_configuracao(session: Session, papel: str, subpapel: str) -> ConfiguracaoPesos:
    existente = session.scalar(
        select(ConfiguracaoPesos).where(
            ConfiguracaoPesos.papel == papel,
            ConfiguracaoPesos.subpapel == subpapel,
        )
    )

    if existente is None:
        existente = ConfiguracaoPesos(papel=papel, subpapel=subpapel)
        session.add(existente)

    for campo, valor in PESOS_PADRAO.items():
        setattr(existente, campo, valor)

    session.flush()
    return existente


def executar_seed() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    upgrade_schema(engine)

    with Session(engine) as session:
        for item in CONFIGURACOES_PADRAO:
            config = upsert_configuracao(session, item["papel"], item["subpapel"])
            logger.info(
                "Configuração %s / %s · id=%s · Ind/Eq=%s/%s",
                config.papel,
                config.subpapel,
                config.id,
                config.peso_ind,
                config.peso_eq,
            )

        session.commit()
        logger.info("Total de configurações: %s", len(CONFIGURACOES_PADRAO))


if __name__ == "__main__":
    executar_seed()
