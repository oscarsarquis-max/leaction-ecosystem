"""Mensagens e helpers amigáveis da importação (sem jargão técnico na UI)."""

from __future__ import annotations

import hashlib
import re
from typing import Any


# Códigos internos → texto para o professor
MSG = {
    "data_ausente": "Faltou a data desta aula. Corrija e tente novamente.",
    "data_invalida": "A data desta aula não foi reconhecida. Use o formato dia/mês/ano.",
    "titulo_ausente": "Faltou o título desta aula ou evento.",
    "disciplina_nao_encontrada": (
        "Não encontramos '{nome}' no seu cadastro. Esta aula será importada sem esse vínculo."
    ),
    "vinculo_parcial": (
        "Instituição ou curso informados sem disciplina. Esta aula será importada sem vínculo."
    ),
    "atualizado": "Esta aula já tinha sido importada antes; os dados foram atualizados.",
    "criado": "Aula ou evento criado com sucesso.",
    "arquivo_vazio": "Não encontramos nenhuma linha de aula ou evento neste arquivo.",
    "arquivo_grande": "Este arquivo tem muitas linhas. Divida em partes menores e tente novamente.",
    "arquivo_invalido": (
        "Não foi possível ler este arquivo. Envie uma planilha de planejamento e tente novamente."
    ),
    "sem_sessao": "Sua sessão expirou. Entre novamente para continuar.",
    "falha_gravar": "Não foi possível salvar esta linha. Corrija os dados e tente novamente.",
    "pendente": "Esta linha precisa de correção antes de ser importada.",
}


CAMPOS_DESTINO = [
    {"key": "titulo", "label": "Título da aula ou evento"},
    {"key": "data", "label": "Data"},
    {"key": "hora_inicio", "label": "Horário de início"},
    {"key": "hora_fim", "label": "Horário de término"},
    {"key": "tipo", "label": "É aula ou é evento?"},
    {"key": "instituicao", "label": "Instituição"},
    {"key": "curso", "label": "Curso"},
    {"key": "disciplina", "label": "Disciplina"},
    {"key": "assunto", "label": "Assunto"},
    {"key": "observacoes", "label": "Observações"},
    {"key": "", "label": "(não usar esta coluna)"},
]


# Aliases para mapeamento automático (inclui nomes amigáveis e técnicos legados)
ALIASES = {
    "titulo": {
        "titulo",
        "titulo_da_aula",
        "titulo_da_aula_ou_evento",
        "title",
        "nome",
        "aula",
        "nome_da_aula",
    },
    "data": {
        "data",
        "date",
        "data_da_aula",
        "dia",
        "data_planejada",
        "data_evento",
    },
    "hora_inicio": {
        "hora_inicio",
        "inicio",
        "horario_inicio",
        "horário_de_início",
        "horario_de_inicio",
        "start",
        "hora",
    },
    "hora_fim": {
        "hora_fim",
        "fim",
        "horario_fim",
        "horário_de_término",
        "horario_de_termino",
        "end",
    },
    "tipo": {
        "tipo",
        "type",
        "e_aula_ou_evento",
        "e_aula_ou_e_evento",
        "aula_ou_evento",
        "tipo_aula_ou_evento",
    },
    "instituicao": {"instituicao", "instituição", "escola", "instituicao_nome"},
    "curso": {"curso", "curso_nome", "turma_curso"},
    "disciplina": {"disciplina", "disciplina_nome", "materia", "matéria"},
    "assunto": {
        "assunto",
        "tema",
        "theme",
        "sequencia",
        "sequência",
        "unidade",
        "bloco",
    },
    "observacoes": {
        "observacoes",
        "observações",
        "obs",
        "nota",
        "notas",
        "descricao",
        "descrição",
    },
    # legado — mapeados mas não exibidos na UI
    "id_externo": {"id_externo", "id", "external_id", "codigo", "código"},
    "vinculo_pai_id_externo": {
        "vinculo_pai_id_externo",
        "pai_id_externo",
        "parent_id",
        "vinculo_pai",
    },
}


def msg(code: str, **kwargs: Any) -> str:
    template = MSG.get(code) or MSG["falha_gravar"]
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def norm_header(raw: str) -> str:
    text = str(raw or "").strip().lower()
    text = text.replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a")
    text = text.replace("é", "e").replace("ê", "e")
    text = text.replace("í", "i")
    text = text.replace("ó", "o").replace("ô", "o").replace("õ", "o")
    text = text.replace("ú", "u").replace("ç", "c")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def sugerir_mapeamento(colunas: list[str]) -> dict[str, str]:
    """coluna_arquivo → campo destino (ou '')."""
    used: set[str] = set()
    out: dict[str, str] = {}
    for col in colunas:
        nk = norm_header(col)
        matched = ""
        for canon, aliases in ALIASES.items():
            if canon in ("id_externo", "vinculo_pai_id_externo"):
                continue
            if nk in aliases and canon not in used:
                matched = canon
                used.add(canon)
                break
        out[col] = matched
    return out


def make_id_externo(
    id_clie: int,
    *,
    instituicao: str,
    data_iso: str,
    titulo: str,
    disciplina: str = "",
) -> str:
    raw = "|".join(
        [
            str(int(id_clie)),
            (instituicao or "").strip().lower(),
            (data_iso or "").strip(),
            (titulo or "").strip().lower(),
            (disciplina or "").strip().lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def format_data_br(iso_or_date: Any) -> str:
    text = str(iso_or_date or "")[:10]
    if len(text) == 10 and text[4] == "-":
        y, m, d = text.split("-")
        return f"{d}/{m}/{y}"
    return text


def tipo_label(tipo: str) -> str:
    return "Evento" if str(tipo or "").lower() == "evento" else "Aula"


def tipo_from_label(raw: str) -> str:
    t = norm_header(raw)
    if t in {"evento", "event", "compromisso", "reuniao", "reunião"}:
        return "evento"
    return "aula"
