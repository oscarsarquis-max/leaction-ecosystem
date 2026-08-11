"""Testes do diagnóstico de Prompt Caching — sem AWS e sem cache_control em produção."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.wizard_cache_feasibility import (  # noqa: E402
    INVOKE_MODEL_CACHE_USAGE_KEYS,
    analyze_cache_feasibility,
    resolve_cache_spec,
    split_system_prompt_blocks,
)
from prompts.inov_ativas import build_estruturar_system_prompt  # noqa: E402
from wizard_routes import BEDROCK_MODEL_ID, WIZARD_BEDROCK_MODEL_ID  # noqa: E402
from wizard_routes import _extrair_usage_bedrock  # noqa: E402

model_id = WIZARD_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
assert "claude-sonnet-4-20250514" in model_id

spec = resolve_cache_spec(model_id)
assert spec["cache_supported"] is True
assert spec["min_checkpoint_tokens"] == 1024
assert spec["max_checkpoints"] == 4
assert "5 minutes" in (spec.get("ttl") or "")

# Instrumentação captura snake_case do InvokeModel
assert "cache_creation_input_tokens" in INVOKE_MODEL_CACHE_USAGE_KEYS
assert "cache_read_input_tokens" in INVOKE_MODEL_CACHE_USAGE_KEYS
u = _extrair_usage_bedrock(
    {
        "usage": {
            "input_tokens": 10,
            "output_tokens": 2,
            "cache_creation_input_tokens": 100,
            "cache_read_input_tokens": 50,
        }
    }
)
assert u["cache_creation_input_tokens"] == 100
assert u["cache_read_input_tokens"] == 50

# Helper de análise não chama Bedrock
import inspect

import core.wizard_cache_feasibility as mod

src = inspect.getsource(mod)
assert "boto3" not in src
assert "bedrock-runtime" not in src
# Produção: body do wizard ainda sem cache_control
import wizard_routes as wr

invoke_src = inspect.getsource(wr._invoke_estruturar_bedrock)
assert "cache_control" not in invoke_src

cands = [
    "criativa_pbl_projetos",
    "criativa_pbl_problemas",
    "agil_canvas_mania",
    "imersiva_aprendizagem_jogos",
    "analitica_chatbots",
    "agil_elevator_pitch",
    "imersiva_escape_room",
    "analitica_diagnostico_coletivo",
]
sys_prompt = build_estruturar_system_prompt(
    "- (estilo) Engajamento: x\n- (estilo) Investigação: y",
    candidate_ids=cands,
)
blocks = split_system_prompt_blocks(sys_prompt)
assert blocks["intro"]
assert "<framework_obrigatorio>" in blocks["framework_section"]
assert "<regras>" in blocks["regras_section"]
assert "<formato>" in blocks["formato_section"]
# Ordem: regras DEPOIS do framework no texto completo
assert sys_prompt.find("<framework_obrigatorio>") < sys_prompt.find("<regras>")

analysis = analyze_cache_feasibility(
    model_id=model_id,
    system_prompt=sys_prompt,
    user_content="PROBLEMA\n\ntest\n",
    candidate_catalog_chars=400,
    measured_input_tokens=1016,
)
assert analysis["static_prefix_chars"] < 300
assert analysis["static_prefix_chars"] < analysis["static_if_reorganized_chars"]
assert analysis["checkpoint_before_candidates_valid"] is False
assert analysis["checkpoint_after_candidates_stable"] is False
assert analysis["classification"] in ("B", "C", "D")
# Com system compacto + usage ~1016, deve ser C (pouco útil / abaixo do mínimo)
assert analysis["classification"] == "C", analysis
assert analysis["full_system_meets_min_status"].startswith("NÃO")

print(
    "OK cache feasibility",
    f"class={analysis['classification']}",
    f"static_prefix={analysis['static_prefix_chars']}",
    f"sys_tok_der={analysis['system_tokens_derived']}",
)
