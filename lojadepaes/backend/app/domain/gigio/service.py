from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import ConfirmationError
from app.domain.gigio.editorial import ensure_editorial_seeds
from app.domain.gigio.pairing import (
    ensure_pairing_seeds,
    is_allowed_source_url,
    needs_stored_evidence,
    sources_for_conversation,
    stored_evidence_brief,
)
from app.domain.gigio.fake import FakeGigioGateway
from app.domain.gigio.gateway import ChatRequest, ChatTurn, GigioGateway
from app.domain.gigio.hygiene import (
    RECOVERY_PROMPT,
    note_invalid_reply,
    note_recovery,
    usable_customer_reply,
)
from app.domain.gigio.policy import (
    INCOMPLETE_REPLY,
    MAX_OUTPUT_CHARS,
    MAX_TOOL_ROUNDS,
    SHOWCASE_CORRECTION,
    SYNTHESIS_PROMPT,
    clip_history,
    looks_like_injection,
    sanitize_user_text,
)
from app.domain.gigio.rules import (
    CULINARY_PROMPTS,
    PROCESS_RULES,
    PROCESS_RULES_VERSION,
    STARTER_PROMPTS,
    WELCOME,
)
from app.domain.gigio.settings import (
    GigioSettingsError,
    load_gigio_model_settings,
    public_model_family,
)
from app.domain.accompaniment_context import _is_guide_score_turn, infer_exclusions_from_text, infer_suggested_query
from app.domain.accompaniments import gigio_lookup
from app.domain.baker_library.access import access_for_account, can_use_ai
from app.domain.baker_library.articles import article_context
from app.domain.baker_library.credits import (
    confirm_credit,
    recovered_reply,
    release_credit,
    remember_operation,
    reserve_credit,
)
from app.domain.baker_library.function import classify_function, deepening_required
from app.domain.baker_library.usage import accidental_repeat, record_usage
from app.domain.actionhub_client import HubUnavailableError
from app.domain.gigio.consult import (
    FREE_ONCE,
    deepen_offer,
    drop_phantom_click,
    free_reply_invites_refinement,
    is_culinary_refinement,
)
from app.domain.gigio.intent import (
    decide_turn,
    skip_accompaniments_result,
    skip_builder_result,
    skip_pairing_result,
)
from app.models.customers import CustomerAccount
from app.domain.gigio.tools import TOOL_SPECS, asks_published_showcase, execute_tool
from app.domain.marketplace_links import is_allowed_outbound_url

logger = logging.getLogger("lojadepaes.gigio")


def resolve_gateway(settings: Settings, override: GigioGateway | None = None) -> GigioGateway:
    if override is not None:
        return override
    mode = (settings.gigio_gateway or "").strip().lower()
    env = settings.env.strip().lower()
    if mode == "fake" or (not mode and env in {"test", "local", "development", "dev"}):
        return FakeGigioGateway()
    from app.domain.gigio.bedrock import BedrockGigioGateway

    model = load_gigio_model_settings(settings)
    return BedrockGigioGateway(settings=model)


def status_payload(settings: Settings) -> dict[str, Any]:
    enabled = bool(settings.gigio_enabled)
    ready = False
    provider = None
    region = None
    family = None
    if enabled:
        try:
            gateway = resolve_gateway(settings)
            ready = True
            if isinstance(gateway, FakeGigioGateway):
                provider = "fake"
                region = "local"
                family = "fake"
            else:
                model = load_gigio_model_settings(settings)
                provider = "bedrock"
                region = model.region
                family = public_model_family(model.model_id)
        except (GigioSettingsError, Exception):
            ready = False
    return {
        "enabled": enabled,
        "ready": ready,
        "welcome": WELCOME if enabled else None,
        "starters": list(STARTER_PROMPTS) if enabled else [],
        "culinary": list(CULINARY_PROMPTS) if enabled else [],
        "rules_version": PROCESS_RULES_VERSION,
        "provider": provider,
        "region": region,
        "model_family": family,
    }


