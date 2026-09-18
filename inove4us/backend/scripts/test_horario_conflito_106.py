"""Prompt 106 — Dia a Dia não pode tratar 12:00–12:50 como horário real do professor."""
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
    intervalos_sobrepoem,
    primeiro_conflito,
    resolver_intervalo,
)

DIA = date(2026, 9, 8)


class _FakeCur:
    def __init__(self, rows):
        self._rows = rows
        self.sql = ""

    def execute(self, sql, _params=None):
        self.sql = sql
        return None

    def fetchall(self):
        return self._rows


def _row(turma, *, id_evento=1, id_clie=10, titulo="Aula A", hora="12:00"):
    h = datetime.strptime(hora, "%H:%M").time()
    return {
        "id_evento": id_evento,
        "id_clie": id_clie,
        "data_evento": datetime.combine(DIA, h),
        "titulo": titulo,
        "turma": turma,
        "turno": None,
        "meta_json": {"hora_inicio": "12:00", "hora_fim": "12:50", "origem": "dia_a_dia"},
    }


def test_1_duas_turmas_mesmo_dia_nao_bloqueia():
    """Professor planeja Dia a Dia pra Turma A e Turma B, mesmo dia — não bloqueia."""
    cur = _FakeCur([_row("6º Ano A", titulo="Frações")])
    ini, fim = resolver_intervalo(data=DIA)
    assert_sem_conflito_agenda(
        cur,
        id_clie=10,
        data_ref=DIA,
        inicio=ini,
        fim=fim,
        turma="6º Ano B",
        somente_eixo_turma=True,
    )
    assert "id_clie" not in cur.sql or "lower(trim(turma))" in cur.sql


def test_2_mesma_turma_mesmo_dia_bloqueia():
    """Duas aulas Dia a Dia pra mesma turma, mesmo dia — bloqueia."""
    cur = _FakeCur([_row("6º Ano A", titulo="Frações")])
    ini, fim = resolver_intervalo(data=DIA)
    try:
        assert_sem_conflito_agenda(
            cur,
            id_clie=10,
            data_ref=DIA,
            inicio=ini,
            fim=fim,
            turma="6º Ano A",
            somente_eixo_turma=True,
        )
        raise AssertionError("deveria bloquear")
    except ConflitoHorarioError as exc:
        assert "6º Ano A" in exc.mensagem
        assert exc.conflito.get("eixo") == "turma"


def test_3_agenda_wizard_ainda_bloqueia_professor_em_outra_turma():
    """Agenda/Desafio com horário real: mesmo professor, turmas diferentes, overlap — bloqueia."""
    existente_ini = datetime.combine(DIA, time(8, 0))
    existente_fim = datetime.combine(DIA, time(12, 0))
    proposto_ini, proposto_fim = resolver_intervalo(data=DIA, turno="manha")
    assert intervalos_sobrepoem(proposto_ini, proposto_fim, existente_ini, existente_fim)
    hit = primeiro_conflito(
        proposto_ini,
        proposto_fim,
        [
            {
                "id_evento": 9,
                "id_clie": 10,
                "titulo": "Desafio 6A",
                "turma": "6º Ano A",
                "inicio": existente_ini,
                "fim": existente_fim,
            }
        ],
    )
    assert hit is not None

    cur = _FakeCur(
        [
            {
                "id_evento": 9,
                "id_clie": 10,
                "data_evento": datetime.combine(DIA, time(8, 0)),
                "titulo": "Desafio 6A",
                "turma": "6º Ano A",
                "turno": "manha",
                "meta_json": {},
            }
        ]
    )
    try:
        assert_sem_conflito_agenda(
            cur,
            id_clie=10,
            data_ref=DIA,
            inicio=proposto_ini,
            fim=proposto_fim,
            turma="6º Ano B",
            somente_eixo_turma=False,
        )
        raise AssertionError("Wizard/Desafio deveria continuar bloqueando o professor")
    except ConflitoHorarioError as exc:
        assert "substituição" in exc.mensagem.lower()


if __name__ == "__main__":
    for fn in (
        test_1_duas_turmas_mesmo_dia_nao_bloqueia,
        test_2_mesma_turma_mesmo_dia_bloqueia,
        test_3_agenda_wizard_ainda_bloqueia_professor_em_outra_turma,
    ):
        fn()
        print("ok", fn.__name__)
    print("106 dia_a_dia placeholder 3 ok")
