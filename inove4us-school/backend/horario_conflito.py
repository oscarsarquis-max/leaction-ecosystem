"""Conflito de horário no Planejamento Escolar (prompt 104).

Sobreposição de intervalo (não só hora idêntica). Vale para a mesma turma
OU o mesmo professor. Substituição institucional (flag + item substituído)
é a única exceção — só este caminho da Secretaria.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

DEFAULT_DURACAO_MIN = 50
DEFAULT_INICIO = time(12, 0)


class ConflitoHorarioError(Exception):
    def __init__(self, mensagem: str, conflito: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.conflito = conflito or {}


def _as_time(value: Any) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value.replace(tzinfo=None) if getattr(value, "tzinfo", None) else value
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    raw = str(value).strip()
    if not raw:
        return None
    if "T" in raw:
        raw = raw.split("T", 1)[1]
    try:
        if len(raw) >= 8 and raw[2] == ":":
            return datetime.strptime(raw[:8], "%H:%M:%S").time()
    except ValueError:
        pass
    try:
        return datetime.strptime(raw[:5], "%H:%M").time()
    except ValueError:
        return None


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def intervalos_sobrepoem(
    a_ini: datetime, a_fim: datetime, b_ini: datetime, b_fim: datetime
) -> bool:
    return a_ini < b_fim and b_ini < a_fim


def resolver_intervalo(
    *,
    data: date | None = None,
    hora_inicio: Any = None,
    hora_fim: Any = None,
    duracao_min: int = DEFAULT_DURACAO_MIN,
) -> tuple[datetime, datetime]:
    dia = _as_date(data) or date.today()
    ini_t = _as_time(hora_inicio) or DEFAULT_INICIO
    start = datetime.combine(dia, ini_t)
    fim_t = _as_time(hora_fim)
    if fim_t is None:
        end = start + timedelta(minutes=max(1, int(duracao_min or DEFAULT_DURACAO_MIN)))
    else:
        end = datetime.combine(dia, fim_t)
        if end <= start:
            end = start + timedelta(minutes=max(1, int(duracao_min or DEFAULT_DURACAO_MIN)))
    return start, end


def fmt_hhmm(value: datetime | time) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    return value.strftime("%H:%M")


def classificar_eixo(
    *,
    proposto_turma_id: Any,
    hit: dict,
    professor_vinculo_id: Any,
) -> str:
    if proposto_turma_id and hit.get("turma_id") and str(hit["turma_id"]) == str(proposto_turma_id):
        return "turma"
    if professor_vinculo_id and hit.get("professor_vinculo_id"):
        if str(hit["professor_vinculo_id"]) == str(professor_vinculo_id):
            return "professor"
    return "horario"


def montar_mensagem_conflito(
    *,
    inicio: datetime,
    fim: datetime,
    hit: dict,
    proposto_turma_id: Any = None,
    professor_vinculo_id: Any = None,
) -> str:
    faixa = f"{fmt_hhmm(inicio)}–{fmt_hhmm(fim)}"
    titulo = str(hit.get("titulo") or "item existente").strip() or "item existente"
    turma = str(hit.get("turma_nome") or "").strip()
    eixo = hit.get("eixo") or classificar_eixo(
        proposto_turma_id=proposto_turma_id,
        hit=hit,
        professor_vinculo_id=professor_vinculo_id,
    )
    if eixo == "turma" and turma:
        onde = f"para a turma {turma}"
    elif eixo == "professor":
        onde = f"para o mesmo professor" + (f" ({turma})" if turma else "")
    else:
        onde = f"para a turma {turma}" if turma else "neste horário"
    return (
        f"Já existe um evento neste intervalo ({faixa}) {onde}: «{titulo}». "
        "Dois eventos não podem ocupar o mesmo horário no mesmo dia. "
        "Marque Substituição institucional e indique o item substituído."
    )


def primeiro_conflito(
    proposto_ini: datetime,
    proposto_fim: datetime,
    candidatos: list[dict],
) -> dict | None:
    for raw in candidatos:
        ini = raw.get("inicio")
        fim = raw.get("fim")
        if ini is None or fim is None:
            ini, fim = resolver_intervalo(
                data=raw.get("data"),
                hora_inicio=raw.get("hora_inicio"),
                hora_fim=raw.get("hora_fim"),
            )
        if intervalos_sobrepoem(proposto_ini, proposto_fim, ini, fim):
            hit = dict(raw)
            hit["inicio"] = ini
            hit["fim"] = fim
            return hit
    return None


def flag_substituicao(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "sim", "yes", "on"}


def assert_sem_conflito_planejamento(
    cur,
    *,
    instituicao_id: str,
    data_ref: date,
    hora_inicio: Any,
    hora_fim: Any,
    turma_id: str,
    professor_vinculo_id: str,
    exclude_id: str | None = None,
    titulo: str | None = None,
) -> None:
    inicio, fim = resolver_intervalo(
        data=data_ref, hora_inicio=hora_inicio, hora_fim=hora_fim
    )
    params: list[Any] = [instituicao_id, data_ref, str(turma_id), str(professor_vinculo_id)]
    sql = """
        SELECT p.id, p.titulo, p.data, p.hora_inicio, p.hora_fim,
               p.turma_id, p.professor_vinculo_id, t.nome AS turma_nome
          FROM public.school_planejamento_escolar p
          JOIN public.school_turmas t ON t.id = p.turma_id
         WHERE p.instituicao_id = %s
           AND p.data = %s
           AND (p.turma_id = %s OR p.professor_vinculo_id = %s)
    """
    if exclude_id:
        sql += " AND p.id <> %s"
        params.append(str(exclude_id))
    cur.execute(sql, params)
    candidatos = []
    for row in cur.fetchall() or []:
        item = dict(row)
        ini, fim_c = resolver_intervalo(
            data=item.get("data") or data_ref,
            hora_inicio=item.get("hora_inicio"),
            hora_fim=item.get("hora_fim"),
        )
        item["inicio"] = ini
        item["fim"] = fim_c
        candidatos.append(item)

    hit = primeiro_conflito(inicio, fim, candidatos)
    if not hit:
        return
    eixo = classificar_eixo(
        proposto_turma_id=turma_id,
        hit=hit,
        professor_vinculo_id=professor_vinculo_id,
    )
    hit["eixo"] = eixo
    mensagem = montar_mensagem_conflito(
        inicio=inicio,
        fim=fim,
        hit=hit,
        proposto_turma_id=turma_id,
        professor_vinculo_id=professor_vinculo_id,
    )
    raise ConflitoHorarioError(
        mensagem,
        {
            "code": "CONFLITO_HORARIO",
            "eixo": eixo,
            "id": str(hit.get("id")) if hit.get("id") else None,
            "titulo": hit.get("titulo"),
            "turma_nome": hit.get("turma_nome"),
            "hora_inicio": fmt_hhmm(inicio),
            "hora_fim": fmt_hhmm(fim),
            "proposto_titulo": titulo,
        },
    )