def chat(
    session: Session,
    settings: Settings,
    *,
    messages: list[dict],
    page: dict | None,
    order_token: str | None,
    is_admin: bool,
    gateway: GigioGateway | None = None,
    account: CustomerAccount | None = None,
    spend_credit: bool = False,
    operation_id: str | None = None,
) -> dict[str, Any]:
    if not settings.gigio_enabled:
        raise ConfirmationError("o Gigio não está disponível neste ambiente")
    ensure_editorial_seeds(session)
    ensure_pairing_seeds(session)
    history = clip_history(messages)
    if not history or history[-1]["role"] != "user":
        raise ConfirmationError("envie uma pergunta")
    user_text = sanitize_user_text(history[-1]["content"])
    if looks_like_injection(user_text):
        return {
            "reply": "Posso ajudar com os pães da vitrine e com o pedido, dentro das regras de A Loja.",
            "links": [],
            "cta": None,
            "builder_cta": None,
            "sources": [],
            "suggestions": list(STARTER_PROMPTS),
            "unavailable": False,
        }
    page = page or {}
    decision = decide_turn(user_text, history)
    function = classify_function(page, decision)
    if function == "atendimento" and is_culinary_refinement(user_text, history):
        logger.info("gigio.consult action=offer")
        return deepen_offer()
    library = page.get("library") if isinstance(page.get("library"), dict) else {}
    article_id = str(library.get("article_id") or "")[:80]
    credit_guard: dict[str, Any] | None = None
    if deepening_required(function):
        access = access_for_account(session, settings, account)
        if not can_use_ai(access) and not access.get("authorized"):
            record_usage(
                session,
                settings,
                origin="biblioteca",
                function="deepen_blocked",
                ok=False,
                duration_ms=0,
                fail_kind=str(access.get("reason") or "no_entitlement")[:40],
                account=account,
                article_id=article_id,
            )
            return {
                "reply": str(access.get("message") or "Este aprofundamento faz parte do plano mensal da Biblioteca."),
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "notice": str(access.get("message") or ""),
                "offer": access.get("plan"),
                "access": {
                    "authorized": False,
                    "reason": access.get("reason"),
                    "identified": access.get("identified"),
                    "credits": access.get("credits"),
                    "exhausted": access.get("exhausted"),
                },
                "unavailable": False,
            }
        if not spend_credit:
            return {
                "reply": (
                    "Você está entrando no aprofundamento com créditos da Biblioteca. "
                    "Saldo e custo aparecem antes do envio. Confirme Usar 1 crédito para mandar esta consulta."
                ),
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "notice": "Envio consciente: 1 crédito por consulta neste modo.",
                "offer": access.get("plan"),
                "access": {
                    "authorized": True,
                    "needs_confirm": True,
                    "credits": access.get("credits"),
                    "valid_until": access.get("valid_until"),
                    "exhausted": access.get("exhausted"),
                    "complementary_eligible": access.get("complementary_eligible"),
                    "balance_source": access.get("balance_source"),
                },
                "unavailable": False,
            }
        op_id = str(operation_id or "").strip()[:80]
        if not op_id or account is None:
            return {
                "reply": "Identifique-se e confirme Usar 1 crédito para esta consulta.",
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "access": {"authorized": True, "needs_confirm": True, "credits": access.get("credits")},
                "unavailable": False,
            }
        recovered = recovered_reply(session, op_id)
        if recovered:
            return recovered
        if access.get("balance_source") == "unavailable":
            return {
                "reply": str(access.get("message") or "O ActionHub não respondeu. Isso não esgota o saldo."),
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "access": {
                    "authorized": True,
                    "reason": "hub_unavailable",
                    "credits": None,
                    "exhausted": False,
                },
                "unavailable": True,
            }
        if access.get("exhausted"):
            return {
                "reply": (
                    "Os créditos deste ciclo acabaram. Artigos, calculadora, compras e atendimento "
                    "continuam abertos. O pacote adicional é compra avulsa na página de planos do ActionHub."
                ),
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "offer": access.get("plan"),
                "access": {
                    "authorized": True,
                    "exhausted": True,
                    "credits": 0,
                    "complementary_eligible": access.get("complementary_eligible"),
                },
                "unavailable": False,
            }
        repeat_key = f"deepen:{account.id}:{article_id}:{op_id}"
        if accidental_repeat(repeat_key):
            return {
                "reply": "Já estou nesta pergunta. Espere a resposta anterior antes de mandar de novo.",
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "unavailable": False,
            }
        try:
            reserved = reserve_credit(settings, account, op_id)
        except HubUnavailableError:
            return {
                "reply": (
                    "Não foi possível reservar o crédito no ActionHub agora. "
                    "Isso não esgota o saldo nem cancela a assinatura."
                ),
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "access": {"authorized": True, "reason": "hub_unavailable", "exhausted": False},
                "unavailable": True,
            }
        if not reserved.get("ok"):
            return {
                "reply": str(reserved.get("message") or "Não foi possível usar o crédito agora."),
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": [],
                "offer": access.get("plan"),
                "access": {
                    "authorized": True,
                    "reason": reserved.get("reason"),
                    "credits": reserved.get("credits"),
                    "exhausted": reserved.get("reason") == "insufficient_credits",
                    "complementary_eligible": access.get("complementary_eligible"),
                },
                "unavailable": False,
            }
        remember_operation(session, settings, account, op_id, "reserved")
        credit_guard = {"operation_id": op_id, "account": account}
    context = _page_context(page, session=session, function=function)
    system = PROCESS_RULES + context
    if function == "atendimento" and (decision.accompaniments or decision.kind == "table"):
        system = f"{system}\n\n{FREE_ONCE}"
    prior = history[:-1]
    if settings.gigio_pairing_refs_enabled and needs_stored_evidence(
        user_text, prior, accompaniments=decision.accompaniments
    ):
        brief, evidence_keys = stored_evidence_brief(session, user_text=user_text, history=prior)
        if brief:
            system = f"{system}\n\n{brief}"
            logger.info("gigio.evidence keys=%s", ",".join(evidence_keys) or "-")
    turns = [ChatTurn(role=item["role"], text=item["content"]) for item in history]
    adapter = resolve_gateway(settings, gateway)
    collected_links: list[dict[str, str]] = []
    collected_sources: list[dict] = []
    collected_notices: list[dict] = []
    started = time.perf_counter()
    tool_rounds = 0
    tool_names: list[str] = []
    showcase_count: int | None = None
    recoveries = 0
    force_no_tools = False
    allowed_tools = {str(spec.get("name") or "") for spec in TOOL_SPECS}
    try:
        while True:
            allow_tools = tool_rounds < MAX_TOOL_ROUNDS and not force_no_tools
            if not allow_tools and not any(
                turn.role == "user" and turn.text in {SYNTHESIS_PROMPT, RECOVERY_PROMPT, SHOWCASE_CORRECTION}
                for turn in turns
            ):
                turns.append(ChatTurn(role="user", text=SYNTHESIS_PROMPT))
            response = adapter.complete(
                ChatRequest(
                    system_prompt=system,
                    messages=turns,
                    tools=TOOL_SPECS if allow_tools else [],
                    max_tokens=min(800, settings.bedrock_max_tokens or 800),
                )
            )
            structured = [
                tool
                for tool in (response.tool_use or [])
                if allow_tools and str(tool.get("name") or "") in allowed_tools
            ]
            if structured:
                results = []
                for tool in structured:
                    result = _execute_allowed_tool(
                        str(tool.get("name")),
                        tool.get("input") if isinstance(tool.get("input"), dict) else {},
                        session=session,
                        settings=settings,
                        order_reference=str(page.get("order_reference") or "") or None,
                        order_token=order_token,
                        is_admin=is_admin,
                        decision=decision,
                        user_text=user_text,
                        history=history[:-1],
                    )
                    tool_names.append(str(tool.get("name") or ""))
                    if str(tool.get("name") or "") == "lookup_products" and result.get("mode") == "showcase":
                        showcase_count = int(result.get("count") or 0)
                    collected_links.extend(_links_from_tool(result))
                    collected_sources.extend(_sources_from_tool(result))
                    if result.get("notice") or result.get("hub_status"):
                        collected_notices.append(result)
                    results.append({"id": tool.get("id"), "content": result})
                turns.append(ChatTurn(role="assistant", tool_use=structured))
                turns.append(ChatTurn(role="user", tool_results=results))
                tool_rounds += 1
                continue
            reply = usable_customer_reply(response.text or "")[:MAX_OUTPUT_CHARS]
            if not reply:
                note_invalid_reply()
                if recoveries < 1:
                    recoveries += 1
                    note_recovery()
                    force_no_tools = True
                    has_data = bool(collected_links) or any(turn.tool_results for turn in turns)
                    turns.append(ChatTurn(role="user", text=SYNTHESIS_PROMPT if has_data else RECOVERY_PROMPT))
                    continue
                logger.info(
                    "gigio.chat empty provider=%s latency_ms=%s stop=%s tools=%s recoveries=%s",
                    response.provider,
                    int((time.perf_counter() - started) * 1000),
                    response.stop_reason,
                    tool_rounds,
                    recoveries,
                )
                _note_usage(
                    session,
                    settings,
                    function=function,
                    ok=False,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    fail_kind="empty",
                    account=account,
                    article_id=article_id,
                    provider=response.provider,
                    tokens_in=response.input_tokens,
                    tokens_out=response.output_tokens,
                )
                return _finish_deepen(
                    session,
                    settings,
                    credit_guard,
                    {
                        "reply": INCOMPLETE_REPLY,
                        "links": [],
                        "cta": None,
                        "builder_cta": None,
                        "sources": [],
                        "suggestions": list(STARTER_PROMPTS),
                        "unavailable": True,
                    },
                    consume=False,
                )
            if (
                function == "atendimento"
                and (decision.accompaniments or decision.kind == "table")
                and free_reply_invites_refinement(reply)
                and recoveries < 1
            ):
                recoveries += 1
                force_no_tools = True
                turns.append(
                    ChatTurn(
                        role="user",
                        text=(
                            "Consulta livre: apague a pergunta final e qualquer convite para continuar, "
                            "montar a mesa, orçamento ou preparo. Não use ponto de interrogação. "
                            "Feche com a condição assumida e a recomendação. "
                            "Cada item de lista fica em uma linha iniciada por hífen. Não chame ferramentas."
                        ),
                    )
                )
                continue
            if showcase_count and _claims_total_showcase_absence(reply) and recoveries < 1:
                recoveries += 1
                note_recovery()
                force_no_tools = True
                logger.info("gigio.chat synthesis_correction count=%s", showcase_count)
                turns.append(ChatTurn(role="user", text=SHOWCASE_CORRECTION))
                continue
            logger.info(
                "gigio.chat ok provider=%s latency_ms=%s tokens_in=%s tokens_out=%s tools=%s names=%s origin=%s",
                response.provider,
                response.latency_ms,
                response.input_tokens,
                response.output_tokens,
                tool_rounds,
                ",".join(tool_names) or "-",
                function,
            )
            _note_usage(
                session,
                settings,
                function=function,
                ok=True,
                duration_ms=int(response.latency_ms or (time.perf_counter() - started) * 1000),
                account=account,
                article_id=article_id,
                provider=response.provider,
                tokens_in=response.input_tokens,
                tokens_out=response.output_tokens,
            )
            cited = _cited_links(reply, collected_links)
            cta = next((item for item in collected_links if item.get("kind") == "vitrine"), None)
            builder_cta = next((item for item in collected_links if item.get("kind") == "builder"), None)
            if not decision.accompaniments:
                cta = None
            if not decision.builder:
                builder_cta = None
            notice = next((str(item.get("notice") or "") for item in collected_notices if item.get("notice")), "")
            if cta is None and decision.accompaniments:
                fallback = _contextual_lookup(session, settings, user_text, reply, history)
                cta = fallback.get("cta")
                notice = notice or str(fallback.get("notice") or "")
            guide_turn = _is_guide_score_turn(user_text)
            read_sources = needs_stored_evidence(user_text, history[:-1], accompaniments=decision.accompaniments)
            grounded = sources_for_conversation(
                session,
                enabled=bool(settings.gigio_pairing_refs_enabled) and read_sources,
                user_text=user_text,
                reply="",
                history=history[:-1] if read_sources else None,
            )
            allowed = {str(item.get("href") or "") for item in grounded}
            sources = [item for item in collected_sources if str(item.get("href") or "") in allowed] or grounded
            return _finish_deepen(
                session,
                settings,
                credit_guard,
                {
                    "reply": drop_phantom_click(reply, has_cta=cta is not None),
                    "links": cited,
                    "cta": cta,
                    "builder_cta": builder_cta,
                    "sources": _public_sources(sources),
                    "suggestions": list(CULINARY_PROMPTS[:3]),
                    "notice": notice,
                    "unavailable": False,
                },
                consume=True,
            )
    except Exception as exc:
        err_name = type(exc).__name__
        err_code = str(getattr(exc, "code", "") or err_name)[:40]
        logger.info(
            "gigio.chat fail latency_ms=%s err=%s code=%s tools=%s origin=%s",
            int((time.perf_counter() - started) * 1000),
            err_name,
            err_code,
            tool_rounds,
            function,
        )
        _note_usage(
            session,
            settings,
            function=function,
            ok=False,
            duration_ms=int((time.perf_counter() - started) * 1000),
            fail_kind=err_code,
            account=account,
            article_id=article_id,
        )
        return _finish_deepen(
            session,
            settings,
            credit_guard,
            {
                "reply": INCOMPLETE_REPLY,
                "links": [],
                "cta": None,
                "builder_cta": None,
                "sources": [],
                "suggestions": list(STARTER_PROMPTS),
                "unavailable": True,
            },
            consume=False,
        )


