"""Render report snapshot JSON to PDF bytes (ReportLab)."""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_report_pdf(snapshot: dict[str, Any], *, report_id: str, version_no: int) -> bytes:
    """Build a compact PDF from immutable structured_content. No secrets."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"QMind Report v{version_no}",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "QTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=8,
        textColor=colors.HexColor("#0f3d3e"),
    )
    h2 = ParagraphStyle(
        "QH2",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#0f3d3e"),
    )
    body = ParagraphStyle("QBody", parent=styles["Normal"], fontSize=9, leading=12)

    story: list[Any] = []
    story.append(Paragraph("QMind — Relatorio de Avaliacao", title))
    story.append(
        Paragraph(
            f"Report ID: {_esc(report_id)} · Versao: {version_no} · "
            f"Imutavel: {bool(snapshot.get('immutable'))}",
            body,
        )
    )
    story.append(Spacer(1, 6))

    findings = snapshot.get("findings") or []
    story.append(Paragraph(f"Constatações ({len(findings)})", h2))
    if not findings:
        story.append(Paragraph("Nenhuma constatação no snapshot.", body))
    else:
        rows = [["Tipo", "Titulo", "Status"]]
        for f in findings[:40]:
            rows.append(
                [
                    _esc(str(f.get("finding_type") or "")),
                    _esc(str(f.get("title") or "")[:80]),
                    _esc(str(f.get("status") or "")),
                ]
            )
        story.append(_table(rows))

    maturity = snapshot.get("maturity") or {}
    story.append(Paragraph("Maturidade", h2))
    if maturity:
        story.append(
            Paragraph(
                f"Pacote: {_esc(str(maturity.get('id') or '—'))} · "
                f"Versao: {maturity.get('version_no', '—')} · "
                f"Status: {_esc(str(maturity.get('status') or '—'))}",
                body,
            )
        )
        agg = maturity.get("aggregates") or maturity.get("summary") or {}
        if isinstance(agg, dict) and agg:
            story.append(Paragraph(f"Agregados: {_esc(str(agg)[:400])}", body))
    else:
        story.append(Paragraph("Maturidade nao incluida neste snapshot.", body))

    plan = snapshot.get("action_plan") or {}
    story.append(Paragraph("Plano de acao", h2))
    if plan:
        item_ids = plan.get("item_ids") or []
        story.append(
            Paragraph(
                f"Plano: {_esc(str(plan.get('id') or '—'))} · "
                f"Itens: {len(item_ids)} · Status: {_esc(str(plan.get('status') or '—'))}",
                body,
            )
        )
    else:
        story.append(Paragraph("Plano de acao nao incluido neste snapshot.", body))

    evo = snapshot.get("evolution_map") or {}
    story.append(Paragraph("Oportunidades de Evolucao Empresarial", h2))
    if evo:
        story.append(
            Paragraph(
                f"Pacote v{evo.get('package_version', '—')} · "
                f"Modo: {_esc(str(evo.get('generation_mode') or '—'))}",
                body,
            )
        )
        sug = evo.get("suggestions") or []
        if not sug:
            story.append(
                Paragraph(
                    "Nenhuma sugestao aceita, marcada para aprofundar ou convertida.",
                    body,
                )
            )
        else:
            rows = [["Titulo", "Situacao", "Prioridade"]]
            for s in sug[:30]:
                rows.append(
                    [
                        _esc(str(s.get("title") or "")[:90]),
                        _esc(str(s.get("status") or "")),
                        _esc(str(s.get("priority") or "")),
                    ]
                )
            story.append(_table(rows))
    else:
        story.append(Paragraph("Mapa de evolucao nao incluido neste snapshot.", body))

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Documento gerado pelo worker QMind a partir do snapshot imutavel. "
            "Acesso controlado por membership e isolamento multiempresa.",
            body,
        )
    )
    doc.build(story)
    data = buf.getvalue()
    if not data.startswith(b"%PDF"):
        raise RuntimeError("pdf_render_invalid")
    return data


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _table(rows: list[list[str]]) -> Table:
    t = Table(rows, hAlign="LEFT", colWidths=[30 * mm, 100 * mm, 30 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8ebe9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9db8b6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t
