"""Carrega questões universais de banco legado ou catálogo estático."""

from __future__ import annotations

import copy
import logging
import os
import re
from typing import Any
from urllib.parse import unquote, urlparse

from app.data.rubric_patterns import default_maturity_options, from_ctdi_rubrica
from app.core.sector_constants import (
    DEFAULT_SECTOR_ACRONYM,
    DEFAULT_SECTOR_ACTION_NAME,
    DEFAULT_SECTOR_FULL_LABEL,
    DEFAULT_SECTOR_LEGACY_SETOR,
    DOMAIN_NAMES_PT,
    SECTOR_LEGACY_DIME_ID,
)
from app.core.framework_definitions import FRAMEWORK_KNOWLEDGE, DOMAIN_NAMES_BY_KEY
from app.data.universal_quest_catalog import (
    DIMENSION_META,
    axis_label,
    get_universal_assessment_items,
)

logger = logging.getLogger(__name__)

LEGACY_DOMA_TO_KEY: dict[int, str] = {
    1: "ds",
    2: "bm",
    3: "ic",
    4: "dc",
    5: "cc",
    6: "dg",
    7: "dp",
    8: "cap",
    9: "dm",
}

LEGACY_DIME_TO_KEY: dict[int, str] = {
    1: "SV",
    2: "HC",
    3: "FS",
    4: "LA",
    5: "DA",
}

_EDUCATION_TERMS_IN_TEXT = re.compile(
    r"(?i)\b(educa[çc][ãa]o|educacional|educacionais)\b"
)

_UNIVERSAL_PHRASE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\bno setor educacional\b"), "no mercado"),
    (re.compile(r"(?i)\bdo setor educacional\b"), "do setor"),
    (re.compile(r"(?i)\bprodutos ou servi[cç]os educacionais\b"), "produtos ou serviços"),
    (re.compile(r"(?i)\bexperi[eê]ncias educacionais\b"), "experiências de clientes e usuários"),
    (re.compile(r"(?i)\bservi[cç]os educacionais\b"), "serviços"),
    (re.compile(r"(?i)\bofertas educacionais\b"), "ofertas"),
    (re.compile(r"(?i)\btend[eê]ncias educacionais\b"), "tendências de mercado"),
    (re.compile(r"(?i)\bsegmentos educacionais\b"), "segmentos de mercado"),
    (re.compile(r"(?i)\btecnol[oó]gicas ou educacionais\b"), "tecnológicas"),
    (re.compile(r"(?i)\bregulat[oó]rias, tecnol[oó]gicas ou educacionais\b"), "regulatórias ou tecnológicas"),
]

UNIVERSAL_AXIS_PREFIXES = ("SV —", "HC —", "FS —", "DA —", "SV -", "HC -", "FS -", "DA -")


def is_universal_assessment_axis(axis: str | None) -> bool:
    text = (axis or "").strip()
    return text.startswith(UNIVERSAL_AXIS_PREFIXES)


def sanitize_universal_question_text(text: str | None) -> str:
    """Neutraliza referências educacionais — dimensões universais devem ser setoriais."""
    if not text:
        return ""
    cleaned = str(text)
    for pattern, replacement in _UNIVERSAL_PHRASE_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = _EDUCATION_TERMS_IN_TEXT.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s+ou\s*\.", ".", cleaned)
    return cleaned.strip()


def _normalize_legacy_setor(setor: str | None) -> str:
    if not setor:
        return ""
    text = setor.strip().upper()
    for src, dst in (("Ç", "C"), ("Ã", "A"), ("Ó", "O"), ("É", "E"), ("Í", "I")):
        text = text.replace(src, dst)
    return text


def is_education_legacy_setor(setor: str | None) -> bool:
    """True quando setor_ques legado aponta para Educação (LA)."""
    return _normalize_legacy_setor(setor) == "EDUCACAO"


