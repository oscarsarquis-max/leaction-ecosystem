"""150 — mapeamento genérico + interseção por escola."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enem_catalogo import destinos_habilidade, linhas_mapeamento, norm_disciplina


def test_dominio_completo():
    discs = {r["disciplina_canonica"] for r in linhas_mapeamento()}
    assert discs >= {
        "Português",
        "Inglês",
        "Espanhol",
        "Educação Física",
        "Arte",
        "Biologia",
        "Física",
        "Química",
        "Matemática",
        "História",
        "Geografia",
        "Sociologia",
        "Filosofia",
        "Redação",
    }
    assert destinos_habilidade("LC", 4) == ["Arte"]
    assert destinos_habilidade("CN", 7) == ["Química"]
    assert destinos_habilidade("MT", 1) == ["Matemática"]
    assert "Inglês" in destinos_habilidade("LC", 2)
    assert "Espanhol" in destinos_habilidade("LC", 2)
    assert "História" in destinos_habilidade("CH", 5)
    assert "Filosofia" in destinos_habilidade("CH", 5)
    assert "Geografia" in destinos_habilidade("CH", 6)
    assert destinos_habilidade("LC", 8) == ["Português"]


def test_alias_portugues_redacao():
    assert norm_disciplina("Português/Redação") == "portugues redacao"
    assert norm_disciplina("Língua Portuguesa") == "lingua portuguesa"


def test_helenita_hoje_bate_148_vinculado():
    """Mesmas 6 disciplinas reais: sem órfãos (MT/CH/Arte/Química)."""
    helenita = {
        "Português",
        "Inglês",
        "Educação Física",
        "Biologia",
        "Física",
        "Redação",
    }
    counts: Counter[str] = Counter()
    grouping = {
        "LC": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8, 9, 9, 9],
        "MT": [1] * 5 + [2] * 4 + [3] * 5 + [4] * 4 + [5] * 5 + [6] * 3 + [7] * 4,
        "CN": [1] * 4 + [2] * 3 + [3] * 5 + [4] * 4 + [5] * 3 + [6] * 4 + [7] * 4 + [8] * 3,
        "CH": [1] * 5 + [2] * 5 + [3] * 5 + [4] * 5 + [5] * 5 + [6] * 5,
    }
    for area, comps in grouping.items():
        for c in comps:
            for disc in destinos_habilidade(area, c):
                if disc in helenita:
                    counts[disc] += 1
    counts["Redação"] += 5
    assert counts["Português"] == 20
    assert counts["Inglês"] == 4
    assert counts["Educação Física"] == 3
    assert counts["Biologia"] == 19
    assert counts["Física"] == 14
    assert counts["Redação"] == 5
    assert sum(counts.values()) == 65


if __name__ == "__main__":
    test_dominio_completo()
    test_alias_portugues_redacao()
    test_helenita_hoje_bate_148_vinculado()
    print("ok")
