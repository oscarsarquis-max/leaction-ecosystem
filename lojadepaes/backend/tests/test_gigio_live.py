"""Validação mínima contra Bedrock do Chamelleon. Desligada por padrão."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from app.core.config import Settings, get_settings
from app.db.session import reset_engine
from app.domain.gigio.bedrock import BedrockGigioGateway
from app.domain.gigio.gateway import ChatRequest, ChatTurn
from app.domain.gigio.service import chat
from app.domain.gigio.settings import (
    CHAMELLEON_BEDROCK_MODEL_ID,
    CHAMELLEON_BEDROCK_REGION,
    load_gigio_model_settings,
)
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

EXACT_CULINARY = (
    "Quero comprar um pão rústico de fermentação natural. Com o que combina na hora de servir?"
)


def _load_chamelleon_runtime_env() -> dict[str, str]:
    """Carrega só identidade AWS do Chamelleon no processo. Não imprime valores."""
    loaded: dict[str, str] = {}
    env_path = Path(r"C:\Projetos\chamelleon\.env")
    if not env_path.is_file():
        return loaded
    wanted = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "BEDROCK_REGION",
        "BEDROCK_MODEL_ID",
        "BEDROCK_SSL_VERIFY",
    }
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in wanted:
            continue
        os.environ.setdefault(key, value.strip().strip("'").strip('"'))
        loaded[key] = "set"
    return loaded


def _live_ready() -> bool:
    if os.getenv("LOJADEPAES_GIGIO_LIVE_TEST") != "1":
        return False
    _load_chamelleon_runtime_env()
    return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))


@pytest.mark.skipif(not _live_ready(), reason="live bedrock off or identity missing")
def test_live_invoke_model_two_generic_questions(db: Session) -> None:
    _load_chamelleon_runtime_env()
    model = load_gigio_model_settings(Settings())
    assert model.region == CHAMELLEON_BEDROCK_REGION
    assert model.model_id == CHAMELLEON_BEDROCK_MODEL_ID
    gateway = BedrockGigioGateway(settings=model)

    culinary = gateway.complete(
        ChatRequest(
            system_prompt=(
                "Você é o Gigio, assistente virtual de A Loja. Responda curto em português brasileiro. "
                "Catálogo de teste: Pão da casa 500 g, publicado. Não invente preço nem estoque. "
                "Não cite dados pessoais."
            ),
            messages=[ChatTurn(role="user", text="Uma ideia simples com o Pão da casa da vitrine de teste.")],
            tools=[],
            max_tokens=180,
        )
    )
    assert culinary.provider == "bedrock"
    assert len(culinary.text) > 20
    assert culinary.model_id == CHAMELLEON_BEDROCK_MODEL_ID
    lowered = culinary.text.casefold()
    assert "glúten" not in lowered or "não" in lowered

    process = gateway.complete(
        ChatRequest(
            system_prompt=(
                "Você é o Gigio. Distinga fermentação (como a massa fermenta) de sova (como é trabalhada). "
                "Não são opostos. Não afirme que todo pão sovado usa fermento comercial. Sem conselho médico."
            ),
            messages=[
                ChatTurn(
                    role="user",
                    text="Qual a diferença entre pão de fermentação natural e pão sovado?",
                )
            ],
            tools=[],
            max_tokens=220,
        )
    )
    process_text = process.text.casefold()
    assert len(process.text) > 40
    assert "ferment" in process_text
    assert "sov" in process_text
    assert process.stop_reason in {"end_turn", "max_tokens", "stop_sequence"}
    evidence = Path(__file__).resolve().parents[2] / "readme" / "evidence" / "prompt-56" / "live-bedrock.md"
    evidence.write_text(
        "\n".join(
            [
                "# Chamelleon Bedrock — validação mínima (56B)",
                "",
                "- API: `invoke_model` (não Converse)",
                f"- Região: `{culinary.region}`",
                f"- Modelo: `{culinary.model_id}`",
                f"- Chamada culinária: {culinary.latency_ms} ms, tokens in/out {culinary.input_tokens}/{culinary.output_tokens}, {len(culinary.text)} chars",
                f"- Chamada fermentação/sova: {process.latency_ms} ms, tokens in/out {process.input_tokens}/{process.output_tokens}, {len(process.text)} chars",
                "- Sem dados de cliente, SES, pedido ou Pix.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    del db


@pytest.mark.skipif(os.getenv("LOJADEPAES_GIGIO_LIVE_TEST") != "1", reason="live bedrock off")
def test_gigio_live_status_reports_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    _load_chamelleon_runtime_env()
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "bedrock")
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        status = client.get("/api/v1/gigio/status").json()
        assert status["enabled"] is True
        assert status["ready"] is True
        assert status["provider"] == "bedrock"
        assert status["region"] == CHAMELLEON_BEDROCK_REGION
        assert status["model_family"] == "claude"
    get_settings.cache_clear()
    reset_engine()


@pytest.mark.skipif(not _live_ready(), reason="live bedrock off or identity missing")
def test_live_chat_exact_culinary_question(db: Session) -> None:
    _load_chamelleon_runtime_env()
    from app.domain.recipe_bases import create_recipe_base
    from app.models.enums import EditorialStatus
    from app.models.products import Product, ProductVariant
    from app.models.week_recipes import WeekRecipe

    base = create_recipe_base(db, code="rb-live57", name="Base")
    product = Product(
        name="Pão Fermentação Natural de Trigo",
        slug="pao-fermentacao-natural-trigo-live",
        short_description="crosta firme",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    db.add(
        ProductVariant(
            product_id=product.id,
            display_name="500 g",
            presentation_type="weight",
            net_weight_grams=500,
            physical_units=1,
            price_cents=7000,
            currency="BRL",
            is_active=True,
        )
    )
    db.add(
        WeekRecipe(
            title="Pan con Tomate",
            slug="pan-con-tomate-live",
            summary="Toste o pão e esfregue tomate.",
            editorial_status=EditorialStatus.PUBLISHED.value,
            is_featured=True,
            method_text="Toste e esfregue o tomate.",
        )
    )
    db.commit()
    settings = Settings(gigio_enabled=True, gigio_gateway="bedrock", bedrock_max_tokens=400)
    first = chat(
        db,
        settings,
        messages=[{"role": "user", "content": EXACT_CULINARY}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
    )
    assert first["unavailable"] is False
    assert "longa demais" not in first["reply"]
    assert len(first["reply"]) > 40
    follow = chat(
        db,
        settings,
        messages=[
            {"role": "user", "content": EXACT_CULINARY},
            {"role": "assistant", "content": first["reply"]},
            {"role": "user", "content": "E uma opção sem queijo?"},
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
    )
    assert follow["unavailable"] is False
    lowered = follow["reply"].casefold()
    assert "sem glúten" not in lowered
    assert "livre de alerg" not in lowered