def _finish_deepen(
    session: Session,
    settings: Settings,
    credit_guard: dict[str, Any] | None,
    payload: dict[str, Any],
    *,
    consume: bool,
) -> dict[str, Any]:
    if not credit_guard:
        return payload
    account = credit_guard["account"]
    operation_id = credit_guard["operation_id"]
    if consume and payload.get("reply") and not payload.get("unavailable"):
        remember_operation(session, settings, account, operation_id, "confirmed", payload)
        try:
            confirmed = confirm_credit(settings, account, operation_id)
            if confirmed.get("ok"):
                payload["access"] = {
                    "authorized": True,
                    "credits": confirmed.get("credits"),
                    "valid_until": confirmed.get("valid_until"),
                    "charged": True,
                    "credit_cost": 1,
                }
        except HubUnavailableError:
            payload["access"] = {
                "authorized": True,
                "charged": True,
                "reason": "confirm_deferred",
                "credit_cost": 1,
            }
        return payload
    try:
        release_credit(settings, account, operation_id)
    except HubUnavailableError:
        logger.info("gigio.credit release deferred operation=%s", operation_id)
    remember_operation(session, settings, account, operation_id, "released")
    payload["access"] = {"authorized": True, "charged": False, "reason": "released"}
    return payload


def _claims_total_showcase_absence(reply: str) -> bool:
    folded = reply.casefold()
    markers = (
        "sem produtos",
        "vitrine vazia",
        "vitrine está vazia",
        "vitrine esta vazia",
        "vitrine está sem",
        "vitrine esta sem",
        "não há pães na vitrine",
        "nao ha paes na vitrine",
        "nenhum pão na vitrine",
        "nenhum pao na vitrine",
    )
    return any(marker in folded for marker in markers)


