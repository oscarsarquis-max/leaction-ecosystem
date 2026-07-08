from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from catalog_service import INDICATOR_CATALOG, build_catalog_entry
from config import DATABASE_URL, JSON_PROCESSED_DIR
from indicator_parser import extract_codigo_e_nome
from ingest_service import backfill_medicoes_from_processados
from models import Indicadores, Medicoes


def limpar_base_local(engine) -> None:
    with Session(engine) as session:
        session.query(Medicoes).update({Medicoes.indicador_id: None}, synchronize_session=False)
        session.query(Indicadores).delete()
        session.commit()

        for cod in sorted(INDICATOR_CATALOG):
            session.add(Indicadores(**build_catalog_entry(cod)))
        session.commit()

        catalog_by_cod = {
            row.cod_indicador: row.id
            for row in session.query(Indicadores).all()
        }

        for medicao in session.query(Medicoes).all():
            payload = medicao.payload if isinstance(medicao.payload, dict) else {}
            try:
                cod_indicador, _ = extract_codigo_e_nome(payload)
                medicao.indicador_id = catalog_by_cod.get(cod_indicador)
            except ValueError:
                medicao.indicador_id = None

        session.commit()
        print("indicadores:", session.query(Indicadores).count())
        print("medicoes:", session.query(Medicoes).count())
        print(
            "medicoes com indicador:",
            session.query(Medicoes).filter(Medicoes.indicador_id.isnot(None)).count(),
        )


if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    limpar_base_local(engine)
    imported = backfill_medicoes_from_processados(engine, JSON_PROCESSED_DIR)
    print(f"reimportados de processados: {imported}")
