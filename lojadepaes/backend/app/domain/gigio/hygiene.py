"""Separa resposta ao cliente de bloco de execução interno. Não executa texto."""

from __future__ import annotations

import logging
import re
from threading import Lock

logger = logging.getLogger("lojadepaes.gigio")

_stats_lock = Lock()
_stats = {"invalid_replies": 0, "recoveries": 0}

INVOKE_BLOCK = re.compile(
    r"(?is)<\s*(?:invoke|tool_call|tool_use|function_call|antml:invoke)\b[^>]*>"
    r".*?"
    r"</\s*(?:invoke|tool_call|tool_use|function_call|antml:invoke)\s*>"
)
INVOKE_OPEN = re.compile(
    r"(?is)<\s*(?:invoke|tool_call|tool_use|function_call)\b[^>]*(?:name|tool)\s*="
)
PARAMETER_BLOCK = re.compile(r"(?is)<\s*parameter\b[^>]*>.*?</\s*parameter\s*>")
TOOL_JSON = re.compile(
    r'(?is)\{\s*"(?:name|tool)"\s*:\s*"(?:lookup_|propose_)[a-z_]+".{0,400}?\}'
)
NAMED_TOOL = re.compile(
    r"(?i)\b(?:lookup_products|lookup_product|lookup_recipes|lookup_recipe|"
    r"lookup_editorial|lookup_builder|propose_builder|lookup_accompaniments|"
    r"lookup_pairing_references|lookup_order|lookup_schedule|lookup_fidelity)\b"
)

RECOVERY_PROMPT = (
    "Não escreva invocação de ferramenta, XML, JSON de chamada nem nome de ferramenta. "
    "Responda agora ao cliente em português brasileiro, de forma útil, com o que já sabe. "
    "Não invente pão, preço, estoque nem oferta."
)


def note_invalid_reply() -> None:
    with _stats_lock:
        _stats["invalid_replies"] += 1
        count = _stats["invalid_replies"]
    logger.info("gigio.reply_invalid count=%s", count)


def note_recovery() -> None:
    with _stats_lock:
        _stats["recoveries"] += 1
        count = _stats["recoveries"]
    logger.info("gigio.reply_recovery count=%s", count)


def diagnostic_counts() -> dict[str, int]:
    with _stats_lock:
        return dict(_stats)


def strip_leaked_tool_markup(text: str) -> str:
    cleaned = INVOKE_BLOCK.sub(" ", text or "")
    cleaned = PARAMETER_BLOCK.sub(" ", cleaned)
    cleaned = TOOL_JSON.sub(" ", cleaned)
    cleaned = re.sub(r"(?is)```(?:xml|json|tool)?[\s\S]*?```", " ", cleaned)
    cleaned = INVOKE_OPEN.sub(" ", cleaned)
    return " ".join(cleaned.split())


def _has_customer_language(text: str) -> bool:
    letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", text or "")
    return len(letters) >= 24


def is_leaked_tool_instruction(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    if INVOKE_BLOCK.search(raw) or INVOKE_OPEN.search(raw) or "<parameter" in raw.casefold():
        remainder = strip_leaked_tool_markup(raw)
        return not _has_customer_language(remainder)
    cleaned = strip_leaked_tool_markup(raw)
    if TOOL_JSON.search(raw) and not _has_customer_language(cleaned):
        return True
    if NAMED_TOOL.search(raw) and not _has_customer_language(cleaned):
        return True
    return False


def usable_customer_reply(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    cleaned = strip_leaked_tool_markup(raw)
    if not cleaned or is_leaked_tool_instruction(cleaned):
        return ""
    if is_leaked_tool_instruction(raw) and not _has_customer_language(cleaned):
        return ""
    return cleaned