def _execute_allowed_tool(
    name: str,
    args: dict,
    *,
    session: Session,
    settings: Settings,
    order_reference: str | None,
    order_token: str | None,
    is_admin: bool,
    decision,
    user_text: str = "",
    history: list[dict] | None = None,
) -> dict:
    if (
        name == "lookup_products"
        and not str(args.get("q") or "").strip()
        and asks_published_showcase(user_text)
    ):
        args = {**args, "q": "vitrine"}
        logger.info("gigio.tool name=lookup_products mode=showcase reason=deliberate")
    if name == "lookup_accompaniments" and not decision.accompaniments:
        logger.info("gigio.tool skipped name=lookup_accompaniments kind=%s", decision.kind)
        return skip_accompaniments_result()
    if name == "propose_builder" and not decision.builder:
        logger.info("gigio.tool skipped name=propose_builder kind=%s", decision.kind)
        return skip_builder_result()
    guide_turn = _is_guide_score_turn(user_text)
    if name == "lookup_pairing_references" and not decision.accompaniments and not guide_turn:
        logger.info("gigio.tool skipped name=lookup_pairing_references kind=%s", decision.kind)
        return skip_pairing_result()
    if name == "lookup_pairing_references" and guide_turn:
        prior = " ".join(str(item.get("content") or "") for item in (history or []) if item.get("role") == "user")
        asked = str(args.get("q") or "")
        args = {**args, "q": " ".join(part for part in (prior, user_text, asked) if part)[:1500]}
    result = execute_tool(
        name,
        args,
        session=session,
        settings=settings,
        order_reference=order_reference,
        order_token=order_token,
        is_admin=is_admin,
    )
    logger.info(
        "gigio.tool name=%s error=%s mode=%s count=%s items=%s completed=%s",
        name,
        result.get("error") or "-",
        result.get("mode") or "-",
        result.get("count"),
        len(result.get("items") or []),
        result.get("completed"),
    )
    return result


