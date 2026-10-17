"""Motor de projeção da ISA. Determinístico, em centavos e datas civis.

Não chama agente, não inventa taxa e não transforma previsão em confirmação.
"""

from datetime import date, timedelta

ENGINE_VERSION = "isa-projecao-1"


def parse_date(value):
    year, month, day = str(value).split("-")
    return date(int(year), int(month), int(day))


def iso(value):
    return value.isoformat()


def month_end(year, month):
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def default_horizon(reference):
    ref = parse_date(reference)
    month = ref.month + 1
    year = ref.year
    if month == 13:
        month = 1
        year += 1
    return month_end(year, month)


def _cents(value):
    if value is None:
        return None
    return int(value)


def project(base, events, reference, horizon=None, extra=None, budgets=None):
    """Projeta a trajetória diária.

    base: as_of, amount_cents, protected_cents, convention, known.
    events: kind entrada|saida, on, cents, included, label, id, already_in_base.
    A reserva protegida é piso, não despesa e não é somada à base.
    """
    ref = parse_date(reference)
    end = parse_date(horizon) if horizon else default_horizon(reference)
    missing = []
    if not base or not base.get("known") or base.get("amount_cents") is None or not base.get("as_of"):
        missing.append("Quanto você tem disponível e em qual data?")
    pending_commitments = [
        item.get("label") or "Compromisso sem data"
        for item in events or []
        if item.get("kind") == "saida" and item.get("included") and (item.get("cents") is None or not item.get("on"))
    ]
    if pending_commitments:
        missing.append("Falta valor ou vencimento de: " + ", ".join(pending_commitments))
    if missing:
        return {
            "complete": False,
            "missing": missing,
            "reference": iso(ref),
            "horizon_end": iso(end),
            "engine_version": ENGINE_VERSION,
            "days": [],
            "margin": {"complete": False, "capacity_cents": None, "deficit_cents": None},
        }

    opening = parse_date(base["as_of"])
    if end < opening:
        end = opening
    for item in list(events or []) + ([extra] if extra else []):
        if item and item.get("on") and item.get("included", True) and item.get("cents") is not None:
            event_day = parse_date(item["on"])
            if event_day > end:
                end = event_day
    protected = int(base.get("protected_cents") or 0)
    balance = int(base["amount_cents"])
    usable = []
    for item in events or []:
        if item.get("kind") == "reserva":
            if item.get("included_in_base") or not item.get("usable") or not item.get("on") or item.get("cents") is None:
                continue
            if item.get("kind_detail") == "limite":
                continue
            usable.append({
                "id": item.get("id"),
                "kind": "entrada",
                "on": item.get("on"),
                "cents": int(item["cents"]),
                "label": item.get("label") or "Reserva utilizável",
                "included": True,
            })
            continue
        if not item.get("included", True) or item.get("cents") is None or not item.get("on"):
            continue
        if item.get("already_in_base"):
            continue
        event_day = parse_date(item["on"])
        if event_day <= opening and base.get("convention") == "encerramento_do_dia":
            continue
        if event_day < opening:
            continue
        usable.append(item)
    if extra and extra.get("cents") is not None and extra.get("on"):
        usable.append({
            "id": extra.get("id") or "gasto-extra",
            "kind": "saida",
            "on": extra["on"],
            "cents": int(extra["cents"]),
            "label": extra.get("label") or "Gasto adicional",
            "included": True,
        })

    days = []
    dependencies = []
    cursor = opening
    while cursor <= end:
        todays = [item for item in usable if parse_date(item["on"]) == cursor]
        if cursor == opening:
            todays = [item for item in todays if item.get("id") == "gasto-extra"]
        incoming = [item for item in todays if item.get("kind") == "entrada"]
        outgoing = [item for item in todays if item.get("kind") == "saida"]
        in_cents = sum(int(item["cents"]) for item in incoming)
        out_cents = sum(int(item["cents"]) for item in outgoing)
        worst = balance - out_cents
        balance = balance + in_cents - out_cents
        order_dependency = bool(incoming and outgoing and ((worst < 0) != (balance < 0) or (worst < protected) != (balance < protected)))
        if order_dependency:
            dependencies.append({
                "date": iso(cursor),
                "sem_horario": True,
                "pior_cents": worst,
                "fim_cents": balance,
            })
        days.append({
            "date": iso(cursor),
            "cents": balance,
            "in_cents": in_cents,
            "out_cents": out_cents,
            "events": [{"id": item.get("id"), "label": item.get("label"), "kind": item.get("kind"), "cents": int(item["cents"])} for item in todays],
            "below_zero": balance < 0,
            "below_floor": balance < protected,
            "order_dependency": order_dependency,
        })
        cursor += timedelta(days=1)

    minimum = min(days, key=lambda item: (item["cents"], item["date"]))
    october = month_end(ref.year, ref.month)
    october_day = next((item for item in days if item["date"] == iso(october)), days[-1])
    first_short = next((item["date"] for item in days if item["below_zero"]), None)
    first_floor = next((item["date"] for item in days if item["below_floor"]), None)
    gap = protected - minimum["cents"] if minimum["cents"] < protected else 0
    later = [item for item in usable if parse_date(item["on"]) > october]
    confirmed_in = [item for item in usable if item.get("kind") == "entrada" and parse_date(item["on"]) >= ref]
    next_in = min(confirmed_in, key=lambda item: item["on"]) if confirmed_in else None
    return {
        "complete": True,
        "missing": [],
        "reference": iso(ref),
        "horizon_end": days[-1]["date"],
        "base_date": iso(opening),
        "base_cents": int(base["amount_cents"]),
        "protected_cents": protected,
        "convention": base.get("convention") or "encerramento_do_dia",
        "days": days,
        "minimum": {"date": minimum["date"], "cents": minimum["cents"]},
        "october_end_cents": october_day["cents"],
        "horizon_end_cents": days[-1]["cents"],
        "first_insufficiency": first_short,
        "first_floor_breach": first_floor,
        "floor_gap_cents": gap,
        "dependencies": dependencies,
        "carried_to_next_month_cents": october_day["cents"],
        "next_month_events": [{"id": item.get("id"), "label": item.get("label"), "on": item.get("on"), "cents": int(item["cents"]), "kind": item.get("kind")} for item in later],
        "next_inflow": None if not next_in else {"id": next_in.get("id"), "label": next_in.get("label"), "on": next_in.get("on"), "cents": int(next_in["cents"])},
        "margin": margin_from(days, protected, iso(ref), True),
        "engine_version": ENGINE_VERSION,
        "budgets": combine_budgets(days, protected, iso(ref), budgets),
    }


