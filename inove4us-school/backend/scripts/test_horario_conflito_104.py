"""Prompt 104 — conflito de horário no Planejamento Escolar."""
from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from horario_conflito import (  # noqa: E402
    ConflitoHorarioError,
    assert_sem_conflito_planejamento,
    flag_substituicao,
    intervalos_sobrepoem,
    montar_mensagem_conflito,
    primeiro_conflito,
    resolver_intervalo,
)

DIA = date(2026, 9, 8)
TURMA_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TURMA_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PROF = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _item(turma_id, turma_nome, ini, fim, *, titulo="Aula", pid="1"):
    h_i = datetime.strptime(ini, "%H:%M").time()
    h_f = datetime.strptime(fim, "%H:%M").time()
    return {
        "id": pid,
        "titulo": titulo,
        "turma_id": turma_id,
        "turma_nome": turma_nome,
        "professor_vinculo_id": PROF,
        "inicio": datetime.combine(DIA, h_i),
        "fim": datetime.combine(DIA, h_f),
    }


def test_1_mesma_turma_bloqueado():
    hit = primeiro_conflito(
        *resolver_intervalo(data=DIA, hora_inicio=time(8, 0), hora_fim=time(8, 50)),
        [_item(TURMA_A, "6º Ano A", "08:00", "08:50", titulo="Frações")],
    )
    assert hit is not None
    msg = montar_mensagem_conflito(
        inicio=hit["inicio"],
        fim=hit["fim"],
        hit=hit,
        proposto_turma_id=TURMA_A,
        professor_vinculo_id=PROF,
    )
    assert "6º Ano A" in msg
    assert "Substituição" in msg or "substituição" in msg.lower()


def test_2_mesmo_professor_outra_turma_bloqueado():
    existente = _item(TURMA_A, "6º Ano A", "08:00", "08:50")
    ini, fim = resolver_intervalo(data=DIA, hora_inicio=time(8, 0), hora_fim=time(8, 50))
    assert primeiro_conflito(ini, fim, [existente]) is not None


def test_3_flag_substituicao():
    assert flag_substituicao(True) is True
    assert flag_substituicao("sim") is True
    assert flag_substituicao(False) is False


def test_4_overlap_parcial():
    existente = _item(TURMA_A, "6º Ano A", "08:00", "09:00")
    ini, fim = resolver_intervalo(data=DIA, hora_inicio=time(8, 30), hora_fim=time(9, 30))
    assert intervalos_sobrepoem(ini, fim, existente["inicio"], existente["fim"])
    assert primeiro_conflito(ini, fim, [existente]) is not None


class _FakeCur:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _sql, _params=None):
        return None

    def fetchall(self):
        return self._rows


def test_assert_planejamento_bloqueia():
    cur = _FakeCur(
        [
            {
                "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "titulo": "Aula existente",
                "data": DIA,
                "hora_inicio": time(8, 0),
                "hora_fim": time(8, 50),
                "turma_id": TURMA_A,
                "professor_vinculo_id": PROF,
                "turma_nome": "6º Ano A",
            }
        ]
    )
    try:
        assert_sem_conflito_planejamento(
            cur,
            instituicao_id="3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50",
            data_ref=DIA,
            hora_inicio=time(8, 0),
            hora_fim=time(8, 50),
            turma_id=TURMA_A,
            professor_vinculo_id=PROF,
        )
        raise AssertionError("deveria bloquear")
    except ConflitoHorarioError as exc:
        assert "Já existe" in exc.mensagem
        assert exc.conflito.get("eixo") == "turma"


if __name__ == "__main__":
    for fn in (
        test_1_mesma_turma_bloqueado,
        test_2_mesmo_professor_outra_turma_bloqueado,
        test_3_flag_substituicao,
        test_4_overlap_parcial,
        test_assert_planejamento_bloqueia,
    ):
        fn()
        print("ok", fn.__name__)
    print("104 school horario_conflito ok")
