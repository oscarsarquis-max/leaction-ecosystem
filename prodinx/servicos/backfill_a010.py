"""Atualiza medições A010 existentes com aliases btes/bprod e resumo de score."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from config import DATABASE_URL
from indicator_parser import enrich_payload_indicador
from models import Medicoes

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

with Session(engine) as session:
    rows = (
        session.query(Medicoes)
        .join(Medicoes.indicador)
        .filter(Medicoes.indicador.has(cod_indicador="A010"))
        .all()
    )

    for medicao in rows:
        payload = medicao.payload if isinstance(medicao.payload, dict) else {}
        medicao.payload = enrich_payload_indicador("A010", payload)
        print(
            f"medicao id={medicao.id} colaborador={medicao.id_colaborador} "
            f"score={medicao.payload.get('resumo', {}).get('score_percentual')}"
        )

    session.commit()
    print(f"Atualizadas {len(rows)} medição(ões) A010.")
