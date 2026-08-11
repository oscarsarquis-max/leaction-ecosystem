"""Testes do matcher lexical (modo diagnóstico) — keywords das 39."""
from __future__ import annotations

from core.catalogo_metodologias_dia import KEYWORDS_POR_ID, entradas_catalogo_dia, total_metodologias_catalogo
from core.metodologia_keyword_matcher import (
    normalizar_texto_match,
    rankear_metodologias_por_keywords,
)

assert total_metodologias_catalogo() == 39
# Todas as 39 têm keywords (mapa ou inline)
sem_kw = [e["id"] for e in entradas_catalogo_dia() if not e.get("keywords")]
assert not sem_kw, f"metodologias sem keywords: {sem_kw}"
assert len(KEYWORDS_POR_ID) == 39

# --- Caso 1: projeto / intervenção ---
r1 = rankear_metodologias_por_keywords(
    problema=(
        "Os alunos farão um projeto de intervenção na comunidade: investigação "
        "de um problema real e entrega de um produto final com apresentação."
    ),
    objetivo="Desenvolver solução interdisciplinar de longo prazo.",
    top_n=5,
)
ids1 = [x["id"] for x in r1]
assert "criativa_pbl_projetos" in ids1[:3], ids1
assert r1[0]["score"] > 0

# --- Caso 2: design thinking ---
r2 = rankear_metodologias_por_keywords(
    problema=(
        "Preciso que a turma pratique empatia com o usuário, faça ideação, "
        "construa um protótipo e teste a solução para um problema aberto."
    ),
    top_n=5,
)
ids2 = [x["id"] for x in r2]
assert "criativa_design_thinking_express" in ids2[:2], ids2

# --- Caso 3: sala invertida ---
r3 = rankear_metodologias_por_keywords(
    problema=(
        "Os estudantes assistem ao vídeo e fazem leitura prévia em casa; "
        "a aula será para discussão e aplicação em aula do conteúdo."
    ),
    top_n=5,
)
ids3 = [x["id"] for x in r3]
assert "criativa_sala_invertida" in ids3[:2], ids3

# --- Caso 4: discussão em pares / votação (World Café no catálogo) ---
r4 = rankear_metodologias_por_keywords(
    problema=(
        "Vou usar uma questão conceitual com votação, discussão em pares "
        "e nova votação para sintetizar ideias nas mesas."
    ),
    top_n=5,
)
ids4 = [x["id"] for x in r4]
assert "criativa_world_cafe" in ids4[:3], ids4

# --- Caso 5: sem sinais claros ---
r5 = rankear_metodologias_por_keywords(
    problema="Quero preparar uma atividade interessante para minha turma.",
    top_n=5,
)
assert all(int(x["score"]) <= 3 for x in r5), r5
# ordenação determinística
r5b = rankear_metodologias_por_keywords(
    problema="Quero preparar uma atividade interessante para minha turma.",
    top_n=5,
)
assert [x["id"] for x in r5] == [x["id"] for x in r5b]

# --- Caso 6: repetição não explode score ---
r6a = rankear_metodologias_por_keywords(problema="projeto", top_n=3)
r6b = rankear_metodologias_por_keywords(
    problema="projeto projeto projeto projeto projeto projeto projeto",
    top_n=3,
)
score_pbl_a = next(x["score"] for x in r6a if x["id"] == "criativa_pbl_projetos")
score_pbl_b = next(x["score"] for x in r6b if x["id"] == "criativa_pbl_projetos")
assert score_pbl_a == score_pbl_b, (score_pbl_a, score_pbl_b)

# --- Caso 7: acentuação / case ---
assert normalizar_texto_match("INVESTIGAÇÃO") == normalizar_texto_match("investigacao")
r7a = rankear_metodologias_por_keywords(problema="INVESTIGAÇÃO do problema real", top_n=5)
r7b = rankear_metodologias_por_keywords(problema="investigacao do problema real", top_n=5)
assert [x["id"] for x in r7a[:3]] == [x["id"] for x in r7b[:3]]

# --- Caso 8: frase composta ---
r8 = rankear_metodologias_por_keywords(
    problema="Trabalharemos um problema real no bairro com entrega de solução.",
    top_n=5,
)
pbl = next(x for x in r8 if x["id"] == "criativa_pbl_projetos")
assert "problema real" in [normalizar_texto_match(k) for k in pbl["matched_keywords"]] or any(
    "problema real" in normalizar_texto_match(k) for k in pbl["matched_keywords"]
), pbl["matched_keywords"]

# --- Exemplo epidemiológico (diagnóstico) ---
epi_problema = (
    "A escola precisa enfrentar o aumento de focos de Aedes aegypti no bairro. "
    "Os estudantes deverão investigar dados reais, mapear focos e desenvolver "
    "uma intervenção para a comunidade."
)
epi_objetivo = (
    "Criar e testar uma solução sustentável e apresentar os resultados "
    "à Secretaria de Saúde."
)
epi = rankear_metodologias_por_keywords(
    problema=epi_problema,
    objetivo=epi_objetivo,
    duracao="1 semestre",
    top_n=5,
)
print("=== Top 5 epidemiológico (diagnóstico) ===")
for i, row in enumerate(epi, 1):
    print(
        f"{i}. {row['id']} | {row['nome']} | score={row['score']} | "
        f"matched={row['matched_keywords']}"
    )
assert epi[0]["score"] > 0
assert any(x["id"] == "criativa_pbl_projetos" for x in epi), [x["id"] for x in epi]

print("OK matcher lexical diagnóstico")
