from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import MONTH_NAMES, bakery_now, bakery_zone
from app.domain.capacity import utc_now
from app.domain.errors import ConfirmationError
from app.models.house_fidelity import HouseFidelityCampaign, HouseFidelityCredit, HouseFidelityEvent

CAMPAIGN_SLUG = "carimbos-da-casa"
RULES_VERSION = "46"
FOCACCIA_SLUG = "focaccia-alta-italian-focaccia"
RULES_JSON = (
    '{"valid_order":"closed_and_paid","closed_means":"admin_accept_confirmed_at",'
    '"paid_means":"server_reconciled_bread_net","credit_size":4,'
    '"reward":"one_500g_showcase_loaf_excluding_focaccia","freight_separate":true,'
    '"no_price_cap":true,"timezone":"America/Sao_Paulo",'
    '"cycle":"civil_month","credits_do_not_expire":true,'
    '"no_historical_import":true,"no_retroactive_link":true,'
    '"delivery_not_required_for_stamp":true,'
    '"partial_refund":"admin_review_pending_no_auto_decision",'
    '"custom_loaf_does_not_qualify":true,'
    '"eligibility_field":"products.fidelity_eligible"}'
)
GENERIC_VERIFY_MESSAGE = (
    "Cadastro confirmado. Quatro pedidos válidos no mesmo mês geram um crédito. "
    "Comprar continua possível sem participar."
)
BENEFIT_COPY = (
    "A cada 4 pedidos válidos no mês, ganhe um pão de 500 g da vitrine. "
    "Focaccias não participam. "
    "Frete, quando houver, é cobrado separadamente. "
    "Sujeito à disponibilidade das fornadas."
)
HOW_IT_WORKS = (
    "A cada 4 pedidos válidos no mês, ganhe um pão de 500 g da vitrine. Focaccias não participam. "
    "Compra válida é a feita durante a campanha, com participação e identidade verificadas no "
    "fechamento, que esteja fechada e paga, e que inclua ao menos um pão da vitrine elegível. "
    "Fechada é o aceite da padaria; paga é o pagamento confirmado no servidor. "
    "Enviar o pedido, abrir o checkout ou gerar um Pix ainda não conta. "
    "Cada compra conta uma vez, mesmo com vários pães. Focaccia e pão personalizado sozinhos não geram carimbo. "
    "O crédito vale um pão de 500 g da vitrine, sem focaccia. "
    "Frete, quando houver entrega, é cobrado à parte e informado antes do envio. "
    "Na virada do mês a contagem recomeça; créditos conquistados permanecem. "
    "O mês é o civil, no horário de Brasília, no instante em que aceite e pagamento se completam. "
    "Compras anteriores à campanha, ou feitas sem identificação, não entram depois. "
    "Pedido só de presente, ou só com frete pago, não gera carimbo. "
    "Capacidade e aceite da padaria continuam valendo no resgate."
)


def next_cycle_start(settings: Settings, now: datetime | None = None) -> datetime:
    current = (now or bakery_now(settings)).astimezone(bakery_zone(settings))
    year = current.year + (1 if current.month == 12 else 0)
    month = 1 if current.month == 12 else current.month + 1
    return datetime(year, month, 1, 0, 0, tzinfo=bakery_zone(settings))


def restart_label(settings: Settings, when: datetime | None = None) -> str:
    start = when or next_cycle_start(settings)
    local = start.astimezone(bakery_zone(settings))
    return f"1º de {MONTH_NAMES[local.month]}, às 00h (horário de Brasília)"


def current_campaign(session: Session) -> HouseFidelityCampaign | None:
    return session.scalar(
        select(HouseFidelityCampaign)
        .where(HouseFidelityCampaign.slug == CAMPAIGN_SLUG)
        .order_by(HouseFidelityCampaign.version.desc())
    )


def campaign_is_publicly_active(settings: Settings, campaign: HouseFidelityCampaign | None) -> bool:
    if not settings.house_fidelity_active:
        return False
    if campaign is None or campaign.status != "active" or campaign.starts_at is None:
        return False
    return bakery_now(settings) >= campaign.starts_at


