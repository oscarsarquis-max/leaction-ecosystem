"""Agregados da tela inicial do Radar — só dado já existente, sem professor.

Blocos: pulso, adoção de metodologia, cobertura BNCC, inclusão PEI/AEE.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

BNCC_CODE_RE = re.compile(r"\b((?:EF|EM)\d{2}[A-Z]{2,4}\d{2,3})\b", re.IGNORECASE)

_ANO_RE = re.compile(
    r"(\d+)\s*[ºo°ªa]?\s*(ano|série|serie)",
    re.IGNORECASE,
)


def as_mesa(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, memoryview)):
        try:
            value = bytes(value).decode("utf-8", errors="replace")
        except Exception:
            return {}
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "t", "yes", "sim")


def flatten_text(*parts: Any) -> str:
    chunks: list[str] = []

    def walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
            return
        if isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
            return
        text = str(node).strip()
        if text:
            chunks.append(text)

    for part in parts:
        walk(part)
    return "\n".join(chunks)


def extract_habilidade_codigos(*parts: Any) -> list[str]:
    """Códigos BNCC presentes em mesa/título/resumo — ordem estável, sem duplicata."""
    blob = flatten_text(*parts)
    seen: set[str] = set()
    ordered: list[str] = []
    for match in BNCC_CODE_RE.finditer(blob):
        code = match.group(1).upper()
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def normalize_curso_ano(serie_ano: str | None, turma_nome: str | None = None) -> str:
    raw = f"{serie_ano or ''} {turma_nome or ''}".strip()
    if not raw:
        return ""
    folded = raw.replace("°", "º").replace("ª", "ª")
    match = _ANO_RE.search(folded)
    if not match:
        return " ".join(raw.split())
    numero = match.group(1)
    kind = match.group(2).casefold()
    if kind.startswith("serie") or kind.startswith("série"):
        return f"{numero}ª série"
    return f"{numero}º ano"


def _norm_key(disciplina: str | None, curso_ano: str | None) -> tuple[str, str]:
    return ((disciplina or "").strip().casefold(), (curso_ano or "").strip().casefold())


def agregar_metodologias(nomes: list[str | None]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for nome in nomes:
        label = str(nome or "").strip()
        if label:
            counter[label] += 1
    return [
        {"nome": nome, "aulas": n}
        for nome, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
    ]


def montar_cobertura(
    catalogo: list[dict[str, Any]],
    aulas: list[dict[str, Any]],
) -> dict[str, Any]:
    """% de temas aprovados já usados no recorte, por disciplina×ano das aulas."""
    catalog_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    code_to_pairs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    label_of: dict[tuple[str, str], tuple[str, str]] = {}

    for row in catalogo:
        disc = str(row.get("disciplina_nome") or "").strip()
        ano = str(row.get("curso_ano") or "").strip()
        code = str(row.get("habilidade_codigo") or "").strip().upper()
        if not disc or not ano or not code:
            continue
        key = _norm_key(disc, ano)
        bucket = catalog_by_pair.setdefault(key, {"codes": set(), "disc": disc, "ano": ano})
        bucket["codes"].add(code)
        label_of[key] = (disc, ano)
        code_to_pairs[code].append(key)

    used_by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
    pairs_in_recorte: set[tuple[str, str]] = set()

    for aula in aulas:
        disc = str(aula.get("disciplina_nome") or "").strip()
        ano = normalize_curso_ano(aula.get("serie_ano"), aula.get("turma_nome"))
        codes = [c.upper() for c in (aula.get("habilidade_codigos") or []) if c]
        pair = _norm_key(disc, ano) if disc and ano else None
        if pair and pair in catalog_by_pair:
            pairs_in_recorte.add(pair)
        elif codes:
            for code in codes:
                for candidate in code_to_pairs.get(code, []):
                    pairs_in_recorte.add(candidate)
                    if pair is None:
                        pair = candidate
        if pair:
            for code in codes:
                used_by_pair[pair].add(code)

    itens: list[dict[str, Any]] = []
    for key in sorted(pairs_in_recorte, key=lambda k: (k[0], k[1])):
        bucket = catalog_by_pair.get(key)
        if not bucket:
            continue
        disc, ano = label_of[key]
        total = len(bucket["codes"])
        cobertos = len(used_by_pair.get(key, set()) & bucket["codes"])
        pct = round(100 * cobertos / total) if total else 0
        itens.append(
            {
                "disciplina_nome": disc,
                "curso_ano": ano,
                "temas_catalogo": total,
                "temas_cobertos": cobertos,
                "percentual": pct,
            }
        )

    aulas_com_tema = sum(1 for a in aulas if a.get("habilidade_codigos"))
    return {
        "itens": itens,
        "aulas_no_recorte": len(aulas),
        "aulas_com_tema_bncc": aulas_com_tema,
    }


def aula_tem_adaptacao_pei(mesa: dict[str, Any]) -> bool:
    if _truthy(mesa.get("has_pei_adaptations")):
        return True
    if str(mesa.get("pei_adaptation_text") or "").strip():
        return True
    if mesa.get("pei_aluno_id") or mesa.get("pei_individualizado_id"):
        return True
    return False


def pei_aluno_id_da_mesa(mesa: dict[str, Any]) -> str | None:
    raw = mesa.get("pei_aluno_id") or mesa.get("pei_individualizado_id")
    text = str(raw or "").strip()
    return text or None


def montar_inclusao(
    *,
    alunos_pei_ativos: int,
    alunos_com_adaptacao: int,
    aulas_com_adaptacao: int,
    aulas_no_recorte: int,
) -> dict[str, Any]:
    y = max(0, int(alunos_pei_ativos or 0))
    x = max(0, min(int(alunos_com_adaptacao or 0), y if y else int(alunos_com_adaptacao or 0)))
    if y:
        x = min(x, y)
    pct = round(100 * x / y) if y else 0
    return {
        "alunos_pei_ativos": y,
        "alunos_com_adaptacao": x,
        "aulas_com_adaptacao": int(aulas_com_adaptacao or 0),
        "aulas_no_recorte": int(aulas_no_recorte or 0),
        "percentual": pct,
    }


def _codigos_estruturados(mesa: dict[str, Any]) -> list[str]:
    raw = mesa.get("habilidade_codigos") or mesa.get("habilidades_bncc")
    if isinstance(raw, (list, tuple)):
        ordered: list[str] = []
        seen: set[str] = set()
        for item in raw:
            piece = item.get("habilidade_codigo") if isinstance(item, dict) else item
            for code in extract_habilidade_codigos(piece):
                if code not in seen:
                    seen.add(code)
                    ordered.append(code)
        return ordered
    return extract_habilidade_codigos(raw)


def _row_aula(row: dict[str, Any]) -> dict[str, Any]:
    mesa = as_mesa(row.get("mesa_payload_json"))
    structured = _codigos_estruturados(mesa)
    extracted = extract_habilidade_codigos(
        mesa,
        row.get("conteudo_resumo"),
        mesa.get("ementa_topico"),
        mesa.get("habilidade_codigo"),
        mesa.get("titulo"),
        mesa.get("aula_contexto"),
    )
    codes: list[str] = []
    seen: set[str] = set()
    for code in structured + extracted:
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    explicit = str(mesa.get("habilidade_codigo") or "").strip().upper()
    if explicit and BNCC_CODE_RE.fullmatch(explicit) and explicit not in codes:
        codes.insert(0, explicit)
    return {
        "metodologia_nome": row.get("metodologia_nome"),
        "serie_ano": row.get("serie_ano"),
        "turma_nome": row.get("turma_nome"),
        "disciplina_nome": row.get("disciplina_nome"),
        "habilidade_codigos": codes,
        "mesa": mesa,
    }


def _try_select(cur: Any, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    """Consulta auxiliar: se a tabela ainda não existe, devolve vazio sem abortar o recorte."""
    cur.execute("SAVEPOINT radar_home_aux")
    try:
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.execute("RELEASE SAVEPOINT radar_home_aux")
        return rows
    except Exception:
        cur.execute("ROLLBACK TO SAVEPOINT radar_home_aux")
        return []


def fetch_radar_home(
    cur: Any,
    *,
    instituicao_id: str,
    data_inicio: date,
    data_fim: date,
    unidade_id: str | None = None,
) -> dict[str, Any]:
    """Agregado anônimo do recorte. Nunca devolve professor."""
    sql = """
        SELECT
            m.nome AS metodologia_nome,
            p.conteudo_resumo,
            p.mesa_payload_json,
            t.serie_ano,
            t.nome AS turma_nome,
            aloc.disciplina_nome
        FROM public.school_planos_aula_espelhados p
        JOIN public.school_turmas t ON t.id = p.turma_id
        JOIN public.school_unidades u ON u.id = t.unidade_id
        JOIN public.school_metodologias_catalogo m ON m.id = p.metodologia_catalogo_id
        LEFT JOIN LATERAL (
            SELECT d.nome AS disciplina_nome
            FROM public.school_alocacoes_docentes a
            JOIN public.school_disciplinas d ON d.id = a.disciplina_id
            WHERE a.professor_vinculo_id = p.professor_vinculo_id
              AND a.ativo = TRUE
            ORDER BY (a.turma_id = p.turma_id) DESC NULLS LAST, a.updated_at DESC
            LIMIT 1
        ) aloc ON TRUE
        WHERE u.instituicao_id = %s
          AND u.ativo = TRUE
          AND p.semana_referencia >= %s
          AND p.semana_referencia <= %s
    """
    params: list[Any] = [str(instituicao_id), data_inicio, data_fim]
    if unidade_id:
        sql += " AND t.unidade_id = %s"
        params.append(str(unidade_id))
    cur.execute(sql, params)
    aulas = [_row_aula(dict(r)) for r in cur.fetchall()]

    catalogo = _try_select(
        cur,
        """
        SELECT disciplina_nome, curso_ano, habilidade_codigo
        FROM public.school_bncc_temas_canonico
        WHERE status = 'aprovado'
        """,
        [],
    )

    cobertura = montar_cobertura(catalogo, aulas)

    pei_ids: set[str] = set()
    aulas_com_adaptacao = 0
    for aula in aulas:
        mesa = aula.get("mesa") or {}
        if aula_tem_adaptacao_pei(mesa):
            aulas_com_adaptacao += 1
        pid = pei_aluno_id_da_mesa(mesa)
        if pid:
            pei_ids.add(pid)

    sql_cur = """
        SELECT DISTINCT c.pei_aluno_id::text AS pei_aluno_id
        FROM public.school_curadoria_pei c
        JOIN public.school_planos_aula_espelhados p ON p.id = c.plano_espelhado_id
        JOIN public.school_turmas t ON t.id = p.turma_id
        JOIN public.school_unidades u ON u.id = t.unidade_id
        WHERE u.instituicao_id = %s
          AND u.ativo = TRUE
          AND c.pei_aluno_id IS NOT NULL
          AND p.semana_referencia >= %s
          AND p.semana_referencia <= %s
    """
    params_cur: list[Any] = [str(instituicao_id), data_inicio, data_fim]
    if unidade_id:
        sql_cur += " AND t.unidade_id = %s"
        params_cur.append(str(unidade_id))
    for row in _try_select(cur, sql_cur, params_cur):
        pid = str(row.get("pei_aluno_id") or "").strip()
        if pid:
            pei_ids.add(pid)

    sql_pei = """
        SELECT COUNT(*)::int AS n
        FROM public.school_pei_alunos p
        LEFT JOIN public.school_alunos a ON a.id = p.aluno_id
        LEFT JOIN public.school_turmas t ON t.id = a.turma_id
        WHERE p.instituicao_id = %s
          AND p.status = 'ativo'
    """
    params_pei: list[Any] = [str(instituicao_id)]
    if unidade_id:
        sql_pei += " AND t.unidade_id = %s"
        params_pei.append(str(unidade_id))
    pei_rows = _try_select(cur, sql_pei, params_pei)
    alunos_pei_ativos = int((pei_rows[0] or {}).get("n") or 0) if pei_rows else 0

    inclusao = montar_inclusao(
        alunos_pei_ativos=alunos_pei_ativos,
        alunos_com_adaptacao=len(pei_ids),
        aulas_com_adaptacao=aulas_com_adaptacao,
        aulas_no_recorte=len(aulas),
    )

    return {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "metodologias": agregar_metodologias([a.get("metodologia_nome") for a in aulas]),
        "cobertura": cobertura,
        "inclusao": inclusao,
    }
