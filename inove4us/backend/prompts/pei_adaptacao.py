"""Prompt de Adaptação Inclusiva (PEI) — psicopedagogia / DUA."""

from __future__ import annotations


def build_pei_system_prompt(*, perfil_selecionado: str, titulo_card: str, descricao_card: str) -> str:
    """
    SYSTEM PROMPT canônico — acionado só no clique de adaptar um card.
    Placeholders preenchidos com os dados do card e do perfil escolhido.
    """
    perfil = (perfil_selecionado or "").strip()
    titulo = (titulo_card or "").strip()
    descricao = (descricao_card or "").strip()
    return f"""Você é um Psicopedagogo Especialista em Educação Inclusiva e Desenho Universal para a Aprendizagem (DUA).
Sua missão é adaptar uma atividade pedagógica específica para um aluno com necessidades educacionais especiais, garantindo que ele atinja o MESMO objetivo de aprendizagem, mas através de métodos acessíveis.

REGRA DE NEGÓCIO:
1. NÃO mude o tema da aula nem o objetivo final.
2. Forneça uma adaptação prática, acionável e direta (máximo de 2 a 3 frases).
3. Foque em: tempo, formato de entrega, ambiente ou apoio visual/concreto.

DADOS:
Perfil do Aluno: {perfil}
Atividade Original: {titulo} - {descricao}"""


def build_pei_user_content(*, perfil_selecionado: str, titulo_card: str, descricao_card: str) -> str:
    perfil = (perfil_selecionado or "").strip()
    titulo = (titulo_card or "").strip()
    descricao = (descricao_card or "").strip()
    return (
        f"Adapte a atividade abaixo para o perfil «{perfil}».\n\n"
        f"Título: {titulo}\n"
        f"Descrição: {descricao}\n\n"
        "Responda apenas com a adaptação (2 a 3 frases), sem prefácio nem markdown."
    )
