"""Comparação genérica campo-a-campo para campos_copia_literal do schema_config.

Reusa a lógica literal de passos (passos_compare) e agrega ratios por campo.
"""

from __future__ import annotations

from typing import Any, Optional

from services.crystal_ball.passos_compare import (
    compare_passos,
    extract_passos_from_artifact,
    _norm_text,
)


def _extract_field_value(artifact: Any, campo: str) -> Any:
    if not isinstance(artifact, dict):
        return None
    if campo in artifact:
        return artifact.get(campo)
    inner = artifact.get("artifact_data")
    if isinstance(inner, dict) and campo in inner:
        return inner.get(campo)
    return None


def compare_texto(generated: Any, reference: Any) -> dict[str, Any]:
    g = _norm_text(generated)
    r = _norm_text(reference)
    identical = bool(r) and g == r
    return {
        "tipo": "texto",
        "identical": identical,
        "identical_ratio": 1.0 if identical else (0.0 if r else None),
        "gerado": str(generated or ""),
        "referencia": str(reference or ""),
    }


def compare_literal_fields(
    *,
    generated_artifact: Any,
    reference_record: dict[str, Any],
    schema_config: dict[str, Any],
) -> dict[str, Any]:
    """Compara todos os campos_copia_literal do schema.

    Retorno estável e comparável entre simulação e resultado real.
    """
    specs = schema_config.get("campos_copia_literal") or []
    nota_por_campo: dict[str, Any] = {}
    ratios: list[float] = []

    for spec in specs:
        if not isinstance(spec, dict):
            continue
        campo = str(spec.get("campo") or "").strip()
        if not campo:
            continue
        tipo = str(spec.get("tipo") or "texto").strip()

        if tipo == "lista_passos" or campo == "passos":
            gen = extract_passos_from_artifact(generated_artifact)
            ref = reference_record.get("passos")
            if not isinstance(ref, list):
                ref = []
            cmp_ = compare_passos(gen, ref)
            ratio = cmp_.get("identical_ratio")
            if isinstance(ratio, (int, float)):
                ratios.append(float(ratio))
            # breakdown por subcampo (titulo≈imperativo, descricao≈descricao_base)
            n_ref = int(cmp_.get("n_referencia") or 0) or 1
            nota_por_campo[campo] = {
                **cmp_,
                "campo": campo,
                "tipo": "lista_passos",
                "subcampos": {
                    "imperativo": {
                        "identical_ratio": (
                            (cmp_.get("titulo_identical_count") or 0) / n_ref
                            if cmp_.get("n_referencia")
                            else None
                        )
                    },
                    "descricao_base": {
                        "identical_ratio": (
                            (cmp_.get("descricao_identical_count") or 0) / n_ref
                            if cmp_.get("n_referencia")
                            else None
                        )
                    },
                },
            }
            continue

        gen_val = _extract_field_value(generated_artifact, campo)
        ref_val = reference_record.get(campo)
        cmp_txt = compare_texto(gen_val, ref_val)
        if isinstance(cmp_txt.get("identical_ratio"), (int, float)):
            ratios.append(float(cmp_txt["identical_ratio"]))
        nota_por_campo[campo] = {**cmp_txt, "campo": campo}

    nota_agregada: Optional[float] = None
    if ratios:
        nota_agregada = sum(ratios) / len(ratios)

    return {
        "identical_ratio": nota_agregada,
        "nota_agregada": nota_agregada,
        "nota_por_campo": nota_por_campo,
        "n_campos": len(nota_por_campo),
    }
