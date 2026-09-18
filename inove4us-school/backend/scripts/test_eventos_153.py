#!/usr/bin/env python3
"""Prompt 153 — mapeamento de tipo e público administradores. Sem I/O de prod."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from eventos_service import (  # noqa: E402
    BROADCAST_TIPOS,
    EVENTO_TIPOS,
    com_tipo_for_evento,
    evento_tipo_from_comunicado,
    normalize_tipo_evento,
    serialize_evento,
)
from secretaria_routes import COM_PUBLICOS  # noqa: E402


def main() -> int:
    assert normalize_tipo_evento("cívico") == "civico"
    assert normalize_tipo_evento("CIVICO") == "civico"
    assert normalize_tipo_evento("aula") == "aula"
    assert normalize_tipo_evento("nope") is None
    assert EVENTO_TIPOS == {"aula", "planejamento", "treinamento", "civico", "geral"}
    assert "aula" not in BROADCAST_TIPOS
    assert com_tipo_for_evento("planejamento") == "reuniao_pedagogica"
    assert com_tipo_for_evento("geral") == "evento_escolar"
    assert evento_tipo_from_comunicado("reuniao_pedagogica") == "planejamento"
    assert evento_tipo_from_comunicado("evento_escolar") == "geral"
    assert "administradores" in COM_PUBLICOS

    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "tipo_evento": "treinamento",
        "titulo": "Capacitação",
        "descricao": "",
        "data_hora_inicio": None,
        "data_hora_fim": None,
        "publico_alvo": "administradores",
        "status": "publicado",
        "substituicao": False,
    }
    ser = serialize_evento(row)
    assert ser["tipo_label"] == "Treinamento"
    assert ser["publico_label"] == "Administradores"
    assert ser["source"] == "broadcast"
    print("ok 153 school eventos map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
