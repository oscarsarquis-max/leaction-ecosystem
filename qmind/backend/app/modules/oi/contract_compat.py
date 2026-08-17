"""Structural compatibility between Core wire DTOs and OI public JSON Schemas v1.

OI owns the public contract; Core mirrors DTOs locally. This module compares shapes
without importing ``qmind_oi`` at runtime.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.modules.oi.schemas import OrganizationContextInput, OrganizationalInsights

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OI_SCHEMAS_DIR = BACKEND_ROOT / "contracts" / "oi" / "v1"

CONTRACTS: tuple[tuple[str, type[Any], str], ...] = (
    (
        "OrganizationContextInput",
        OrganizationContextInput,
        "organization-context-input.schema.json",
    ),
    (
        "OrganizationalInsights",
        OrganizationalInsights,
        "organizational-insights.schema.json",
    ),
)


class CompatibilityIssue:
    def __init__(self, contract: str, message: str) -> None:
        self.contract = contract
        self.message = message

    def __str__(self) -> str:
        return f"{self.contract}: {self.message}"


def core_schema_for(model: type[Any]) -> dict[str, Any]:
    return model.model_json_schema(mode="serialization")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_oi_schemas_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    import os

    env = os.environ.get("QMIND_OI_SCHEMAS_DIR", "").strip()
    if env:
        return Path(env)
    sibling = BACKEND_ROOT.parent.parent / "qmind-oi" / "schemas" / "v1"
    # Prefer committed Core snapshot for deterministic CI; sibling only if snapshot missing.
    if DEFAULT_OI_SCHEMAS_DIR.is_dir() and any(DEFAULT_OI_SCHEMAS_DIR.glob("*.json")):
        return DEFAULT_OI_SCHEMAS_DIR
    if sibling.is_dir():
        return sibling
    return DEFAULT_OI_SCHEMAS_DIR


def _deref(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"unsupported $ref {ref!r}")
    name = ref.split("/")[-1]
    defs = root.get("$defs") or root.get("definitions") or {}
    target = defs.get(name)
    if not isinstance(target, dict):
        raise ValueError(f"missing $defs entry for {name!r}")
    return target


def _strip_null_union(node: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return (non-null branch, nullable)."""
    if "anyOf" in node or "oneOf" in node:
        key = "anyOf" if "anyOf" in node else "oneOf"
        branches = list(node[key])
        non_null = [b for b in branches if not (isinstance(b, dict) and b.get("type") == "null")]
        nullable = len(non_null) < len(branches)
        if len(non_null) == 1 and isinstance(non_null[0], dict):
            return non_null[0], nullable
        if len(non_null) == 0:
            return {"type": "null"}, True
        # Keep multi-branch as opaque for type compare
        return {key: non_null}, nullable
    return node, False


def _base_types(node: dict[str, Any], root: dict[str, Any]) -> set[str]:
    node = _deref(node, root)
    node, _ = _strip_null_union(node)
    node = _deref(node, root)
    if "enum" in node:
        return {"enum"}
    if "const" in node:
        return {"const"}
    t = node.get("type")
    if isinstance(t, list):
        return {x for x in t if x != "null"}
    if isinstance(t, str):
        return {t}
    if "anyOf" in node or "oneOf" in node:
        return {"union"}
    if "$ref" in node:
        return _base_types(node, root)
    if "properties" in node:
        return {"object"}
    return {"unknown"}


def _enum_values(node: dict[str, Any], root: dict[str, Any]) -> set[Any] | None:
    node = _deref(node, root)
    node, _ = _strip_null_union(node)
    node = _deref(node, root)
    if "enum" in node and isinstance(node["enum"], list):
        return set(node["enum"])
    return None


def _required(node: dict[str, Any]) -> set[str]:
    req = node.get("required") or []
    return set(req) if isinstance(req, list) else set()


def _props(node: dict[str, Any]) -> dict[str, Any]:
    props = node.get("properties") or {}
    return props if isinstance(props, dict) else {}


def _additional_allowed(node: dict[str, Any]) -> bool | None:
    if "additionalProperties" not in node:
        return None
    ap = node["additionalProperties"]
    if ap is False:
        return False
    if ap is True:
        return True
    return None


