"""Relatório de Execução do PEI — dados + PDF (reportlab)."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


VIOLET = colors.HexColor("#6d28d9")
INK = colors.HexColor("#1e1b4b")
MUTED = colors.HexColor("#64748b")


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-":
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None


def _fmt_br(value: Any) -> str:
    d = _as_date(value)
    if not d:
        return "—"
    return d.strftime("%d/%m/%Y")


def _norm_nome(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def aula_no_periodo(semana: Any, inicio: date | None, fim: date | None) -> bool:
    d = _as_date(semana)
    if not d or not inicio or not fim:
        return False
    return inicio <= d <= fim


def aula_do_aluno(
    mesa: dict[str, Any],
    *,
    pei_id: str,
    aluno_id: str | None,
    aluno_nome: str,
) -> bool:
    if not isinstance(mesa, dict):
        return False
    raw_pei = str(mesa.get("pei_aluno_id") or "").strip()
    if raw_pei and raw_pei == str(pei_id):
        return True
    raw_aluno = str(mesa.get("aluno_id") or "").strip()
    if aluno_id and raw_aluno and raw_aluno == str(aluno_id):
        return True
    nome_mesa = _norm_nome(mesa.get("aluno_nome"))
    alvo = _norm_nome(aluno_nome)
    return bool(alvo and nome_mesa and nome_mesa == alvo)


def _as_mesa(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    return {}


def _diario_da_aula(mesa: dict[str, Any], aluno_nome: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    raw: Any = mesa.get("cards") or mesa.get("kanban_cards") or mesa.get("tarefas")
    if not raw:
        ks = mesa.get("kanban_state")
        if isinstance(ks, dict):
            raw = ks.get("tarefas")
        elif isinstance(ks, list):
            raw = ks
    cards = raw if isinstance(raw, list) else []
    alvo = _norm_nome(aluno_nome)
    for card in cards:
        if not isinstance(card, dict):
            continue
        titulo = str(card.get("titulo") or card.get("titulo_do_card") or "Card").strip()
        hist = card.get("historico") if isinstance(card.get("historico"), list) else []
        notas = []
        for h in hist:
            if isinstance(h, dict) and str(h.get("nota") or "").strip():
                notas.append(str(h.get("nota") or "").strip())
        obs = str(card.get("ultima_observacao") or "").strip()
        if obs and obs not in notas:
            notas.append(obs)
        for nota in notas:
            entries.append({"card": titulo, "nota": nota})
    return entries


def _adaptacoes_aula(mesa: dict[str, Any]) -> dict[str, Any]:
    texto = str(
        mesa.get("pei_adaptation_text")
        or (mesa.get("adaptations") or {}).get("pei")
        or ""
    ).strip()
    versao = mesa.get("pei_override_versao_aplicada")
    cards = []
    raw = mesa.get("cards") or mesa.get("kanban_cards") or []
    if isinstance(raw, list):
        for card in raw:
            if not isinstance(card, dict):
                continue
            if card.get("perfil_inclusao") or card.get("parent_card_id"):
                cards.append(
                    {
                        "titulo": str(card.get("titulo") or card.get("titulo_do_card") or "Card"),
                        "objetivo": str(card.get("objetivo") or "").strip(),
                        "perfil": str(card.get("perfil_inclusao") or "").strip(),
                    }
                )
    return {
        "texto": texto,
        "versao": versao if isinstance(versao, dict) else None,
        "cards": cards,
    }


def montar_dossie(
    *,
    pei: dict[str, Any],
    periodo: dict[str, Any] | None,
    matriz: dict[str, Any] | None,
    aulas: list[dict[str, Any]],
) -> dict[str, Any]:
    inicio = _as_date((periodo or {}).get("data_inicio"))
    fim = _as_date((periodo or {}).get("data_fim"))
    pei_id = str(pei.get("id") or "")
    aluno_id = str(pei.get("aluno_id") or "") or None
    aluno_nome = str(pei.get("nome_completo") or "")
    aulas_aluno = []
    for aula in aulas:
        mesa = _as_mesa(aula.get("mesa") or aula.get("mesa_payload_json"))
        if not aula_do_aluno(
            mesa, pei_id=pei_id, aluno_id=aluno_id, aluno_nome=aluno_nome
        ):
            continue
        if not aula_no_periodo(aula.get("semana_referencia"), inicio, fim):
            continue
        aulas_aluno.append(
            {
                "id": str(aula.get("id") or ""),
                "data": _fmt_br(aula.get("semana_referencia")),
                "turma": aula.get("turma_nome") or "—",
                "metodologia": aula.get("metodologia_nome") or mesa.get("metodologia_nome") or "—",
                "titulo": mesa.get("titulo") or aula.get("conteudo_resumo") or "Aula",
                "adaptacoes": _adaptacoes_aula(mesa),
                "diario": _diario_da_aula(mesa, aluno_nome),
            }
        )
    return {
        "aluno": aluno_nome or "Aluno",
        "matricula": pei.get("matricula") or "—",
        "condicao": pei.get("condicao_categoria") or "—",
        "periodo_rotulo": (periodo or {}).get("rotulo") or (periodo or {}).get("nome") or "—",
        "periodo_inicio": _fmt_br(inicio),
        "periodo_fim": _fmt_br(fim),
        "matriz_texto": str((matriz or {}).get("texto_escola") or "").strip(),
        "matriz_campos": str((matriz or {}).get("campos_experiencia_metodologica") or "").strip(),
        "aulas": aulas_aluno,
        "vazio": not aulas_aluno,
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    safe = (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    return Paragraph(safe or "—", style)


def gerar_pdf_bytes(dossie: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Relatório de Execução do PEI",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TituloDossie",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=VIOLET,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "SecaoDossie",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=VIOLET,
        spaceBefore=12,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "CorpoDossie",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=INK,
        leading=12,
    )
    small = ParagraphStyle(
        "MetaDossie",
        parent=styles["BodyText"],
        fontSize=8,
        textColor=MUTED,
        leading=11,
    )

    story: list[Any] = [
        _p("Relatório de Execução do PEI", title),
        _p(
            f"{dossie.get('aluno')} · Matrícula {dossie.get('matricula')} · "
            f"Condição {dossie.get('condicao')}",
            body,
        ),
        _p(
            f"Período letivo do PEI: {dossie.get('periodo_rotulo')} "
            f"({dossie.get('periodo_inicio')} a {dossie.get('periodo_fim')})",
            small,
        ),
        Spacer(1, 4 * mm),
        _p("1. Matriz canônica da condição", h2),
        _p(dossie.get("matriz_texto") or "Matriz AEE sem texto vigente nesta condição.", body),
    ]
    if dossie.get("matriz_campos"):
        story.append(Spacer(1, 2 * mm))
        story.append(_p("Campos de experiência metodológica", small))
        story.append(_p(dossie.get("matriz_campos"), body))

    story.append(_p("2. Aulas e metodologias cursadas no período", h2))
    aulas = dossie.get("aulas") or []
    if dossie.get("vazio") or not aulas:
        story.append(
            _p(
                "Nenhuma aula deste aluno no período letivo declarado neste PEI. "
                "O relatório não inclui dados de outros alunos.",
                body,
            )
        )
    else:
        rows = [[_p("Data", small), _p("Turma", small), _p("Metodologia", small), _p("Aula", small)]]
        for a in aulas:
            rows.append(
                [
                    _p(a.get("data") or "—", body),
                    _p(a.get("turma") or "—", body),
                    _p(a.get("metodologia") or "—", body),
                    _p(a.get("titulo") or "—", body),
                ]
            )
        table = Table(rows, colWidths=[28 * mm, 38 * mm, 48 * mm, 56 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ddd6fe")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)

    story.append(_p("3. Adaptações metodológicas exibidas ao professor", h2))
    if dossie.get("vazio") or not aulas:
        story.append(_p("Sem adaptações no período — nenhuma aula deste aluno.", body))
    else:
        for a in aulas:
            ad = a.get("adaptacoes") or {}
            story.append(_p(f"{a.get('data')} · {a.get('metodologia')}", small))
            versao = ad.get("versao")
            if versao:
                story.append(
                    _p(
                        "Versão aplicada (pei_override_versao_aplicada): "
                        + ", ".join(f"{k}={v}" for k, v in versao.items()),
                        small,
                    )
                )
            story.append(_p(ad.get("texto") or "Sem texto de adaptação registrado nesta aula.", body))
            for card in ad.get("cards") or []:
                story.append(
                    _p(
                        f"Card PEI “{card.get('titulo')}”"
                        + (f" · {card.get('perfil')}" if card.get("perfil") else "")
                        + (f" — {card.get('objetivo')}" if card.get("objetivo") else ""),
                        body,
                    )
                )

    story.append(_p("4. Diário de bordo — engajamento do aluno", h2))
    if dossie.get("vazio") or not aulas:
        story.append(_p("Sem anotações — nenhuma aula deste aluno no período.", body))
    else:
        alguma = False
        for a in aulas:
            for nota in a.get("diario") or []:
                alguma = True
                story.append(
                    _p(
                        f"{a.get('data')} · {nota.get('card')}: {nota.get('nota')}",
                        body,
                    )
                )
        if not alguma:
            story.append(
                _p(
                    "As aulas do período não têm anotação de diário de bordo sincronizada.",
                    body,
                )
            )

    doc.build(story)
    return buf.getvalue()


def nome_arquivo_pdf(dossie: dict[str, Any]) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", str(dossie.get("aluno") or "aluno"))
    return f"Relatorio_Execucao_PEI_{base[:40]}.pdf"
