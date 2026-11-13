"""Única leitura da Loja feita pelo marketplace: pão publicado, pelo slug."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def published_slug_exists(db: Session, slug: str) -> bool:
    token = (slug or "").strip()
    if not token or len(token) > 80:
        return False
    row = db.execute(
        text(
            "SELECT 1 FROM products "
            "WHERE slug = :slug AND editorial_status = 'published' "
            "LIMIT 1"
        ),
        {"slug": token},
    ).first()
    return row is not None


def published_product_name(db: Session, slug: str) -> str | None:
    token = (slug or "").strip()
    if not token or len(token) > 80:
        return None
    row = db.execute(
        text(
            "SELECT name FROM products "
            "WHERE slug = :slug AND editorial_status = 'published' "
            "LIMIT 1"
        ),
        {"slug": token},
    ).first()
    if row is None or row[0] is None:
        return None
    return str(row[0])