def _contextual_lookup(
    session: Session,
    settings: Settings,
    user_text: str,
    reply: str,
    history: list[dict] | None = None,
) -> dict:
    if not settings.gigio_accompaniments_enabled:
        return {"cta": None, "notice": ""}
    query = infer_suggested_query(user_text=user_text, reply=reply, history=history)
    if not query.useful:
        return {"cta": None, "notice": ""}
    prior = " ".join(str(item.get("content") or "") for item in (history or []) if item.get("role") == "user")
    result = gigio_lookup(
        session,
        settings,
        categories=query.categories,
        wine_style=query.wine_style,
        beer_style=query.beer_style,
        potato_form=query.potato_form,
        dishes=query.dishes,
        query_text=user_text,
        exclusions=infer_exclusions_from_text(f"{prior} {user_text}".strip()),
    )
    cta = result.get("cta") or {}
    button = None
    if cta.get("href") and cta.get("label"):
        button = {"href": str(cta["href"]), "label": str(cta["label"]), "kind": "vitrine"}
    return {"cta": button, "notice": str(result.get("notice") or "")}


def _note_usage(
    session: Session,
    settings: Settings,
    *,
    function: str,
    ok: bool,
    duration_ms: int,
    account: CustomerAccount | None = None,
    article_id: str = "",
    provider: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    fail_kind: str | None = None,
) -> None:
    try:
        record_usage(
            session,
            settings,
            origin=function,
            function="chat",
            ok=ok,
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            fail_kind=fail_kind,
            account=account,
            article_id=article_id or None,
            provider=provider,
        )
    except Exception:
        logger.info("gigio.usage skip")


