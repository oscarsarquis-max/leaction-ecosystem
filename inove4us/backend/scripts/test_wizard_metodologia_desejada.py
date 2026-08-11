"""Regressão: metodologia desejada no wizard (preferência explícita → slot A)."""
from __future__ import annotations

from prompts.inov_ativas import build_estruturar_system_prompt
from wizard_qualidade import montar_user_content_estruturar
from wizard_routes import (
    _fallback_payload,
    _resolver_metodologia_desejada,
    _stitch_ranking_hibrido,
)

PBL = "criativa_pbl_projetos"
# alias comum do catálogo
PBL_ALT = "criativa_pbl_problemas"

problema = (
    "Os alunos precisam desenvolver uma intervenção para reduzir o desperdício de água "
    "no entorno da escola, com entrega pública em seis aulas."
)
contexto = "Escola pública"

# --- Resolver ---
mid, nome = _resolver_metodologia_desejada(PBL, exclude_ids=set())
assert mid == PBL, (mid, nome)
assert nome and len(nome) > 3

mid_inv, nome_inv = _resolver_metodologia_desejada("metodologia_inexistente_xyz", exclude_ids=set())
assert mid_inv is None and nome_inv is None

mid_blk, nome_blk = _resolver_metodologia_desejada(PBL, exclude_ids={PBL})
assert mid_blk is None and nome_blk is None

mid_none, _ = _resolver_metodologia_desejada(None, exclude_ids=set())
assert mid_none is None

# --- user_content ---
uc_sem = montar_user_content_estruturar(problema_limpo=problema)
assert "METODOLOGIA INFORMADA" not in uc_sem

uc_com = montar_user_content_estruturar(
    problema_limpo=problema,
    metodologia_nome="Aprendizagem Baseada em Projetos",
    metodologia_id=PBL,
)
assert "METODOLOGIA INFORMADA PELO PROFESSOR" in uc_com
assert PBL in uc_com
assert "Aprendizagem Baseada em Projetos" in uc_com

# --- system prompt mínimo ---
p_ob = build_estruturar_system_prompt(
    "- (estilo) Engajamento: turma dispersa.",
    metodologia_obrigatoria_id=PBL,
    metodologia_obrigatoria_nome="Aprendizagem Baseada em Projetos",
)
assert "O professor EXIGIU" in p_ob
assert PBL in p_ob
p_livre = build_estruturar_system_prompt("- (estilo) Engajamento: turma dispersa.")
assert "O professor EXIGIU" not in p_livre

# --- Sonnet ignora preferência → stitch força A ---
raw_ignorou = {
    "trecho_relato_usado": "desperdício de água no entorno da escola",
    "causas": [
        {"titulo": "Desperdício", "descricao": "A turma precisa mapear perdas de água no entorno da escola com evidência observável."},
        {"titulo": "Engajamento", "descricao": "Sem papéis claros, a intervenção de seis aulas perde ritmo e entrega pública fica frágil."},
        {"titulo": "Evidência", "descricao": "Falta definir o que medir para mostrar redução do desperdício de água aos colegas."},
    ],
    "A": {
        "id_metodologia": "agil_elevator_pitch",
        "gancho_adaptacao": "Use o relato do desperdício de água para abrir a prática com a turma.",
        "hipotese_teste": "Se a turma mapear o desperdício de água, você observa evidência concreta na entrega.",
    },
    "B": {
        "id_metodologia": "criativa_design_thinking_express",
        "gancho_adaptacao": "Ideação rápida a partir do entorno da escola.",
        "hipotese_teste": "Se idearem soluções de baixo custo, a turma pratica síntese e você observa propostas.",
    },
    "C": {
        "id_metodologia": "imersiva_escape_room",
        "gancho_adaptacao": "Missão curta com pistas sobre água.",
        "hipotese_teste": "Se resolverem a missão, praticam colaboração e você observa engajamento.",
    },
}

stitched = _stitch_ranking_hibrido(
    raw_ignorou,
    problema,
    contexto,
    [],
    [],
    preferred_metodologia_id=PBL,
)
caminhos = stitched["caminhos"]
assert len(caminhos) == 3
assert caminhos[0]["id_metodologia"] == PBL, caminhos[0].get("id_metodologia")
assert caminhos[0]["id"] == "A"
ids_bc = {caminhos[1]["id_metodologia"], caminhos[2]["id_metodologia"]}
assert PBL not in ids_bc, ids_bc
assert caminhos[1]["id_metodologia"] != caminhos[2]["id_metodologia"]
# Cards coerentes com A (há cards ou plano pedagógico)
plano_a = caminhos[0].get("plano_eduscrum") or {}
cards_a = plano_a.get("tarefas_kanban") or caminhos[0].get("cards") or []
assert caminhos[0].get("metodologia"), caminhos[0]
assert "Projeto" in (caminhos[0].get("metodologia") or "") or PBL in str(
    caminhos[0].get("id_metodologia")
)

# --- sem preferência: fluxo segue (3 IDs distintos; não exige forçar PBL) ---
stitched_livre = _stitch_ranking_hibrido(
    raw_ignorou,
    problema,
    contexto,
    [],
    [],
    preferred_metodologia_id=None,
)
assert len(stitched_livre["caminhos"]) == 3
assert len({c["id_metodologia"] for c in stitched_livre["caminhos"]}) == 3

# --- preferência inválida: degrado seguro (não usa o ID inventado) ---
stitched_inv = _stitch_ranking_hibrido(
    raw_ignorou,
    problema,
    contexto,
    [],
    [],
    preferred_metodologia_id="nao_existe_xyz",
)
assert stitched_inv["caminhos"][0]["id_metodologia"] != "nao_existe_xyz"
assert len({c["id_metodologia"] for c in stitched_inv["caminhos"]}) == 3

# --- preferência bloqueada: não força ---
stitched_blk = _stitch_ranking_hibrido(
    raw_ignorou,
    problema,
    contexto,
    [],
    [],
    exclude_ids={PBL},
    preferred_metodologia_id=PBL,
)
assert stitched_blk["caminhos"][0]["id_metodologia"] != PBL

# --- fallback com preferência ---
fb = _fallback_payload(
    problema,
    contexto,
    [],
    [],
    preferred_metodologia_id=PBL,
)
assert fb["caminhos"][0]["id_metodologia"] == PBL
assert fb["caminhos"][1]["id_metodologia"] != PBL
assert fb["caminhos"][2]["id_metodologia"] != PBL
assert len({c["id_metodologia"] for c in fb["caminhos"]}) == 3

# fallback sem preferência ainda gera 3 caminhos
fb0 = _fallback_payload(problema, contexto, [], [])
assert len(fb0["caminhos"]) == 3

print("OK metodologia desejada → slot A + fallback + degradação segura")
