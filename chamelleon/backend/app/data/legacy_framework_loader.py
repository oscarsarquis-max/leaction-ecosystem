"""Estrutura metodológica PanelDX — leaf_dime × leaf_doma × leaf_bloc × leaf_derv."""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from urllib.parse import unquote, urlparse

from app.core.framework_definitions import (
    DOMAIN_NAMES_BY_KEY,
    FRAMEWORK_KNOWLEDGE,
    SECTOR_DIMENSION_TEMPLATE_KEY,
    UNIVERSAL_DIMENSION_KEYS,
    normalize_domain_key,
)
from app.core.sector_constants import SECTOR_LEGACY_DIME_ID
from app.data.legacy_quest_loader import LEGACY_DOMA_TO_KEY, LEGACY_DIME_TO_KEY

logger = logging.getLogger(__name__)

UNIVERSAL_LEGACY_DIME_IDS = (1, 2, 3, 5)

_LEGACY_DIME_KEY_TO_ID = {v: k for k, v in LEGACY_DIME_TO_KEY.items()}
_LEGACY_DOMAIN_KEY_TO_ID = {v: k for k, v in LEGACY_DOMA_TO_KEY.items()}


def _legacy_connect():
    database_url = os.getenv("LEGACY_QUEST_DATABASE_URL")
    if not database_url:
        return None

    try:
        import psycopg2
    except ImportError:
        return None

    parsed = urlparse(database_url)
    dbname = (parsed.path or "/LeAction_SysF").lstrip("/")
    if "?" in dbname:
        dbname = dbname.split("?", 1)[0]

    try:
        return psycopg2.connect(
            host=parsed.hostname or "127.0.0.1",
            port=parsed.port or 5432,
            dbname=dbname,
            user=unquote(parsed.username or "postgres"),
            password=unquote(parsed.password or ""),
            client_encoding="UTF8",
        )
    except Exception as exc:
        logger.warning("Conexão legado indisponível para leaf_bloc/leaf_derv: %s", exc)
        return None


def _parse_framework_knowledge_deliverable(markdown: str) -> dict[str, str]:
    text = (markdown or "").strip()
    title_match = re.search(r"####\s+(.+)", text)
    name = title_match.group(1).strip() if title_match else "Entregável"
    composition = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Composição:"):
            composition = stripped.replace("- Composição:", "", 1).strip()
            break
    body = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE).strip()
    return {
        "name_derv": name,
        "desc_derv": body,
        "derv_defi": name,
        "derv_comp": composition,
        "derv_metr": "",
    }


def _domain_blocks_from_knowledge(dim_data: dict[str, Any]) -> list[dict[str, Any]]:
    domains_out: list[dict[str, Any]] = []
    for domain_key, domain_data in (dim_data.get("dominios") or {}).items():
        canonical_key = normalize_domain_key(domain_key)
        blocks_out: list[dict[str, Any]] = []
        for block_name, block_md in (domain_data.get("blocos") or {}).items():
            deliverable = _parse_framework_knowledge_deliverable(block_md)
            blocks_out.append(
                {
                    "id_bloc": None,
                    "name_bloc": block_name,
                    "desc_bloc": deliverable["desc_derv"],
                    "level_bloc": len(blocks_out) + 1,
                    "quali_bloc": None,
                    "deliverables": [deliverable],
                }
            )
        domains_out.append(
            {
                "id_doma": _LEGACY_DOMAIN_KEY_TO_ID.get(canonical_key),
                "domain_key": canonical_key,
                "name_doma": domain_data.get("nome") or DOMAIN_NAMES_BY_KEY.get(canonical_key, ""),
                "desc_doma": None,
                "blocks": blocks_out,
            }
        )
    return domains_out