def is_500g_unit(variant) -> bool:
    if not getattr(variant, "is_active", True):
        return False
    if variant.net_weight_grams != 500:
        return False
    if variant.physical_units not in (None, 1):
        return False
    if variant.units_per_pack not in (None, 1):
        return False
    return True


def product_is_fidelity_eligible(product) -> bool:
    return bool(getattr(product, "fidelity_eligible", True))


def lines_qualify_for_stamp(session: Session, quoted: list[dict]) -> bool:
    from uuid import UUID

    from app.models.products import Product

    showcase_ids = {item.id for item in vitrine_products(session)}
    for line in quoted:
        if line.get("origin") == "custom" or line.get("dough_type_id"):
            continue
        product_id = line.get("product_id")
        if not product_id:
            continue
        product = session.get(Product, UUID(str(product_id)))
        if product is None or not product_is_fidelity_eligible(product):
            continue
        if product.id not in showcase_ids:
            continue
        if int(line.get("line_cents") or 0) <= 0:
            continue
        return True
    return False


def activate_campaign(session: Session, settings: Settings) -> HouseFidelityCampaign:
    del settings
    campaign = current_campaign(session)
    if campaign is None:
        raise ConfirmationError("campanha da fidelidade não encontrada")
    if campaign.status == "active" and campaign.starts_at is not None:
        return campaign
    catalog = reward_catalog(session)
    if not catalog:
        raise ConfirmationError("não dá para ativar: a vitrine não tem tipo publicado")
    gaps = reward_gaps(session)
    if gaps:
        names = ", ".join(item["name"] for item in gaps)
        raise ConfirmationError(
            f"não dá para ativar: falta apresentação de 500 g / uma unidade em {names}"
        )
    campaign.status = "active"
    campaign.starts_at = utc_now()
    campaign.rules_version = RULES_VERSION
    campaign.rules_json = RULES_JSON
    session.flush()
    return campaign


def parse_demo_state(raw: str | None, preview: bool) -> str:
    if not preview:
        return "visitor"
    value = (raw or "").strip().lower()
    if value in {"partial", "parcial"}:
        return "partial"
    if value in {"credit", "credito", "crédito"}:
        return "credit"
    return "visitor"


def _demo_participant(state: str, restart: str) -> dict | None:
    if state == "partial":
        return {
            "kind": "partial",
            "valid_orders": 2,
            "cycle_size": 4,
            "credits": 0,
            "progress_label": "2 de 4 pedidos para seu próximo crédito",
            "remaining_label": "Faltam 2 para conquistar seu próximo crédito.",
            "restart_label": restart,
            "credits_label": "0 créditos disponíveis",
        }
    if state == "credit":
        return {
            "kind": "credit",
            "valid_orders": 4,
            "cycle_size": 4,
            "credits": 1,
            "progress_label": "Você ganhou um pão de presente · 0 de 4 para o próximo crédito",
            "remaining_label": "A contagem do próximo grupo de quatro já começou.",
            "restart_label": restart,
            "credits_label": "1 crédito disponível",
        }
    return None


def cycle_of(settings: Settings, moment: datetime) -> tuple[int, int]:
    local = moment.astimezone(bakery_zone(settings))
    return local.year, local.month


