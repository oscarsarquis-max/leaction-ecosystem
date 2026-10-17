"""Leitura do Início. Os números vêm do motor e dos registros; nada aqui chama um modelo."""

import hashlib
import json
from datetime import date, timedelta


def parse_date(value):
    year, month, day = str(value).split("-")
    return date(int(year), int(month), int(day))


def iso(value):
    return value.isoformat()


def half_up(numerator, denominator):
    sign = 1 if numerator >= 0 else -1
    number = abs(int(numerator))
    quotient, remainder = divmod(number, int(denominator))
    if remainder * 2 >= int(denominator):
        quotient += 1
    return sign * quotient


def show(value):
    text = str(value or "")
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[8:10] + "/" + text[5:7] + "/" + text[0:4]
    return text


def when_label(reference, target):
    if not target:
        return ""
    delta = (parse_date(target) - parse_date(reference)).days
    if delta == 0:
        return "Hoje"
    if delta == 1:
        return "Amanhã"
    if delta > 1:
        return "Em " + str(delta) + " dias"
    if delta == -1:
        return "Venceu há 1 dia"
    return "Venceu há " + str(-delta) + " dias"


def _conditions(item):
    try:
        parsed = json.loads(item.get("conditions_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def period_for(reference, projection, inflows):
    ref = parse_date(reference)
    horizon = projection.get("horizon_end") or iso(ref + timedelta(days=30))
    confirmed = [item for item in inflows if item.get("state") == "confirmada" and item.get("amount_cents") is not None and item.get("due_on") and item["due_on"] >= reference]
    if confirmed:
        target = min(item["due_on"] for item in confirmed)
        if target <= horizon:
            return {"from": reference, "until": target, "basis": "ate-entrada", "limited": False}
        return {"from": reference, "until": horizon, "basis": "ate-horizonte", "limited": True, "inflowOn": target}
    end = iso(ref + timedelta(days=30))
    if end > horizon:
        end = horizon
    return {"from": reference, "until": end, "basis": "30-dias", "limited": False}


def payables(reference, commitments, until):
    known = []
    pending = []
    overdue = []
    for item in commitments:
        remaining = item.get("remaining_cents")
        due = item.get("due_on")
        if remaining in (0, "0"):
            continue
        if remaining is None or not due:
            pending.append(item["id"])
            continue
        if due < reference:
            overdue.append(item)
        if due <= until or due < reference:
            known.append(item)
    return {
        "cents": sum(int(item["remaining_cents"]) for item in known),
        "count": len(known),
        "overdueCount": len(overdue),
        "overdueCents": sum(int(item["remaining_cents"]) for item in overdue),
        "pendingCount": len(pending),
        "coverage": "Compromissos do planejamento",
    }


def charge_estimate(item, pay_on):
    """Encargos em centavos. Sem taxa presumida. Zero só quando a condição registrada sustenta."""
    conditions = _conditions(item)
    useful = {key: value for key, value in conditions.items() if key not in ("custo", "aceite") or value not in (None, "", "desconhecido")}
    if not useful or not item.get("due_on") or not pay_on:
        return {"status": "unknown", "text": "Ainda não sei os encargos desse atraso. Informe as condições para calcular."}
    principal = conditions.get("principalCents")
    if principal is None:
        principal = item.get("remaining_cents")
    if principal is None:
        return {"status": "unknown", "text": "Ainda não sei os encargos desse atraso. Informe as condições para calcular."}
    principal = int(principal)
    late = parse_date(pay_on) > parse_date(item["due_on"])
    components = []
    missing = []
    if "fineCents" in conditions:
        fine = 0 if not late else int(conditions["fineCents"])
        components.append({"name": "multa", "cents": fine, "basis": "valor informado"})
    elif "fineRateBps" in conditions:
        fine = 0 if not late else half_up(principal * int(conditions["fineRateBps"]), 10000)
        components.append({"name": "multa", "cents": fine, "basis": "principal ainda devido", "rateBps": int(conditions["fineRateBps"])})
    if "interestCents" in conditions:
        interest = 0 if not late else int(conditions["interestCents"])
        components.append({"name": "juros", "cents": interest, "basis": "valor informado"})
    elif isinstance(conditions.get("interest"), dict):
        rule = conditions["interest"]
        if rule.get("regime") == "simples" and rule.get("period") in ("day", "month") and rule.get("rateBps") is not None:
            count = 0 if not late else _periods(item["due_on"], pay_on, rule["period"])
            interest = half_up(principal * int(rule["rateBps"]) * count, 10000)
            components.append({"name": "juros", "cents": interest, "basis": "principal ainda devido", "periods": count, "period": rule["period"], "rateBps": int(rule["rateBps"]), "regime": "simples"})
        else:
            missing.append("juros")
    if not components:
        return {"status": "unknown", "text": "Ainda não sei os encargos desse atraso. Informe as condições para calcular."}
    extra = sum(part["cents"] for part in components)
    return {
        "status": "partial" if missing else "estimated",
        "missing": missing,
        "payOn": pay_on,
        "principalCents": principal,
        "components": components,
        "extraCents": extra,
        "totalCents": None if missing else principal + extra,
        "kind": conditions.get("kind") if conditions.get("kind") == "fatura" else "compromisso",
        "text": "Estimado para pagamento em " + show(pay_on) + ". Não é uma cobrança confirmada pelo credor.",
    }


def _periods(due_on, pay_on, period):
    due = parse_date(due_on)
    pay = parse_date(pay_on)
    if pay <= due:
        return 0
    if period == "day":
        return (pay - due).days
    months = (pay.year - due.year) * 12 + (pay.month - due.month)
    if pay.day > due.day:
        months += 1
    return max(months, 1)


def situation(reference, projection, guide):
    if not projection.get("complete"):
        return {"kind": "incomplete", "gaps": list((guide or {}).get("gaps") or [])}
    days = {item["date"]: item for item in projection.get("days") or []}
    short = projection.get("first_insufficiency")
    if short and short in days:
        minimum = projection.get("minimum") or {}
        return {
            "kind": "shortfall",
            "on": short,
            "cents": abs(int(days[short]["cents"])),
            "when": when_label(reference, short),
            "minimum": None if minimum.get("date") in (None, short) else {"on": minimum.get("date"), "cents": minimum.get("cents")},
        }
    floor = projection.get("first_floor_breach")
    if floor and floor in days:
        used = int(projection.get("protected_cents") or 0) - int(days[floor]["cents"])
        return {"kind": "reserve", "on": floor, "cents": max(used, 0), "when": when_label(reference, floor)}
    margin = projection.get("margin") or {}
    return {"kind": "covers", "until": projection.get("horizon_end"), "marginCents": margin.get("capacity_cents"), "marginUntil": projection.get("horizon_end")}


def insights(reference, projection, guide, commitments, inflows, period, payable):
    items = []
    used = set()
    today_due = [item for item in commitments if item.get("due_on") == reference and item.get("remaining_cents") not in (None, 0)]
    overdue = [item for item in commitments if item.get("due_on") and item["due_on"] < reference and item.get("remaining_cents") not in (None, 0)]
    chosen = (today_due or overdue or [None])[0]
    if chosen:
        kind = "fatura" if _conditions(chosen).get("kind") == "fatura" else "compromisso"
        items.append({
            "id": "due:" + chosen["id"],
            "tone": "attention",
            "title": ("Sua fatura " + chosen["label"] + (" vence hoje." if chosen.get("due_on") == reference else " está vencida.")) if kind == "fatura" else (chosen["label"] + (" vence hoje." if chosen.get("due_on") == reference else " está vencido.")),
            "cents": int(chosen["remaining_cents"]),
            "on": chosen.get("due_on"),
            "action": "Ver compromisso",
            "href": "#planejar/contas/voltar",
        })
        used.add(chosen["id"])
        pay_on = reference if chosen.get("due_on") and chosen["due_on"] <= reference else chosen.get("due_on")
        estimate = charge_estimate(chosen, pay_on)
        if estimate["status"] == "estimated" and estimate["extraCents"] is not None:
            items.append({
                "id": "charge:" + chosen["id"],
                "tone": "attention",
                "label": chosen["label"],
                "title": "Se pagar " + chosen["label"] + " em " + show(pay_on) + ", os encargos estimados são calculados à parte do valor que falta.",
                "cents": estimate["extraCents"],
                "totalCents": estimate["totalCents"],
                "on": pay_on,
                "action": "Conferir cálculo",
                "href": "#planejar/contas/voltar",
                "estimate": estimate,
            })
        elif estimate["status"] == "unknown" and (chosen.get("due_on") or "") < reference:
            items.append({
                "id": "charge:" + chosen["id"],
                "tone": "attention",
                "title": estimate["text"],
                "cents": None,
                "action": "Completar informações",
                "href": "#planejar/contas/voltar",
                "estimate": estimate,
            })
    for item in overdue:
        if len(items) >= 3 or item["id"] in used:
            continue
        other = charge_estimate(item, reference)
        if other["status"] != "unknown":
            continue
        items.append({
            "id": "charge:" + item["id"],
            "tone": "attention",
            "title": other["text"],
            "cents": None,
            "action": "Completar informações",
            "href": "#planejar/contas/voltar",
            "estimate": other,
        })
        break
    state = situation(reference, projection, guide)
    if state["kind"] == "shortfall" and len(items) < 3:
        items.append({
            "id": "shortfall",
            "tone": "out",
            "title": "Para os compromissos informados, falta dinheiro nesta data.",
            "cents": state["cents"],
            "on": state["on"],
            "action": "Comparar alternativas",
            "href": "#planejar/resumo",
        })
    pending = payable["pendingCount"]
    if pending and len(items) < 3 and not any(item["id"] == "pending" for item in items):
        items.append({
            "id": "pending",
            "tone": "attention",
            "title": "Há informações sem valor ou data. Complete para conferir se o dinheiro chega.",
            "count": pending,
            "action": "Completar informações",
            "href": "#planejar/" + {"availability": "disponivel", "inflow": "entrada", "commitments": "contas"}.get(((guide or {}).get("gaps") or ["commitments"])[0], "contas") + "/voltar",
        })
    return items[:3]


def build_overview(reference, projection, guide, commitments, inflows):
    guide = guide or {}
    period = period_for(reference, projection or {}, inflows or [])
    payable = payables(reference, commitments or [], period["until"])
    availability = guide.get("availability")
    informed = None
    if availability:
        informed = {
            "cents": availability["amountCents"],
            "on": availability["asOf"],
            "protectedCents": availability.get("protectedCents") or 0,
            "label": "Disponível informado",
        }
    projected = None
    if projection and projection.get("complete"):
        day = next((item for item in projection.get("days") or [] if item["date"] == reference), None)
        if day and (not informed or informed["on"] != reference or int(day["cents"]) != int(informed["cents"])):
            projected = {"cents": int(day["cents"]), "on": reference, "label": "Projeção para esta data"}
    confirmed = [item for item in inflows or [] if item.get("state") == "confirmada" and item.get("amount_cents") is not None and item.get("due_on")]
    uncertain = [item for item in inflows or [] if item.get("state") == "incerta"]
    nxt = min(confirmed, key=lambda item: item["due_on"]) if confirmed else None
    uncertain_next = min([item for item in uncertain if item.get("due_on")], key=lambda item: item["due_on"], default=None)
    margin = (projection or {}).get("margin") or {}
    return {
        "reference": reference,
        "period": period,
        "informed": informed,
        "projected": projected,
        "payables": payable,
        "nextInflow": None if not nxt else {"label": nxt["label"], "cents": nxt["amount_cents"], "on": nxt["due_on"], "state": "confirmada", "when": when_label(reference, nxt["due_on"])},
        "uncertainInflow": None if not uncertain_next else {"label": uncertain_next["label"], "cents": uncertain_next.get("amount_cents"), "on": uncertain_next.get("due_on"), "state": "incerta", "when": when_label(reference, uncertain_next.get("due_on"))},
        "situation": situation(reference, projection or {}, guide),
        "margin": {"cents": margin.get("capacity_cents"), "from": margin.get("from"), "until": (projection or {}).get("horizon_end"), "complete": bool(margin.get("complete"))},
        "series": (projection or {}).get("days") if (projection or {}).get("complete") else None,
        "protectedCents": (projection or {}).get("protected_cents") if (projection or {}).get("complete") else (informed or {}).get("protectedCents"),
        "insights": insights(reference, projection or {}, guide, commitments or [], inflows or [], period, payable),
        "coverage": "Compromissos do planejamento",
        "fingerprint": financial_fingerprint(reference, guide, commitments or [], inflows or []),
    }


def financial_fingerprint(reference, guide, commitments, inflows):
    body = {
        "reference": reference,
        "availability": (guide or {}).get("availability"),
        "commitments": sorted((item.get("id"), item.get("remaining_cents"), item.get("due_on"), item.get("conditions_json")) for item in commitments),
        "inflows": sorted((item.get("id"), item.get("amount_cents"), item.get("due_on"), item.get("state")) for item in inflows),
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
