"""
MAtivas - Guardrails de vocabulário para prompts de IA
=================================================================
Regras estáticas de marca + regras dinâmicas da tabela VocabularyRule.
"""

import logging
import os
import sys
from contextlib import contextmanager

logger = logging.getLogger("mativas.guardrails")

GUARDRAILS_PROMPT = (
    "=== GUARDRAILS DE VOCABULÁRIO (OBRIGATÓRIO) ===\n"
    "Regra 1: É ESTRITAMENTE PROIBIDO usar o termo \"metodologias ativas\" "
    "sozinho ou em qualquer variação isolada. Use EXCLUSIVAMENTE "
    "\"metodologias inov-ativas\" (com hífen em \"inov-ativas\").\n"
    "Regra 2: É ESTRITAMENTE PROIBIDO usar as palavras \"dor\" ou \"dores\" "
    "para se referir a problemas pedagógicos. Use \"desafio\", \"dificuldade\" "
    "ou \"necessidade\".\n"
    "Todas as saídas (metodologia, justificativa, títulos e descrições dos "
    "passos) DEVEM respeitar estas regras.\n"
    "=== FIM DOS GUARDRAILS ===\n\n"
)


def _ensure_database_path():
    """Garante que database.models seja importável (local e Docker)."""
    services_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(services_dir)
    backend_dir = os.path.join(project_root, "backend")
    for path in (project_root, backend_dir):
        if path not in sys.path:
            sys.path.insert(0, path)


@contextmanager
def _db_session():
    """Abre sessão SQLAlchemy e garante fechamento (evita vazar conexões)."""
    from database.models import get_db_session

    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def _format_rule_line(keyword: str, rule_type: str, replacement: str | None) -> str:
    """Formata uma regra do banco em instrução legível para o System Prompt."""
    tipo = (rule_type or "").strip().lower()

    if tipo in ("bloqueada", "proibir"):
        return f"- É PROIBIDO utilizar o termo '{keyword}'."

    if tipo == "substituir":
        destino = (replacement or "").strip() or "termo adequado ao contexto pedagógico"
        return f"- NUNCA utilize '{keyword}'. Substitua sempre por '{destino}'."

    if tipo in ("obrigatoria", "forcar"):
        return f"- É OBRIGATÓRIO utilizar o termo '{keyword}'."

    return f"- Regra ({rule_type}): '{keyword}'."


def _format_dynamic_rules(rules) -> str:
    if not rules:
        return ""

    lines = [
        "=== REGRAS DINÂMICAS DO BANCO (VocabularyRule) ===\n",
        "As instruções abaixo são obrigatórias e complementam os guardrails acima:\n",
    ]
    for keyword, rule_type, replacement in rules:
        lines.append(_format_rule_line(keyword, rule_type, replacement))

    lines.append("\n=== FIM DAS REGRAS DINÂMICAS ===\n\n")
    return "\n".join(lines)


def load_vocabulary_rules_from_db() -> str:
    """Consulta regras ativas (is_active=1) e retorna texto para o prompt."""
    try:
        _ensure_database_path()
        from database.models import VocabularyRule

        with _db_session() as session:
            rules = (
                session.query(
                    VocabularyRule.keyword,
                    VocabularyRule.rule_type,
                    VocabularyRule.replacement,
                )
                .filter(VocabularyRule.is_active == 1)
                .order_by(VocabularyRule.id.asc())
                .all()
            )
        return _format_dynamic_rules(rules)
    except Exception as exc:
        logger.warning("Falha ao carregar regras do banco: %s", exc)
        return ""


def build_guardrails_prompt() -> str:
    """Monta guardrails estáticos + dinâmicos antes de invocar o Bedrock."""
    return GUARDRAILS_PROMPT + load_vocabulary_rules_from_db()
