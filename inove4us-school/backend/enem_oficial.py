"""Matriz de Referência do ENEM — dado oficial importado (prompt 147).

Texto e numeração vêm só do PDF do INEP. IA não gera habilidade.
Redação fica em tabela própria (5 competências, sem H1–H30).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

FONTE_PDF_URL = "https://download.inep.gov.br/download/enem/matriz_referencia.pdf"
FONTE_PDF_SHA256 = "6b56d523ccb85f74f7ed33e0cd679f3dd178ed6f13a5b0948bcfdfe8964ce6a1"
FONTE_EDITAL_2026 = (
    "Edital INEP nº 64, de 21 de maio de 2026, item 3.1 — "
    "o Enem é estruturado a partir das matrizes em "
    "download.inep.gov.br/download/enem/matriz_referencia.pdf"
)
FONTE_DOCUMENTO = "INEP, Matriz de Referência do ENEM (PDF oficial vigente no Enem 2026)"
CARTILHA_URL = (
    "https://download.inep.gov.br/publicacoes/institucionais/"
    "avaliacoes_e_exames_da_educacao_basica/"
    "a_redacao_no_enem_2025_cartilha_do_participante.pdf"
)
CARTILHA_SHA256 = "d8ab44dcbf5af808829d9dee89d23e7efa4f59df022b99102fac87489b870288"
CARTILHA_DOCUMENTO = (
    "INEP, A Redação do Enem 2025 — Cartilha do(a) participante, "
    "seção 1. Matriz de Referência para a Redação"
)
DATASET_VERSAO = "enem-oficial-2026.09.1"
EXPECTED_HABILIDADES = 120
EXPECTED_COMPETENCIAS_AREA = 30
EXPECTED_REDAÇÃO = 5

AREAS = {
    "LC": "Linguagens, Códigos e suas Tecnologias",
    "MT": "Matemática e suas Tecnologias",
    "CN": "Ciências da Natureza e suas Tecnologias",
    "CH": "Ciências Humanas e suas Tecnologias",
}

AREA_HEADINGS = {
    "Linguagens, Códigos e suas Tecnologias": "LC",
    "Matemática e suas Tecnologias": "MT",
    "Ciências da Natureza e suas Tecnologias": "CN",
    "Ciências Humanas e suas Tecnologias": "CH",
}

# Textos oficiais da cartilha 2025 (quadro da matriz de redação).
REDACAO_OFICIAL = [
    (1, "Demonstrar domínio da modalidade escrita formal da língua portuguesa."),
    (
        2,
        "Compreender a proposta de redação e aplicar conceitos das várias áreas de "
        "conhecimento para desenvolver o tema dentro dos limites estruturais do "
        "texto dissertativo-argumentativo em prosa.",
    ),
    (
        3,
        "Selecionar, relacionar, organizar e interpretar informações, fatos, "
        "opiniões e argumentos em defesa de um ponto de vista.",
    ),
    (
        4,
        "Demonstrar conhecimento dos mecanismos linguísticos necessários para a "
        "construção da argumentação.",
    ),
    (
        5,
        "Elaborar proposta de intervenção para o problema abordado, respeitando "
        "os direitos humanos.",
    ),
]


def cache_dir(root: Path) -> Path:
    d = root / "var" / "enem-oficial"
    d.mkdir(parents=True, exist_ok=True)
    return d


def normalize_cmp(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    t = re.sub(r"\s+", " ", t).strip().lower()
    t = t.rstrip(".*")
    return t


def texto_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _join_wrapped(lines: list[str]) -> str:
    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if out and not out[-1].endswith((".", ";", ":", "?", "!")):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return " ".join(out).strip()


def parse_matriz_txt(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    eixos = []
    eixo_re = re.compile(
        r"^([IVX]+)\.\s+(.+?)\s+\(([A-Z]{2})\):\s*(.+)$",
        re.MULTILINE,
    )
    for m in eixo_re.finditer(text):
        eixos.append(
            {
                "romano": m.group(1),
                "sigla": m.group(3),
                "nome": m.group(2).strip(),
                "texto": m.group(4).strip(),
            }
        )

    split = re.split(r"####\s+Matriz de Referência de\s+", text)
    habilidades: list[dict[str, Any]] = []
    competencias: list[dict[str, Any]] = []
    for block in split[1:]:
        head = block.splitlines()[0].strip()
        area_nome = re.sub(r"^Matriz de Referência de\s+", "", head).strip()
        area = AREA_HEADINGS.get(area_nome)
        if not area:
            for nome, codigo in AREA_HEADINGS.items():
                if nome.split()[0] in head:
                    area, area_nome = codigo, nome
                    break
        if not area:
            continue
        body = block
        if "## ANEXO" in body:
            body = body.split("## ANEXO", 1)[0]
        chunks = re.split(r"Competência de área\s+(\d+)\s*[-–]\s*", body)
        # chunks[0] preamble; then n, text, n, text...
        for i in range(1, len(chunks), 2):
            n_comp = int(chunks[i])
            rest = chunks[i + 1]
            hab_parts = re.split(r"\nH(\d+)\s*[-–]\s*", rest)
            comp_texto = _join_wrapped(hab_parts[0].splitlines())
            competencias.append(
                {
                    "area_codigo": area,
                    "area_nome": AREAS[area],
                    "competencia_numero": n_comp,
                    "texto": comp_texto,
                }
            )
            for j in range(1, len(hab_parts), 2):
                n_hab = int(hab_parts[j])
                hab_texto = _join_wrapped(hab_parts[j + 1].splitlines())
                codigo = f"ENEM-{area}-H{n_hab:02d}"
                habilidades.append(
                    {
                        "codigo": codigo,
                        "area_codigo": area,
                        "area_nome": AREAS[area],
                        "competencia_numero": n_comp,
                        "competencia_texto": comp_texto,
                        "habilidade_numero": n_hab,
                        "texto": hab_texto,
                    }
                )
    return {"eixos": eixos, "competencias": competencias, "habilidades": habilidades}


def redação_rows() -> list[dict[str, Any]]:
    rows = []
    for n, texto in REDACAO_OFICIAL:
        rows.append(
            {
                "codigo": f"ENEM-RED-C{n}",
                "competencia_numero": n,
                "texto": texto,
            }
        )
    return rows


def flatten_oficial(root: Path) -> dict[str, Any]:
    txt = cache_dir(root) / "matriz_referencia.inep.txt"
    parsed = parse_matriz_txt(txt)
    return {
        "dataset_versao": DATASET_VERSAO,
        "fonte": {
            "documento": FONTE_DOCUMENTO,
            "url": FONTE_PDF_URL,
            "sha256": FONTE_PDF_SHA256,
            "edital": FONTE_EDITAL_2026,
            "redacao_documento": CARTILHA_DOCUMENTO,
            "redacao_url": CARTILHA_URL,
            "redacao_sha256": CARTILHA_SHA256,
        },
        "eixos": parsed["eixos"],
        "competencias": parsed["competencias"],
        "habilidades": parsed["habilidades"],
        "redacao": redação_rows(),
    }


def compare_enemwise(oficial: dict[str, Any], enemwise_path: Path) -> dict[str, Any]:
    third = json.loads(enemwise_path.read_text(encoding="utf-8"))
    area_map = {"LC": "LC", "MT": "MT", "CN": "CN", "CH": "CH"}
    # enemwise keys
    ew_areas = third.get("areas") or {}
    if "MAT" in ew_areas:
        area_map["MT"] = "MAT"
    diffs = []
    missing = []
    extra_bloom = 0
    matched = 0
    for row in oficial["habilidades"]:
        area = row["area_codigo"]
        ew_key = area_map.get(area, area)
        bloco = ew_areas.get(ew_key) or ew_areas.get(area) or {}
        habs = bloco.get("habilidades") or {}
        item = habs.get(str(row["habilidade_numero"]))
        if not item:
            missing.append(row["codigo"])
            continue
        if item.get("bloom"):
            extra_bloom += 1
        a = normalize_cmp(row["texto"])
        b = normalize_cmp(item.get("descricao") or "")
        if a == b:
            matched += 1
        else:
            diffs.append(
                {
                    "codigo": row["codigo"],
                    "oficial": row["texto"],
                    "enemwise": item.get("descricao"),
                }
            )
    return {
        "enemwise_areas": sorted(ew_areas.keys()),
        "oficial_habilidades": len(oficial["habilidades"]),
        "matched": matched,
        "texto_diferente": diffs,
        "faltando_no_enemwise": missing,
        "enemwise_tem_bloom_nao_oficial": extra_bloom,
        "enemwise_tem_redacao": "RED" in ew_areas or "redacao" in third,
    }


def upsert_oficial(conn, payload: dict[str, Any]) -> dict[str, int]:
    habs = payload["habilidades"]
    reds = payload["redacao"]
    fonte = payload["fonte"]
    with conn.cursor() as cur:
        for row in habs:
            cur.execute(
                """
                INSERT INTO public.enem_habilidades_oficial (
                    codigo, area_codigo, area_nome, competencia_numero,
                    competencia_texto, habilidade_numero, texto,
                    fonte_documento, fonte_url, fonte_proveniencia,
                    fonte_localizador, dataset_versao, texto_hash, payload_json
                ) VALUES (
                    %(codigo)s, %(area_codigo)s, %(area_nome)s, %(competencia_numero)s,
                    %(competencia_texto)s, %(habilidade_numero)s, %(texto)s,
                    %(fonte_documento)s, %(fonte_url)s, %(fonte_proveniencia)s,
                    %(fonte_localizador)s, %(dataset_versao)s, %(texto_hash)s, %(payload_json)s
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    area_codigo = EXCLUDED.area_codigo,
                    area_nome = EXCLUDED.area_nome,
                    competencia_numero = EXCLUDED.competencia_numero,
                    competencia_texto = EXCLUDED.competencia_texto,
                    habilidade_numero = EXCLUDED.habilidade_numero,
                    texto = EXCLUDED.texto,
                    fonte_documento = EXCLUDED.fonte_documento,
                    fonte_url = EXCLUDED.fonte_url,
                    fonte_proveniencia = EXCLUDED.fonte_proveniencia,
                    fonte_localizador = EXCLUDED.fonte_localizador,
                    dataset_versao = EXCLUDED.dataset_versao,
                    texto_hash = EXCLUDED.texto_hash,
                    payload_json = EXCLUDED.payload_json
                """,
                {
                    **row,
                    "fonte_documento": FONTE_DOCUMENTO,
                    "fonte_url": FONTE_PDF_URL,
                    "fonte_proveniencia": (
                        f"PDF oficial INEP sha256={FONTE_PDF_SHA256}; {FONTE_EDITAL_2026}"
                    ),
                    "fonte_localizador": (
                        f"{row['area_codigo']} competência {row['competencia_numero']} "
                        f"H{row['habilidade_numero']}"
                    ),
                    "dataset_versao": DATASET_VERSAO,
                    "texto_hash": texto_hash(row["texto"]),
                    "payload_json": json.dumps(
                        {"sha256_pdf": FONTE_PDF_SHA256, "edital": FONTE_EDITAL_2026},
                        ensure_ascii=False,
                    ),
                },
            )
        for row in reds:
            cur.execute(
                """
                INSERT INTO public.enem_redacao_competencias_oficial (
                    codigo, competencia_numero, texto,
                    fonte_documento, fonte_url, fonte_proveniencia,
                    dataset_versao, texto_hash, payload_json
                ) VALUES (
                    %(codigo)s, %(competencia_numero)s, %(texto)s,
                    %(fonte_documento)s, %(fonte_url)s, %(fonte_proveniencia)s,
                    %(dataset_versao)s, %(texto_hash)s, %(payload_json)s
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    competencia_numero = EXCLUDED.competencia_numero,
                    texto = EXCLUDED.texto,
                    fonte_documento = EXCLUDED.fonte_documento,
                    fonte_url = EXCLUDED.fonte_url,
                    fonte_proveniencia = EXCLUDED.fonte_proveniencia,
                    dataset_versao = EXCLUDED.dataset_versao,
                    texto_hash = EXCLUDED.texto_hash,
                    payload_json = EXCLUDED.payload_json
                """,
                {
                    **row,
                    "fonte_documento": CARTILHA_DOCUMENTO,
                    "fonte_url": CARTILHA_URL,
                    "fonte_proveniencia": (
                        f"Cartilha oficial INEP 2025 sha256={CARTILHA_SHA256}"
                    ),
                    "dataset_versao": DATASET_VERSAO,
                    "texto_hash": texto_hash(row["texto"]),
                    "payload_json": json.dumps(fonte, ensure_ascii=False),
                },
            )
        for row in payload.get("eixos") or []:
            cur.execute(
                """
                INSERT INTO public.enem_eixos_cognitivos_oficial (
                    sigla, romano, nome, texto, fonte_documento, fonte_url,
                    dataset_versao, texto_hash
                ) VALUES (
                    %(sigla)s, %(romano)s, %(nome)s, %(texto)s, %(fonte_documento)s,
                    %(fonte_url)s, %(dataset_versao)s, %(texto_hash)s
                )
                ON CONFLICT (sigla) DO UPDATE SET
                    romano = EXCLUDED.romano,
                    nome = EXCLUDED.nome,
                    texto = EXCLUDED.texto,
                    fonte_documento = EXCLUDED.fonte_documento,
                    fonte_url = EXCLUDED.fonte_url,
                    dataset_versao = EXCLUDED.dataset_versao,
                    texto_hash = EXCLUDED.texto_hash
                """,
                {
                    **row,
                    "fonte_documento": FONTE_DOCUMENTO,
                    "fonte_url": FONTE_PDF_URL,
                    "dataset_versao": DATASET_VERSAO,
                    "texto_hash": texto_hash(row["texto"]),
                },
            )
    return {
        "habilidades": len(habs),
        "redacao": len(reds),
        "eixos": len(payload.get("eixos") or []),
    }
