"""148/150 — LC não é 1:1; recorte pelo texto oficial."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enem_catalogo import destinos_habilidade  # noqa: E402


def test_lc_nao_forca_edfisica_em_portugues():
    assert destinos_habilidade("LC", 3) == ["Educação Física"]
    assert destinos_habilidade("LC", 8) == ["Português"]
    assert destinos_habilidade("LC", 2) == ["Inglês", "Espanhol"]
    assert destinos_habilidade("LC", 4) == ["Arte"]


if __name__ == "__main__":
    test_lc_nao_forca_edfisica_em_portugues()
    print("ok")