def _page_context(page: dict, session: Session | None = None, function: str = "atendimento") -> str:
    path = str(page.get("path") or "")[:120]
    product = str(page.get("product_slug") or "")[:80]
    recipe = str(page.get("recipe_slug") or "")[:80]
    parts = ["\n\nContexto da página (use só se for útil; não envie dados pessoais):"]
    if path:
        parts.append(f" caminho={path}.")
    if product:
        parts.append(f" Pão em vista (slug): {product}. Ofereça ideias com este pão se estiver publicado.")
    if recipe:
        parts.append(f" Receita em vista (slug): {recipe}.")
    if path.startswith("/acompanhar"):
        parts.append(" Página de complementos: responda primeiro à mesa; só cite item se a consulta confirmar publicação.")
    if path.startswith("/admin"):
        parts.append(" Superfície administrativa: presença discreta; não liste clientes nem todos os pedidos.")
    builder = page.get("builder") if isinstance(page.get("builder"), dict) else {}
    flour = str(builder.get("flour") or "")[:80]
    prep = str(builder.get("preparation") or "")[:80]
    shape = str(builder.get("shape") or "")[:80]
    extras = builder.get("inclusions") if isinstance(builder.get("inclusions"), list) else []
    extra_names = ", ".join(str(item)[:40] for item in extras[:6] if item)
    if flour or prep or shape or extra_names:
        parts.append(
            f" Pão em montagem no Criador: farinha={flour or '—'}; preparo={prep or '—'}; "
            f"complementos={extra_names or 'nenhum'}; formato={shape or '—'}. "
            "Fale desta composição; não troque ingredientes sem o cliente pedir."
        )
    library = page.get("library") if isinstance(page.get("library"), dict) else {}
    if function == "biblioteca" and session is not None:
        parts.append(
            " Aprofundamento da Biblioteca: explique aplicações, adapte fórmulas e oriente "
            "experimentação doméstica só com o conhecimento publicado. Não prometa gestão "
            "profissional, Panne, acompanhamento humano, consultoria ilimitada nem uso sem medida."
        )
        article_id = str(library.get("article_id") or "")
        if article_id:
            parts.append(article_context(session, article_id))
        if library.get("calculator_mode"):
            parts.append(
                f" Calculadora no modo {str(library.get('calculator_mode'))[:32]}. "
                "Não peça a fórmula pessoal completa; use o resultado já calculado na página."
            )
    return "".join(parts)


