"""150 — mapeamento genérico disciplina canônica → ENEM (domínio, sem escola).

O recorte por instituição é JOIN com o catálogo curricular dela, não uma
tabela pré-gerada. Texto oficial permanece em enem_*_oficial (147).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# (área, competência ou None=todas da área, disciplina canônica, nuance)
# RED usa área RED e competencia None = as 5 da cartilha.
MAPEAMENTO: list[tuple[str, int | None, str, str]] = [
    # LC
    ("LC", 1, "Português", "Sistemas de comunicação e informação — não é Ed. Física nem só LEM."),
    ("LC", 2, "Inglês", "H5–H8: língua estrangeira moderna (LEM)."),
    ("LC", 2, "Espanhol", "Mesmas H5–H8 de LEM; a matriz não separa o idioma."),
    ("LC", 3, "Educação Física", "H9–H11: linguagem corporal / hábitos corporais."),
    ("LC", 4, "Arte", "H12–H14: funções da arte e produções artísticas."),
    ("LC", 5, "Português", "Texto literário e contexto de produção."),
    ("LC", 6, "Português", "Gêneros, progressão temática e sistemas simbólicos."),
    ("LC", 7, "Português", "Argumentação em textos da matriz LC — Redação tem competências próprias."),
    ("LC", 8, "Português", "Língua portuguesa como língua materna, norma e variedades."),
    ("LC", 9, "Português", "Impacto social das TICs na linguagem."),
    # CN
    ("CN", 1, "Biologia", "Ciências naturais como construção humana — transversal."),
    ("CN", 1, "Física", "Ciências naturais como construção humana — transversal."),
    ("CN", 1, "Química", "Ciências naturais como construção humana — transversal."),
    ("CN", 2, "Física", "H5 circuitos; H6–H7 manuais e testes de materiais."),
    ("CN", 3, "Biologia", "Ciclos, biotecnologia e impactos ambientais."),
    ("CN", 4, "Biologia", "Organismos, saúde, evolução."),
    ("CN", 5, "Biologia", "Métodos e linguagens das ciências naturais."),
    ("CN", 5, "Física", "Métodos e linguagens das ciências naturais."),
    ("CN", 5, "Química", "Métodos e linguagens das ciências naturais."),
    ("CN", 6, "Física", "Enunciado oficial: conhecimentos da física."),
    ("CN", 7, "Química", "Enunciado oficial: conhecimentos da química."),
    ("CN", 8, "Biologia", "Enunciado oficial: conhecimentos da biologia."),
    # CH — a matriz não nomeia Sociologia/Filosofia; o conteúdo delas está nas competências.
    ("CH", 1, "História", "Identidades, memória e patrimônio; H1 também cita o recorte geográfico."),
    ("CH", 1, "Sociologia", "Diversidade, grupos e memória social — sem a palavra Sociologia no PDF."),
    ("CH", 2, "Geografia", "Competência de espaços geográficos, cartografia e escalas."),
    ("CH", 2, "História", "H7–H10 são histórico-geográficas (nações, Estados, movimentos)."),
    ("CH", 3, "História", "Instituições, conflitos e movimentos no tempo."),
    ("CH", 3, "Sociologia", "Justiça, grupos e movimentos sociais."),
    ("CH", 4, "Geografia", "Territorialização da produção, rural/urbano, circulação."),
    ("CH", 4, "História", "Técnicas e tecnologias na organização do trabalho e da vida social."),
    ("CH", 4, "Sociologia", "Mundo do trabalho e implicações sociais das técnicas."),
    ("CH", 5, "História", "Competência se declara 'conhecimentos históricos' (cidadania, lutas)."),
    ("CH", 5, "Sociologia", "Mídia, inclusão, cidadania e organização da vida social."),
    ("CH", 5, "Filosofia", "H23 valores éticos; H24 cidadania e democracia — não há a palavra Filosofia."),
    ("CH", 6, "Geografia", "Sociedade e natureza, paisagem, recursos, escalas."),
    # MT
    ("MT", None, "Matemática", "As 30 habilidades da área de Matemática."),
    # Redação
    ("RED", None, "Redação", "Cinco competências da cartilha — não misturar com H1–H30 de LC."),
]

ALIASES: dict[str, list[str]] = {
    "portugues": ["Português"],
    "lingua portuguesa": ["Português"],
    "lingua portuguesa e literatura": ["Português"],
    "literatura": ["Português"],
    "portugues redacao": ["Português", "Redação"],
    "portugues / redacao": ["Português", "Redação"],
    "redacao": ["Redação"],
    "ingles": ["Inglês"],
    "lingua inglesa": ["Inglês"],
    "lingua estrangeira": ["Inglês"],
    "lingua estrangeira moderna": ["Inglês"],
    "espanhol": ["Espanhol"],
    "lingua espanhola": ["Espanhol"],
    "educacao fisica": ["Educação Física"],
    "ed fisica": ["Educação Física"],
    "arte": ["Arte"],
    "artes": ["Arte"],
    "biologia": ["Biologia"],
    "fisica": ["Física"],
    "quimica": ["Química"],
    "matematica": ["Matemática"],
    "historia": ["História"],
    "geografia": ["Geografia"],
    "sociologia": ["Sociologia"],
    "filosofia": ["Filosofia"],
}


def norm_disciplina(nome: str | None) -> str:
    t = unicodedata.normalize("NFKD", nome or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower().replace("/", " ").replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


def destinos_habilidade(area: str, competencia: int) -> list[str]:
    out: list[str] = []
    for ar, comp, disc, _n in MAPEAMENTO:
        if ar != area:
            continue
        if comp is None or comp == competencia:
            out.append(disc)
    return out


def linhas_mapeamento() -> list[dict[str, Any]]:
    rows = []
    for area, comp, disc, nuance in MAPEAMENTO:
        rows.append(
            {
                "disciplina_canonica": disc,
                "area_codigo": area,
                "competencia_numero": comp,
                "nuance": nuance,
            }
        )
    return rows


def linhas_alias() -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, str]] = []
    for canon in {r[2] for r in MAPEAMENTO}:
        key = norm_disciplina(canon)
        pair = (key, canon)
        if pair not in seen:
            seen.add(pair)
            rows.append({"alias_norm": key, "disciplina_canonica": canon})
    for alias, canons in ALIASES.items():
        key = norm_disciplina(alias)
        for canon in canons:
            pair = (key, canon)
            if pair in seen:
                continue
            seen.add(pair)
            rows.append({"alias_norm": key, "disciplina_canonica": canon})
    return rows
