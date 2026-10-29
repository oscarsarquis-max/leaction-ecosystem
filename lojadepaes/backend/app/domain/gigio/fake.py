from __future__ import annotations

import json

from app.domain.accompaniment_context import (
    MEAL_COMPLEMENTS,
    infer_beer_style_from_text,
    infer_categories_from_text,
    infer_dishes_from_text,
    infer_potato_form_from_text,
    infer_wine_style_from_text,
)
from app.domain.gigio.gateway import ChatRequest, ChatResponse, GatewayError


class FakeGigioGateway:
    def __init__(self, script: list[ChatResponse] | None = None) -> None:
        self.calls: list[ChatRequest] = []
        self.script = list(script or [])

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        if self.script:
            return self.script.pop(0)
        if "dica do Gigio" in request.system_prompt or "Composição atual do Criador:" in " ".join(
            turn.text for turn in request.messages
        ):
            return ChatResponse(
                text=_tip_json(request),
                tool_use=[],
                stop_reason="end_turn",
                input_tokens=12,
                output_tokens=60,
                latency_ms=6,
                provider="fake",
                model_id="fake",
                region="local",
            )
        if not request.tools:
            payload = _last_tool_payload(request)
            return ChatResponse(
                text=_reply_from_tool(payload) if payload is not None else "Posso ajudar com ideias para a mesa e com o pedido.",
                tool_use=[],
                stop_reason="end_turn",
                input_tokens=12,
                output_tokens=40,
                latency_ms=8,
                provider="fake",
                model_id="fake",
                region="local",
            )
        last = request.messages[-1] if request.messages else None
        user_text = ""
        for turn in reversed(request.messages):
            if turn.role == "user" and turn.text:
                user_text = turn.text
                break
        if last and last.tool_results:
            nxt = _next_custom_tool(request, user_text)
            if nxt:
                return ChatResponse(
                    text="",
                    tool_use=[nxt],
                    stop_reason="tool_use",
                    input_tokens=10,
                    output_tokens=8,
                    latency_ms=5,
                    provider="fake",
                    model_id="fake",
                    region="local",
                )
            payload = last.tool_results[0].get("content") or {}
            return ChatResponse(
                text=_reply_from_tool(payload),
                tool_use=[],
                stop_reason="end_turn",
                input_tokens=12,
                output_tokens=40,
                latency_ms=8,
                provider="fake",
                model_id="fake",
                region="local",
            )
        tool = _choose_tool(user_text)
        if tool:
            return ChatResponse(
                text="",
                tool_use=[tool],
                stop_reason="tool_use",
                input_tokens=10,
                output_tokens=8,
                latency_ms=5,
                provider="fake",
                model_id="fake",
                region="local",
            )
        if "timeout" in user_text.casefold():
            raise GatewayError("timeout", "modelo demorou demais")
        if "retirada" in user_text.casefold() or "retirar" in user_text.casefold():
            return ChatResponse(
                text=(
                    "A Loja faz somente entregas. Não há retirada. "
                    "Você informa o endereço ao finalizar o pedido."
                ),
                tool_use=[],
                stop_reason="end_turn",
                input_tokens=8,
                output_tokens=24,
                latency_ms=4,
                provider="fake",
                model_id="fake",
                region="local",
            )
        return ChatResponse(
            text="Posso ajudar com ideias para a mesa e com o pedido. O que você gostaria de saber?",
            tool_use=[],
            stop_reason="end_turn",
            input_tokens=8,
            output_tokens=20,
            latency_ms=4,
            provider="fake",
            model_id="fake",
            region="local",
        )