def real_balance(
    session: Session, settings: Settings, account_id, campaign: HouseFidelityCampaign
) -> dict:
    now = bakery_now(settings)
    year, month = cycle_of(settings, now)
    qualified = list(
        session.scalars(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.campaign_id == campaign.id,
                HouseFidelityEvent.account_id == account_id,
                HouseFidelityEvent.kind == "qualify",
                HouseFidelityEvent.status == "applied",
                HouseFidelityEvent.cycle_year == year,
                HouseFidelityEvent.cycle_month == month,
            )
        )
    )
    credits = list(
        session.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.campaign_id == campaign.id,
                HouseFidelityCredit.account_id == account_id,
                HouseFidelityCredit.status.in_(("available", "reserved")),
            )
        )
    )
    available = [row for row in credits if row.status == "available"]
    count = len(qualified)
    remainder = count % 4
    earned_this_cycle = count // 4
    restart = restart_label(settings)
    if count > 0 and remainder == 0:
        progress = (
            "Você ganhou um pão de presente · 0 de 4 para o próximo crédito"
            if earned_this_cycle
            else f"{remainder} de 4 pedidos para seu próximo crédito"
        )
        remaining = "A contagem do próximo grupo de quatro já começou."
    else:
        progress = f"{remainder} de 4 pedidos para seu próximo crédito"
        missing = 4 - remainder if remainder else 4
        remaining = f"Faltam {missing} para conquistar seu próximo crédito."
    return {
        "kind": "credit" if available else "partial",
        "valid_orders": remainder if remainder or not earned_this_cycle else 0,
        "valid_orders_month": count,
        "cycle_size": 4,
        "credits": len(available),
        "progress_label": progress,
        "remaining_label": remaining,
        "restart_label": restart,
        "credits_label": f"{len(available)} crédito"
        + ("s" if len(available) != 1 else "")
        + " disponível"
        + ("is" if len(available) != 1 else ""),
        "benefit": BENEFIT_COPY,
    }


def status_payload(
    session: Session,
    settings: Settings,
    *,
    demo: str | None = None,
    account=None,
) -> dict:
    preview = bool(settings.preview_protection)
    campaign = current_campaign(session)
    active = campaign_is_publicly_active(settings, campaign)
    restart = next_cycle_start(settings)
    label = restart_label(settings, restart)
    participant = None
    if account is not None and active and campaign is not None:
        participant = real_balance(session, settings, account.id, campaign)
    elif account is None and preview:
        participant = _demo_participant(parse_demo_state(demo, preview), label)
    return {
        "campaign_active": active,
        "preview": preview and account is None,
        "restart_at": restart.isoformat(),
        "restart_label": label,
        "stamps": "progress" if participant else "neutral",
        "participant": participant,
        "how_it_works": HOW_IT_WORKS,
        "benefit": BENEFIT_COPY,
        "verified": bool(account),
        "cpf_masked": None,
        "name": account.name if account is not None else None,
        "can_redeem": bool(active and participant and participant.get("credits", 0) > 0),
        "gaps": reward_gaps(session) if active else [],
    }


def vitrine_products(session: Session) -> list:
    from app.domain.showcase import ensure_slots
    from app.models.enums import EditorialStatus
    from app.models.products import Product

    products = []
    seen: set = set()
    for slot in ensure_slots(session):
        if slot.product_id is None:
            continue
        product = session.get(Product, slot.product_id)
        if product is None or product.id in seen:
            continue
        if product.editorial_status != EditorialStatus.PUBLISHED.value or not product.is_available:
            continue
        seen.add(product.id)
        products.append(product)
    return products


def reward_catalog(session: Session) -> list[dict]:
    from app.models.products import ProductVariant

    items = []
    for product in vitrine_products(session):
        variants = list(
            session.scalars(
                select(ProductVariant).where(
                    ProductVariant.product_id == product.id,
                    ProductVariant.is_active.is_(True),
                )
            )
        )
        eligible = [
            row for row in variants if is_500g_unit(row) and product_is_fidelity_eligible(product)
        ]
        items.append(
            {
                "slug": product.slug,
                "name": product.name,
                "eligible": bool(eligible),
                "presentations": [
                    {
                        "display_name": row.display_name,
                        "net_weight_grams": row.net_weight_grams,
                        "physical_units": row.physical_units,
                        "units_per_pack": row.units_per_pack,
                        "eligible": is_500g_unit(row) and product_is_fidelity_eligible(product),
                    }
                    for row in variants
                ],
            }
        )
    return items


def reward_gaps(session: Session) -> list[dict]:
    from app.models.products import ProductVariant

    gaps = []
    for product in vitrine_products(session):
        if not product_is_fidelity_eligible(product):
            continue
        variants = list(
            session.scalars(
                select(ProductVariant).where(
                    ProductVariant.product_id == product.id,
                    ProductVariant.is_active.is_(True),
                )
            )
        )
        if not any(is_500g_unit(row) for row in variants):
            gaps.append({"slug": product.slug, "name": product.name})
    return gaps
