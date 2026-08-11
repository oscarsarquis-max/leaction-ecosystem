"""Contrato de retry do wizard — mockado, sem AWS.

Confirma: mesma system/candidatos na 2ª chamada; agregação de tokens/latência;
parse permanece válido.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.metodologia_candidatos_prompt import selecionar_candidatos_para_sonnet  # noqa: E402
from core.metodologia_keyword_matcher import rankear_metodologias_por_keywords  # noqa: E402
from prompts.inov_ativas import build_estruturar_system_prompt  # noqa: E402
from wizard_routes import (  # noqa: E402
    _invoke_estruturar_bedrock,
    _sum_optional_ints,
)


class _Body:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw


ranking = rankear_metodologias_por_keywords(
    problema="Alunos não concluem entregas em grupo na Biologia.",
    contexto="1º ano EM, 32 alunos.",
    top_n=0,
)
sel = selecionar_candidatos_para_sonnet(ranking, top_n=8, preferred_id="agil_eduscrum")
cids = list(sel["candidate_ids"] or [])
assert "agil_eduscrum" in cids
assert len(cids) == 8

system_prompt = build_estruturar_system_prompt(
    "- (estilo) Engajamento: papéis e ritmo de entrega.",
    candidate_ids=cids,
    metodologia_obrigatoria_id="agil_eduscrum",
    metodologia_obrigatoria_nome="EduScrum",
)
# Retry reutiliza o mesmo system (candidatos não são recalculados).
system_retry = system_prompt
assert system_retry == system_prompt
assert all(mid in system_prompt for mid in cids)

payload_ok = {
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 100, "output_tokens": 40},
    "content": [
        {
            "text": (
                '"trecho_relato_usado":"entregas em grupo",'
                '"causas":[{"titulo":"a","descricao":"d1"},'
                '{"titulo":"b","descricao":"d2"},'
                '{"titulo":"c","descricao":"d3"}],'
                '"A":{"id_metodologia":"agil_eduscrum",'
                '"gancho_adaptacao":"g","hipotese_teste":"h"},'
                '"B":{"id_metodologia":"agil_canvas_mania",'
                '"gancho_adaptacao":"g","hipotese_teste":"h"},'
                '"C":{"id_metodologia":"imersiva_escape_room",'
                '"gancho_adaptacao":"g","hipotese_teste":"h"}}'
            )
        }
    ],
}
payload_retry = {
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 110, "output_tokens": 45},
    "content": payload_ok["content"],
}

bedrock = MagicMock()
bedrock.invoke_model.side_effect = [
    {"body": _Body(payload_ok)},
    {"body": _Body(payload_retry)},
]

parsed1, meta1 = _invoke_estruturar_bedrock(
    bedrock=bedrock,
    model_id="test-model",
    system_prompt=system_prompt,
    user_content="USER",
    max_tokens=4096,
    json_prefill="{",
)
parsed2, meta2 = _invoke_estruturar_bedrock(
    bedrock=bedrock,
    model_id="test-model",
    system_prompt=system_retry,
    user_content="USER\n\nATENÇÃO: reescreva",
    max_tokens=4096,
    json_prefill="{",
)

assert isinstance(parsed1, dict) and "A" in parsed1
assert isinstance(parsed2, dict) and "A" in parsed2
assert meta1["input_tokens"] == 100 and meta1["output_tokens"] == 40
assert meta2["input_tokens"] == 110 and meta2["output_tokens"] == 45

# Mesmo system_prompt nas duas invocações (candidatos idênticos).
call1 = json.loads(bedrock.invoke_model.call_args_list[0].kwargs["body"])
call2 = json.loads(bedrock.invoke_model.call_args_list[1].kwargs["body"])
assert call1["system"] == call2["system"] == system_prompt
assert call1["system"] == call2["system"]

total_in = _sum_optional_ints([meta1.get("input_tokens"), meta2.get("input_tokens")])
total_out = _sum_optional_ints([meta1.get("output_tokens"), meta2.get("output_tokens")])
assert total_in == 210
assert total_out == 85
assert _sum_optional_ints(
    [meta1.get("bedrock_latency_ms"), meta2.get("bedrock_latency_ms")]
) is not None

print("OK test_wizard_retry_contract")
