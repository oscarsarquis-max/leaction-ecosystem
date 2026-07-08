"""Garante dados mínimos para o cadastro público funcionar em desenvolvimento."""

from __future__ import annotations

import logging

from app.core.education_framework_seeder import ensure_education_framework
from app.database.models import Framework

logger = logging.getLogger(__name__)


def ensure_published_framework() -> str | None:
    """Garante framework padrão Educação (educacao-v1) completo e ativo."""
    framework_id = ensure_education_framework()

    # Desativa outros frameworks bootstrap incompletos (ex.: telecom minimal)
    from app.database.models import db

    for fw in Framework.query.filter(Framework.id != framework_id).all():
        meta = fw.rules_metadata or {}
        if meta.get("bootstrap") and not meta.get("ingestion_complete"):
            fw.is_active = False

    db.session.commit()
    logger.info("Framework padrão Educação '%s' ativo.", framework_id)
    return framework_id
