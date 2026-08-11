"""Testes da instrumentação do wizard — não depende de AWS."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from prompts.inov_ativas import (  # noqa: E402
    build_estruturar_system_prompt,
    medir_componentes_entrada_prompt,
)
from wizard_routes import (  # noqa: E402
    _extrair_usage_bedrock,
    _invoke_estruturar_bedrock,
    _log_wizard_ai_metrics,
    _sum_optional_ints,
)


# --- usage ausente / parcial não quebra ---
assert _extrair_usage_bedrock({}) == {
    "input_tokens": None,
    "output_tokens": None,
}
assert _extrair_usage_bedrock({"usage": None}) == {
    "input_tokens": None,
    "output_tokens": None,
}
assert _extrair_usage_bedrock({"usage": {"input_tokens": 10}}) == {
    "input_tokens": 10,
    "output_tokens": None,
}
u = _extrair_usage_bedrock(
    {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 40,
            "cache_read_input_tokens": 5,
        }
    }
)
assert u["input_tokens"] == 100
assert u["output_tokens"] == 40
assert u["cache_read_input_tokens"] == 5

assert _sum_optional_ints([None, None]) is None
assert _sum_optional_ints([10, None, 5]) == 15


# --- medir componentes não altera o system prompt ---
bloco = "- (estilo) Engajamento: turma dispersa precisa de papéis claros."
sys1 = build_estruturar_system_prompt(bloco)
sys2 = build_estruturar_system_prompt(bloco)
assert sys1 == sys2
partes = medir_componentes_entrada_prompt(
    bloco,
    system_prompt=sys1,
    user_content="PROBLEMA\n\nx\n",
    ancoras_count=1,
)
assert partes["system_total_chars"] == len(sys1)
assert partes["system_catalogo_chars"] > 0
assert partes["system_ancoras_chars"] == len(bloco)
assert partes["user_content_chars"] == len("PROBLEMA\n\nx\n")
# catálogo é componente de entrada — não precisa somar exatamente ao system
assert partes["system_catalogo_chars"] < partes["system_total_chars"]


# --- invoke: body inalterado + parse ok sem usage ---
class _Body:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw


bedrock = MagicMock()
bedrock.invoke_model.return_value = {
    "body": _Body(
        {
            "stop_reason": "end_turn",
            "content": [{"text": '"trecho_relato_usado":"x","causas":[],"A":{},"B":{},"C":{}}'}],
            # sem "usage"
        }
    )
}
parsed, meta = _invoke_estruturar_bedrock(
    bedrock=bedrock,
    model_id="test-model",
    system_prompt="SYSTEM",
    user_content="USER",
    max_tokens=4096,
    json_prefill="{",
)
assert isinstance(parsed, dict)
assert "A" in parsed
assert meta.get("input_tokens") is None
assert meta.get("output_tokens") is None
assert meta.get("bedrock_latency_ms") is not None
assert meta.get("max_tokens_config") == 4096

call_kwargs = bedrock.invoke_model.call_args.kwargs
body = json.loads(call_kwargs["body"])
assert body["system"] == "SYSTEM"
assert body["messages"][0]["content"] == "USER"
assert body["messages"][1]["content"] == "{"
assert body["max_tokens"] == 4096
assert body["temperature"] == 0.2


# --- log de métricas não inclui texto sensível ---
buf = io.StringIO()
old = sys.stderr
sys.stderr = buf
try:
    _log_wizard_ai_metrics(
        request_id="abc123",
        attempt=1,
        meta={"input_tokens": 12, "output_tokens": 3, "bedrock_latency_ms": 100.0},
        partes={
            "system_total_chars": 5000,
            "system_catalogo_chars": 2000,
            "system_ancoras_chars": 100,
            "ancoras_count": 2,
            "system_diretrizes_chars": 0,
            "system_obrigatoria_chars": 0,
            "user_content_chars": 200,
        },
        matcher_top_ids="agil_x,dia_y",
        matcher_top_scores="9,7",
    )
finally:
    sys.stderr = old
logged = buf.getvalue()
assert "wizard_ai_metrics" in logged
assert "request_id=abc123" in logged
assert "input_tokens=12" in logged
assert "SYSTEM" not in logged
assert "USER" not in logged
assert "turma dispersa" not in logged


# --- script diagnóstico importa e monta sem Bedrock ---
import importlib.util  # noqa: E402

_diag_path = Path(__file__).resolve().parent / "diagnosticar_wizard_prompt.py"
_spec = importlib.util.spec_from_file_location("diagnosticar_wizard_prompt", _diag_path)
_diag = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_diag)

for nome, factory in _diag.CENARIOS.items():
    m = _diag._montar_cenario(factory())
    assert m["partes"]["system_total_chars"] > 0
    assert m["partes"]["system_catalogo_chars"] > 0
    assert m["partes"]["user_content_chars"] > 0
    assert len(m["ranking"]) == 5

curto = _diag._montar_cenario(_diag.CENARIOS["curto"]())
medio = _diag._montar_cenario(_diag.CENARIOS["medio"]())
longo = _diag._montar_cenario(_diag.CENARIOS["longo"]())
assert curto["partes"]["user_content_chars"] < medio["partes"]["user_content_chars"]
assert medio["partes"]["user_content_chars"] < longo["partes"]["user_content_chars"]
# faixas aproximadas pedidas (relato+contexto sintéticos)
medio_chars = len(medio["dados"]["problema"]) + len(medio["dados"]["contexto"])
longo_chars = len(longo["dados"]["problema"]) + len(longo["dados"]["contexto"])
assert 800 <= medio_chars <= 2500, medio_chars
assert 3500 <= longo_chars <= 6000, longo_chars

print("OK test_wizard_ai_metrics")
