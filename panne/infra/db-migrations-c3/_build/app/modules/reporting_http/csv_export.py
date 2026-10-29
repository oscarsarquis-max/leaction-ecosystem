"""CSV UTF-8 com proteção contra fórmula e semântica de ausência."""

import csv
from io import StringIO


def neutralize(value) -> str:
    text = "" if value is None else str(value)
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def build_csv(payload: dict) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["# relatorio", payload.get("report_code")])
    writer.writerow(["# versao", payload.get("report_version")])
    writer.writerow(["# hash", payload.get("content_hash")])
    writer.writerow(["# corte", payload.get("data_cutoff_at")])
    writer.writerow(["# periodo_inicio", payload.get("period_start")])
    writer.writerow(["# periodo_fim", payload.get("period_end")])
    writer.writerow(["# fuso", payload.get("timezone")])
    writer.writerow(["# completude", payload.get("completeness")])
    writer.writerow(["codigo", "nome", "status", "valor", "unidade", "motivo", "universo", "validos", "ausentes"])
    for item in payload.get("indicators") or []:
        cover = item.get("coverage") or {}
        value = item.get("value")
        if item.get("status") == "unavailable":
            rendered = ""
        else:
            rendered = value
        writer.writerow(
            [
                neutralize(item.get("code")),
                neutralize(item.get("name")),
                neutralize(item.get("status")),
                rendered,
                neutralize(item.get("unit")),
                neutralize(item.get("reason")),
                cover.get("universe"),
                cover.get("valid_count"),
                cover.get("missing_count"),
            ]
        )
    return buffer.getvalue()