def _choose_tool(text: str) -> dict | None:
    lowered = text.casefold()
    if "pedido" in lowered and ("lp-" in lowered or "meu pedido" in lowered or "encomenda" in lowered):
        return {"id": "tool-order", "name": "lookup_order", "input": {}}
    if "fidelidade" in lowered or "carimbo" in lowered or "focaccia" in lowered:
        return {"id": "tool-fid", "name": "lookup_fidelity", "input": {}}
    if "agenda" in lowered or "hoje" in lowered or "calendário" in lowered or "calendario" in lowered:
        return {"id": "tool-cal", "name": "lookup_schedule", "input": {}}
    if "harmoniz" in lowered or "referência especializada" in lowered or "referencia especializada" in lowered:
        return {
            "id": "tool-pair",
            "name": "lookup_pairing_references",
            "input": {
                "q": text[:80],
                "categories": infer_categories_from_text(text),
                "dishes": infer_dishes_from_text(text),
            },
        }
    if any(token in lowered for token in ("hamburguer", "hambúrguer", "hamburger", "burger")) and (
        "pão" in lowered or "pao" in lowered
    ):
        return {"id": "tool-p", "name": "lookup_products", "input": {"q": text[:80]}}
    if "levain" in lowered or "sovado" in lowered or "fermentação" in lowered or "fermentacao" in lowered:
        return {"id": "tool-ed", "name": "lookup_editorial", "input": {}}
    if _wants_custom(lowered):
        return {"id": "tool-p", "name": "lookup_products", "input": {"q": text[:80]}}
    if "criador" in lowered or "farinha" in lowered:
        return {"id": "tool-b", "name": "lookup_builder", "input": {}}
    if "receita" in lowered:
        return {"id": "tool-r", "name": "lookup_recipes", "input": {"q": text[:80]}}
    if any(
        token in lowered
        for token in (
            "acompanhar",
            "acompanhamento",
            "complemento",
            "azeite",
            "geleia",
            "vinho",
            "queijo",
            "servir",
            "leitão",
            "leitao",
            "porco",
            "mesa",
            "frios",
            "embutido",
            "peixe",
            "sardinha",
            "camarão",
            "camarao",
            "lagosta",
            "hamburguer",
            "hambúrguer",
            "cerveja",
            "batata",
            "bebida",
        )
    ):
        dishes = infer_dishes_from_text(text)
        categories = infer_categories_from_text(text)
        if not categories and dishes:
            for dish in dishes:
                for category in MEAL_COMPLEMENTS.get(dish, ("vinhos", "queijos", "azeites")):
                    if category not in categories:
                        categories.append(category)
        return {
            "id": "tool-acc",
            "name": "lookup_accompaniments",
            "input": {
                "categories": categories,
                "wine_style": infer_wine_style_from_text(text),
                "beer_style": infer_beer_style_from_text(text),
                "potato_form": infer_potato_form_from_text(text),
                "dishes": dishes,
            },
        }
    if "pão" in lowered or "pao" in lowered or "vitrine" in lowered or "ideia" in lowered:
        return {"id": "tool-p", "name": "lookup_products", "input": {"q": text[:80]}}
    return None


def _reply_from_tool(payload: object) -> str:
    data = payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {"raw": payload}
    if not isinstance(data, dict):
        return "Consultei A Loja e posso ajudar com o que está publicado."
    if data.get("authorized") is False:
        return str(data.get("reason") or "Não posso abrir este pedido por aqui.")
    if data.get("authorized") is True:
        return f"Sobre o pedido {data.get('reference')}: {data.get('next_action')}"
    if data.get("found") is False:
        return str(data.get("reason") or "Não encontrei isso publicado.")
    if data.get("found") is True and data.get("href"):
        name = data.get("name") or data.get("title")
        return f"{name} está no acervo de A Loja. Leia em {data.get('href')}."
    notes = data.get("notes") or []
    if notes:
        first = notes[0]
        return f"{first.get('title')}: {first.get('body')}"
    refs = data.get("references") or []
    if refs:
        first = refs[0]
        return (
            f"{first.get('title')}: {first.get('synthesis')} "
            "Esta é uma sugestão do Gigio a partir da fonte consultada, sem endosso do produtor."
        )
    if data.get("enabled") is False and data.get("reason"):
        return str(data["reason"])
    items = data.get("items") or []
    if items:
        first = items[0]
        label = first.get("name") or first.get("title")
        href = first.get("href")
        extra = f" Veja {href}." if href else ""
        outbound = first.get("outbound_href")
        destination = first.get("outbound_label") or "No Mercado Livre"
        market = f" {destination}: {outbound}." if outbound else ""
        note = " Compra e entrega são separadas." if outbound else ""
        demo = " Esta é uma prévia local simulada, sem oferta comercial." if first.get("demo") else ""
        cta = data.get("cta") or {}
        button = f" {cta.get('label')}: {cta.get('href')}." if cta.get("href") and cta.get("label") else extra
        return (
            f"Na vitrine/acervo de A Loja está {label}.{button}{market}{note}{demo} "
            "Esta é uma sugestão a partir do que está publicado."
        )
    if data.get("how_it_works"):
        return str(data["how_it_works"])
    if data.get("same_day_rule"):
        return f"{data['same_day_rule']} {data.get('date_request')}"
    if data.get("preparations"):
        return (
            f"No Criador, o pão padrão tem {data.get('weight_grams')} g e {data.get('price')}. "
            "Nome e e-mail vêm antes do envio; o aceite de A Loja libera o pagamento do personalizado."
        )
    if data.get("accepted") is True:
        cta = data.get("cta") or {}
        button = f" {cta.get('label')}: {cta.get('href')}." if cta.get("href") else ""
        return (
            f"Para montar no Criador: {data.get('summary')}.{button} "
            "Isso não cria pedido, não reserva data e não adiciona ao carrinho."
        )
    if data.get("accepted") is False:
        return str(data.get("reason") or "Essa combinação não está no Criador.")
    return "Consultei as informações publicadas de A Loja."


