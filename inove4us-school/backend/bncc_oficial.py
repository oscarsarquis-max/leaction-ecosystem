"""BNCC oficial: flatten do dataset bncc-dev/bncc-dados + mapeamento Escola Teste.

IA não gera código nem enunciado. Texto e código vêm só do JSON importado.
O rótulo `tema` é extraído de campos oficiais (objeto único ou unidade temática).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATASET_VERSAO = "dados-2026.07.1"
FONTE_REPO = "https://github.com/bncc-dev/bncc-dados"
FONTE_URL_HABILIDADE = "https://bncc.dev/habilidade/{codigo}"
RAW_BASE = "https://raw.githubusercontent.com/bncc-dev/bncc-dados/main"

JSON_FILES = {
    "ensino-fundamental.json": f"{RAW_BASE}/dados/bncc-2018/ensino-fundamental.json",
    "ensino-medio.json": f"{RAW_BASE}/dados/bncc-2018/ensino-medio.json",
    "educacao-infantil.json": f"{RAW_BASE}/dados/bncc-2018/educacao-infantil.json",
    "computacao.json": f"{RAW_BASE}/dados/computacao-2022/computacao.json",
    "estrutura.json": f"{RAW_BASE}/dados/bncc-2018/estrutura.json",
}

EXPECTED_TOTAL = 1721

# Escola Teste (prompt 70): nomes de disciplina → recorte BNCC.
# EM sem habilidade própria do componente usa a área (CHS/LGG/CNT).
MAPA_DISCIPLINA: dict[str, dict[str, Any]] = {
    "Matemática": {
        "EF": {"componente_id": "ef-comp-ma"},
        "EM": {"area_id": "em-area-mat"},
    },
    "Língua Portuguesa": {
        "EF": {"componente_id": "ef-comp-lp"},
        "EM": {"componente_id": "em-comp-lp"},
    },
    "Português": {
        "EF": {"componente_id": "ef-comp-lp"},
        "EM": {"componente_id": "em-comp-lp"},
    },
    "Ciências": {"EF": {"componente_id": "ef-comp-ci"}},
    "História": {
        "EF": {"componente_id": "ef-comp-hi"},
        "EM": {"area_id": "em-area-chs"},
    },
    "Geografia": {
        "EF": {"componente_id": "ef-comp-ge"},
        "EM": {"area_id": "em-area-chs"},
    },
    "Inglês": {
        "EF": {"componente_id": "ef-comp-li"},
        "EM": {"area_id": "em-area-lgg", "componente_id_isnull": True},
    },
    "Arte": {
        "EF": {"componente_id": "ef-comp-ar"},
        "EM": {"area_id": "em-area-lgg", "componente_id_isnull": True},
    },
    "Educação Física": {
        "EF": {"componente_id": "ef-comp-ef"},
        "EM": {"area_id": "em-area-lgg", "componente_id_isnull": True},
    },
    "Biologia": {"EM": {"area_id": "em-area-cnt"}},
}

STATUS_PENDENTE = "pendente_revisao"
STATUS_APROVADO = "aprovado"
ORIGEM = "bncc_importado"

DDL_OFICIAL = Path(__file__).resolve().parents[1] / "infra" / "db" / "migrations" / "044_school_bncc_oficial.sql"


def cache_dir(root: Path) -> Path:
    d = root / "var" / "bncc-oficial"
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_dataset(root: Path) -> Path:
    import urllib.request

    dest = cache_dir(root)
    for name, url in JSON_FILES.items():
        path = dest / name
        urllib.request.urlretrieve(url, path)
    (dest / "SOURCE.txt").write_text(
        f"repo={FONTE_REPO}\nversao={DATASET_VERSAO}\n",
        encoding="utf-8",
    )
    return dest


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_ctx(items: list[dict]) -> dict[str, dict]:
    return {str(it.get("id")): it for it in items if it.get("id")}


def _nome_ctx(ctx: dict[str, dict], cid: Any) -> str:
    if not cid:
        return ""
    hit = ctx.get(str(cid)) or {}
    return str(hit.get("nome") or "").strip()


def _fonte(rec: dict) -> dict:
    f = rec.get("fonte") if isinstance(rec.get("fonte"), dict) else {}
    return {
        "fonte_documento": f.get("documento") or rec.get("documento"),
        "fonte_arquivo": f.get("arquivo"),
        "fonte_proveniencia": f.get("proveniencia"),
        "fonte_localizador": f.get("localizador"),
        "fonte_localizador_pdf": f.get("localizador_pdf"),
    }


def _tema_oficial(
    *,
    objetos_nomes: list[str],
    unidade_tematica: str,
    fallback: str,
) -> tuple[str, str]:
    """Rótulo só com texto já importado. Nunca inventa enunciado."""
    objs = [n for n in objetos_nomes if n]
    if len(objs) == 1:
        return objs[0], "objeto_conhecimento"
    if unidade_tematica:
        return unidade_tematica, "unidade_tematica"
    if objs:
        return objs[0], "objeto_conhecimento"
    return fallback, "componente_area"


def flatten_dataset(data_dir: Path) -> list[dict[str, Any]]:
    estrutura = _load_json(data_dir / "estrutura.json")
    comp_nomes = {
        str(c.get("id")): str(c.get("nome") or "")
        for c in (estrutura.get("componentes_curriculares") or [])
        if c.get("id")
    }
    area_nomes = {
        str(a.get("id")): str(a.get("nome") or "")
        for a in (estrutura.get("areas_conhecimento") or [])
        if a.get("id")
    }
    ce_index = {
        str(c.get("id")): c
        for c in (estrutura.get("competencias_especificas") or [])
        if c.get("id")
    }

    ef = _load_json(data_dir / "ensino-fundamental.json")
    em = _load_json(data_dir / "ensino-medio.json")
    ei = _load_json(data_dir / "educacao-infantil.json")
    co = _load_json(data_dir / "computacao.json")
    ctx = {}
    ctx.update(_index_ctx(ef.get("contextos_organizacao") or []))
    ctx.update(_index_ctx(em.get("contextos_organizacao") or []))
    for oc in co.get("objetos_conhecimento") or []:
        if oc.get("id"):
            ctx[str(oc["id"])] = {"id": oc["id"], "nome": oc.get("nome"), "tipo": "oc"}
    for eixo in co.get("eixos") or []:
        if eixo.get("id"):
            ctx[str(eixo["id"])] = {"id": eixo["id"], "nome": eixo.get("nome"), "tipo": "eixo"}

    rows: list[dict[str, Any]] = []

    def add(
        *,
        codigo: str,
        etapa: str,
        texto: str,
        rec: dict,
        componente_id: str | None = None,
        area_id: str | None = None,
        anos: list[int] | None = None,
        unidade_id: str | None = None,
        objetos_ids: list | None = None,
    ) -> None:
        objetos_ids = [str(x) for x in (objetos_ids or []) if x]
        objetos_nomes = [_nome_ctx(ctx, oid) for oid in objetos_ids]
        ut = _nome_ctx(ctx, unidade_id)
        rows.append(
            {
                "codigo": codigo.strip(),
                "etapa": etapa,
                "componente_id": componente_id,
                "componente_nome": comp_nomes.get(componente_id or "", "") or None,
                "area_id": area_id,
                "area_nome": area_nomes.get(area_id or "", "") or None,
                "anos": anos,
                "unidade_tematica": ut or None,
                "objetos_conhecimento": "; ".join(n for n in objetos_nomes if n) or None,
                "objetos_nomes": [n for n in objetos_nomes if n],
                "texto": (texto or "").strip(),
                "vigencia_status": ((rec.get("vigencia") or {}) or {}).get("status"),
                **_fonte(rec),
                "fonte_url": FONTE_URL_HABILIDADE.format(codigo=codigo.strip()),
                "dataset_versao": DATASET_VERSAO,
                "payload_json": rec,
            }
        )

    for h in ef.get("habilidades") or []:
        org = h.get("organizacao") if isinstance(h.get("organizacao"), dict) else {}
        add(
            codigo=str(h.get("codigo") or ""),
            etapa="EF",
            texto=str(h.get("texto") or ""),
            rec=h,
            componente_id=h.get("componente"),
            anos=list(h.get("anos") or []) or None,
            unidade_id=org.get("unidade_tematica"),
            objetos_ids=h.get("objetos_conhecimento") or [],
        )
    for h in em.get("habilidades") or []:
        ce_ids = [str(x) for x in (h.get("competencias_especificas") or []) if x]
        unidade_em = None
        if ce_ids:
            ce0 = ce_index.get(ce_ids[0]) or {}
            num = ce0.get("numero")
            if num is not None:
                unidade_em = f"Competência específica {num}"
        add(
            codigo=str(h.get("codigo") or ""),
            etapa="EM",
            texto=str(h.get("texto") or ""),
            rec=h,
            componente_id=h.get("componente"),
            area_id=h.get("area"),
            anos=None,
            unidade_id=None,
            objetos_ids=[],
        )
        if unidade_em and rows:
            rows[-1]["unidade_tematica"] = unidade_em
    for o in ei.get("objetivos") or []:
        add(
            codigo=str(o.get("codigo") or ""),
            etapa="EI",
            texto=str(o.get("texto") or ""),
            rec=o,
            componente_id=None,
            area_id=None,
            anos=None,
        )
    for o in co.get("objetivos_ei") or []:
        add(
            codigo=str(o.get("codigo") or ""),
            etapa="EI",
            texto=str(o.get("texto") or ""),
            rec=o,
            anos=None,
            unidade_id=o.get("eixo"),
        )
    for h in co.get("habilidades_ef") or []:
        add(
            codigo=str(h.get("codigo") or ""),
            etapa="EF",
            texto=str(h.get("texto") or ""),
            rec=h,
            anos=list(h.get("anos") or []) or None,
            unidade_id=h.get("eixo"),
            objetos_ids=h.get("objetos_conhecimento") or [],
        )
    for h in co.get("habilidades_em") or []:
        add(
            codigo=str(h.get("codigo") or ""),
            etapa="EM",
            texto=str(h.get("texto") or ""),
            rec=h,
        )
    rows = [r for r in rows if r["codigo"] and r["texto"]]
    return rows


def ensure_schema(conn) -> None:
    sql = DDL_OFICIAL.read_text(encoding="utf-8")
    # psycopg2 não aceita múltiplos comandos com BEGIN/COMMIT misturados via execute
    # se o driver estiver em transação. Usar o arquivo inteiro com autocommit no script.
    with conn.cursor() as cur:
        cur.execute(sql)


def upsert_oficial(conn, rows: list[dict[str, Any]]) -> int:
    from psycopg2.extras import Json

    sql = """
        INSERT INTO public.bncc_habilidades_oficial (
            codigo, etapa, componente_id, componente_nome, area_id, area_nome,
            anos, unidade_tematica, objetos_conhecimento, texto, vigencia_status,
            fonte_documento, fonte_arquivo, fonte_proveniencia, fonte_localizador,
            fonte_localizador_pdf, fonte_url, dataset_versao, payload_json, imported_at
        ) VALUES (
            %(codigo)s, %(etapa)s, %(componente_id)s, %(componente_nome)s,
            %(area_id)s, %(area_nome)s, %(anos)s, %(unidade_tematica)s,
            %(objetos_conhecimento)s, %(texto)s, %(vigencia_status)s,
            %(fonte_documento)s, %(fonte_arquivo)s, %(fonte_proveniencia)s,
            %(fonte_localizador)s, %(fonte_localizador_pdf)s, %(fonte_url)s,
            %(dataset_versao)s, %(payload_json)s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (codigo) DO UPDATE SET
            etapa = EXCLUDED.etapa,
            componente_id = EXCLUDED.componente_id,
            componente_nome = EXCLUDED.componente_nome,
            area_id = EXCLUDED.area_id,
            area_nome = EXCLUDED.area_nome,
            anos = EXCLUDED.anos,
            unidade_tematica = EXCLUDED.unidade_tematica,
            objetos_conhecimento = EXCLUDED.objetos_conhecimento,
            texto = EXCLUDED.texto,
            vigencia_status = EXCLUDED.vigencia_status,
            fonte_documento = EXCLUDED.fonte_documento,
            fonte_arquivo = EXCLUDED.fonte_arquivo,
            fonte_proveniencia = EXCLUDED.fonte_proveniencia,
            fonte_localizador = EXCLUDED.fonte_localizador,
            fonte_localizador_pdf = EXCLUDED.fonte_localizador_pdf,
            fonte_url = EXCLUDED.fonte_url,
            dataset_versao = EXCLUDED.dataset_versao,
            payload_json = EXCLUDED.payload_json,
            imported_at = CURRENT_TIMESTAMP
    """
    payload = []
    for r in rows:
        d = dict(r)
        d.pop("objetos_nomes", None)
        d["payload_json"] = Json(d["payload_json"])
        payload.append(d)
    with conn.cursor() as cur:
        cur.executemany(sql, payload)
    return len(payload)


def skill_matches_filter(row: dict[str, Any], spec: dict[str, Any], *, ano: int | None) -> bool:
    if spec.get("componente_id"):
        if row.get("componente_id") != spec["componente_id"]:
            return False
    if spec.get("area_id"):
        if row.get("area_id") != spec["area_id"]:
            return False
    if spec.get("componente_id_isnull"):
        if row.get("componente_id"):
            return False
    if ano is not None and row.get("etapa") == "EF":
        anos = row.get("anos") or []
        if ano not in anos:
            return False
    return True


def rotulo_tema(row: dict[str, Any]) -> tuple[str, str]:
    fallback = (
        row.get("componente_nome")
        or row.get("area_nome")
        or row.get("codigo")
        or "BNCC"
    )
    return _tema_oficial(
        objetos_nomes=list(row.get("objetos_nomes") or []),
        unidade_tematica=str(row.get("unidade_tematica") or ""),
        fallback=str(fallback),
    )
