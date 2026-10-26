"""Catálogo local dos participantes do STR.

A fonte é o CSV oficial do Banco Central. A aplicação não consulta o BCB a cada tecla.
ISPB, número-código e participação na Compe são campos diferentes e não se substituem.
"""

import csv
import os
import unicodedata

SOURCE_URL = "https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv"
OBTAINED_ON = "2026-10-26"
OFFICIAL_NOTE = (
    "O CSV não traz uma data de atualização no arquivo. O Banco Central descreve a relação como atualizada diariamente. "
    "A data de obtenção desta cópia é 2026-10-26 e não é a data oficial de atualização."
)

ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ROOT, "catalog", "ParticipantesSTR.csv")


def fold(value):
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(text.lower().split())


def _code(value):
    text = str(value or "").strip()
    if not text or text.lower() == "n/a" or not text.isdigit() or len(text) != 3 or text == "000":
        return ""
    return text


def _rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load():
    items = []
    for raw in _rows():
        full = " ".join(str(raw.get("Nome_Extenso") or "").split())
        short = " ".join(str(raw.get("Nome_Reduzido") or "").split())
        ispb = str(raw.get("ISPB") or "").strip()
        code = _code(raw.get("Número_Código"))
        joined = (full + " " + short).upper()
        liquidating = "LIQUIDA" in joined
        items.append({
            "ispb": ispb,
            "code": code,
            "name": full or short,
            "shortName": short,
            "compe": str(raw.get("Participa_da_Compe") or "").strip(),
            "access": str(raw.get("Acesso_Principal") or "").strip(),
            "startedOn": str(raw.get("Início_da_Operação") or "").strip(),
            "selectable": bool((full or short) and ispb and not liquidating),
            "liquidating": liquidating,
        })
    items.sort(key=lambda item: (item["code"] or "9999", fold(item["name"]), item["ispb"]))
    return items


CATALOG = load()
BY_CODE = {}
BY_ISPB = {}
for _item in CATALOG:
    if _item["code"]:
        BY_CODE.setdefault(_item["code"], []).append(_item)
    if _item["ispb"]:
        BY_ISPB[_item["ispb"]] = _item


def summary():
    selectable = [item for item in CATALOG if item["selectable"]]
    return {
        "sourceUrl": SOURCE_URL,
        "obtainedOn": OBTAINED_ON,
        "officialUpdate": "",
        "note": OFFICIAL_NOTE,
        "rows": len(CATALOG),
        "withCode": sum(1 for item in CATALOG if item["code"]),
        "withoutCode": sum(1 for item in CATALOG if not item["code"]),
        "liquidating": sum(1 for item in CATALOG if item["liquidating"]),
        "selectable": len(selectable),
        "coverage": "Participantes do STR no Brasil. Não é catálogo mundial nem a lista de todos os tipos de instituição.",
    }


def public_banks():
    banks = []
    for item in CATALOG:
        if not item["selectable"]:
            continue
        banks.append({
            "code": item["code"],
            "name": item["name"],
            "shortName": item["shortName"],
            "ispb": item["ispb"],
        })
    return banks


def same_name(item, institution):
    folded = fold(institution)
    return folded and folded in (fold(item["name"]), fold(item["shortName"]))


def match_choice(code, institution, ispb):
    code = str(code or "").strip()
    ispb = str(ispb or "").strip()
    institution = " ".join(str(institution or "").split())
    if code and code in BY_CODE:
        for item in BY_CODE[code]:
            if item["selectable"] and same_name(item, institution):
                return item
        return None
    if ispb and ispb in BY_ISPB:
        item = BY_ISPB[ispb]
        if item["selectable"] and not item["code"] and same_name(item, institution):
            return item
    return None