def _wants_custom(text: str) -> bool:
    return any(
        token in text
        for token in (
            "sanduíche",
            "sanduiche",
            "personalizado",
            "montar um pão",
            "montar um pao",
            "pão de forma",
            "pao de forma",
            "fermentação natural",
            "fermentacao natural",
        )
    )


def _last_tool_payload(request: ChatRequest) -> dict | None:
    chosen: dict | None = None
    for turn in request.messages:
        for item in turn.tool_results or []:
            content = item.get("content") or {}
            if isinstance(content, dict):
                chosen = content
                if content.get("accepted") is not None:
                    return content
    return chosen


def _tools_used(request: ChatRequest) -> set[str]:
    names: set[str] = set()
    for turn in request.messages:
        for tool in turn.tool_use or []:
            name = str(tool.get("name") or "")
            if name:
                names.add(name)
    return names


def _next_custom_tool(request: ChatRequest, user_text: str) -> dict | None:
    if not _wants_custom(user_text.casefold()):
        return None
    used = _tools_used(request)
    if "lookup_builder" not in used:
        return {"id": "tool-b", "name": "lookup_builder", "input": {}}
    if "propose_builder" not in used:
        return {"id": "tool-pb", "name": "propose_builder", "input": _propose_input(user_text)}
    return None


def _propose_input(text: str) -> dict:
    lowered = text.casefold()
    flour = "farinha-branca-strong-white"
    if "centeio" in lowered:
        flour = "farinha-integral-centeio"
    elif "integral" in lowered:
        flour = "farinha-integral-trigo"
    elif "fubá" in lowered or "fuba" in lowered:
        flour = "farinha-fuba"
    preparation = "fermentacao-natural-curta"
    if "maturada" in lowered:
        preparation = "maturada"
    elif "sovada" in lowered:
        preparation = "sovada"
    inclusions: list[str] = []
    if "parmes" in lowered or ("queijo" in lowered and "sem queijo" not in lowered):
        inclusions.append("queijo-parmesao")
    if "granola" in lowered or "grãos" in lowered or "graos" in lowered:
        inclusions.append("granola")
    if "nozes" in lowered:
        inclusions.append("nozes")
    shape = "pao-de-forma" if "rústico" not in lowered and "rustico" not in lowered else "rustico-de-cesto"
    if "inexistente" in lowered or "slug-falso" in lowered:
        inclusions.append("graos-inventados")
    return {
        "flour": flour,
        "preparation": preparation,
        "inclusions": inclusions,
        "shape": shape,
        "note": "",
    }


def _tip_json(request: ChatRequest) -> str:
    blob = " ".join(turn.text for turn in request.messages)
    current = blob.split("ocasião=")[0] if "ocasião=" in blob else blob
    extras = "parmesão" in current.casefold() or "queijo parmes" in current.casefold()
    observation = (
        "Farinha branca com fermentação natural curta e parmesão fica salgada e aromática, boa para fatiar."
        if extras
        else "Farinha branca e fermentação natural curta são uma base clara do Criador para fatiar."
    )
    suggestion = None
    if "sem queijo" not in blob.casefold() and not extras:
        suggestion = {
            "field": "inclusions",
            "add": ["queijo-parmesao"],
            "remove": [],
            "label": "Incluir queijo parmesão na massa",
        }
    return json.dumps(
        {
            "observation": observation,
            "serving": "Fatie e monte sanduíches; o recheio fica a seu gosto.",
            "suggestion": suggestion,
        },
        ensure_ascii=True,
    )
