"""Ocorrência de aula + união de objetivos de card (paliativo do split/cascata)."""

from __future__ import annotations

from typing import Any

OCORRENCIA_TIPOS = frozenset(
    {"concluida", "interrompida", "substituicao", "trabalho_monitorado"}
)
RESOLUCOES = frozenset(
    {"aguardando_continuacao", "concluida_via_juncao", "agendada_continuacao"}
)

NOTA_OBRIGATORIA = frozenset({"interrompida", "substituicao"})


def normalize_ocorrencia_tipo(raw: Any) -> str:
    tipo = str(raw or "").strip().lower()
    if tipo in OCORRENCIA_TIPOS:
        return tipo
    return "concluida"


def nota_obrigatoria(tipo: str) -> bool:
    return tipo in NOTA_OBRIGATORIA


def resolucao_ao_fechar(tipo: str, agendou_continuacao: bool) -> str | None:
    if tipo != "interrompida":
        return None
    if agendou_continuacao:
        return "agendada_continuacao"
    return "aguardando_continuacao"


def _tarefas(kanban_state: Any) -> list[dict[str, Any]]:
    if isinstance(kanban_state, list):
        return [t for t in kanban_state if isinstance(t, dict)]
    if isinstance(kanban_state, dict):
        tarefas = kanban_state.get("tarefas")
        if isinstance(tarefas, list):
            return [t for t in tarefas if isinstance(t, dict)]
    return []


def objetivos_dos_cards(kanban_state: Any) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for card in _tarefas(kanban_state):
        obj = str(card.get("objetivo") or "").strip()
        if obj and obj not in seen:
            seen.add(obj)
            out.append(obj)
    return out


def unir_objetivos_kanban(destino_kanban: Any, origem_kanban: Any) -> dict[str, Any]:
    """Une objetivos dos cards da aula pendente nos cards da aula que absorve."""
    dest_cards = [dict(t) for t in _tarefas(destino_kanban)]
    extras = objetivos_dos_cards(origem_kanban)
    if not dest_cards:
        return {"tarefas": dest_cards}

    for card in dest_cards:
        atual = str(card.get("objetivo") or "").strip()
        missing = [o for o in extras if o not in atual]
        if not missing:
            continue
        card["objetivo"] = " · ".join([p for p in (atual, *missing) if p])

    first = dest_cards[0]
    first_obj = str(first.get("objetivo") or "")
    leftover = [o for o in extras if o not in first_obj]
    if leftover:
        first["objetivo"] = " · ".join([p for p in (first_obj, *leftover) if p])

    if isinstance(destino_kanban, dict):
        merged = dict(destino_kanban)
        merged["tarefas"] = dest_cards
        return merged
    return {"tarefas": dest_cards}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def mesma_cadeia(atual: dict[str, Any], pendente: dict[str, Any]) -> bool:
    turma_a = str(atual.get("turma") or "").strip().lower()
    turma_b = str(pendente.get("turma") or "").strip().lower()
    if not turma_a or turma_a != turma_b:
        return False
    disc_a = atual.get("disciplina_id")
    disc_b = pendente.get("disciplina_id")
    if disc_a in (None, "") or disc_b in (None, ""):
        return False
    try:
        return int(disc_a) == int(disc_b)
    except (TypeError, ValueError):
        return False


def mesmo_assunto(atual: dict[str, Any], pendente: dict[str, Any]) -> bool:
    """Mesmo fio: turma+disciplina e, se ambos tiverem, o mesmo plano/desafio/tema."""
    if not mesma_cadeia(atual, pendente):
        return False
    for field in ("plano_session", "desafio_id", "tema"):
        va = _norm(atual.get(field))
        vb = _norm(pendente.get(field))
        if va and vb and va != vb:
            return False
    return True


def _data_iso(ev: dict[str, Any]) -> str:
    return str(ev.get("data_evento") or "")


def eh_proxima(
    pendente: dict[str, Any],
    candidata: dict[str, Any],
    irmas: list[dict[str, Any]] | None = None,
) -> bool:
    """True se candidata é a primeira aula do mesmo fio após a pendente (por data)."""
    if not mesmo_assunto(pendente, candidata):
        return False
    dp = _data_iso(pendente)
    dc = _data_iso(candidata)
    if not dp or not dc or dc <= dp:
        return False
    pid = pendente.get("id_evento")
    cid = candidata.get("id_evento")
    for outra in irmas or []:
        oid = outra.get("id_evento")
        if oid in (pid, cid):
            continue
        if not mesmo_assunto(pendente, outra):
            continue
        do = _data_iso(outra)
        if dp < do < dc:
            return False
    return True


def titulo_continuacao(pendente: dict[str, Any]) -> str:
    data = str(pendente.get("data_evento") or "")[:10]
    base = str(pendente.get("titulo") or "aula").strip() or "aula"
    label = f"Continuação de [Parte 1 — {data}]" if data else f"Continuação de {base}"
    return label[:200]


def titulo_parte1(pendente: dict[str, Any]) -> str:
    data = str(pendente.get("data_evento") or "")[:10]
    if data:
        return f"Parte 1 — {data}"
    return str(pendente.get("titulo") or "aula pendente")[:120]
