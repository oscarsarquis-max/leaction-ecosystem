"""Chunking hierárquico de Markdown (header-aware + breadcrumb)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class MarkdownChunk:
    """Um pedaço de seção com trilha de títulos."""

    text: str
    breadcrumb: str
    heading: str
    level: int
    doc_title: str
    tipo: Optional[str] = None
    frontmatter: dict[str, Any] | None = None

    @property
    def indexed_text(self) -> str:
        """Texto enviado ao embedder (breadcrumb + corpo)."""
        body = self.text.strip()
        if self.breadcrumb:
            return f"{self.breadcrumb}\n\n{body}".strip()
        return body


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extrai YAML frontmatter simples (chave: valor) se existir."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    meta: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip().strip("\"'")
        if key:
            meta[key] = value
    body = content[match.end() :]
    return meta, body


def infer_tipo_from_path_and_meta(
    rel_path: str,
    frontmatter: dict[str, Any] | None = None,
) -> str:
    """Infere PRD|SDD|DOC a partir de frontmatter, pasta ou nome do arquivo."""
    fm = frontmatter or {}
    raw = str(fm.get("tipo") or fm.get("type") or "").strip().upper()
    if raw in {"PRD", "SDD", "DOC", "PLAYBOOK", "ADR"}:
        return raw

    norm = rel_path.replace("\\", "/").lower()
    name = norm.rsplit("/", 1)[-1]
    if "/prd/" in f"/{norm}" or name.startswith("prd") or "prd-" in name or name.endswith("-prd.md"):
        return "PRD"
    if "/sdd/" in f"/{norm}" or name.startswith("sdd") or "sdd-" in name or name.endswith("-sdd.md"):
        return "SDD"
    if "prd" in name:
        return "PRD"
    if "sdd" in name:
        return "SDD"
    return "DOC"


def chunk_markdown(
    content: str,
    *,
    rel_path: str = "",
    max_heading_level: int = 3,
) -> list[MarkdownChunk]:
    """
    Divide markdown por headings h1..h{max_heading_level}.

    Cada chunk preserva breadcrumb: "Titulo > Secao > Sub".
    Conteúdo antes do primeiro heading vira chunk com heading = doc_title.
    """
    frontmatter, body = parse_frontmatter(content)
    doc_title = str(
        frontmatter.get("title")
        or frontmatter.get("titulo")
        or _title_from_path(rel_path)
        or "Documento"
    ).strip()
    tipo = infer_tipo_from_path_and_meta(rel_path, frontmatter)

    lines = body.splitlines()
    # stack: list[(level, title)]
    stack: list[tuple[int, str]] = []
    sections: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_heading = doc_title
    current_level = 0
    saw_heading = False

    def flush() -> None:
        nonlocal current_lines, current_heading, current_level
        text = "\n".join(current_lines).strip()
        if not text and not sections:
            # ignora preâmbulo vazio
            current_lines = []
            return
        if not text and saw_heading:
            current_lines = []
            return
        crumb_parts = [t for _, t in stack]
        if not crumb_parts and current_heading:
            crumb_parts = [current_heading]
        breadcrumb = " > ".join(crumb_parts)
        sections.append(
            {
                "text": text or current_heading,
                "breadcrumb": breadcrumb,
                "heading": current_heading,
                "level": current_level,
            }
        )
        current_lines = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if level <= max_heading_level:
                flush()
                saw_heading = True
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                current_heading = title
                current_level = level
                continue
        current_lines.append(line)

    flush()

    if not sections:
        sections.append(
            {
                "text": body.strip() or doc_title,
                "breadcrumb": doc_title,
                "heading": doc_title,
                "level": 0,
            }
        )

    # Prefixa breadcrumb com doc_title quando o h1 não é o título do doc
    chunks: list[MarkdownChunk] = []
    for sec in sections:
        breadcrumb = sec["breadcrumb"]
        if doc_title and not breadcrumb.startswith(doc_title):
            # se o primeiro nível já é o h1 igual ao doc_title, ok; senão prefixa
            first = breadcrumb.split(" > ", 1)[0]
            if first != doc_title:
                breadcrumb = f"{doc_title} > {breadcrumb}" if breadcrumb else doc_title
        chunks.append(
            MarkdownChunk(
                text=sec["text"],
                breadcrumb=breadcrumb,
                heading=sec["heading"],
                level=sec["level"],
                doc_title=doc_title,
                tipo=tipo,
                frontmatter=frontmatter or None,
            )
        )
    return chunks


def _title_from_path(rel_path: str) -> str:
    if not rel_path:
        return ""
    name = rel_path.replace("\\", "/").rsplit("/", 1)[-1]
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name.replace("-", " ").replace("_", " ").strip()
