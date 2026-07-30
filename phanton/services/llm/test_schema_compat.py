"""Teste de tradução dict → types.Schema (Google)."""

from __future__ import annotations

from google.genai import types

from services.llm.schema_compat import dict_to_genai_schema, to_provider_schema


def test_dict_to_genai_schema_object_with_array():
    schema = {
        "type": "OBJECT",
        "properties": {
            "items": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "camada": {
                "type": "STRING",
                "enum": ["backend", "frontend"],
            },
        },
        "required": ["items"],
    }
    converted = dict_to_genai_schema(schema)
    assert converted.type == types.Type.OBJECT
    assert "items" in converted.properties
    assert converted.properties["items"].type == types.Type.ARRAY
    assert converted.properties["camada"].enum == ["backend", "frontend"]
    assert list(converted.required) == ["items"]


def test_to_provider_schema_passthrough_existing():
    original = types.Schema(type=types.Type.STRING)
    assert to_provider_schema(original) is original