def _apply_new_framework_universal_hygiene(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Higieniza enunciados universais herdados por frameworks novos (não Educação)."""
    hygienized: list[dict[str, Any]] = []
    for item in items:
        entry = copy.deepcopy(item)
        meta = dict(entry.get("metadata") or {})
        original_text = entry.get("question_text") or ""
        cleaned_text = sanitize_universal_question_text(original_text)
        if cleaned_text != original_text:
            meta["legacy_question_text"] = original_text
            meta["text_hygiene"] = "education_terms_removed"
        entry["metadata"] = meta
        entry["question_text"] = cleaned_text or original_text
        hygienized.append(entry)
    return hygienized


def _load_from_legacy_database(*, for_new_framework: bool = False) -> list[dict[str, Any]] | None:
    """Importa questões de banco externo quando LEGACY_QUEST_DATABASE_URL estiver configurado."""
    database_url = os.getenv("LEGACY_QUEST_DATABASE_URL")
    if not database_url:
        return None

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        logger.warning("psycopg2 indisponível — usando catálogo estático universal.")
        return None

    parsed = urlparse(database_url)
    dbname = (parsed.path or "/LeAction_SysF").lstrip("/")
    if "?" in dbname:
        dbname = dbname.split("?", 1)[0]

    connect_kwargs: dict[str, Any] = {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 5432,
        "dbname": dbname,
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "client_encoding": "UTF8",
    }

    try:
        conn = psycopg2.connect(**connect_kwargs)
    except Exception as exc:
        logger.warning("Não foi possível conectar ao banco legado (%s). Usando catálogo estático.", exc)
        return None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT q.id_ques,
                   q.desc_ques,
                   q.id_dime,
                   q.id_doma,
                   q.prefu_ques,
                   q.setor_ques
            FROM ctdi_quest q
            WHERE q.id_dime IN (1, 2, 3, 5)
              AND q.id_doma IS NOT NULL
              AND UPPER(COALESCE(q.setor_ques, 'GERAL')) = 'GERAL'
              AND UPPER(TRIM(COALESCE(q.setor_ques, ''))) NOT IN ('EDUCACAO', 'EDUCAÇÃO')
            ORDER BY q.id_dime, q.id_doma, q.prefu_ques, q.id_ques
            """
        )
        rows = cur.fetchall()

        if not rows:
            return None

        if for_new_framework:
            rows = [
                row
                for row in rows
                if not is_education_legacy_setor(row.get("setor_ques"))
            ]
            if not rows:
                return None

        ques_ids = list({r["id_ques"] for r in rows})
        if LEGACY_DA_DC_FUTURE_QUES_ID not in ques_ids:
            ques_ids.append(LEGACY_DA_DC_FUTURE_QUES_ID)
        cur.execute(
            """
            SELECT id_ques, grad_rubr, label_rubr, desc_rubr
            FROM ctdi_rubricas
            WHERE id_ques = ANY(%s)
            ORDER BY id_ques, grad_rubr ASC
            """,
            (ques_ids,),
        )
        rubrics_by_ques: dict[int, list[dict[str, Any]]] = {}
        for rub in cur.fetchall():
            rubrics_by_ques.setdefault(rub["id_ques"], []).append(rub)

        seen_keys: set[tuple[str, str, str]] = set()
        items: list[dict[str, Any]] = []

        for row in rows:
            dim_key = LEGACY_DIME_TO_KEY.get(int(row["id_dime"]))
            dom_key = LEGACY_DOMA_TO_KEY.get(int(row["id_doma"]))
            if not dim_key or not dom_key:
                continue

            prefu = (row.get("prefu_ques") or "P").upper()
            dedupe_key = (dim_key, dom_key, prefu)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            rubrics = rubrics_by_ques.get(row["id_ques"], [])
            options = _rubricas_to_options(rubrics)
            prefu_label = "Presente" if prefu == "P" else "Futuro"
            question_text = row["desc_ques"]
            if for_new_framework:
                question_text = sanitize_universal_question_text(question_text) or row["desc_ques"]

            metadata: dict[str, Any] = {
                "dimension_key": dim_key,
                "domain_key": dom_key,
                "prefu_ques": prefu,
                "temporal_key": "future" if prefu == "F" else "present",
                "legacy_id_ques": row["id_ques"],
                "legacy_id_dime": int(row["id_dime"]),
                "legacy_id_doma": int(row["id_doma"]),
                "origin": "legacy_database",
            }
            legacy_setor = row.get("setor_ques")
            if legacy_setor:
                metadata["legacy_setor_ques"] = legacy_setor
            if for_new_framework and question_text != row["desc_ques"]:
                metadata["legacy_question_text"] = row["desc_ques"]
                metadata["text_hygiene"] = "education_terms_removed"

            items.append(
                {
                    "axis": f"{axis_label(dim_key, dom_key)} ({prefu_label})",
                    "question_text": question_text,
                    "question_type": "multiple_choice",
                    "options": options,
                    "metadata": metadata,
                }
            )

        if ("DA", "dc", "F") not in seen_keys:
            items.append(_build_da_dc_future_gap_item(rubrics_by_ques))

        return items if items else None
    except Exception as exc:
        logger.warning("Falha ao ler questões do banco legado: %s", exc)
        return None
    finally:
        conn.close()


