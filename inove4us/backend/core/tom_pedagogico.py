"""
Tom de voz canônico da inove4us — textos para professores e instrutores.

Regras (todo o produto):
- Linguagem simples, direta e completa (não cortar no meio da ideia).
- Vocabulário pedagógico: aprendizagem, turma, objetivo, mediação, evidência,
  feedback, engajamento, prática, avaliação formativa.
- Evitar jargão de sistema ("catálogo", "IA inventou", "framework", "payload").
- Falar com o professor: "na sua aula", "com a sua turma", "para o seu objetivo".
"""

from __future__ import annotations

# Só proteção contra texto absurdamente longo (abuse/bug) — nunca para "caber na UI".
# Textos pedagógicas para o professor devem ir completas.
LIMITE_JUSTIFICATIVA = 8000
LIMITE_DINAMICA_SALA = 8000
LIMITE_MOTIVO = 4000
LIMITE_HIPOTESE = 4000
LIMITE_GANCHO = 4000

BLOCO_TOM_PROMPT = """
<tom_de_voz>
Público: professores e instrutores.
Escreva em português do Brasil, simples, direto e completo — sem cortar a ideia no meio.
Use vocabulário pedagógico (aprendizagem, turma, objetivo, mediação, evidência, feedback, engajamento, prática, avaliação formativa).
Evite jargão técnico de software, marketing vazio e frases genéricas.
Cada frase deve ajudar o professor a decidir o que fazer na aula.
Não mencione "IA", "catálogo interno", "prompt" nem "framework".
</tom_de_voz>
""".strip()


def completar_frase(texto: str, limite: int) -> str:
    """Se precisar limitar, corta só no fim de frase — nunca no meio da palavra."""
    t = " ".join(str(texto or "").split()).strip()
    if not t or len(t) <= limite:
        return t
    corte = t[:limite].rstrip()
    for sep in (". ", "! ", "? ", "; "):
        idx = corte.rfind(sep)
        if idx >= max(80, limite // 4):
            return corte[: idx + 1].strip()
    # último espaço
    idx = corte.rfind(" ")
    if idx >= 60:
        return corte[:idx].rstrip(",;:") + "."
    return corte.rstrip(",;:") + "."


def justificar_para_professor(
    *,
    nome: str,
    etiqueta: str,
    mecanica: str,
    gancho: str = "",
    trecho: str = "",
) -> str:
    """Justificativa completa: o que a dinâmica faz + por que serve nesta aula."""
    nome = (nome or "esta dinâmica").strip()
    etiqueta = (etiqueta or "").strip()
    mecanica = " ".join((mecanica or "").split()).strip()
    gancho = " ".join((gancho or "").split()).strip()
    trecho = " ".join((trecho or "").split()).strip()

    grupo = f", do grupo {etiqueta}," if etiqueta else ""
    partes: list[str] = []
    if mecanica:
        partes.append(
            f"{nome}{grupo} trabalha {mecanica.rstrip('.')}."
        )
    else:
        partes.append(
            f"{nome}{grupo} é uma dinâmica ativa para envolver a turma "
            f"em torno de um objetivo claro de aprendizagem."
        )

    if gancho:
        partes.append(f"Na sua aula: {gancho.rstrip('.')}.")
    elif trecho:
        partes.append(
            f"Na sua aula, isso ajuda a enfrentar o que você descreveu "
            f"(«{trecho}»), com prática mediada e evidência do que a turma aprendeu."
        )
    else:
        partes.append(
            "Na sua aula, use-a para tornar a aprendizagem mais ativa, "
            "com papéis claros e um fechamento que mostre o progresso da turma."
        )

    return completar_frase(" ".join(partes), LIMITE_JUSTIFICATIVA)


def motivo_sugestao_dia(
    *,
    nome: str,
    etiqueta: str,
    descricao: str,
    tema: str = "",
    elos: list[str] | None = None,
    alternativa: bool = False,
) -> str:
    """Motivo completo da sugestão no Dia a Dia."""
    nome = (nome or "esta dinâmica").strip()
    etiqueta = (etiqueta or "").strip()
    desc = " ".join((descricao or "").split()).strip()
    tema_limpo = " ".join((tema or "").split()).strip()
    elos = [e for e in (elos or []) if e]

    if alternativa and tema_limpo:
        cabeca = (
            f"Outra opção para a aula sobre «{tema_limpo}»: {nome}"
            f"{f' (grupo {etiqueta})' if etiqueta else ''}."
        )
    elif tema_limpo:
        cabeca = (
            f"Para a aula sobre «{tema_limpo}», sugerimos {nome}"
            f"{f' (grupo {etiqueta})' if etiqueta else ''}."
        )
    else:
        cabeca = (
            f"{nome}{f' (grupo {etiqueta})' if etiqueta else ''} "
            f"é uma dinâmica ativa adequada a um ciclo de aula."
        )

    meio = ""
    if elos:
        meio = (
            f" Ela ajuda a trabalhar na aula o que você destacou "
            f"({', '.join(elos[:5])})."
        )

    fim = f" {desc}" if desc else (
        " Use-a para mediar a prática da turma e fechar com evidência de aprendizagem."
    )
    return completar_frase(f"{cabeca}{meio}{fim}".strip(), LIMITE_MOTIVO)


def dinamica_em_sala(
    *,
    nome: str,
    objetivo: str = "",
    mecanica: str = "",
    descricao: str = "",
) -> str:
    """Texto completo de 'como conduzir em sala' — sem reticências no meio."""
    nome = (nome or "a dinâmica").strip()
    objetivo = " ".join((objetivo or "").split()).strip()
    mecanica = " ".join((mecanica or "").split()).strip()
    descricao = " ".join((descricao or "").split()).strip()

    if objetivo and mecanica:
        texto = f"{objetivo.rstrip('.')}. Como conduzir: {mecanica}"
    elif mecanica:
        texto = f"Como conduzir «{nome}»: {mecanica}"
    elif objetivo:
        texto = objetivo
    elif descricao:
        texto = descricao
    else:
        texto = (
            f"Conduza «{nome}» em um tempo de aula: apresente o objetivo, "
            f"organize a turma, medeie a prática e feche com um checkout rápido "
            f"do que foi aprendido."
        )
    return completar_frase(texto, LIMITE_DINAMICA_SALA)
