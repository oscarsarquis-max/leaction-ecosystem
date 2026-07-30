"""Tradução de schemas agnósticos (dict) → types.Schema do Google GenAI."""

from __future__ import annotations

from typing import Any, Optional

from google.genai import types

_TYPE_MAP = {
    "OBJECT": types.Type.OBJECT,
    "object": types.Type.OBJECT,
    "ARRAY": types.Type.ARRAY,
    "array": types.Type.ARRAY,
    "STRING": types.Type.STRING,
    "string": types.Type.STRING,
    "NUMBER": types.Type.NUMBER,
    "number": types.Type.NUMBER,
    "INTEGER": types.Type.INTEGER,
    "integer": types.Type.INTEGER,
    "BOOLEAN": types.Type.BOOLEAN,
    "boolean": types.Type.BOOLEAN,
}


def is_genai_schema(value: Any) -> bool:
    """True se já for um objeto Schema do SDK Google."""
    return value is not None and hasattr(value, "type") and not isinstance(value, dict)


def dict_to_genai_schema(schema: Any) -> Any:
    """Converte dict JSON-Schema-like / agnóstico em ``types.Schema``.

    Formato esperado (exemplo)::

        {
          "type": "OBJECT",
          "properties": {"campo": {"type": "STRING"}},
          "required": ["campo"],
          "enum": ["a", "b"],  # opcional
          "items": {"type": "STRING"},  # para ARRAY
        }

    Se ``schema`` já for ``types.Schema``, devolve como está.
    """
    if schema is None:
        return None
    if is_genai_schema(schema):
        return schema
    if not isinstance(schema, dict):
        raise TypeError(
            f"response_schema deve ser dict ou types.Schema, recebeu {type(schema)!r}"
        )

    raw_type = schema.get("type", "OBJECT")
    if isinstance(raw_type, types.Type):
        type_enum = raw_type
    else:
        type_enum = _TYPE_MAP.get(str(raw_type), types.Type.OBJECT)

    kwargs: dict[str, Any] = {"type": type_enum}

    props = schema.get("properties")
    if isinstance(props, dict) and props:
        kwargs["properties"] = {
            str(key): dict_to_genai_schema(value) for key, value in props.items()
        }

    items = schema.get("items")
    if items is not None:
        kwargs["items"] = dict_to_genai_schema(items)

    required = schema.get("required")
    if isinstance(required, list) and required:
        kwargs["required"] = [str(item) for item in required]

    enum_vals = schema.get("enum")
    if isinstance(enum_vals, list) and enum_vals:
        kwargs["enum"] = list(enum_vals)

    return types.Schema(**kwargs)


def to_provider_schema(schema: Any) -> Any:
    """Normaliza schema para o GoogleProvider (dict → Schema)."""
    if schema is None:
        return None
    if is_genai_schema(schema):
        return schema
    return dict_to_genai_schema(schema)
