"""Textos demonstrativos. Usam só o resultado do motor. Não chamam provedor."""

RULE_VERSION = "regras-demonstrativas-1"
PROMPT_VERSION = "isa-planejamento-004"


def brl(cents):
    sign = "-" if int(cents) < 0 else ""
    value = abs(int(cents))
    whole, frac = divmod(value, 100)
    return sign + "R$ " + f"{whole:,}".replace(",", ".") + "," + f"{frac:02d}"


def show_date(iso):
    year, month, day = iso.split("-")
    return day + "/" + month + "/" + year


def explain_current(result):
    if not result.get("complete"):
        return {
            "origin": "regras-demonstrativas",
            "text": result["missing"][0],
            "premises": result.get("missing") or [],
        }
    minimum = result["minimum"]
    parts = [
        "Em " + show_date(minimum["date"]) + " o disponível chega a " + brl(minimum["cents"]) + ".",
    ]
    cause = next((item for item in result["days"] if item["date"] == minimum["date"]), None)
    if cause and cause["events"]:
        names = ", ".join(item["label"] + " de " + brl(item["cents"]) for item in cause["events"] if item["kind"] == "saida")
        if names:
            parts.append("Nesse dia entra o compromisso " + names + ".")
    if result.get("next_inflow"):
        income = result["next_inflow"]
        parts.append("A próxima entrada confirmada é " + brl(income["cents"]) + " em " + show_date(income["on"]) + ".")
    parts.append("Terminar o mês em " + brl(result["october_end_cents"]) + " não evita a falta do meio do caminho.")
    if result["floor_gap_cents"]:
        parts.append("Para preservar a reserva de " + brl(result["protected_cents"]) + ", faltam " + brl(result["floor_gap_cents"]) + " no ponto mais baixo.")
    if result["margin"]["capacity_cents"] == 0:
        parts.append("A margem para um gasto adicional nesta data é zero. O déficit para manter a reserva é " + brl(result["margin"]["deficit_cents"]) + ".")
    else:
        parts.append("Ainda cabem " + brl(result["margin"]["capacity_cents"]) + " sem invadir a reserva, até o fim do horizonte.")
    if result.get("dependencies"):
        parts.append("Em " + show_date(result["dependencies"][0]["date"]) + " há entrada e saída no mesmo dia. Sem horário, não dá para afirmar qual ocorre primeiro.")
    parts.append("Projeção calculada com os dados informados. A análise da ISA aparece na área de ajuda.")
    return {"origin": "regras-demonstrativas", "text": " ".join(parts), "premises": [result["base_date"], result["engine_version"]]}


def explain_alternative(current, alternative, change_label):
    text = (
        "No plano atual, o ponto mais baixo é " + brl(current["minimum"]["cents"]) + " em " + show_date(current["minimum"]["date"]) + ". "
        "Se " + change_label + ", o ponto mais baixo passa a " + brl(alternative["minimum"]["cents"]) + " e o mês termina em " + brl(alternative["october_end_cents"]) + ". "
        "Custo do adiamento ainda não informado. O credor não confirmou esta data. Não é renegociação concluída nem recomendação definitiva. "
        "Simulação calculada com os dados informados."
    )
    return {"origin": "regras-demonstrativas", "text": text}


def explain_spend(result, label, cents, on):
    if not result.get("complete"):
        return {"origin": "regras-demonstrativas", "text": "A projeção está parcial. " + result["missing"][0]}
    limiting = next((item for item in result["days"] if item["date"] == result["margin"].get("limiting_date")), None)
    cause = ""
    if limiting and limiting["events"]:
        cause = " O dia limite tem " + ", ".join(item["label"] for item in limiting["events"]) + "."
    if result["margin"]["capacity_cents"] == 0:
        body = "Um gasto de " + brl(cents) + " em " + show_date(on) + " (" + label + ") deixa a margem em zero. O déficit para a reserva fica em " + brl(result["margin"]["deficit_cents"]) + "." + cause
    else:
        body = "Depois desse gasto ainda sobram " + brl(result["margin"]["capacity_cents"]) + " acima da reserva até o fim do horizonte." + cause
    if not result.get("budgets", {}).get("categories"):
        body += " Não há verba mensal desta categoria. O efeito é o da trajetória, não um teto inventado."
    body += " Simulação calculada com os dados informados."
    return {"origin": "regras-demonstrativas", "text": body}
