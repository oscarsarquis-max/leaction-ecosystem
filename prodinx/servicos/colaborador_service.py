from sqlalchemy.orm import Session

from indicator_parser import extract_matricula
from models import Colaboradores


def find_colaborador_id_by_matricula(
    session: Session,
    matricula: str | None,
) -> int | None:
    if not matricula:
        return None

    normalized = str(matricula).strip()
    if not normalized:
        return None

    colaborador = (
        session.query(Colaboradores)
        .filter(Colaboradores.matricula == normalized)
        .first()
    )
    return colaborador.id_colaborador if colaborador else None


def resolve_id_colaborador_from_payload(engine, payload: dict) -> int | None:
    matricula = extract_matricula(payload)
    if not matricula:
        return None

    with Session(engine) as session:
        return find_colaborador_id_by_matricula(session, matricula)
