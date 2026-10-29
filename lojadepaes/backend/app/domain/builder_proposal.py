from __future__ import annotations

import hashlib
import hmac
import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.custom_loaf import public_builder_catalog
from app.domain.errors import ConfirmationError
from app.domain.gigio.policy import strip_instructions

BUILDER_CTA_LABEL = "Montar esse pão"
PROPOSAL_HREF_PREFIX = "/?proposta="
MAX_NOTE_CHARS = 200
_SLUG_MAX = 80


def compact_builder_capabilities(catalog: dict[str, Any]) -> dict[str, Any]:
    """Representação compacta da fonte canônica. Sem lista paralela de opções."""
    return {
        "price": _money(catalog.get("price_cents")),
        "weight_grams": catalog.get("weight_grams"),
        "preparations": [_compact_option(row) for row in catalog.get("doughs") or []],
        "flours": [_compact_option(row) for row in catalog.get("flours") or []],
        "inclusions": [_compact_option(row) for row in catalog.get("ingredients") or []],
        "shapes": [_compact_option(row) for row in catalog.get("shapes") or []],
        "structured": ["flour", "preparation", "inclusions", "shape"],
        "free_text": (
            "Observação opcional no campo livre. A Loja avalia; "
            "não vira escolha estruturada nem altera o preço sozinha."
        ),
        "limits": (
            "Use só estes slugs. Não invente ingrediente, formato ou preço. "
            "Não prometa textura, aceite, data ou capacidade."
        ),
    }


def propose_from_slugs(
    session: Session,
    settings: Settings,
    *,
    flour: str = "",
    preparation: str = "",
    inclusions: list[str] | None = None,
    shape: str = "",
    note: str = "",
) -> dict[str, Any]:
    catalog = public_builder_catalog(session)
    resolved = resolve_slugs(
        catalog,
        flour=_clean_slug(flour),
        preparation=_clean_slug(preparation),
        inclusions=[_clean_slug(item) for item in (inclusions or []) if _clean_slug(item)],
        shape=_clean_slug(shape),
        note=strip_instructions(note)[:MAX_NOTE_CHARS],
    )
    if not resolved["kept_slugs"]:
        return {
            "accepted": False,
            "reason": resolved["reason"] or "Nenhuma escolha do Criador foi reconhecida.",
            "unknown": resolved["unknown"],
            "needs_choice": resolved["needs_choice"],
            "dropped": resolved["dropped"],
        }
    token = sign_proposal(settings, resolved["payload"])
    summary = _summary(resolved["choices"])
    href = f"{PROPOSAL_HREF_PREFIX}{token}#criacao"
    return {
        "accepted": True,
        "summary": summary,
        "proposal_token": token,
        "href": href,
        "cta": {"href": href, "label": BUILDER_CTA_LABEL, "kind": "builder"},
        "needs_choice": resolved["needs_choice"],
        "dropped": resolved["dropped"],
        "unknown": resolved["unknown"],
        "observation_pending": bool(resolved["payload"].get("note")),
        "note": (
            "Isso abre o Criador com esta composição. "
            "Não cria pedido, não reserva data e não adiciona ao carrinho."
        ),
    }


