from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.accompaniment_context import infer_exclusions_from_text, infer_suggested_query
from app.domain.accompaniments import gigio_lookup
from app.domain.builder_proposal import compact_builder_capabilities, resolve_slugs
from app.domain.custom_loaf import public_builder_catalog
from app.domain.errors import ConfirmationError
from app.domain.gigio.gateway import ChatRequest, ChatTurn, GigioGateway
from app.domain.gigio.policy import MAX_OUTPUT_CHARS, strip_instructions

TIP_USER_PREFIX = "Composição atual do Criador:"
TIP_SYSTEM = """
Você escreve uma dica curta do Gigio sobre UM pão já escolhido no Criador.
Responda só com JSON: {"observation":"...","serving":"...","suggestion":null}
ou suggestion como {"field":"inclusions","add":["slug"],"remove":[],"label":"..."}.
Regras: sem avaliação negativa de escolha válida; sem alergênico, glúten,
lactose, saúde ou textura garantida; sem inventar slug; suggestion só com
slugs da lista recebida; sem data, aceite, preço novo ou pedido.
observation e serving: uma frase cada, em português brasileiro.
""".strip()


def builder_tip(
    session: Session,
    settings: Settings,
    payload: dict[str, Any],
    gateway: GigioGateway,
) -> dict[str, Any]:
    catalog = public_builder_catalog(session)
    composition = _resolve_ids(catalog, payload)
    occasion = strip_instructions(str(payload.get("occasion") or ""))[:200]
    prior = strip_instructions(str(payload.get("context_text") or ""))[:400]
    exclusions = infer_exclusions_from_text(f"{prior} {occasion}".strip())
    acc = _accompaniments(session, settings, occasion, prior, exclusions, composition)
    draft = _ask_model(gateway, settings, catalog, composition, occasion, exclusions)
    suggestion = _sanitize_suggestion(catalog, composition, draft.get("suggestion"), exclusions)
    return {
        "ok": True,
        "observation": _clip(draft.get("observation"), 280)
        or "Esta combinação está disponível no Criador. A Loja avalia o pedido no aceite.",
        "serving": _clip(draft.get("serving"), 280)
        or "Fatie na hora de servir. Recheio e acompanhamentos ficam a seu gosto.",
        "composition": composition["public"],
        "suggestion": suggestion,
        "cta": acc.get("cta"),
        "notice": acc.get("notice") or "",
    }


