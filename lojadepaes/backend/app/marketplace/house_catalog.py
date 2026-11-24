"""Leituras da Loja feitas pelo marketplace: pão publicado (pelo slug) e situação de um pedido da casa."""

from uuid import UUID

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


def house_order_cancelled(db: Session, house_order_id: UUID) -> bool:
    """O pedido da casa foi cancelado pela Loja? Só leitura do status; sem importar o domínio de pedidos."""
    row = db.execute(
        text("SELECT status FROM orders WHERE id = :house_order_id"),
        {"house_order_id": house_order_id},
    ).first()
    return row is not None and str(row[0]) == "cancelled"