def resolve_proposal(session: Session, settings: Settings, token: str) -> dict[str, Any]:
    payload = verify_proposal(settings, token)
    catalog = public_builder_catalog(session)
    resolved = resolve_slugs(
        catalog,
        flour=str(payload.get("flour") or ""),
        preparation=str(payload.get("preparation") or ""),
        inclusions=list(payload.get("inclusions") or []),
        shape=str(payload.get("shape") or ""),
        note=str(payload.get("note") or ""),
    )
    choices = resolved["choices"]
    return {
        "token_ok": True,
        "flour_id": (choices.get("flour") or {}).get("id") or "",
        "flour_name": (choices.get("flour") or {}).get("name") or "",
        "flour_slug": (choices.get("flour") or {}).get("slug") or "",
        "dough_id": (choices.get("preparation") or {}).get("id") or "",
        "dough_name": (choices.get("preparation") or {}).get("name") or "",
        "dough_slug": (choices.get("preparation") or {}).get("slug") or "",
        "ingredient_ids": [item["id"] for item in choices.get("inclusions") or []],
        "ingredient_names": [item["name"] for item in choices.get("inclusions") or []],
        "ingredient_slugs": [item["slug"] for item in choices.get("inclusions") or []],
        "shape_id": (choices.get("shape") or {}).get("id") or "",
        "shape_name": (choices.get("shape") or {}).get("name") or "",
        "shape_slug": (choices.get("shape") or {}).get("slug") or "",
        "free_text": str(payload.get("note") or ""),
        "needs_choice": resolved["needs_choice"],
        "dropped": resolved["dropped"],
        "unknown": resolved["unknown"],
        "notice": _apply_notice(resolved),
        "source": "gigio",
        "price_cents": catalog.get("price_cents"),
        "weight_grams": catalog.get("weight_grams"),
    }


def resolve_slugs(
    catalog: dict[str, Any],
    *,
    flour: str,
    preparation: str,
    inclusions: list[str],
    shape: str,
    note: str,
) -> dict[str, Any]:
    flours = {row["slug"]: row for row in catalog.get("flours") or [] if row.get("slug")}
    doughs = {row["slug"]: row for row in catalog.get("doughs") or [] if row.get("slug")}
    extras = {row["slug"]: row for row in catalog.get("ingredients") or [] if row.get("slug")}
    shapes = {row["slug"]: row for row in catalog.get("shapes") or [] if row.get("slug")}
    unknown: list[str] = []
    dropped: list[dict[str, str]] = []
    needs_choice: list[str] = []
    choices: dict[str, Any] = {}

    if flour:
        if flour in flours:
            choices["flour"] = flours[flour]
        else:
            unknown.append(flour)
            dropped.append(
                {"slug": flour, "field": "flour", "reason": "esta farinha não está no Criador"}
            )
            needs_choice.append("flour")
    else:
        needs_choice.append("flour")

    if preparation:
        if preparation in doughs:
            choices["preparation"] = doughs[preparation]
        else:
            unknown.append(preparation)
            dropped.append(
                {
                    "slug": preparation,
                    "field": "preparation",
                    "reason": "este preparo não está no Criador",
                }
            )
            needs_choice.append("preparation")
    else:
        needs_choice.append("preparation")

    kept_inclusions = []
    seen: set[str] = set()
    for slug in inclusions:
        if slug in seen:
            continue
        seen.add(slug)
        if slug in extras:
            kept_inclusions.append(extras[slug])
        elif slug in flours or slug in doughs or slug in shapes:
            dropped.append(
                {"slug": slug, "field": "inclusions", "reason": "este slug não é complemento"}
            )
            unknown.append(slug)
        else:
            unknown.append(slug)
            dropped.append(
                {
                    "slug": slug,
                    "field": "inclusions",
                    "reason": "este complemento não está no Criador",
                }
            )
    if kept_inclusions:
        choices["inclusions"] = kept_inclusions

    if shape:
        if shape in shapes:
            choices["shape"] = shapes[shape]
        else:
            unknown.append(shape)
            dropped.append(
                {"slug": shape, "field": "shape", "reason": "este formato não está no Criador"}
            )
            needs_choice.append("shape")

    kept_slugs = {
        "flour": (choices.get("flour") or {}).get("slug") or "",
        "preparation": (choices.get("preparation") or {}).get("slug") or "",
        "inclusions": [item["slug"] for item in choices.get("inclusions") or []],
        "shape": (choices.get("shape") or {}).get("slug") or "",
        "note": note.strip()[:MAX_NOTE_CHARS],
    }
    has_structured = bool(
        kept_slugs["flour"]
        or kept_slugs["preparation"]
        or kept_slugs["inclusions"]
        or kept_slugs["shape"]
    )
    reason = ""
    if not has_structured:
        if unknown:
            reason = "Essas opções não existem no Criador. Escolha entre as capacidades reais."
        else:
            reason = "Informe farinha, preparo ou formato com slugs do Criador."
    return {
        "choices": choices,
        "payload": kept_slugs,
        "kept_slugs": has_structured,
        "unknown": unknown,
        "dropped": dropped,
        "needs_choice": list(dict.fromkeys(needs_choice)),
        "reason": reason,
    }


