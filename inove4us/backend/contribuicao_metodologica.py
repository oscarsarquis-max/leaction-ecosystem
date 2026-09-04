"""Índice de Contribuição Metodológica — cálculo local no B2C.

Sem ranking, sem média de colegas. Faixa a partir do carimbo
`origem_card` + `editado` no card; selo Voz Ativa só via aviso do loop 53.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Any

ORIGEM_CATALOGO = "catalogo"
ORIGEM_CUSTOM = "custom"

FAIXA_FIEL = "fiel_ao_roteiro"
FAIXA_EQUILIBRIO = "equilibrio_metodologico"
FAIXA_ALTA = "alta_personalizacao"

FAIXA_ROTULOS = {
    FAIXA_FIEL: "Fiel ao Roteiro",
    FAIXA_EQUILIBRIO: "Equilíbrio Metodológico",
    FAIXA_ALTA: "Alta Personalização",
}

FAIXA_TEXTOS = {
    FAIXA_FIEL: (
        "Você caminhou perto do roteiro-base. Esse é um perfil válido — "
        "comum em quem está começando ou consolidando a prática."
    ),
    FAIXA_EQUILIBRIO: (
        "Você misturou o roteiro-base com ajustes seus: um equilíbrio "
        "entre o padrão e a sua voz."
    ),
    FAIXA_ALTA: (
        "Você deu bastante voz própria aos cards, com edições e passos "
        "criados na Mesa."
    ),
}

# Predominância: abaixo de 40% personalizado → Fiel; acima de 60% → Alta.
LIMIAR_FIEL = 0.40
LIMIAR_ALTA = 0.60
DELTA_EVOLUCAO = 0.05

RESULTADOS_INCORPORADOS = frozenset({"aprovada", "adaptada"})
TIPO_RESPOSTA_PROPOSTA = "resposta_proposta_metodologica"

_MESES_PT = (
    "",
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def carimbar_origem_catalogo(card: dict[str, Any]) -> dict[str, Any]:
    """Carimbo de criação a partir do roteiro/catálogo. Não sobrescreve custom."""
    out = dict(card)
    atual = str(out.get("origem_card") or "").strip().lower()
    if atual != ORIGEM_CUSTOM:
        out["origem_card"] = ORIGEM_CATALOGO
    if "editado" not in out:
        out["editado"] = False
    else:
        out["editado"] = bool(out.get("editado"))
    return out


def carimbar_origem_custom(card: dict[str, Any]) -> dict[str, Any]:
    out = dict(card)
    out["origem_card"] = ORIGEM_CUSTOM
    if "editado" not in out:
        out["editado"] = False
    return out


def marcar_editado(card: dict[str, Any]) -> dict[str, Any]:
    out = dict(card)
    out["editado"] = True
    return out


def _eh_subcard_pei(card: dict[str, Any]) -> bool:
    if card.get("parent_card_id"):
        return True
    if card.get("perfil_inclusao"):
        return True
    return False


def classificar_card(card: Any) -> str | None:
    """Retorna canonico | personalizado | None (sem carimbo / PEI)."""
    if not isinstance(card, dict) or _eh_subcard_pei(card):
        return None
    origem = str(card.get("origem_card") or "").strip().lower()
    if origem not in (ORIGEM_CATALOGO, ORIGEM_CUSTOM):
        return None
    if origem == ORIGEM_CUSTOM:
        return "personalizado"
    if card.get("editado") is True:
        return "personalizado"
    if str(card.get("editado") or "").strip().lower() in {"true", "1", "sim"}:
        return "personalizado"
    return "canonico"


def tarefas_do_evento(evento: Any) -> list[dict[str, Any]]:
    if not isinstance(evento, dict):
        return []
    ks = evento.get("kanban_state")
    if isinstance(ks, dict) and isinstance(ks.get("tarefas"), list):
        return [t for t in ks["tarefas"] if isinstance(t, dict)]
    if isinstance(ks, list):
        return [t for t in ks if isinstance(t, dict)]
    plan = evento.get("plan_data")
    if isinstance(plan, dict):
        plano = plan.get("plano") or plan.get("plano_eduscrum") or plan
        if isinstance(plano, dict) and isinstance(plano.get("tarefas_kanban"), list):
            return [t for t in plano["tarefas_kanban"] if isinstance(t, dict)]
    return []


def consolidar_cards(eventos: list[Any]) -> list[dict[str, Any]]:
    """Um card por id no período; se houver conflito, prevalece o personalizado."""
    by_id: dict[str, dict[str, Any]] = {}
    anon = 0
    for ev in eventos or []:
        for t in tarefas_do_evento(ev):
            cid = str(t.get("id") or "").strip()
            if not cid:
                anon += 1
                cid = f"_anon_{anon}"
            prev = by_id.get(cid)
            if prev is None:
                by_id[cid] = t
                continue
            if classificar_card(t) == "personalizado":
                by_id[cid] = t
    return list(by_id.values())


def resumo_aula_contribuicao(cards: list[Any]) -> dict[str, Any]:
    """2–3 campos da aula para o LESSON_RECORD_SYNC (mesma fonte da faixa B2C)."""
    counts = contar_classificados(cards)
    total = counts["total"]
    personalizados = counts["personalizado"]
    return {
        "tem_carimbos": total > 0,
        "cards_canonicos": counts["canonico"],
        "cards_personalizados": personalizados,
        "aula_personalizada": personalizados > 0,
        "aula_canonica": total > 0 and personalizados == 0,
    }


def contar_classificados(cards: list[Any]) -> dict[str, int]:
    canonico = 0
    personalizado = 0
    for c in cards or []:
        kind = classificar_card(c)
        if kind == "canonico":
            canonico += 1
        elif kind == "personalizado":
            personalizado += 1
    return {
        "canonico": canonico,
        "personalizado": personalizado,
        "total": canonico + personalizado,
    }


def razao_personalizacao(contagem: dict[str, int]) -> float | None:
    total = int(contagem.get("total") or 0)
    if total <= 0:
        return None
    return int(contagem.get("personalizado") or 0) / total


def calcular_faixa(contagem: dict[str, int]) -> str | None:
    total = int(contagem.get("total") or 0)
    if total <= 0:
        return None
    ratio = razao_personalizacao(contagem) or 0.0
    if ratio < LIMIAR_FIEL:
        return FAIXA_FIEL
    if ratio > LIMIAR_ALTA:
        return FAIXA_ALTA
    return FAIXA_EQUILIBRIO


def voz_ativa_desbloqueada(avisos: list[Any]) -> bool:
    """Só incorporação real do loop 53 (aprovada / adaptada). Sem segunda fonte."""
    for a in avisos or []:
        if not isinstance(a, dict):
            continue
        tipo = str(a.get("tipo") or "").strip()
        if tipo != TIPO_RESPOSTA_PROPOSTA:
            continue
        meta = a.get("meta") if isinstance(a.get("meta"), dict) else {}
        if not meta and isinstance(a.get("meta_json"), dict):
            meta = a["meta_json"]
        resultado = str(meta.get("resultado") or "").strip().lower()
        if resultado in RESULTADOS_INCORPORADOS:
            return True
    return False


def rotulo_periodo(chave: str) -> str:
    try:
        ano_s, mes_s = chave.split("-", 1)
        mes = int(mes_s)
        ano = int(ano_s)
    except (ValueError, AttributeError):
        return chave
    if mes < 1 or mes > 12:
        return chave
    return f"{_MESES_PT[mes]} de {ano}"


def periodo_anterior(chave: str) -> str:
    ano, mes = [int(p) for p in chave.split("-")]
    if mes == 1:
        return f"{ano - 1}-12"
    return f"{ano}-{mes - 1:02d}"


def parse_chave_mes(raw: str | None, hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    texto = (raw or "").strip()
    if len(texto) == 7 and texto[4] == "-":
        try:
            ano, mes = int(texto[:4]), int(texto[5:7])
            if 1 <= mes <= 12:
                monthrange(ano, mes)
                return f"{ano:04d}-{mes:02d}"
        except ValueError:
            pass
    return f"{hoje.year:04d}-{hoje.month:02d}"


def _data_do_evento(evento: dict[str, Any]) -> date | None:
    raw = evento.get("data_evento")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    texto = str(raw).strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def eventos_do_mes(eventos: list[Any], chave: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in eventos or []:
        if not isinstance(ev, dict):
            continue
        d = _data_do_evento(ev)
        if d is None:
            continue
        if f"{d.year:04d}-{d.month:02d}" == chave:
            out.append(ev)
    return out


def texto_evolucao(
    ratio_atual: float | None,
    ratio_anterior: float | None,
) -> str:
    if ratio_anterior is None:
        return (
            "Ainda não há um período anterior no seu histórico para comparar."
        )
    if ratio_atual is None:
        return (
            "Neste período ainda não há cards carimbados o bastante "
            "para comparar com o mês passado."
        )
    delta = ratio_atual - ratio_anterior
    if delta > DELTA_EVOLUCAO:
        return "Sua personalização cresceu em relação ao mês passado."
    if delta < -DELTA_EVOLUCAO:
        return "Você ficou mais próximo do roteiro-base em relação ao mês passado."
    return "Seu jeito de usar o roteiro se manteve em relação ao mês passado."


def montar_resumo(
    *,
    eventos: list[Any],
    avisos: list[Any],
    mes: str,
    hoje: date | None = None,
) -> dict[str, Any]:
    chave = parse_chave_mes(mes, hoje)
    chave_ant = periodo_anterior(chave)
    atual = contar_classificados(consolidar_cards(eventos_do_mes(eventos, chave)))
    anterior = contar_classificados(
        consolidar_cards(eventos_do_mes(eventos, chave_ant))
    )
    faixa = calcular_faixa(atual)
    ratio_a = razao_personalizacao(atual)
    ratio_b = razao_personalizacao(anterior)
    selos: list[dict[str, str]] = []
    if voz_ativa_desbloqueada(avisos):
        selos.append({"id": "voz_ativa", "rotulo": "Voz Ativa"})

    if faixa is None:
        faixa_texto = (
            "Ainda estamos formando seu retrato deste período. "
            "Conforme você usa e ajusta os cards na Mesa, o resumo "
            "passa a mostrar sua faixa."
        )
        evolucao = (
            texto_evolucao(None, ratio_b)
            if ratio_b is not None
            else (
                "Quando houver cards carimbados em dois períodos, "
                "você verá a evolução em relação ao seu próprio histórico."
            )
        )
    else:
        faixa_texto = FAIXA_TEXTOS[faixa]
        evolucao = texto_evolucao(ratio_a, ratio_b)

    return {
        "periodo": {"chave": chave, "rotulo": rotulo_periodo(chave)},
        "periodo_anterior": {
            "chave": chave_ant,
            "rotulo": rotulo_periodo(chave_ant),
        },
        "faixa": faixa,
        "faixa_rotulo": FAIXA_ROTULOS.get(faixa) if faixa else None,
        "faixa_texto": faixa_texto,
        "evolucao_texto": evolucao,
        "selos": selos,
        "tem_carimbos": atual["total"] > 0,
    }
