"""
Biblioteca de passos canônicos das Metodologias Inov-ativas (Andrea Filatro).

Cada metodologia possui imperativos fixos (título do passo) e um texto-base
que a IA adapta ao nível de ensino, modalidade, participantes e tema citado.
"""

from __future__ import annotations

import unicodedata


def _chave(metodologia: str) -> str:
    texto = metodologia or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower()


# Aprendizagem Baseada em Problemas — Biblioteca de Metodologias Inov-ativas
_PASSOS_ABP = [
    {
        "imperativo": "Apresente a situação-problema",
        "descricao_base": (
            "Escolha uma situação relacionada ao tema do curso ou disciplina e "
            "contextualize-a em aspectos históricos, sociais, técnicos, econômicos, "
            "culturais, éticos ou profissionais. Formule perguntas disparadoras, "
            'como: "O que já sabemos sobre o problema?", "O que ainda precisamos '
            'descobrir?", "Quais hipóteses iniciais parecem plausíveis?", "Que '
            'evidências podem confirmar, revisar ou refutar essas hipóteses?" e '
            '"Que critérios usaremos para escolher uma solução?".'
        ),
    },
    {
        "imperativo": "Estabeleça um contrato didático com e entre os estudantes",
        "descricao_base": (
            "Defina com a turma as regras de trabalho, prazos, produtos esperados, "
            "critérios de participação, formas de registro, organização dos grupos, "
            "fontes de pesquisa e instrumentos de avaliação. O contrato didático "
            "ajuda os estudantes a compreenderem o que eles devem produzir, como "
            "devem colaborar e como serão avaliados."
        ),
    },
    {
        "imperativo": "Oriente a exploração inicial",
        "descricao_base": (
            "Ofereça referências, casos, dados, fontes, vídeos, textos, bases de "
            "informação ou exemplos. O objetivo é apoiar a investigação sem entregar "
            "a solução para o problema. Nessa etapa, ajude os estudantes a identificar "
            "conceitos-chave, lacunas de conhecimento e focos de pesquisa."
        ),
    },
    {
        "imperativo": "Acompanhe a pesquisa e a produção individual",
        "descricao_base": (
            "Peça que cada estudante pesquise em fontes teóricas, técnicas, empíricas "
            "ou digitais e produza uma síntese individual com achados, dúvidas, "
            "hipóteses ou proposta inicial de solução. Durante esse processo, sugira "
            "fontes, apoie a leitura crítica, oriente registros e provoque "
            "aprofundamento conceitual."
        ),
    },
    {
        "imperativo": "Promova a discussão coletiva",
        "descricao_base": (
            "Organize a socialização das pesquisas individuais. Estimule a comparação "
            "de descobertas, a argumentação, a escuta, a identificação de convergências "
            "e divergências e a negociação de caminhos de solução. Essa etapa transforma "
            "a pesquisa individual em construção coletiva."
        ),
    },
    {
        "imperativo": "Oriente a produção coletiva",
        "descricao_base": (
            "Apoie os grupos na construção da proposta de solução. Monitore a colaboração, "
            "a coerência conceitual, a integração das contribuições individuais e a "
            "justificativa das escolhas. A produção pode assumir diferentes formatos, "
            "como proposta, plano de ação, relatório, protótipo, apresentação, "
            "diagnóstico ou solução técnica."
        ),
    },
    {
        "imperativo": "Coordene a apresentação e a avaliação da produção",
        "descricao_base": (
            "Organize a apresentação das soluções e aplique uma rubrica de avaliação "
            "ou outro instrumento de sua preferência. Considere critérios como "
            "pertinência da solução, fundamentação, viabilidade, criatividade, clareza, "
            "aplicabilidade e qualidade técnica. Ofereça feedback para que os estudantes "
            "possam revisar ou aprimorar a proposta."
        ),
    },
    {
        "imperativo": "Conduza a avaliação da aprendizagem e do processo",
        "descricao_base": (
            "Avalie domínio conceitual, raciocínio, investigação, participação, "
            "argumentação, colaboração e contribuição individual para o grupo. Proponha "
            "autoavaliação e/ou avaliação por pares e/ou finalize com uma reflexão sobre "
            "o processo, sistematizando aprendizados e possíveis novas problematizações."
        ),
    },
]

BIBLIOTECA_PASSOS: dict[str, list[dict]] = {
    "aprendizagem baseada em problemas": _PASSOS_ABP,
}


def obter_passos_biblioteca(metodologia: str) -> list[dict] | None:
    """Retorna passos canônicos da metodologia ou None se não cadastrada."""
    if not metodologia:
        return None
    return BIBLIOTECA_PASSOS.get(_chave(metodologia))


def formatar_passos_para_prompt(passos: list[dict]) -> str:
    """Serializa passos canônicos para injeção no prompt da IA."""
    import json

    payload = [
        {
            "ordem": i + 1,
            "imperativo": p["imperativo"],
            "descricao_base": p.get("descricao_base", ""),
        }
        for i, p in enumerate(passos)
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def mesclar_passos_gerados(canonicos: list[dict], gerados: list[dict]) -> list[dict]:
    """Garante imperativos da biblioteca; usa descrições adaptadas pela IA."""
    resultado = []
    for i, canon in enumerate(canonicos):
        gen = gerados[i] if i < len(gerados) else {}
        desc = (
            (gen.get("descricao") or gen.get("desc") or "").strip()
            or canon.get("descricao_base", "")
        )
        resultado.append(
            {
                "titulo": canon["imperativo"],
                "descricao": desc,
                "tempo": (gen.get("tempo") or "").strip(),
            }
        )
    return resultado
