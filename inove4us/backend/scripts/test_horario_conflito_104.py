"""Prompt 104 — conflito de horário (sobreposição) e exceção de substituição."""
from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from horario_conflito import (  # noqa: E402
    ConflitoHorarioError,
    assert_sem_conflito_agenda,
    flag_substituicao_school,
    intervalos_sobrepoem,
    montar_mensagem_conflito,
    primeiro_conflito,
    resolver_intervalo,
)


DIA = date(2026, 9, 8)


def _slot(turma: str, ini: str, fim: str, *, id_clie=10, titulo="Aula A", id_evento=1):
    h_i = datetime.strptime(ini, "%H:%M").time()
    h_f = datetime.strptime(fim, "%H:%M").time()
    return {
        "id_evento": id_evento,
        "id_clie": id_clie,
        "titulo": titulo,
        "turma": turma,
        "inicio": datetime.combine(DIA, h_i),
        "fim": datetime.combine(DIA, h_f),
    }


def test_1_mesma_turma_mesmo_horario_bloqueado():
    """Professor tenta 2 aulas no mesmo horário, mesma turma — bloqueado."""
    existente = _slot("6º Ano A", "08:00", "08:50", titulo="Frações")
    ini, fim = resolver_intervalo(
        data=DIA, hora_inicio=time(8, 0), hora_fim=time(8, 50)
    )
    hit = primeiro_conflito(ini, fim, [existente])
    assert hit is not None
    msg = montar_mensagem_conflito(
        inicio=ini, fim=fim, hit=hit, proposto_turma="6º Ano A", id_clie=10
    )
    assert "6º Ano A" in msg
    assert "substituição" in msg.lower()


def test_2_mesmo_professor_turmas_diferentes_bloqueado():
    """Mesmo professor, mesmo horário, turmas diferentes — bloqueado."""
    existente = _slot("6º Ano A", "08:00", "08:50", titulo="Frações")
    ini, fim = resolver_intervalo(
        data=DIA, hora_inicio=time(8, 0), hora_fim=time(8, 50)
    )
    hit = primeiro_conflito(ini, fim, [existente])
    assert hit is not None
    msg = montar_mensagem_conflito(
        inicio=ini, fim=fim, hit=hit, proposto_turma="6º Ano B", id_clie=10
    )
    assert "substituição" in msg.lower()
    assert "você" in msg or "Frações" in msg


def test_3_substituicao_school_nao_usa_bloqueio():
    """School com substituicao=true não passa pelo assert (chamador pulou)."""
    assert flag_substituicao_school(True) is True
    assert flag_substituicao_school("true") is True
    assert flag_substituicao_school("sim") is True
    # Body do professor no B2C não autoriza: o flag só é lido no S2S School.
    assert flag_substituicao_school(False) is False
    assert flag_substituicao_school(None) is False


def test_4_sobreposição_parcial_bloqueada():
    """08:00–09:00 vs 08:30–09:30 — overlap, não só horário idêntico."""
    existente = _slot("6º Ano A", "08:00", "09:00", titulo="Números")
    ini, fim = resolver_intervalo(
        data=DIA, hora_inicio=time(8, 30), hora_fim=time(9, 30)
    )
    assert intervalos_sobrepoem(ini, fim, existente["inicio"], existente["fim"])
    hit = primeiro_conflito(ini, fim, [existente])
    assert hit is not None


def test_encostar_no_fim_nao_conflita():
    """08:00–08:50 e 08:50–09:40 podem coexistir (aulas seguidas)."""
    existente = _slot("6º Ano A", "08:00", "08:50")
    ini, fim = resolver_intervalo(
        data=DIA, hora_inicio=time(8, 50), hora_fim=time(9, 40)
    )
    assert primeiro_conflito(ini, fim, [existente]) is None


def test_turno_manha_conflita_com_outro_manha():
    ini_a, fim_a = resolver_intervalo(data=DIA, turno="manha")
    ini_b, fim_b = resolver_intervalo(data=DIA, turno="manha")
    assert intervalos_sobrepoem(ini_a, fim_a, ini_b, fim_b)
    ini_t, fim_t = resolver_intervalo(data=DIA, turno="tarde")
    assert not intervalos_sobrepoem(ini_a, fim_a, ini_t, fim_t)


def test_dia_a_dia_padrao_meio_dia():
    ini, fim = resolver_intervalo(data=DIA)
    assert ini.hour == 12 and ini.minute == 0
    assert fim.hour == 12 and fim.minute == 50


class _FakeCur:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _sql, _params=None):
        return None

    def fetchall(self):
        return self._rows


def test_assert_agenda_levanta_409_semantico():
    cur = _FakeCur(
        [
            {
                "id_evento": 7,
                "id_clie": 10,
                "data_evento": datetime.combine(DIA, time(8, 0)),
                "titulo": "Aula existente",
                "turma": "6º Ano A",
                "turno": None,
                "meta_json": {"hora_inicio": "08:00", "hora_fim": "08:50"},
            }
        ]
    )
    ini, fim = resolver_intervalo(
        data=DIA, hora_inicio=time(8, 0), hora_fim=time(8, 50)
    )
    try:
        assert_sem_conflito_agenda(
            cur,
            id_clie=10,
            data_ref=DIA,
            inicio=ini,
            fim=fim,
            turma="6º Ano A",
        )
        raise AssertionError("deveria bloquear")
    except ConflitoHorarioError as exc:
        assert "Já existe" in exc.mensagem
        assert exc.conflito.get("eixo") == "turma"


if __name__ == "__main__":
    tests = [
        test_1_mesma_turma_mesmo_horario_bloqueado,
        test_2_mesmo_professor_turmas_diferentes_bloqueado,
        test_3_substituicao_school_nao_usa_bloqueio,
        test_4_sobreposição_parcial_bloqueada,
        test_encostar_no_fim_nao_conflita,
        test_turno_manha_conflita_com_outro_manha,
        test_dia_a_dia_padrao_meio_dia,
        test_assert_agenda_levanta_409_semantico,
    ]
    for fn in tests:
        fn()
        print("ok", fn.__name__)
    print("104 horario_conflito", len(tests), "ok")
