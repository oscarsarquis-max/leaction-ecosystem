"""Conflito de horário em eventos agendados (prompt 104).

Dois eventos no mesmo dia não podem ter intervalos sobrepostos se
compartilham o professor (id_clie) ou a turma. Sobreposição parcial conta.
A única exceção é substituição institucional via push do School.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Any

DEFAULT_DURACAO_MIN = 50
DEFAULT_INICIO = time(12, 0)

# Turno EduScrum: o slot ocupa o período inteiro, não só o timestamp 08:00/14:00/19:00.
TURNO_INTERVALO: dict[str, tuple[time, time]] = {
    "manha": (time(8, 0), time(12, 0)),
    "tarde": (time(13, 0), time(18, 0)),
    "noite": (time(18, 30), time(22, 30)),
}


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


def _as_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, DEFAULT_INICIO)
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1]
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19] if "T" in raw or " " in raw else raw[:10], fmt)
        except ValueError:
            continue
    return None


def _meta_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, memoryview)):
        value = bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def intervalos_sobrepoem(
    a_ini: datetime, a_fim: datetime, b_ini: datetime, b_fim: datetime
) -> bool:
    """Intervalos semiabertos [ini, fim): encostar no fim do outro não é conflito."""
    return a_ini < b_fim and b_ini < a_fim


def resolver_intervalo(
    *,
    data: date | None = None,
    hora_inicio: Any = None,
    hora_fim: Any = None,
    turno: str | None = None,
    data_evento: Any = None,
    duracao_min: int = DEFAULT_DURACAO_MIN,
) -> tuple[datetime, datetime]:
    """Converte data + horas/turno em [inicio, fim)."""
    turno_key = str(turno or "").strip().lower()
    dt_ev = _as_datetime(data_evento)
    dia = _as_date(data) or (dt_ev.date() if dt_ev else date.today())

    if turno_key in TURNO_INTERVALO:
        ini_t, fim_t = TURNO_INTERVALO[turno_key]
        return datetime.combine(dia, ini_t), datetime.combine(dia, fim_t)

    ini_t = _as_time(hora_inicio)
    if ini_t is None and dt_ev is not None:
        ini_t = dt_ev.time().replace(microsecond=0)
    if ini_t is None:
        ini_t = DEFAULT_INICIO

    start = datetime.combine(dia, ini_t)
    fim_t = _as_time(hora_fim)
    if fim_t is None:
        end = start + timedelta(minutes=max(1, int(duracao_min or DEFAULT_DURACAO_MIN)))
    else:
        end = datetime.combine(dia, fim_t)
        if end <= start:
            end = start + timedelta(minutes=max(1, int(duracao_min or DEFAULT_DURACAO_MIN)))
    return start, end


def intervalo_do_evento_agenda(row: dict) -> tuple[datetime, datetime]:
    meta = _meta_dict(row.get("meta_json"))
    return resolver_intervalo(
        data=_as_date(row.get("data_evento")) or _as_date(row.get("data")),
        hora_inicio=meta.get("hora_inicio") or row.get("hora_inicio"),
        hora_fim=meta.get("hora_fim") or row.get("hora_fim"),
        turno=row.get("turno"),
        data_evento=row.get("data_evento"),
        duracao_min=int(meta.get("duracao_min") or DEFAULT_DURACAO_MIN),
    )


def _norm_turma(value: Any) -> str:
    return str(value or "").strip().lower()


def classificar_eixo(*, proposto_turma: str | None, hit: dict, id_clie: int | None) -> str:
    hit_turma = _norm_turma(hit.get("turma") or hit.get("turma_nome"))
    prop = _norm_turma(proposto_turma)
    if prop and hit_turma and prop == hit_turma:
        return "turma"
    if id_clie is not None and hit.get("id_clie") is not None:
        try:
            if int(hit["id_clie"]) == int(id_clie):
                return "professor"
        except (TypeError, ValueError):
            pass
    return "horario"


def fmt_hhmm(value: datetime | time) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    return value.strftime("%H:%M")


def montar_mensagem_conflito(
    *,
    inicio: datetime,
    fim: datetime,
    hit: dict,
    proposto_turma: str | None = None,
    id_clie: int | None = None,
) -> str:
    faixa = f"{fmt_hhmm(inicio)}–{fmt_hhmm(fim)}"
    titulo = str(hit.get("titulo") or "evento existente").strip() or "evento existente"
    turma = str(hit.get("turma") or hit.get("turma_nome") or "").strip()
    eixo = hit.get("eixo") or classificar_eixo(
        proposto_turma=proposto_turma, hit=hit, id_clie=id_clie
    )
    if eixo == "turma" and turma:
        onde = f"para a turma {turma}"
    elif eixo == "professor":
        onde = f"para você" + (f" ({turma})" if turma else "")
    else:
        onde = f"para a turma {turma}" if turma else "neste horário"
    return (
        f"Já existe um evento neste intervalo ({faixa}) {onde}: «{titulo}». "
        "Dois eventos não podem ocupar o mesmo horário no mesmo dia. "
        "Só a Secretaria, via Planejamento Escolar, pode registrar uma substituição."
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
            ini, fim = intervalo_do_evento_agenda(raw)
        if intervalos_sobrepoem(proposto_ini, proposto_fim, ini, fim):
            hit = dict(raw)
            hit["inicio"] = ini
            hit["fim"] = fim
            return hit
    return None


def _carregar_candidatos_agenda(
    cur,
    *,
    id_clie: int,
    data_ref: date,
    turma: str | None,
    exclude_id: int | None,
) -> list[dict]:
    turma_norm = (turma or "").strip()
    params: list[Any] = [data_ref, int(id_clie)]
    sql = """
        SELECT id_evento, id_clie, data_evento, titulo, turma, turno, meta_json
          FROM public.inove_agenda_eventos
         WHERE data_evento::date = %s
           AND (
                id_clie = %s
    """
    if turma_norm:
        sql += " OR (turma IS NOT NULL AND trim(turma) <> '' AND lower(trim(turma)) = lower(trim(%s)))"
        params.append(turma_norm)
    sql += ")"
    if exclude_id is not None:
        sql += " AND id_evento <> %s"
        params.append(int(exclude_id))
    cur.execute(sql, params)
    rows = cur.fetchall() or []
    out = []
    for row in rows:
        item = dict(row)
        ini, fim = intervalo_do_evento_agenda(item)
        item["inicio"] = ini
        item["fim"] = fim
        out.append(item)
    return out


def assert_sem_conflito_agenda(
    cur,
    *,
    id_clie: int,
    data_ref: date,
    inicio: datetime,
    fim: datetime,
    turma: str | None = None,
    exclude_id: int | None = None,
    titulo: str | None = None,
) -> None:
    """Levanta ConflitoHorarioError se já houver overlap para o professor ou a turma."""
    candidatos = _carregar_candidatos_agenda(
        cur,
        id_clie=id_clie,
        data_ref=data_ref,
        turma=turma,
        exclude_id=exclude_id,
    )
    hit = primeiro_conflito(inicio, fim, candidatos)
    if not hit:
        return
    eixo = classificar_eixo(proposto_turma=turma, hit=hit, id_clie=id_clie)
    hit["eixo"] = eixo
    mensagem = montar_mensagem_conflito(
        inicio=inicio,
        fim=fim,
        hit=hit,
        proposto_turma=turma,
        id_clie=id_clie,
    )
    raise ConflitoHorarioError(
        mensagem,
        {
            "code": "CONFLITO_HORARIO",
            "eixo": eixo,
            "id_evento": hit.get("id_evento"),
            "titulo": hit.get("titulo"),
            "turma": hit.get("turma"),
            "hora_inicio": fmt_hhmm(inicio),
            "hora_fim": fmt_hhmm(fim),
            "proposto_titulo": titulo,
        },
    )


def conflito_http(exc: ConflitoHorarioError, *, school_shape: bool = False):
    """Payload Flask 409. school_shape=True → {error} (secretaria); senão B2C."""
    body = {"error": exc.mensagem, "code": "CONFLITO_HORARIO", "conflito": exc.conflito}
    if not school_shape:
        body["success"] = False
    return body


def flag_substituicao_school(value: Any) -> bool:
    """Só o S2S do School deve passar True. Chamadores B2C ignoram o body do professor."""
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "sim", "yes", "on"}
