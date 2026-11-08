"""Modelo falso para teste e para a demonstração local. Não chama a rede."""

from __future__ import annotations

from app.domain.gigio.gateway import ChatRequest, ChatResponse


class FakeGateway:
    def __init__(self, script: list[ChatResponse] | None = None) -> None:
        self.calls: list[ChatRequest] = []
        self.script = list(script or [])

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        if self.script:
            return self.script.pop(0)
        texto = " ".join(turn.text for turn in request.messages)
        return ChatResponse(
            text="",
            tool_use=[{"id": "fake-1", "name": "sugerir_receita", "input": _canela(texto)}],
            stop_reason="tool_use",
            input_tokens=20,
            output_tokens=80,
            latency_ms=4,
            provider="fake",
            model_id="fake",
            region="local",
        )


def _canela(texto: str) -> dict:
    """Uma sugestão típica de pão de canela. As linhas fixas são corrigidas pelo servidor."""
    return {
        "linhas": [
            {
                "ingrediente": "Farinha de trigo",
                "quantidade_g": 500,
                "percentual": 100,
                "faixa_min": 100,
                "faixa_max": 100,
                "confianca": "alta",
                "motivo": "A farinha da massa vale 100 %.",
            },
            {
                "ingrediente": "Água",
                "quantidade_g": 300,
                "percentual": 60,
                "faixa_min": 58,
                "faixa_max": 62,
                "confianca": "alta",
                "motivo": "Hidratação, padrão da casa.",
            },
            {
                "ingrediente": "Açúcar",
                "quantidade_g": 50,
                "percentual": 10,
                "faixa_min": 8,
                "faixa_max": 15,
                "confianca": "media",
                "motivo": "Doçura típica de pão de canela.",
            },
            {
                "ingrediente": "Canela",
                "quantidade_g": 8,
                "percentual": 1.6,
                "faixa_min": 1,
                "faixa_max": 3,
                "confianca": "baixa",
                "motivo": "Inclusão. A faixa é típica; o padeiro confere.",
            },
            {
                "ingrediente": "Manteiga",
                "quantidade_g": 40,
                "percentual": 8,
                "faixa_min": 5,
                "faixa_max": 12,
                "confianca": "baixa",
                "motivo": "Inclusão gordurosa, sem medida exata.",
            },
        ],
        "rendimento_g": 900,
        "perda_pct": 10,
        "modo_de_fazer": [
            "Misture a farinha com a água da hidratação.",
            "Incorpore o açúcar e a manteiga.",
            "Polvilhe a canela na faixa, sem tratar o número como exato.",
        ],
        "observacoes": "",
        "substituicoes": (
            [
                {
                    "ingrediente": "Farinha de trigo integral",
                    "percentual": 15,
                    "motivo": "Meio integral: 15 % da farinha da base, no lugar da farinha branca.",
                    "confianca": "media",
                }
            ]
            if "integral" in texto.lower()
            else []
        ),
    }
