"""Prompt do conteúdo sugerido da disciplina (Dia a Dia, prompt 86).

Uma geração por tema × nível da turma. Sem metodologia, sem AEE.
"""
from __future__ import annotations


def build_system_prompt() -> str:
    return (
        "Você é um professor experiente do ensino básico brasileiro. "
        "Gere um roteiro curto e prático do CONTEÚDO da disciplina para o professor usar em aula. "
        "Não escolha metodologia. Não adapte para AEE. Não invente códigos BNCC. "
        "Responda SOMENTE um JSON válido, sem markdown, com as chaves: "
        "pontos_chave (array de 3 a 5 strings), "
        "vocabulario (array de 4 a 8 termos curtos), "
        "equivoco_comum (string), "
        "analogia (string adequada à idade), "
        "pergunta_abertura (string), "
        "perguntas_alunos (array de 2 ou 3 objetos {pergunta, resposta}), "
        "checklist_material (array de 3 a 6 itens físicos ou digitais)."
    )


def build_user_prompt(
    *,
    tema: str,
    nivel_turma: str,
    disciplina: str = "",
    habilidade_codigo: str = "",
    texto_oficial: str = "",
    fonte: str = "bncc",
) -> str:
    linhas = [
        f"Disciplina: {disciplina or 'não informada'}",
        f"Nível da turma: {nivel_turma}",
        f"Tema: {tema}",
        f"Fonte: {fonte}",
    ]
    if habilidade_codigo:
        linhas.append(f"Habilidade BNCC: {habilidade_codigo}")
    if texto_oficial:
        linhas.append(f"Texto oficial da habilidade:\n{texto_oficial}")
    linhas.append(
        "Escreva em português do Brasil, linguagem de sala de aula, sem jargão de sistema."
    )
    return "\n".join(linhas)
