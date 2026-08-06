"""Dicionário canônico AEE (Atendimento Educacional Especializado) — Inove4us.

Cada condição possui:
- descricao_base_canonica: política / texto legal-orientador
- campos_experiencia_metodologica_canonica: roteiro prático de adaptações
"""
from __future__ import annotations

from typing import Any

# Ordem estável para UI / API
CONDICOES_ORDEM: list[str] = [
    "TEA",
    "TDAH",
    "Altas Habilidades",
    "Deficiência Intelectual",
    "Deficiência Visual",
    "Deficiência Auditiva",
    "Deficiência Física",
    "Outras Dificuldades Severas",
]

AEE_CANONICO: dict[str, dict[str, str]] = {
    "TEA": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Transtorno do Espectro Autista (TEA)\n\n"
            "Fundamento: LBI (Lei 13.146/2015), Política Nacional de Educação Especial "
            "na Perspectiva da Educação Inclusiva e diretrizes de AEE.\n\n"
            "Princípios: previsibilidade, comunicação alternativa/aumentativa quando "
            "necessário, redução de sobrecarga sensorial, rotinas claras e parceria "
            "família–escola–rede de apoio.\n\n"
            "A escola assegura avaliação funcional das barreiras, metas realistas, "
            "revisão periódica do plano e participação plena nas atividades escolares "
            "com os apoios necessários."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Privilegiar metodologias visuais e sequências previsíveis.\n"
            "No PBL, quebrar o problema em micro-entregas com checklists ilustrados.\n"
            "Na Sala de Aula Invertida, antecipar materiais em 48h e oferecer roteiro "
            "de atenção (o que observar / o que anotar).\n"
            "Em Design Thinking, limitar etapas abertas; usar templates e exemplos "
            "concretos antes da exploração livre.\n"
            "Evitar mudanças bruscas de ambiente; sinalizar transições com cartões "
            "ou timers visuais."
        ),
    },
    "TDAH": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Transtorno de Déficit de Atenção/Hiperatividade (TDAH)\n\n"
            "Fundamento: equidade de aprendizagem, acessibilidade pedagógica e "
            "monitoramento contínuo das barreiras de atenção, impulsividade e "
            "organização do tempo.\n\n"
            "Princípios: instruções curtas e objetivas, fragmentação de tarefas, "
            "feedback frequente, espaços de movimento regulado e critérios de "
            "avaliação que valorizem o processo além do produto final."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Privilegiar metodologias com ciclos curtos (sprints, estações, microdesafios).\n"
            "No PBL, definir marcos diários/semanais e check-ins de 5 minutos.\n"
            "Na Sala de Aula Invertida, antecipar materiais e oferecer guia de foco "
            "(tempo estimado por trecho).\n"
            "Em aprendizagem colaborativa, papéis claros e turnos curtos de fala.\n"
            "Permitir pausas motoras e uso de timers; reduzir tarefas longas sem "
            "quebra intermediária."
        ),
    },
    "Altas Habilidades": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Altas Habilidades / Superdotação\n\n"
            "Fundamento: enriquecimento curricular, aceleração quando indicada e "
            "respeito ao ritmo e profundidade de interesse do estudante.\n\n"
            "Princípios: aprofundamento, autonomia orientada, mentoria e oportunidades "
            "de produção criativa/científica, sem isolamento social."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Oferecer trilhas de aprofundamento e projetos de extensão ao núcleo "
            "curricular.\n"
            "No PBL, permitir escopos avançados e critérios de excelência explícitos.\n"
            "Na Sala de Aula Invertida, disponibilizar materiais de nível desafiador "
            "e mentoria assíncrona.\n"
            "Em Design Thinking / Maker, estimular protótipos complexos e documentação "
            "reflexiva.\n"
            "Evitar apenas 'mais do mesmo'; priorizar complexidade e transferência."
        ),
    },
    "Deficiência Intelectual": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Deficiência Intelectual\n\n"
            "Fundamento: funcionalidade, autonomia progressiva, ensino explícito e "
            "adaptação de objetivos sem exclusão do currículo comum.\n\n"
            "Princípios: linguagem acessível, modelagem, prática guiada, generalização "
            "para contextos reais e avaliação por evidências de progresso funcional."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Privilegiar modelagem passo a passo e apoios visuais permanentes.\n"
            "No PBL, reduzir carga abstrata; usar problemas concretos do cotidiano "
            "escolar.\n"
            "Na Sala de Aula Invertida, materiais curtos, repetição espaçada e "
            "acompanhamento adulto/pares.\n"
            "Em metodologias colaborativas, duplas estruturadas com papel de apoio.\n"
            "Avaliar por rubricas simplificadas e portfólio de evidências."
        ),
    },
    "Deficiência Visual": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Deficiência Visual\n\n"
            "Fundamento: acessibilidade de materiais, tecnologias assistivas e "
            "organização espacial previsível.\n\n"
            "Princípios: contraste/ampliação ou Braille conforme necessidade, "
            "descrições auditivas, tempo adicional e mobilidade segura no ambiente."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Garantir materiais em formato acessível (áudio, texto ampliado, Braille, "
            "leitor de tela).\n"
            "No PBL, descrever imagens/mapas e usar maquetes táteis quando possível.\n"
            "Na Sala de Aula Invertida, antecipar arquivos compatíveis com leitores "
            "de tela em 48h.\n"
            "Em atividades práticas, orientar verbalmente posições e trajetos.\n"
            "Evitar dependência exclusiva de pistas exclusivamente visuais."
        ),
    },
    "Deficiência Auditiva": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Deficiência Auditiva / Surdez\n\n"
            "Fundamento: Libras, legendas, comunicação visual e acessibilidade "
            "informacional.\n\n"
            "Princípios: contato visual, redução de ruído, intérprete quando "
            "necessário e materiais bilíngues/visuais."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Privilegiar canais visuais (slides claros, gestos, legendas).\n"
            "No PBL, registrar combinados por escrito e em Libras quando aplicável.\n"
            "Na Sala de Aula Invertida, vídeos legendados e antecipação de glossário.\n"
            "Em discussões orais, turnos sinalizados e sínteses escritas.\n"
            "Posicionar o estudante com boa visão do interlocutor/intérprete."
        ),
    },
    "Deficiência Física": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Deficiência Física\n\n"
            "Fundamento: acessibilidade arquitetônica e pedagógica, mobilidade e "
            "recursos de apoio à escrita/manipulação.\n\n"
            "Princípios: adaptações de mobiliário, tempo flexível, tecnologias "
            "assistivas e participação em todas as experiências escolares."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Adequar estações de trabalho e trajetos antes da aula.\n"
            "No PBL / Maker, prever ferramentas e papéis que não dependam apenas "
            "de destreza fina.\n"
            "Na Sala de Aula Invertida, permitir registros digitais alternativos.\n"
            "Em atividades motoras, oferecer equivalentes funcionais com dignidade.\n"
            "Planejar tempo extra para deslocamento e organização de materiais."
        ),
    },
    "Outras Dificuldades Severas": {
        "descricao_base_canonica": (
            "DIRETRIZ AEE — Outras Dificuldades Severas de Aprendizagem / Desenvolvimento\n\n"
            "Fundamento: abordagem funcional das barreiras (linguagem, memória, "
            "regulação emocional, saúde etc.) com plano personalizado.\n\n"
            "Princípios: avaliação multidimensional, metas prioritárias, articulação "
            "com rede de saúde/assistência e revisão frequente."
        ),
        "campos_experiencia_metodologica_canonica": (
            "Mapear barreiras prioritárias e escolher 1–2 adaptações de alto impacto "
            "por trimestre.\n"
            "No PBL, simplificar enunciados e oferecer âncoras de início (primeira "
            "ação explícita).\n"
            "Na Sala de Aula Invertida, antecipar materiais e tutoriais curtos.\n"
            "Em qualquer metodologia, prever plano B sensorial/emocional e ponto "
            "de apoio adulto.\n"
            "Documentar o que funciona para replicar entre professores."
        ),
    },
}


def listar_condicoes() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for nome in CONDICOES_ORDEM:
        item = AEE_CANONICO[nome]
        out.append(
            {
                "condicao_categoria": nome,
                "descricao_base_canonica": item["descricao_base_canonica"],
                "campos_experiencia_metodologica_canonica": item[
                    "campos_experiencia_metodologica_canonica"
                ],
            }
        )
    return out


def get_canonico(condicao: str) -> dict[str, str] | None:
    key = str(condicao or "").strip()
    if key in AEE_CANONICO:
        return dict(AEE_CANONICO[key])
    # match case-insensitive
    for nome, data in AEE_CANONICO.items():
        if nome.lower() == key.lower():
            return dict(data)
    return None


def condicao_valida(condicao: str) -> bool:
    return get_canonico(condicao) is not None