def _resolve_ids(catalog: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    flour = _by_id(catalog.get("flours") or [], payload.get("flour_id"))
    dough = _by_id(catalog.get("doughs") or [], payload.get("dough_id"))
    shape = _by_id(catalog.get("shapes") or [], payload.get("shape_id"))
    extras = []
    seen: set[str] = set()
    for raw in payload.get("ingredient_ids") or []:
        item = _by_id(catalog.get("ingredients") or [], raw)
        if item and item["id"] not in seen:
            extras.append(item)
            seen.add(item["id"])
    if not flour or not dough:
        raise ConfirmationError("a composição ainda não está completa para a dica")
    note = strip_instructions(str(payload.get("free_text") or ""))[:200]
    public = {
        "flour": flour["name"],
        "preparation": dough["name"],
        "inclusions": [item["name"] for item in extras],
        "shape": shape["name"] if shape else "",
        "note": note,
    }
    return {
        "flour": flour,
        "preparation": dough,
        "inclusions": extras,
        "shape": shape,
        "note": note,
        "public": public,
        "slugs": {
            "flour": flour.get("slug") or "",
            "preparation": dough.get("slug") or "",
            "inclusions": [item.get("slug") or "" for item in extras],
            "shape": (shape or {}).get("slug") or "",
        },
    }


def _by_id(rows: list[dict[str, Any]], raw: object) -> dict[str, Any] | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        UUID(value)
    except ValueError:
        return None
    return next((row for row in rows if row.get("id") == value), None)


def _accompaniments(
    session: Session,
    settings: Settings,
    occasion: str,
    prior: str,
    exclusions: list[str],
    composition: dict[str, Any],
) -> dict[str, Any]:
    if not settings.gigio_accompaniments_enabled:
        return {"cta": None, "notice": ""}
    query_text = " ".join(
        part
        for part in (
            occasion,
            prior,
            composition["public"]["flour"],
            composition["public"]["preparation"],
            " ".join(composition["public"]["inclusions"]),
        )
        if part
    )
    query = infer_suggested_query(user_text=query_text, reply="", history=None)
    if not query.useful and not occasion:
        return {"cta": None, "notice": ""}
    result = gigio_lookup(
        session,
        settings,
        categories=query.categories,
        wine_style=query.wine_style,
        beer_style=query.beer_style,
        potato_form=query.potato_form,
        dishes=query.dishes,
        query_text=query_text,
        exclusions=exclusions,
    )
    cta = result.get("cta") or {}
    button = None
    if cta.get("href") and cta.get("label"):
        button = {"href": str(cta["href"]), "label": str(cta["label"]), "kind": "vitrine"}
    return {"cta": button, "notice": str(result.get("notice") or "")}


def _ask_model(
    gateway: GigioGateway,
    settings: Settings,
    catalog: dict[str, Any],
    composition: dict[str, Any],
    occasion: str,
    exclusions: list[str],
) -> dict[str, Any]:
    capabilities = compact_builder_capabilities(catalog)
    user = (
        f"{TIP_USER_PREFIX} {json.dumps(composition['public'], ensure_ascii=True)}. "
        f"ocasião={occasion or 'não informada'}. "
        f"exclusões={', '.join(exclusions) or 'nenhuma'}. "
        f"slugs={json.dumps(capabilities, ensure_ascii=True)}"
    )
    try:
        response = gateway.complete(
            ChatRequest(
                system_prompt=TIP_SYSTEM,
                messages=[ChatTurn(role="user", text=user)],
                tools=[],
                max_tokens=min(400, settings.bedrock_max_tokens or 400),
            )
        )
    except Exception:
        raise ConfirmationError("não consegui montar a dica agora")
    text = (response.text or "").strip()
    if not text:
        raise ConfirmationError("não consegui montar a dica agora")
    parsed = _parse_tip_json(text)
    if parsed is None:
        raise ConfirmationError("não consegui montar a dica agora")
    return parsed


def _parse_tip_json(text: str) -> dict[str, Any] | None:
    clipped = text[:MAX_OUTPUT_CHARS]
    match = re.search(r"\{.*\}", clipped, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _sanitize_suggestion(
    catalog: dict[str, Any],
    composition: dict[str, Any],
    raw: object,
    exclusions: list[str],
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    field = str(raw.get("field") or "inclusions")
    add = [str(item) for item in (raw.get("add") or [])][:3]
    remove = [str(item) for item in (raw.get("remove") or [])][:3]
    current = {
        "flour": composition["slugs"]["flour"],
        "preparation": composition["slugs"]["preparation"],
        "inclusions": list(composition["slugs"]["inclusions"]),
        "shape": composition["slugs"]["shape"],
        "note": composition["note"],
    }
    if field == "flour" and add:
        current["flour"] = add[0]
    elif field == "preparation" and add:
        current["preparation"] = add[0]
    elif field == "shape" and add:
        current["shape"] = add[0]
    else:
        kept = [slug for slug in current["inclusions"] if slug not in remove]
        for slug in add:
            if slug not in kept:
                kept.append(slug)
        current["inclusions"] = kept
    blocked = {item.casefold() for item in exclusions}
    if blocked & {"queijos", "queijo", "laticinio", "laticínio"}:
        current["inclusions"] = [slug for slug in current["inclusions"] if "queijo" not in slug]
    resolved = resolve_slugs(
        catalog,
        flour=current["flour"],
        preparation=current["preparation"],
        inclusions=current["inclusions"],
        shape=current["shape"],
        note=current["note"],
    )
    if resolved["unknown"] or not resolved["kept_slugs"]:
        return None
    changes = _diff(composition, resolved["choices"])
    if not changes:
        return None
    return {
        "label": _clip(raw.get("label"), 120) or "Aplicar ajuste sugerido na massa",
        "changes": changes,
        "patch": {
            "flour_id": (resolved["choices"].get("flour") or {}).get("id") or "",
            "flour_name": (resolved["choices"].get("flour") or {}).get("name") or "",
            "dough_id": (resolved["choices"].get("preparation") or {}).get("id") or "",
            "dough_name": (resolved["choices"].get("preparation") or {}).get("name") or "",
            "ingredient_ids": [item["id"] for item in resolved["choices"].get("inclusions") or []],
            "ingredient_names": [
                item["name"] for item in resolved["choices"].get("inclusions") or []
            ],
            "shape_id": (resolved["choices"].get("shape") or {}).get("id") or "",
            "shape_name": (resolved["choices"].get("shape") or {}).get("name") or "",
        },
    }


def _diff(composition: dict[str, Any], next_choices: dict[str, Any]) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    pairs = (
        (
            "flour",
            composition["flour"]["name"],
            (next_choices.get("flour") or {}).get("name") or "",
        ),
        (
            "preparation",
            composition["preparation"]["name"],
            (next_choices.get("preparation") or {}).get("name") or "",
        ),
        (
            "shape",
            (composition["shape"] or {}).get("name") or "",
            (next_choices.get("shape") or {}).get("name") or "",
        ),
    )
    for field, before, after in pairs:
        if before != after:
            changes.append({"field": field, "from": before, "to": after})
    before_extras = ", ".join(composition["public"]["inclusions"]) or "sem complementos"
    after_extras = (
        ", ".join(item["name"] for item in next_choices.get("inclusions") or [])
        or "sem complementos"
    )
    if before_extras != after_extras:
        changes.append({"field": "inclusions", "from": before_extras, "to": after_extras})
    return changes


def _clip(value: object, limit: int) -> str:
    return strip_instructions(str(value or "")).strip()[:limit]