def margin_from(days, protected, start, complete):
    window = [item for item in days if item["date"] >= start]
    if not window or not complete:
        return {"complete": False, "from": start, "capacity_cents": None, "deficit_cents": None}
    surplus = min(item["cents"] - protected for item in window)
    if surplus < 0:
        return {"complete": True, "from": start, "capacity_cents": 0, "deficit_cents": -surplus, "limiting_date": min(window, key=lambda item: item["cents"] - protected)["date"]}
    return {"complete": True, "from": start, "capacity_cents": surplus, "deficit_cents": 0, "limiting_date": min(window, key=lambda item: item["cents"] - protected)["date"]}


def combine_budgets(days, protected, start, budgets):
    global_margin = margin_from(days, protected, start, True)
    if not budgets:
        return {"global": global_margin, "categories": [], "note": "Não há verba mensal por categoria. O efeito é o da trajetória inteira."}
    categories = []
    for item in budgets:
        remaining = item.get("remaining_cents")
        if remaining is None:
            categories.append({"category": item.get("category"), "offered_cents": None, "note": "Orçamento sem valor restante."})
            continue
        offered = min(global_margin["capacity_cents"], int(remaining))
        categories.append({
            "category": item.get("category"),
            "remaining_cents": int(remaining),
            "offered_cents": offered,
            "note": "O limite da categoria e a margem global valem para o mesmo dinheiro. Não se somam.",
        })
    return {"global": global_margin, "categories": categories, "note": "A margem global não é uma verba nova para cada categoria."}
