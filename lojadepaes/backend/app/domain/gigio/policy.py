from __future__ import annotations

import re

from app.domain.errors import ConfirmationError

MAX_MESSAGE_CHARS = 2000
MAX_HISTORY = 12
MAX_TOOL_ROUNDS = 3
MAX_OUTPUT_CHARS = 4000
INCOMPLETE_REPLY = "Não consegui concluir a resposta agora. Tente novamente."
SHOWCASE_CORRECTION = (
    "A consulta lookup_products em modo vitrine foi concluída e devolveu pães publicados. "
    "Não diga que a vitrine está vazia. Responda a pergunta usando somente os nomes, preços "
    "e caminhos que essa consulta devolveu. Não invente pão. Não chame ferramentas."
)
SYNTHESIS_PROMPT = (
    "Responda agora ao cliente em português brasileiro. Primeiro a pergunta feita, "
    "completa e útil. Depois, se fizer sentido para a refeição já descrita e a conversa "
    "não for de pedido ou pagamento, um complemento breve começando por «Para completar a mesa…». "
    "Não chame ferramentas. Distinga o que é ideia do Gigio e o que é receita publicada de A Loja. "
    "Só cite pão ou receita se a consulta anterior confirmou que está publicado. "
    "Não invente produto, preço, safra nem combinação certificada."
)
INJECTION_MARKERS = (
    "ignore as regras",
    "ignore previous",
    "ignore as previous",
    "system prompt",
    "revelar segredo",
    "reveal the secret",
    "mostre a chave",
    "aws_secret",
    "ignore all rules",
)


def sanitize_user_text(value: object) -> str:
    text = " ".join(str(value or "").replace("\r\n", "\n").split())
    if not text:
        raise ConfirmationError("escreva uma pergunta para o Gigio")
    if len(text) > MAX_MESSAGE_CHARS:
        raise ConfirmationError("a mensagem é longa demais")
    return text


def looks_like_injection(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in INJECTION_MARKERS)


def strip_instructions(text: str) -> str:
    cleaned = re.sub(r"(?is)<(?:script|style|iframe|object)[^>]*>.*?</(?:script|style|iframe|object)>", " ", text)
    cleaned = re.sub(r"(?i)ignore (?:all |as |the )?previous.+", " ", cleaned)
    return " ".join(cleaned.split())


def clip_history(messages: list[dict]) -> list[dict]:
    trimmed: list[dict] = []
    for raw in messages[-MAX_HISTORY:]:
        role = str(raw.get("role") or "")
        if role not in {"user", "assistant"}:
            continue
        content = sanitize_user_text(raw.get("content")) if role == "user" else str(raw.get("content") or "")
        if role == "assistant":
            content = content[:MAX_OUTPUT_CHARS]
        trimmed.append({"role": role, "content": content})
    return trimmed