def load_la_template_methodology_structure() -> dict[str, Any]:
    """Dimensão LA (Aprendizagem em Ação) — template canônico substituído pelo setor."""
    la_data = FRAMEWORK_KNOWLEDGE.get(SECTOR_DIMENSION_TEMPLATE_KEY)
    if not la_data:
        return {
            "dimension_key": SECTOR_DIMENSION_TEMPLATE_KEY,
            "name_dime": "Aprendizagem em Ação (LA)",
            "desc_dime": None,
            "is_template": True,
            "domains": [],
        }
    return {
        "dimension_key": SECTOR_DIMENSION_TEMPLATE_KEY,
        "name_dime": la_data.get("nome", "Aprendizagem em Ação (LA)"),
        "desc_dime": (
            "Template metodológico canônico PanelDX — substituído pela 5ª dimensão setorial."
        ),
        "is_template": True,
        "domains": _domain_blocks_from_knowledge(la_data),
    }


def _leaf_blocks_from_sector_block(
    sector_block: dict[str, Any],
    la_domain_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Monta leaf_bloc/leaf_derv setoriais; usa template LA quando a IA não envia leaf_blocks."""
    leaf_blocks = sector_block.get("leaf_blocks")
    if isinstance(leaf_blocks, list) and leaf_blocks:
        blocks_out: list[dict[str, Any]] = []
        for index, raw in enumerate(leaf_blocks):
            if not isinstance(raw, dict):
                continue
            deliverables_in = raw.get("deliverables") or []
            deliverables_out: list[dict[str, Any]] = []
            for d_index, derv in enumerate(deliverables_in):
                if not isinstance(derv, dict):
                    continue
                deliverables_out.append(
                    {
                        "id_derv": None,
                        "name_derv": derv.get("name_derv") or derv.get("name") or "Entregável",
                        "desc_derv": derv.get("desc_derv") or derv.get("description") or "",
                        "derv_defi": derv.get("derv_defi") or derv.get("name_derv") or "",
                        "derv_comp": derv.get("derv_comp") or derv.get("composition") or "",
                        "derv_metr": derv.get("derv_metr") or "",
                    }
                )
            if not deliverables_out and raw.get("desc_bloc"):
                deliverables_out.append(
                    {
                        "id_derv": None,
                        "name_derv": raw.get("name_bloc") or "Entregável",
                        "desc_derv": raw.get("desc_bloc"),
                        "derv_defi": raw.get("name_bloc") or "",
                        "derv_comp": "",
                        "derv_metr": "",
                    }
                )
            blocks_out.append(
                {
                    "id_bloc": None,
                    "name_bloc": raw.get("name_bloc") or raw.get("block_name") or f"Bloco {index + 1}",
                    "desc_bloc": raw.get("desc_bloc") or raw.get("block_description"),
                    "level_bloc": index + 1,
                    "quali_bloc": None,
                    "deliverables": deliverables_out,
                }
            )
        if blocks_out:
            return blocks_out

    if la_domain_blocks:
        import copy

        customized = copy.deepcopy(la_domain_blocks)
        sector_name = (sector_block.get("block_name") or "").strip()
        sector_desc = (sector_block.get("block_description") or "").strip()
        if sector_name:
            customized[0]["name_bloc"] = sector_name
        if sector_desc:
            customized[0]["desc_bloc"] = sector_desc
            if customized[0].get("deliverables"):
                customized[0]["deliverables"][0]["desc_derv"] = sector_desc
        return customized

    sector_name = sector_block.get("block_name") or sector_block.get("domain_name") or "Bloco setorial"
    sector_desc = sector_block.get("block_description") or ""
    return [
        {
            "id_bloc": None,
            "name_bloc": sector_name,
            "desc_bloc": sector_desc,
            "level_bloc": 1,
            "quali_bloc": None,
            "deliverables": [
                {
                    "id_derv": None,
                    "name_derv": sector_name,
                    "desc_derv": sector_desc or sector_name,
                    "derv_defi": sector_name,
                    "derv_comp": "",
                    "derv_metr": "",
                }
            ],
        }
    ]


def _structure_from_framework_knowledge() -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []

    for dim_key in UNIVERSAL_DIMENSION_KEYS:
        dim_data = FRAMEWORK_KNOWLEDGE.get(dim_key)
        if not dim_data:
            continue

        domains_out: list[dict[str, Any]] = []
        for domain_key, domain_data in (dim_data.get("dominios") or {}).items():
            canonical_key = normalize_domain_key(domain_key)
            blocks_out: list[dict[str, Any]] = []
            for block_name, block_md in (domain_data.get("blocos") or {}).items():
                deliverable = _parse_framework_knowledge_deliverable(block_md)
                blocks_out.append(
                    {
                        "id_bloc": None,
                        "name_bloc": block_name,
                        "desc_bloc": deliverable["desc_derv"],
                        "level_bloc": len(blocks_out) + 1,
                        "quali_bloc": None,
                        "deliverables": [deliverable],
                    }
                )

            domains_out.append(
                {
                    "id_doma": _LEGACY_DOMAIN_KEY_TO_ID.get(canonical_key),
                    "domain_key": canonical_key,
                    "name_doma": domain_data.get("nome") or DOMAIN_NAMES_BY_KEY.get(canonical_key, ""),
                    "desc_doma": None,
                    "blocks": blocks_out,
                }
            )

        dimensions.append(
            {
                "id_dime": _LEGACY_DIME_KEY_TO_ID.get(dim_key),
                "dimension_key": dim_key,
                "name_dime": dim_data.get("nome", dim_key),
                "desc_dime": None,
                "code_dime": dim_key,
                "long_description": None,
                "domains": domains_out,
            }
        )

    return dimensions


def load_universal_methodology_from_legacy() -> list[dict[str, Any]] | None:
    conn = _legacy_connect()
    if not conn:
        return None

    try:
        from psycopg2.extras import RealDictCursor

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                dime.id_dime,
                dime.name_dime,
                dime.desc_dime,
                dime.code_dime,
                dime.long_description,
                doma.id_doma,
                doma.name_doma,
                doma.desc_doma,
                bloc.id_bloc,
                bloc.name_bloc,
                bloc.desc_bloc,
                bloc.level_bloc,
                bloc.quali_bloc,
                derv.id_derv,
                derv.name_derv,
                derv.desc_derv,
                derv.derv_defi,
                derv.derv_comp,
                derv.derv_metr
            FROM public.leaf_bloc bloc
            JOIN public.leaf_dime dime ON bloc.id_dime = dime.id_dime
            JOIN public.leaf_doma doma ON bloc.id_doma = doma.id_doma
            LEFT JOIN public.leaf_derv derv ON derv.id_bloc = bloc.id_bloc
            WHERE dime.id_dime = ANY(%s)
            ORDER BY dime.id_dime, doma.id_doma, bloc.level_bloc NULLS LAST, bloc.id_bloc, derv.id_derv
            """,
            (list(UNIVERSAL_LEGACY_DIME_IDS),),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        by_dim: dict[int, dict[str, Any]] = {}
        by_domain: dict[tuple[int, int], dict[str, Any]] = {}
        by_block: dict[int, dict[str, Any]] = {}

        for row in rows:
            id_dime = int(row["id_dime"])
            dim_key = LEGACY_DIME_TO_KEY.get(id_dime, (row.get("code_dime") or "XX").upper())

            dim = by_dim.setdefault(
                id_dime,
                {
                    "id_dime": id_dime,
                    "dimension_key": dim_key,
                    "name_dime": row["name_dime"],
                    "desc_dime": row.get("desc_dime"),
                    "code_dime": row.get("code_dime"),
                    "long_description": row.get("long_description"),
                    "domains": [],
                },
            )

            id_doma = int(row["id_doma"])
            domain_key = LEGACY_DOMA_TO_KEY.get(id_doma, f"dom{id_doma}")
            dom = by_domain.setdefault(
                (id_dime, id_doma),
                {
                    "id_doma": id_doma,
                    "domain_key": domain_key,
                    "name_doma": row["name_doma"],
                    "desc_doma": row.get("desc_doma"),
                    "blocks": [],
                },
            )
            if dom not in dim["domains"]:
                dim["domains"].append(dom)

            id_bloc = int(row["id_bloc"])
            bloc = by_block.setdefault(
                id_bloc,
                {
                    "id_bloc": id_bloc,
                    "name_bloc": row["name_bloc"],
                    "desc_bloc": row.get("desc_bloc"),
                    "level_bloc": row.get("level_bloc"),
                    "quali_bloc": row.get("quali_bloc"),
                    "deliverables": [],
                },
            )
            if not any(b.get("id_bloc") == id_bloc for b in dom["blocks"]):
                dom["blocks"].append(bloc)

            if row.get("id_derv"):
                deliverable = {
                    "id_derv": row["id_derv"],
                    "name_derv": row["name_derv"],
                    "desc_derv": row.get("desc_derv"),
                    "derv_defi": row.get("derv_defi"),
                    "derv_comp": row.get("derv_comp"),
                    "derv_metr": row.get("derv_metr"),
                }
                if not any(d.get("id_derv") == deliverable["id_derv"] for d in bloc["deliverables"]):
                    bloc["deliverables"].append(deliverable)

        return [by_dim[i] for i in sorted(by_dim)]
    except Exception as exc:
        logger.warning("Falha ao carregar leaf_bloc/leaf_derv: %s", exc)
        return None
    finally:
        conn.close()


def load_la_methodology_from_legacy() -> dict[str, Any] | None:
    """Dimensão LA completa com leaf_bloc/leaf_derv do banco PanelDX."""
    conn = _legacy_connect()
    if not conn:
        return None

    try:
        from psycopg2.extras import RealDictCursor

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                dime.id_dime, dime.name_dime, dime.desc_dime, dime.code_dime,
                doma.id_doma, doma.name_doma, doma.desc_doma,
                bloc.id_bloc, bloc.name_bloc, bloc.desc_bloc, bloc.level_bloc, bloc.quali_bloc,
                derv.id_derv, derv.name_derv, derv.desc_derv, derv.derv_defi,
                derv.derv_comp, derv.derv_metr
            FROM public.leaf_bloc bloc
            JOIN public.leaf_dime dime ON bloc.id_dime = dime.id_dime
            JOIN public.leaf_doma doma ON bloc.id_doma = doma.id_doma
            LEFT JOIN public.leaf_derv derv ON derv.id_bloc = bloc.id_bloc
            WHERE dime.id_dime = %s
            ORDER BY doma.id_doma, bloc.level_bloc NULLS LAST, bloc.id_bloc, derv.id_derv
            """,
            (SECTOR_LEGACY_DIME_ID,),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        by_domain: dict[int, dict[str, Any]] = {}
        by_block: dict[int, dict[str, Any]] = {}

        for row in rows:
            id_doma = int(row["id_doma"])
            domain_key = LEGACY_DOMA_TO_KEY.get(id_doma, f"dom{id_doma}")
            dom = by_domain.setdefault(
                id_doma,
                {
                    "id_doma": id_doma,
                    "domain_key": domain_key,
                    "name_doma": row["name_doma"],
                    "desc_doma": row.get("desc_doma"),
                    "blocks": [],
                },
            )

            id_bloc = int(row["id_bloc"])
            bloc = by_block.setdefault(
                id_bloc,
                {
                    "id_bloc": id_bloc,
                    "name_bloc": row["name_bloc"],
                    "desc_bloc": row.get("desc_bloc"),
                    "level_bloc": row.get("level_bloc"),
                    "quali_bloc": row.get("quali_bloc"),
                    "id_dime": int(row["id_dime"]),
                    "id_doma": id_doma,
                    "deliverables": [],
                },
            )
            if not any(b.get("id_bloc") == id_bloc for b in dom["blocks"]):
                dom["blocks"].append(bloc)

            if row.get("id_derv"):
                deliverable = {
                    "id_derv": row["id_derv"],
                    "name_derv": row["name_derv"],
                    "desc_derv": row.get("desc_derv"),
                    "derv_defi": row.get("derv_defi"),
                    "derv_comp": row.get("derv_comp"),
                    "derv_metr": row.get("derv_metr"),
                }
                if not any(d.get("id_derv") == deliverable["id_derv"] for d in bloc["deliverables"]):
                    bloc["deliverables"].append(deliverable)

        first_row = rows[0]
        return {
            "id_dime": SECTOR_LEGACY_DIME_ID,
            "dimension_key": "LA",
            "name_dime": first_row.get("name_dime") or "Aprendizagem em Ação (LA)",
            "desc_dime": first_row.get("desc_dime"),
            "code_dime": "LA",
            "is_canonical_sector": True,
            "domains": [by_domain[i] for i in sorted(by_domain)],
        }
    except Exception as exc:
        logger.warning("Falha ao carregar metodologia LA: %s", exc)
        return None
    finally:
        conn.close()


def load_la_methodology_structure() -> dict[str, Any]:
    """Metodologia LA — banco legado ou FRAMEWORK_KNOWLEDGE."""
    from_db = load_la_methodology_from_legacy()
    if from_db:
        logger.info(
            "Metodologia LA: %d domínios via leaf_bloc/leaf_derv.",
            len(from_db.get("domains") or []),
        )
        return from_db
    return load_la_template_methodology_structure()


def load_universal_methodology_structure() -> list[dict[str, Any]]:
    from_db = load_universal_methodology_from_legacy()
    if from_db:
        logger.info("Metodologia universal: %d dimensões via leaf_bloc/leaf_derv.", len(from_db))
        return from_db

    static = _structure_from_framework_knowledge()
    logger.info("Metodologia universal: %d dimensões via FRAMEWORK_KNOWLEDGE.", len(static))
    return static


def build_sector_methodology_structure(operational_dimension: dict[str, Any] | None) -> dict[str, Any]:
    """5ª dimensão setorial — substitui o template LA (Aprendizagem em Ação)."""
    op_dim = operational_dimension or {}
    la_template = load_la_template_methodology_structure()
    la_blocks_by_domain = {
        dom.get("domain_key"): dom.get("blocks") or []
        for dom in la_template.get("domains") or []
        if dom.get("domain_key")
    }

    domains_map: dict[str, dict[str, Any]] = {}
    for block in op_dim.get("building_blocks") or []:
        domain_key = normalize_domain_key(block.get("domain_key")) or "ds"
        domain_name = block.get("domain_name") or DOMAIN_NAMES_BY_KEY.get(domain_key, domain_key)
        domain = domains_map.setdefault(
            domain_key,
            {
                "domain_key": domain_key,
                "name_doma": domain_name,
                "desc_doma": block.get("block_description"),
                "blocks": [],
            },
        )
        for leaf_bloc in _leaf_blocks_from_sector_block(block, la_blocks_by_domain.get(domain_key, [])):
            leaf_bloc["level_bloc"] = len(domain["blocks"]) + 1
            domain["blocks"].append(leaf_bloc)

    return {
        "dimension_key": (op_dim.get("acronym") or "TA").upper(),
        "name_dime": op_dim.get("full_label") or op_dim.get("name") or "Dimensão setorial",
        "desc_dime": op_dim.get("description"),
        "replaces_dimension_key": SECTOR_DIMENSION_TEMPLATE_KEY,
        "domains": list(domains_map.values()),
    }


def build_full_methodology_document(
    *,
    operational_dimension: dict[str, Any] | None = None,
) -> dict[str, Any]:
    universal = load_universal_methodology_structure()
    return {
        "schema": "paneldx_leaf",
        "tables": ["leaf_dime", "leaf_doma", "leaf_bloc", "leaf_derv"],
        "replaces_dimension_key": SECTOR_DIMENSION_TEMPLATE_KEY,
        "canonical_dimensions": universal,
        "sector_dimension_template_la": load_la_template_methodology_structure(),
        "sector_dimension": build_sector_methodology_structure(operational_dimension),
        "universal_dimensions": universal,
    }


def methodology_summary_counts(structure: dict[str, Any]) -> dict[str, int]:
    universal = structure.get("universal_dimensions") or []
    blocks = 0
    deliverables = 0
    for dim in universal:
        for dom in dim.get("domains") or []:
            for bloc in dom.get("blocks") or []:
                blocks += 1
                deliverables += len(bloc.get("deliverables") or [])

    sector = structure.get("sector_dimension") or {}
    for dom in sector.get("domains") or []:
        for bloc in dom.get("blocks") or []:
            blocks += 1
            deliverables += len(bloc.get("deliverables") or [])

    return {
        "dimensions": len(universal) + (1 if sector.get("domains") else 0),
        "blocks": blocks,
        "deliverables": deliverables,
    }


def load_full_taxonomy_from_legacy() -> dict[str, Any] | None:
    """Importa leaf_dime, leaf_doma, leaf_bloc e leaf_derv completos do PanelDX."""
    conn = _legacy_connect()
    if not conn:
        return None

    try:
        from psycopg2.extras import RealDictCursor

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT id_dime, name_dime, desc_dime, long_description, code_dime, perspective_dime
            FROM public.leaf_dime
            ORDER BY id_dime
            """
        )
        dimensions: list[dict[str, Any]] = []
        for row in cur.fetchall():
            id_dime = int(row["id_dime"])
            dimensions.append(
                {
                    "id_dime": id_dime,
                    "dimension_key": LEGACY_DIME_TO_KEY.get(id_dime, (row.get("code_dime") or "XX").upper()),
                    "name_dime": row["name_dime"],
                    "desc_dime": row.get("desc_dime"),
                    "long_description": row.get("long_description"),
                    "code_dime": row.get("code_dime"),
                    "perspective_dime": row.get("perspective_dime"),
                }
            )

        cur.execute(
            """
            SELECT id_doma, name_doma, desc_doma, vetor_estrategico
            FROM public.leaf_doma
            ORDER BY id_doma
            """
        )
        domains: list[dict[str, Any]] = []
        for row in cur.fetchall():
            id_doma = int(row["id_doma"])
            domains.append(
                {
                    "id_doma": id_doma,
                    "domain_key": LEGACY_DOMA_TO_KEY.get(id_doma, f"dom{id_doma}"),
                    "name_doma": row["name_doma"],
                    "desc_doma": row.get("desc_doma"),
                    "vetor_estrategico": row.get("vetor_estrategico"),
                }
            )

        cur.execute(
            """
            SELECT
                b.id_bloc, b.name_bloc, b.desc_bloc, b.id_dime, b.id_doma,
                b.level_bloc, b.quali_bloc,
                d.id_derv, d.name_derv, d.desc_derv, d.derv_defi, d.derv_comp,
                d.derv_metr, d.criteria_dod
            FROM public.leaf_bloc b
            LEFT JOIN public.leaf_derv d ON d.id_bloc = b.id_bloc
            ORDER BY b.id_dime, b.id_doma, b.level_bloc NULLS LAST, b.id_bloc, d.id_derv
            """
        )
        rows = cur.fetchall()
        if not rows:
            return None

        blocks_by_id: dict[int, dict[str, Any]] = {}
        deliverables: list[dict[str, Any]] = []

        for row in rows:
            id_bloc = int(row["id_bloc"])
            if id_bloc not in blocks_by_id:
                blocks_by_id[id_bloc] = {
                    "id_bloc": id_bloc,
                    "name_bloc": row["name_bloc"],
                    "desc_bloc": row.get("desc_bloc"),
                    "id_dime": int(row["id_dime"]),
                    "id_doma": int(row["id_doma"]),
                    "level_bloc": row.get("level_bloc"),
                    "quali_bloc": row.get("quali_bloc"),
                }
            if row.get("id_derv"):
                deliverables.append(
                    {
                        "id_derv": int(row["id_derv"]),
                        "id_bloc": id_bloc,
                        "name_derv": row["name_derv"],
                        "desc_derv": row.get("desc_derv"),
                        "derv_defi": row.get("derv_defi"),
                        "derv_comp": row.get("derv_comp"),
                        "derv_metr": row.get("derv_metr"),
                        "criteria_dod": row.get("criteria_dod") or {},
                    }
                )

        return {
            "dimensions": dimensions,
            "domains": domains,
            "blocks": list(blocks_by_id.values()),
            "deliverables": deliverables,
        }
    except Exception as exc:
        logger.warning("Falha ao carregar taxonomia completa PanelDX: %s", exc)
        return None
    finally:
        conn.close()