def sign_proposal(settings: Settings, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    raw = urlsafe_b64encode(encoded)
    body = raw.decode("ascii").rstrip("=")
    digest = hmac.new(_secret(settings), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{digest}"


def verify_proposal(settings: Settings, token: str) -> dict[str, Any]:
    value = (token or "").strip()
    if "." not in value or len(value) > 800:
        raise ConfirmationError("esta sugestão do Gigio não é mais válida")
    body, digest = value.rsplit(".", 1)
    expected = hmac.new(_secret(settings), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    if len(digest) != len(expected) or not hmac.compare_digest(digest, expected):
        raise ConfirmationError("esta sugestão do Gigio não é mais válida")
    padded = body + "=" * (-len(body) % 4)
    try:
        parsed = json.loads(urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ConfirmationError("esta sugestão do Gigio não é mais válida") from exc
    if not isinstance(parsed, dict):
        raise ConfirmationError("esta sugestão do Gigio não é mais válida")
    return {
        "flour": _clean_slug(str(parsed.get("flour") or "")),
        "preparation": _clean_slug(str(parsed.get("preparation") or "")),
        "inclusions": [
            _clean_slug(str(item))
            for item in (parsed.get("inclusions") or [])
            if _clean_slug(str(item))
        ],
        "shape": _clean_slug(str(parsed.get("shape") or "")),
        "note": strip_instructions(str(parsed.get("note") or ""))[:MAX_NOTE_CHARS],
    }


def _secret(settings: Settings) -> bytes:
    raw = (settings.customer_identity_secret or settings.admin_session_secret or "").strip()
    if len(raw) < 16:
        raw = "lojadepaes-builder-proposal-local"
    return raw.encode("utf-8")


def _clean_slug(value: str) -> str:
    slug = strip_instructions(value).strip().casefold().replace(" ", "-")
    if not slug or len(slug) > _SLUG_MAX:
        return ""
    if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in slug):
        return ""
    return slug


def _compact_option(row: dict[str, Any]) -> dict[str, str]:
    return {
        "slug": str(row.get("slug") or ""),
        "name": str(row.get("name") or ""),
        "description": strip_instructions(str(row.get("description") or "")),
    }


def _money(cents: object) -> str | None:
    if cents is None:
        return None
    try:
        value = int(cents)
    except (TypeError, ValueError):
        return None
    return f"R$ {value / 100:.2f}".replace(".", ",")


def _summary(choices: dict[str, Any]) -> str:
    parts = []
    flour = choices.get("flour") or {}
    prep = choices.get("preparation") or {}
    if flour.get("name") or prep.get("name"):
        parts.append(" · ".join(item for item in (flour.get("name"), prep.get("name")) if item))
    extras = [item.get("name") for item in choices.get("inclusions") or [] if item.get("name")]
    if extras:
        parts.append(", ".join(extras))
    shape = (choices.get("shape") or {}).get("name")
    if shape:
        parts.append(shape)
    return " · ".join(parts) or "Composição do Criador"


def _apply_notice(resolved: dict[str, Any]) -> str:
    bits = ["Sugestão do Gigio. Você pode alterar."]
    if resolved["needs_choice"]:
        labels = {
            "flour": "farinha",
            "preparation": "fermentação e preparo",
            "shape": "formato",
        }
        missing = [labels.get(item, item) for item in resolved["needs_choice"]]
        bits.append("Falta escolher: " + ", ".join(missing) + ".")
    if resolved["dropped"]:
        names = ", ".join(item["slug"] for item in resolved["dropped"])
        bits.append(f"Não aplicamos {names}: não está no Criador.")
    return " ".join(bits)
