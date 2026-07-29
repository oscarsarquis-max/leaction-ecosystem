"""Fila de módulos do prompt_cursor a partir de build_order do SDD."""

from __future__ import annotations

from typing import Any, Optional


VALID_STATUSES = frozenset({"liberado", "pendente", "entregue"})
VALID_CAMADAS = frozenset({"backend", "frontend", "shared"})


def _normalize_camada(raw: Any, *, modulo: str, escopo: str) -> str:
    camada = str(raw or "").strip().lower()
    if camada in VALID_CAMADAS:
        return camada
    blob = f"{modulo} {escopo}".lower()
    if any(
        tok in blob
        for tok in ("frontend", "front-end", "-ui", "player", "spa", "portal", "webapp")
    ):
        return "frontend"
    if "shared" in blob or "common" in blob or "lib-" in blob:
        return "shared"
    return "backend"


def normalize_build_order(raw: Any) -> list[dict[str, Any]]:
    """Normaliza lista build_order do SDD."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        modulo = str(
            item.get("modulo") or item.get("module") or item.get("name") or ""
        ).strip()
        if not modulo or modulo.lower() in seen:
            continue
        seen.add(modulo.lower())
        deps_raw = item.get("depende_de") or item.get("depends_on") or item.get("deps") or []
        if isinstance(deps_raw, str):
            deps = [d.strip() for d in deps_raw.split(",") if d.strip()]
        elif isinstance(deps_raw, list):
            deps = [str(d).strip() for d in deps_raw if str(d).strip()]
        else:
            deps = []
        # remove self-deps
        deps = [d for d in deps if d.lower() != modulo.lower()]
        escopo = str(item.get("escopo") or item.get("scope") or "").strip()
        camada = _normalize_camada(
            item.get("camada") or item.get("layer") or item.get("tier"),
            modulo=modulo,
            escopo=escopo,
        )
        out.append(
            {
                "modulo": modulo,
                "depende_de": deps,
                "escopo": escopo,
                "camada": camada,
            }
        )
    return out


def _deps_satisfied(
    depende_de: list[str],
    status_by_mod: dict[str, str],
    known: set[str],
) -> bool:
    for dep in depende_de:
        key = dep.strip()
        if not key:
            continue
        # dependência fora da fila: trata como satisfeita
        if key not in known and key.lower() not in {k.lower() for k in known}:
            continue
        # resolve case-insensitive
        matched = None
        for name in known:
            if name.lower() == key.lower():
                matched = name
                break
        if matched is None:
            continue
        if status_by_mod.get(matched) != "entregue":
            return False
    return True


def compute_statuses(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Recalcula liberado/pendente a partir de entregue + depende_de.
    Módulos já entregue permanecem entregue.
    """
    known = {str(i.get("modulo") or "") for i in items if i.get("modulo")}
    status_by_mod = {
        str(i.get("modulo")): str(i.get("status") or "pendente")
        for i in items
        if i.get("modulo")
    }

    result: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        modulo = str(row.get("modulo") or "")
        current = status_by_mod.get(modulo, "pendente")
        if current == "entregue":
            row["status"] = "entregue"
        else:
            deps = row.get("depende_de") or []
            if not isinstance(deps, list):
                deps = []
            if _deps_satisfied([str(d) for d in deps], status_by_mod, known):
                row["status"] = "liberado"
            else:
                row["status"] = "pendente"
        result.append(row)
    return result


def build_initial_queue(
    build_order: list[dict[str, Any]],
    prompts_by_module: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Monta fila inicial com status calculado e prompts opcionais."""
    prompts_by_module = prompts_by_module or {}
    items: list[dict[str, Any]] = []
    for entry in normalize_build_order(build_order):
        modulo = entry["modulo"]
        items.append(
            {
                "modulo": modulo,
                "depende_de": list(entry.get("depende_de") or []),
                "escopo": entry.get("escopo") or "",
                "camada": entry.get("camada") or "backend",
                "prompt": str(prompts_by_module.get(modulo) or "").strip(),
                "status": "pendente",
            }
        )
    return compute_statuses(items)


def mark_module_entregue(
    queue: list[dict[str, Any]],
    modulo: str,
) -> list[dict[str, Any]]:
    """Marca módulo como entregue e libera próximos cujas deps foram satisfeitas."""
    if not isinstance(queue, list):
        raise ValueError("module_prompts inválido")
    target = str(modulo or "").strip()
    if not target:
        raise ValueError("modulo obrigatório")

    found = False
    updated: list[dict[str, Any]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        name = str(row.get("modulo") or "")
        if name.lower() == target.lower():
            found = True
            if row.get("status") != "liberado" and row.get("status") != "entregue":
                raise ValueError(
                    f"Módulo '{name}' não está liberado (status={row.get('status')})"
                )
            row["status"] = "entregue"
        updated.append(row)

    if not found:
        raise ValueError(f"Módulo não encontrado na fila: {target}")

    return compute_statuses(updated)


def extract_build_order_from_inputs(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Procura build_order nos artefatos de depends_on (SDD)."""
    for payload in (inputs or {}).values():
        if not isinstance(payload, dict):
            continue
        order = normalize_build_order(payload.get("build_order"))
        if order:
            return order
        nested = payload.get("artifact_data")
        if isinstance(nested, dict):
            order = normalize_build_order(nested.get("build_order"))
            if order:
                return order
    return []


def locate_module_queue(artifact: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Retorna (container, lista module_prompts).
    container é o dict que deve receber a lista atualizada.
    """
    if not isinstance(artifact, dict):
        raise ValueError("artefato inválido")
    if isinstance(artifact.get("module_prompts"), list):
        return artifact, artifact["module_prompts"]
    nested = artifact.get("artifact_data")
    if isinstance(nested, dict) and isinstance(nested.get("module_prompts"), list):
        return nested, nested["module_prompts"]
    raise ValueError("Artefato sem fila module_prompts")