def _compare_nodes(
    *,
    contract: str,
    path: str,
    oi_node: dict[str, Any],
    core_node: dict[str, Any],
    oi_root: dict[str, Any],
    core_root: dict[str, Any],
    issues: list[CompatibilityIssue],
) -> None:
    oi = _deref(oi_node, oi_root)
    core = _deref(core_node, core_root)
    oi, oi_null = _strip_null_union(oi)
    core, core_null = _strip_null_union(core)
    oi = _deref(oi, oi_root)
    core = _deref(core, core_root)

    if oi_null != core_null:
        issues.append(
            CompatibilityIssue(
                contract,
                f'field "{path}" nullability mismatch (OI nullable={oi_null}, Core nullable={core_null})',
            )
        )

    oi_types = _base_types(oi, oi_root)
    core_types = _base_types(core, core_root)
    # enum vs string: treat enum as compatible with string when values checked
    if oi_types == {"enum"} and "string" in core_types:
        oi_types = {"string"}
    if core_types == {"enum"} and "string" in oi_types:
        core_types = {"string"}
    if oi_types != core_types and not (
        oi_types <= {"string", "enum"} and core_types <= {"string", "enum"}
    ):
        issues.append(
            CompatibilityIssue(
                contract,
                f'field "{path}" type mismatch (OI={sorted(oi_types)}, Core={sorted(core_types)})',
            )
        )

    oi_enum = _enum_values(oi, oi_root)
    core_enum = _enum_values(core, core_root)
    if oi_enum is not None and core_enum is not None and oi_enum != core_enum:
        missing = sorted(oi_enum - core_enum, key=str)
        extra = sorted(core_enum - oi_enum, key=str)
        detail = []
        if missing:
            detail.append(f"missing in Core={missing}")
        if extra:
            detail.append(f"extra in Core={extra}")
        issues.append(
            CompatibilityIssue(
                contract,
                f'field "{path}" enum incompatible ({"; ".join(detail)})',
            )
        )
    elif oi_enum is not None and core_enum is None and "string" not in core_types:
        issues.append(
            CompatibilityIssue(
                contract,
                f'field "{path}" enum missing in Core representation',
            )
        )

    oi_is_obj = "object" in _base_types(oi, oi_root) or bool(_props(oi))
    core_is_obj = "object" in _base_types(core, core_root) or bool(_props(core))
    if oi_is_obj and core_is_obj:
        oi_req = _required(oi)
        core_req = _required(core)
        for name in sorted(oi_req - core_req):
            issues.append(
                CompatibilityIssue(
                    contract,
                    f'required field "{path + "." if path else ""}{name}" missing in Core representation'
                    if path
                    else f'required field "{name}" missing in Core representation',
                )
            )
        for name in sorted(core_req - oi_req):
            issues.append(
                CompatibilityIssue(
                    contract,
                    f'required field "{path + "." if path else ""}{name}" missing in OI representation'
                    if path
                    else f'required field "{name}" missing in OI representation',
                )
            )

        oi_props = _props(oi)
        core_props = _props(core)
        for name in sorted(oi_props.keys() - core_props.keys()):
            issues.append(
                CompatibilityIssue(
                    contract,
                    f'field "{path + "." if path else ""}{name}" present in OI but missing in Core'
                    if path
                    else f'field "{name}" present in OI but missing in Core',
                )
            )
        for name in sorted(core_props.keys() - oi_props.keys()):
            issues.append(
                CompatibilityIssue(
                    contract,
                    f'field "{path + "." if path else ""}{name}" present in Core but missing in OI'
                    if path
                    else f'field "{name}" present in Core but missing in OI',
                )
            )

        oi_ap = _additional_allowed(oi)
        core_ap = _additional_allowed(core)
        if oi_ap is False and core_ap is True:
            issues.append(
                CompatibilityIssue(
                    contract,
                    f'field "{path or "<root>"}" additionalProperties: OI forbids extras, Core allows',
                )
            )

        for name in sorted(oi_props.keys() & core_props.keys()):
            child = f"{path}.{name}" if path else name
            oi_child = oi_props[name]
            core_child = core_props[name]
            if not isinstance(oi_child, dict) or not isinstance(core_child, dict):
                continue
            # arrays
            oi_c = _deref(oi_child, oi_root)
            core_c = _deref(core_child, core_root)
            oi_c, _ = _strip_null_union(oi_c)
            core_c, _ = _strip_null_union(core_c)
            oi_c = _deref(oi_c, oi_root)
            core_c = _deref(core_c, core_root)
            if oi_c.get("type") == "array" and core_c.get("type") == "array":
                oi_items = oi_c.get("items")
                core_items = core_c.get("items")
                if isinstance(oi_items, dict) and isinstance(core_items, dict):
                    _compare_nodes(
                        contract=contract,
                        path=f"{child}[]",
                        oi_node=oi_items,
                        core_node=core_items,
                        oi_root=oi_root,
                        core_root=core_root,
                        issues=issues,
                    )
                continue
            _compare_nodes(
                contract=contract,
                path=child,
                oi_node=oi_child,
                core_node=core_child,
                oi_root=oi_root,
                core_root=core_root,
                issues=issues,
            )


def compare_schemas(
    contract: str,
    oi_schema: dict[str, Any],
    core_schema: dict[str, Any],
) -> list[CompatibilityIssue]:
    issues: list[CompatibilityIssue] = []
    _compare_nodes(
        contract=contract,
        path="",
        oi_node=oi_schema,
        core_node=core_schema,
        oi_root=oi_schema,
        core_root=core_schema,
        issues=issues,
    )
    return issues


def check_contracts(*, oi_schemas_dir: Path | None = None) -> list[CompatibilityIssue]:
    schemas_dir = resolve_oi_schemas_dir(oi_schemas_dir)
    all_issues: list[CompatibilityIssue] = []
    for name, model, filename in CONTRACTS:
        path = schemas_dir / filename
        if not path.is_file():
            all_issues.append(
                CompatibilityIssue(name, f"OI schema file missing: {path}")
            )
            continue
        oi_schema = load_json(path)
        core_schema = core_schema_for(model)
        all_issues.extend(compare_schemas(name, oi_schema, core_schema))
    return all_issues


def assert_compatible(*, oi_schemas_dir: Path | None = None) -> None:
    issues = check_contracts(oi_schemas_dir=oi_schemas_dir)
    if issues:
        lines = "\n".join(f"  - {i}" for i in issues)
        raise AssertionError(f"Core <-> OI contract incompatibility:\n{lines}")


def irrelevant_metadata_only_diff_demo(schema: dict[str, Any]) -> dict[str, Any]:
    """Clone schema with noisy metadata changes (must remain compatible)."""
    out = copy.deepcopy(schema)
    out["title"] = "Totally Different Title"
    out["description"] = "noise"
    if "$defs" in out:
        for node in out["$defs"].values():
            if isinstance(node, dict):
                node["title"] = "x"
                node["description"] = "y"
    return out
