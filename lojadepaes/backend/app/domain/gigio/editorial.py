from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ConfirmationError, NotFoundError
from app.models.gigio import GigioEditorialNote

CONCEPT_SEEDS: tuple[tuple[str, str, str], ...] = (
    (
        "concept:fermentacao",
        "Fermentação",
        "Fermentação é o tempo em que microrganismos da massa transformam açúcares em gases e ácidos. "
        "Isso muda aroma, sabor e estrutura. Não é o contrário da sova: uma massa pode fermentar e também ser sovada. "
        "O resultado concreto de A Loja depende da receita e do preparo cadastrados, não deste conceito geral.",
    ),
    (
        "concept:sova",
        "Sova",
        "Sova é o trabalho da massa — à mão ou por tempo de amasso — para organizar o glúten. "
        "Não significa automaticamente fermento comercial, ausência de fermentação ou miolo sempre macio. "
        "Sovado pode ser de fermentação natural. Confirme o preparo específico de A Loja antes de prometer textura.",
    ),
    (
        "concept:levain",
        "Levain",
        "Levain é uma cultura de farinha e água com leveduras e bactérias. Alimentada, ela fermenta a massa "
        "e participa do aroma e da textura. Não é garantia de ausência de glúten nem de melhor digestão para qualquer pessoa.",
    ),
    (
        "concept:maturacao",
        "Maturação",
        "Maturação é o descanso extra da massa antes de assar. Em geral favorece aroma e estrutura, mas o tempo "
        "exato de A Loja só vale se estiver na descrição aprovada do preparo. Sem esse detalhe, o conceito precisa ser confirmado.",
    ),
    (
        "preparation:fermentacao-natural-curta",
        "Fermentação natural curta",
        "Conceito: massa fermentada com cultura natural em um ciclo mais curto do que uma massa longa. "
        "A rotulagem do criador não autoriza inferir fórmula, horas ou intensidade de acidez. "
        "O detalhe de como A Loja prepara esta opção precisa da descrição aprovada abaixo, quando publicada.",
    ),
    (
        "preparation:maturada",
        "Maturada",
        "Conceito: a massa descansa mais tempo antes de assar. Isso não promete acidez, maciez ou fermento específicos. "
        "Use só a descrição publicada de A Loja para falar deste preparo concreto.",
    ),
    (
        "preparation:sovada",
        "Sovada",
        "Conceito: massa trabalhada para um miolo mais regular. Sovada não é o oposto de fermentação natural "
        "e não implica fermento comercial. Características do pão concreto dependem da receita.",
    ),
    (
        "flour:farinha-branca-strong-white",
        "Farinha branca",
        "Farinha de trigo branca, comum em pães de miolo mais claro. Combina com torradas e sanduíches quando o pão da vitrine for deste tipo. "
        "Não afirma ausência de glúten.",
    ),
    (
        "flour:farinha-integral-trigo",
        "Farinha integral de trigo",
        "Farinha de trigo com o grão mais inteiro. Em geral dá sabor mais marcado. Confirme o produto publicado antes de indicar um pão específico.",
    ),
    (
        "flour:farinha-integral-centeio",
        "Farinha integral de centeio",
        "Centeio integral costuma deixar a massa mais densa e aromática. Não invente disponibilidade: só cite pães publicados.",
    ),
    (
        "flour:farinha-fuba",
        "Fubá",
        "Farinha de milho. Pode dar cor e um sabor mais adocicado. Use apenas se houver pão ou opção do criador com esta farinha.",
    ),
)


def ensure_editorial_seeds(session: Session) -> None:
    existing = {row.topic_key for row in session.scalars(select(GigioEditorialNote))}
    for topic_key, title, body in CONCEPT_SEEDS:
        if topic_key in existing:
            continue
        session.add(
            GigioEditorialNote(
                topic_key=topic_key,
                title=title,
                body=body,
                editorial_status="published",
                version=1,
            )
        )
    session.flush()


def published_notes(session: Session, topic_key: str | None = None) -> list[GigioEditorialNote]:
    ensure_editorial_seeds(session)
    query = select(GigioEditorialNote).where(GigioEditorialNote.editorial_status == "published")
    if topic_key:
        query = query.where(GigioEditorialNote.topic_key == topic_key)
    return list(session.scalars(query.order_by(GigioEditorialNote.topic_key)))


def list_notes(session: Session) -> list[GigioEditorialNote]:
    ensure_editorial_seeds(session)
    return list(session.scalars(select(GigioEditorialNote).order_by(GigioEditorialNote.topic_key)))


def get_note(session: Session, note_id) -> GigioEditorialNote:
    row = session.get(GigioEditorialNote, note_id)
    if row is None:
        raise NotFoundError("explicação não encontrada")
    return row


def save_note(session: Session, note_id, title: str, body: str, status: str) -> GigioEditorialNote:
    row = get_note(session, note_id)
    cleaned_title = " ".join((title or "").split())
    cleaned_body = (body or "").strip()
    if not cleaned_title or len(cleaned_title) > 160:
        raise ConfirmationError("informe um título de até 160 caracteres")
    if not cleaned_body or len(cleaned_body) > 4000:
        raise ConfirmationError("informe o texto aprovado, até 4000 caracteres")
    if status not in {"draft", "published"}:
        raise ConfirmationError("estado editorial inválido")
    row.title = cleaned_title
    row.body = cleaned_body
    row.editorial_status = status
    row.version = int(row.version or 1) + 1
    session.flush()
    return row


def note_view(row: GigioEditorialNote) -> dict:
    return {
        "id": str(row.id),
        "topic_key": row.topic_key,
        "title": row.title,
        "body": row.body,
        "editorial_status": row.editorial_status,
        "version": row.version,
    }
