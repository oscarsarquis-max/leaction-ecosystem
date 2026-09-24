"""Prompt do conteúdo sugerido da disciplina (Dia a Dia, prompts 86/149).

Uma geração por tema oficial × nível da turma. Sem metodologia, sem AEE.
BNCC = assunto curricular. ENEM = habilidade cognitiva cobrada na prova.
"""
from __future__ import annotations


def build_system_prompt(*, fonte: str = "bncc") -> str:
    base = (
        "Você é um professor experiente do ensino básico brasileiro. "
        "Gere um roteiro curto e prático para o professor usar em aula. "
        "Não escolha metodologia. Não adapte para AEE. Não invente códigos. "
        "Responda SOMENTE um JSON válido, sem markdown, com as chaves: "
        "pontos_chave (array de 3 a 5 strings), "
        "vocabulario (array de 4 a 8 termos curtos), "
        "equivoco_comum (string), "
        "analogia (string adequada à idade), "
        "pergunta_abertura (string), "
        "perguntas_alunos (array de 2 ou 3 objetos {pergunta, resposta}), "
        "checklist_material (array de 3 a 6 itens físicos ou digitais)."
    )
    if (fonte or "").strip().lower() == "enem":
        return (
            base
            + " O dado de entrada é uma HABILIDADE ou COMPETÊNCIA AVALIADA no ENEM, "
            "não um tema de conteúdo. O roteiro deve treinar o que a prova cobra "
            "(operação cognitiva, leitura de enunciado, tipo de item), sem tratar "
            "o código ENEM como se fosse um assunto da ementa."
        )
    return (
        base
        + " O dado de entrada é um TEMA de conteúdo curricular da BNCC: aborde este assunto."
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
    origem = (fonte or "bncc").strip().lower()
    linhas = [
        f"Disciplina: {disciplina or 'não informada'}",
        f"Nível da turma: {nivel_turma}",
        f"Fonte: {origem}",
    ]
    if origem == "enem":
        linhas.append(
            "Natureza: habilidade/competência avaliada no ENEM — desenvolva esta "
            "operação cognitiva cobrada na prova. Não trate o enunciado como tema "
            "de conteúdo genérico."
        )
        if habilidade_codigo:
            linhas.append(f"Habilidade ENEM: {habilidade_codigo}")
        if tema:
            linhas.append(f"Recorte: {tema}")
    else:
        linhas.append(f"Tema: {tema}")
        if habilidade_codigo:
            linhas.append(f"Habilidade BNCC: {habilidade_codigo}")
    if texto_oficial:
        linhas.append(f"Texto oficial:\n{texto_oficial}")
    linhas.append(
        "Escreva em português do Brasil, linguagem de sala de aula, sem jargão de sistema."
    )
    return "\n".join(linhas)
