"""Testes da integração matcher → Top N candidatos no prompt (sem AWS)."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.catalogo_metodologias_dia import (  # noqa: E402
    entradas_catalogo_dia,
    resolver_entrada_catalogo,
)
from core.metodologia_candidatos_prompt import (  # noqa: E402
    MATCHER_CANDIDATE_TOP_N,
    ORIGEM_DIVERSITY,
    ORIGEM_PREFERRED,
    ORIGEM_SCORE,
    selecionar_candidatos_para_sonnet,
)
from core.metodologia_keyword_matcher import rankear_metodologias_por_keywords  # noqa: E402
from prompts.inov_ativas import (  # noqa: E402
    _framework_ids_block,
    build_estruturar_system_prompt,
)

assert MATCHER_CANDIDATE_TOP_N == 8

# --- Baixa confiança: relato genérico ---
ranking_gen = rankear_metodologias_por_keywords(
    problema="Quero desenvolver uma atividade interessante com minha turma.",
    top_n=0,
)
sel_gen = selecionar_candidatos_para_sonnet(ranking_gen, exclude_ids=set())
assert sel_gen["full_catalog_fallback"] is False
assert len(sel_gen["candidate_ids"]) == 8
assert sel_gen["n_min_ok"] is True
# Determinístico
sel_gen2 = selecionar_candidatos_para_sonnet(ranking_gen, exclude_ids=set())
assert sel_gen["candidate_ids"] == sel_gen2["candidate_ids"]
# Diversidade: pelo menos 2 famílias
fams = {
    (resolver_entrada_catalogo(m) or {}).get("etiqueta")
    for m in sel_gen["candidate_ids"]
}
assert len([f for f in fams if f]) >= 2, fams
# Não é simplesmente os 8 primeiros IDs lexicográficos do catálogo
lex = sorted(e["id"] for e in entradas_catalogo_dia())[:8]
assert sel_gen["candidate_ids"] != lex

# --- Epidemiológico curto ---
ranking_epi = rankear_metodologias_por_keywords(
    problema=(
        "A escola precisa enfrentar o aumento de focos de Aedes aegypti no bairro. "
        "Os estudantes deverão investigar dados reais, mapear focos e desenvolver "
        "uma intervenção para a comunidade."
    ),
    objetivo=(
        "Criar e testar uma solução sustentável e apresentar os resultados "
        "à Secretaria de Saúde."
    ),
    duracao="1 semestre",
    top_n=0,
)
sel_epi = selecionar_candidatos_para_sonnet(ranking_epi, exclude_ids=set())
assert len(sel_epi["candidate_ids"]) == 8
positivos = [r for r in ranking_epi if int(r["score"]) > 0]
print("=== Epidemiológico (diagnóstico) ===")
print("matcher_top:", [(r["id"], r["score"]) for r in ranking_epi[:8]])
print("positive_count:", sel_epi["positive_count"])
print("fill_count:", sel_epi["fill_count"])
print("candidate_ids:", sel_epi["candidate_ids"])
print("origins:", sel_epi["origins"])
assert sel_epi["positive_count"] == len(positivos)
assert sel_epi["fill_count"] == sum(
    1 for o in sel_epi["origins"].values() if o == ORIGEM_DIVERSITY
)

# --- Metodologia desejada fora do Top lexical ---
# Escolhe um ID que tipicamente não está no Top score do relato genérico
all_ids = [e["id"] for e in entradas_catalogo_dia()]
top_scores = {r["id"] for r in ranking_gen if int(r["score"]) > 0}
# Preferir um ID que não seria naturalmente o 1º por score
pref = "agil_eduscrum"
if pref in top_scores and len(all_ids) > 1:
    pref = next(i for i in all_ids if i not in list(sel_gen["candidate_ids"])[:3])
sel_pref = selecionar_candidatos_para_sonnet(
    ranking_gen, preferred_id=pref, exclude_ids=set()
)
assert pref in sel_pref["candidate_ids"]
assert sel_pref["origins"].get(pref) == ORIGEM_PREFERRED
assert len(sel_pref["candidate_ids"]) == 8
assert sel_pref["preferred_injected"] is True

# Prompt inclui preferida e NÃO inclui scores/keywords
prompt_pref = build_estruturar_system_prompt(
    "- (estilo) Engajamento: x",
    candidate_ids=sel_pref["candidate_ids"],
    metodologia_obrigatoria_id=pref,
    metodologia_obrigatoria_nome="EduScrum",
)
assert pref in prompt_pref
assert "METODOLOGIAS DISPONÍVEIS" in prompt_pref
assert "matched_keywords" not in prompt_pref
assert "score" not in prompt_pref.lower()
assert "keywords" not in prompt_pref.lower()

# --- Bloqueio ---
blocked = {"criativa_pbl_projetos"}
sel_block = selecionar_candidatos_para_sonnet(
    ranking_epi, exclude_ids=blocked
)
assert "criativa_pbl_projetos" not in sel_block["candidate_ids"]
cat_block = _framework_ids_block(blocked, candidate_ids=sel_block["candidate_ids"])
assert "criativa_pbl_projetos" not in cat_block
# Preferida bloqueada → tratada como sem preferência
sel_pref_block = selecionar_candidatos_para_sonnet(
    ranking_epi,
    preferred_id="criativa_pbl_projetos",
    exclude_ids=blocked,
)
assert "criativa_pbl_projetos" not in sel_pref_block["candidate_ids"]
assert sel_pref_block["preferred_injected"] is False

# --- Falha / ranking inválido → full catalog ---
sel_fail = selecionar_candidatos_para_sonnet(None)
assert sel_fail["full_catalog_fallback"] is True
assert sel_fail["candidate_ids"] == []
sel_empty = selecionar_candidatos_para_sonnet([])
assert sel_empty["full_catalog_fallback"] is True

# Falha do matcher no wizard → ranking None → full catalog (sem 500)
sel_exc = selecionar_candidatos_para_sonnet(None)
assert sel_exc["full_catalog_fallback"] is True
assert sel_exc["candidate_ids"] == []

# Prompt full vs subset
full = build_estruturar_system_prompt("- (estilo) x")
sub = build_estruturar_system_prompt(
    "- (estilo) x", candidate_ids=sel_epi["candidate_ids"]
)
assert len(sub) < len(full)
for mid in sel_epi["candidate_ids"]:
    assert mid in sub
# IDs fora do subset não entram (amostra)
fora = next(
    e["id"] for e in entradas_catalogo_dia() if e["id"] not in sel_epi["candidate_ids"]
)
assert fora not in _framework_ids_block(candidate_ids=sel_epi["candidate_ids"])

# Origens de score presentes quando há positivos
if sel_epi["positive_count"] > 0:
    assert any(o == ORIGEM_SCORE for o in sel_epi["origins"].values())

print("OK test_wizard_matcher_candidatos")