# PanelDX legado não cadastrou GERAL Futuro para DA × Cultura de Dados (id_dime=5, id_doma=4).
# Existe apenas id_ques=157 (setor EDUCACAO), filtrado na importação universal.
LEGACY_DA_DC_FUTURE_QUES_ID = 157
DA_DC_FUTURE_QUESTION_TEXT = (
    "Nossa infraestrutura de dados será capaz de garantir a coleta segura, "
    "a integridade e a proteção das informações organizacionais, "
    "em conformidade com exigências legais e avanços tecnológicos."
)


def _build_da_dc_future_gap_item(
    rubrics_by_ques: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    dim_key, dom_key = "DA", "dc"
    rubrics = rubrics_by_ques.get(LEGACY_DA_DC_FUTURE_QUES_ID, [])
    options = _rubricas_to_options(rubrics)
    return {
        "axis": f"{axis_label(dim_key, dom_key)} (Futuro)",
        "question_text": DA_DC_FUTURE_QUESTION_TEXT,
        "question_type": "multiple_choice",
        "options": options,
        "metadata": {
            "dimension_key": dim_key,
            "domain_key": dom_key,
            "prefu_ques": "F",
            "temporal_key": "future",
            "legacy_id_ques": LEGACY_DA_DC_FUTURE_QUES_ID,
            "legacy_id_dime": 5,
            "legacy_id_doma": 4,
            "origin": "legacy_gap_fill",
            "gap_reason": "PanelDX sem questão GERAL Futuro para DA/dc",
        },
    }


def _rubricas_to_options(rubrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rubrics:
        return default_maturity_options()

    options: list[dict[str, Any]] = []
    for rub in rubrics:
        try:
            options.append(from_ctdi_rubrica(rub, display_order=len(options) + 1))
        except ValueError:
            continue

    return options or default_maturity_options()


def load_universal_assessment_items(*, for_new_framework: bool = False) -> list[dict[str, Any]]:
    """
    Importa questões universais: banco legado (se disponível) ou catálogo estático.

    for_new_framework=True exclui questões legadas marcadas como setor EDUCACAO.
    A higienização textual (cunho geral) é sempre aplicada às 4 dimensões universais.
    """
    from_db = _load_from_legacy_database(for_new_framework=for_new_framework)
    if from_db:
        items = from_db
        source = "banco legado"
    else:
        items = get_universal_assessment_items()
        source = "catálogo estático"

    items = _apply_new_framework_universal_hygiene(items)
    logger.info(
        "Catálogo universal: %d questões de %s (enunciados neutros).",
        len(items),
        source,
    )
    return items


def _load_la_from_legacy_database() -> list[dict[str, Any]] | None:
    """Questões da dimensão LA (Educação) — id_dime=4, setor EDUCACAO."""
    database_url = os.getenv("LEGACY_QUEST_DATABASE_URL")
    if not database_url:
        return None

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        return None

    parsed = urlparse(database_url)
    dbname = (parsed.path or "/LeAction_SysF").lstrip("/").split("?")[0]

    try:
        conn = psycopg2.connect(
            host=parsed.hostname or "127.0.0.1",
            port=parsed.port or 5432,
            dbname=dbname,
            user=unquote(parsed.username or "postgres"),
            password=unquote(parsed.password or ""),
            client_encoding="UTF8",
        )
    except Exception as exc:
        logger.warning("Conexão legado indisponível para questões LA: %s", exc)
        return None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT q.id_ques, q.desc_ques, q.id_doma, q.prefu_ques, q.setor_ques
            FROM ctdi_quest q
            WHERE q.id_dime = %s
              AND q.id_doma IS NOT NULL
              AND UPPER(COALESCE(q.setor_ques, '')) = %s
            ORDER BY q.id_doma, q.prefu_ques, q.id_ques
            """,
            (SECTOR_LEGACY_DIME_ID, DEFAULT_SECTOR_LEGACY_SETOR),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        cur.execute(
            """
            SELECT id_ques, grad_rubr, label_rubr, desc_rubr
            FROM ctdi_rubricas
            WHERE id_ques = ANY(%s)
            ORDER BY id_ques, grad_rubr ASC
            """,
            ([r["id_ques"] for r in rows],),
        )
        rubrics_by_ques: dict[int, list[dict[str, Any]]] = {}
        for rub in cur.fetchall():
            rubrics_by_ques.setdefault(rub["id_ques"], []).append(rub)

        seen: set[tuple[str, str]] = set()
        items: list[dict[str, Any]] = []
        for row in rows:
            dom_key = LEGACY_DOMA_TO_KEY.get(int(row["id_doma"]))
            if not dom_key:
                continue
            prefu = (row.get("prefu_ques") or "P").upper()
            dedupe = (dom_key, prefu)
            if dedupe in seen:
                continue
            seen.add(dedupe)

            domain_name = DOMAIN_NAMES_PT.get(dom_key) or DOMAIN_NAMES_BY_KEY.get(dom_key, dom_key)
            prefu_label = "Presente" if prefu == "P" else "Futuro"
            temporal_key = "present" if prefu == "P" else "future"
            axis = (
                f"{DEFAULT_SECTOR_ACRONYM} — {DEFAULT_SECTOR_FULL_LABEL} / "
                f"{dom_key} — {domain_name} ({prefu_label})"
            )
            items.append(
                {
                    "axis": axis,
                    "question_text": row["desc_ques"],
                    "question_type": "multiple_choice",
                    "options": _rubricas_to_options(rubrics_by_ques.get(row["id_ques"], [])),
                    "metadata": {
                        "dimension_key": DEFAULT_SECTOR_ACRONYM,
                        "domain_key": dom_key,
                        "domain_name": domain_name,
                        "dimension_type": "sector",
                        "prefu_ques": prefu,
                        "temporal_key": temporal_key,
                        "legacy_id_ques": row["id_ques"],
                        "legacy_id_dime": SECTOR_LEGACY_DIME_ID,
                        "legacy_id_doma": int(row["id_doma"]),
                        "sector": "educação",
                        "origin": "legacy_database_la",
                    },
                }
            )
        return items if items else None
    except Exception as exc:
        logger.warning("Falha ao ler questões LA do banco legado: %s", exc)
        return None
    finally:
        conn.close()


def _la_items_from_framework_knowledge() -> list[dict[str, Any]]:
    """Fallback estático — 9 domínios × Presente/Futuro a partir do template LA."""
    la_data = FRAMEWORK_KNOWLEDGE.get("LA") or {}
    items: list[dict[str, Any]] = []
    for domain_key, domain_data in (la_data.get("dominios") or {}).items():
        from app.core.framework_definitions import normalize_domain_key

        dom_key = normalize_domain_key(domain_key)
        domain_name = domain_data.get("nome") or DOMAIN_NAMES_BY_KEY.get(dom_key, dom_key)
        blocos = list((domain_data.get("blocos") or {}).keys())
        block_name = blocos[0] if blocos else domain_name
        block_desc = f"Capacidades de {domain_name} no contexto educacional."

        for prefu, temporal_key, prefu_label in (
            ("P", "present", "Presente"),
            ("F", "future", "Futuro"),
        ):
            if prefu == "P":
                qtext = (
                    f"Qual o nível atual de maturidade em {domain_name} "
                    f"na operação educacional (prática presente)?"
                )
            else:
                qtext = (
                    f"Qual a perspectiva de evolução/adopção em {domain_name} "
                    f"no contexto educacional (planejamento futuro)?"
                )
            axis = (
                f"{DEFAULT_SECTOR_ACRONYM} — {DEFAULT_SECTOR_FULL_LABEL} / "
                f"{dom_key} — {domain_name} ({prefu_label})"
            )
            items.append(
                {
                    "axis": axis,
                    "question_text": qtext,
                    "question_type": "multiple_choice",
                    "options": default_maturity_options(),
                    "metadata": {
                        "dimension_key": DEFAULT_SECTOR_ACRONYM,
                        "domain_key": dom_key,
                        "domain_name": domain_name,
                        "dimension_type": "sector",
                        "prefu_ques": prefu,
                        "temporal_key": temporal_key,
                        "block_name": block_name,
                        "block_description": block_desc,
                        "sector": "educação",
                        "origin": "framework_knowledge_la",
                    },
                }
            )
    return items


def load_la_sector_assessment_items() -> list[dict[str, Any]]:
    """Questões setoriais Educação (dimensão LA) — banco legado ou template estático."""
    from_db = _load_la_from_legacy_database()
    if from_db:
        logger.info("Catálogo LA/Educação: %d questões do banco legado.", len(from_db))
        return from_db

    static = _la_items_from_framework_knowledge()
    logger.info("Catálogo LA/Educação: %d questões do template estático.", len(static))
    return static


def universal_dimensions_summary() -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "name": meta["name"],
            "label": meta["label"],
        }
        for key, meta in DIMENSION_META.items()
    ]
