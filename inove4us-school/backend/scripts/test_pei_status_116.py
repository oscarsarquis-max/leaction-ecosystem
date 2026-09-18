#!/usr/bin/env python3
"""Prompt 116 — status intermediário PEI + labels. Sem I/O de prod."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from pei_documental_routes import (  # noqa: E402
    _serialize_pei,
    _status_assinatura_pei,
    _status_pei_persistido,
)


def test_labels() -> None:
    assert _status_assinatura_pei(False, False) == (
        "aguardando_coordenador",
        "Aguardando coordenador",
    )
    assert _status_assinatura_pei(True, False) == (
        "aguardando_psicopedagogo",
        "Aguardando psicopedagogo",
    )
    assert _status_assinatura_pei(False, True) == (
        "aguardando_coordenador",
        "Aguardando coordenador",
    )
    assert _status_assinatura_pei(True, True) == ("assinado", "Assinado")
    assert _status_pei_persistido(True, True) == "ativo"
    assert _status_pei_persistido(True, False) == "aguardando_psicopedagogo"


def test_serialize_unsigned() -> None:
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "instituicao_id": "00000000-0000-0000-0000-000000000002",
        "aee_matriz_id": "00000000-0000-0000-0000-000000000003",
        "versao": 1,
        "status": "rascunho",
        "assinado_coordenador": False,
        "assinado_psicopedagogo": False,
        "aluno_id": None,
        "nome_completo": "X",
        "matricula": "",
    }
    s = _serialize_pei(row)
    assert s["status"] == "aguardando_coordenador"
    assert s["status_assinatura"] == "aguardando_coordenador"
    assert s["status_assinatura_label"] == "Aguardando coordenador"
    assert s["valido"] is False


def test_serialize_coord_only() -> None:
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "instituicao_id": "00000000-0000-0000-0000-000000000002",
        "aee_matriz_id": "00000000-0000-0000-0000-000000000003",
        "versao": 1,
        "status": "aguardando_psicopedagogo",
        "assinado_coordenador": True,
        "assinado_psicopedagogo": False,
        "aluno_id": None,
        "nome_completo": "X",
        "matricula": "",
    }
    s = _serialize_pei(row)
    assert s["status"] == "aguardando_psicopedagogo"
    assert s["status_assinatura_label"] == "Aguardando psicopedagogo"
    assert s["valido"] is False


def test_serialize_signed() -> None:
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "instituicao_id": "00000000-0000-0000-0000-000000000002",
        "aee_matriz_id": "00000000-0000-0000-0000-000000000003",
        "versao": 1,
        "status": "ativo",
        "assinado_coordenador": True,
        "assinado_psicopedagogo": True,
        "aluno_id": None,
        "nome_completo": "X",
        "matricula": "",
    }
    s = _serialize_pei(row)
    assert s["status"] == "ativo"
    assert s["status_assinatura"] == "assinado"
    assert s["valido"] is True


def main() -> int:
    test_labels()
    test_serialize_unsigned()
    test_serialize_coord_only()
    test_serialize_signed()
    print("ok 116 pei status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
