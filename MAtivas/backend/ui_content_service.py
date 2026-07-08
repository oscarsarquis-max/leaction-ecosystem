"""
Conteúdo dinâmico da interface — leitura pública e helpers.
"""

from database.models import UiContent, VocabularyRule


def _ui_row_to_dict(row: UiContent) -> dict:
    return {
        "key": row.content_key,
        "value": row.content_value,
        "type": row.content_type,
        "label": row.label,
        "is_active": bool(row.is_active),
    }


def carregar_conteudo_ui(session) -> dict:
    """Monta payload público: textos, imagens e substituições de vocabulário."""
    rows = (
        session.query(UiContent)
        .filter(UiContent.is_active == 1)
        .order_by(UiContent.content_key.asc())
        .all()
    )

    textos = {}
    imagens = {}
    for row in rows:
        if row.content_type == "image_url":
            if (row.content_value or "").strip():
                imagens[row.content_key] = row.content_value.strip()
        else:
            textos[row.content_key] = row.content_value

    regras = (
        session.query(VocabularyRule)
        .filter(VocabularyRule.is_active == 1, VocabularyRule.rule_type == "substituir")
        .order_by(VocabularyRule.id.asc())
        .all()
    )
    substituicoes = [
        {
            "de": r.keyword,
            "para": r.replacement or "",
            "ignore_case": True,
        }
        for r in regras
        if r.keyword and r.replacement
    ]

    versao = max(
        [r.id for r in rows] + [r.id for r in regras] + [0],
    )

    return {
        "versao": versao,
        "textos": textos,
        "imagens": imagens,
        "substituicoes": substituicoes,
    }


def listar_ui_content_admin(session):
    rows = session.query(UiContent).order_by(UiContent.content_key.asc()).all()
    return [_ui_row_to_dict(r) for r in rows]


def atualizar_ui_content(session, key: str, value: str, content_type: str | None = None, label: str | None = None):
    row = session.query(UiContent).filter(UiContent.content_key == key).first()
    if not row:
        row = UiContent(
            content_key=key,
            content_value=value,
            content_type=content_type or "text",
            label=label,
            is_active=1,
        )
        session.add(row)
    else:
        row.content_value = value
        if content_type:
            row.content_type = content_type
        if label is not None:
            row.label = label
    session.flush()
    session.refresh(row)
    return _ui_row_to_dict(row)
