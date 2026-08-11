"""Garantias do system prompt compactado (Etapa 6) — sem AWS."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.catalogo_metodologias_dia import (  # noqa: E402
    entradas_catalogo_dia,
    total_metodologias_catalogo,
)
from prompts.inov_ativas import (  # noqa: E402
    IDS_METODOLOGIA_CATALOGO,
    _framework_ids_block,
    build_estruturar_system_prompt,
    medir_componentes_entrada_prompt,
)

assert total_metodologias_catalogo() == 39
assert len(IDS_METODOLOGIA_CATALOGO) == 39

bloco = "- (estilo) Engajamento: turma dispersa precisa de papéis claros."
catalogo = _framework_ids_block()
prompt = build_estruturar_system_prompt(bloco)

# 39 IDs e nomes presentes no catálogo compacto e no system
for e in entradas_catalogo_dia():
    assert e["id"] in catalogo, e["id"]
    assert e["nome"] in catalogo, e["nome"]
    assert e["id"] in prompt, e["id"]

# Formato compacto id|Nome
assert "|" in catalogo
assert "`" not in catalogo

# Contrato JSON preservado
for campo in (
    "trecho_relato_usado",
    "causas",
    "id_metodologia",
    "gancho_adaptacao",
    "hipotese_teste",
):
    assert campo in prompt, campo
assert '"A"' in prompt and '"B"' in prompt and '"C"' in prompt

assert "framework_obrigatorio" in prompt
assert "ancoras_de_estilo" in prompt
# Bloco obrigatório só quando há metodologia desejada
assert "<metodologia_obrigatoria_do_professor>" not in build_estruturar_system_prompt(bloco)

# Concisão: não pedir parágrafos longos no output
assert "3–5 frases" not in prompt
assert "2–4 frases" not in prompt
assert "2–3 frases" not in prompt
assert "1 frase" in prompt
assert "não gere cards" in prompt.lower()

# Exclusões ainda removem IDs
exc = {"agil_eduscrum"}
cat_exc = _framework_ids_block(exc)
assert "agil_eduscrum" not in cat_exc
assert "agil_eduscrum" not in build_estruturar_system_prompt(bloco, exclude_ids=exc)

# Obrigatoriedade preservada
p_ob = build_estruturar_system_prompt(
    bloco,
    metodologia_obrigatoria_id="criativa_pbl_projetos",
    metodologia_obrigatoria_nome="Aprendizagem Baseada em Projetos",
)
assert "O professor EXIGIU" in p_ob
assert "criativa_pbl_projetos" in p_ob

# Menor que baseline da Etapa 5 (~5577) e catálogo menor que ~2273
partes = medir_componentes_entrada_prompt(
    bloco, system_prompt=prompt, user_content="x", ancoras_count=1
)
assert partes["system_total_chars"] < 4200, partes["system_total_chars"]
assert partes["system_catalogo_chars"] < 2000, partes["system_catalogo_chars"]

# BLOCO_TOM longo não deve entrar no estruturar
assert "<tom_de_voz>" not in prompt

print(
    "OK prompt compacto",
    f"system={partes['system_total_chars']}",
    f"catalogo={partes['system_catalogo_chars']}",
)