def _sources_from_tool(result: dict) -> list[dict]:
    items = []
    for item in result.get("sources") or []:
        if isinstance(item, dict) and item.get("href"):
            items.append(item)
    return items


def _public_sources(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    public: list[dict] = []
    for item in items:
        href = str(item.get("href") or "")
        title = str(item.get("title") or "")
        key = f"{href}|{title}"
        if key in seen or not is_allowed_source_url(href):
            continue
        seen.add(key)
        public.append(
            {
                "href": href,
                "label": str(item.get("label") or item.get("title") or "Fonte"),
                "kind": "source",
                "title": str(item.get("title") or ""),
                "synthesis": str(item.get("synthesis") or "")[:600],
                "source_kind": str(item.get("source_kind") or ""),
                "kind_note": str(item.get("kind_note") or ""),
                "author": str(item.get("author") or ""),
                "consulted_at": str(item.get("consulted_at") or ""),
                "scope": str(item.get("scope") or ""),
                "evidence_type": str(item.get("evidence_type") or ""),
                "retrieval_role": str(item.get("retrieval_role") or ""),
                "score_line": str(item.get("score_line") or ""),
                "support_locator": str(item.get("support_locator") or ""),
                "loja_choice": bool(item.get("loja_choice")),
            }
        )
        if len(public) >= 3:
            break
    return public


def _links_from_tool(result: dict) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    cta = result.get("cta") or {}
    if cta.get("href") and cta.get("label"):
        kind = str(cta.get("kind") or "vitrine")
        links.append({"href": str(cta["href"]), "label": str(cta["label"]), "kind": kind})
    if result.get("href") and (result.get("name") or result.get("title") or result.get("reference")):
        links.append(
            {
                "href": str(result["href"]),
                "label": str(result.get("name") or result.get("title") or result.get("reference")),
            }
        )
    if result.get("story_href") and not cta:
        links.append({"href": str(result["story_href"]), "label": "Para acompanhar seu pão"})
    for item in result.get("items") or []:
        item_href = str(item.get("href") or "")
        if item_href.startswith(("/paes/", "/receitas/", "/pedido/", "/#")):
            links.append({"href": item_href, "label": str(item.get("name") or item.get("title") or item_href)})
        outbound = str(item.get("outbound_href") or "")
        if outbound and (item.get("name") or item.get("outbound_label")):
            links.append(
                {
                    "href": outbound,
                    "label": str(item.get("outbound_label") or item.get("name")),
                }
            )
    return links


def _allowed_chat_href(href: str) -> bool:
    if href.startswith("/") and not href.startswith("//"):
        return True
    return is_allowed_outbound_url(href)


def _cited_links(reply: str, items: list[dict[str, str]]) -> list[dict[str, str]]:
    lowered = reply.casefold()
    cited: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        href = item.get("href") or ""
        label = item.get("label") or ""
        if not _allowed_chat_href(href) or href in seen:
            continue
        kind = item.get("kind")
        if kind == "source":
            continue
        if kind in {"vitrine", "builder"} or href in reply or (label and label.casefold() in lowered):
            seen.add(href)
            cited.append({"href": href, "label": label, **({"kind": kind} if kind else {})})
    return cited[:4]
