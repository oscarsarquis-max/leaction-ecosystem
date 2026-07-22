"""Gera database/biblioteca_passos.json a partir de fonte_faca_facil.txt."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTE = ROOT / "database" / "fonte_faca_facil.txt"
OUT = ROOT / "database" / "biblioteca_passos.json"

# Nome canônico (como em problema_mativa) -> chave normalizada
METODOLOGIAS = [
    "Abordagem Problematizadora",
    "Aprendizagem Baseada em Problemas",
    "Aprendizagem Baseada em Projetos",
    "Aprendizagem Baseada em Casos",
    "Design Thinking",
    "Aprendizagem Maker",
    "Sala de Aula Invertida",
    "World Café",
    "Mapa de Polaridades",
    "Aprendizagem Baseada em Equipes",
    "Narrativas Transmídia em Rotação por Estações",
    "Painel da Diversidade de Perspectivas",
    "Rotina Veja-Pense-Pergunte-Crie",
    "Coaching Reverso",
    "Pedagogia Extrema",
    "EduScrum",
    "Discurso de Elevador",
    "Hackathons",
    "Mapeamento mental",
    "Minute Paper",
    "Pecha Kucha",
    "Canvas Mania",
    "Aprendizagem Baseada em Jogos",
    "Gamificação Estrutural",
    "Gamificação de Conteúdo",
    "Simulações",
    "Roleplay",
    "Jogos Sérios com Blocos 3D",
    "Escape Room",
    "Vivência Metodologia imersiva Multissensorial",
    "Diagnóstico Coletivo",
    "Extrato de Participação",
    "Trilhas de Aprendizagem",
    "Metodologia analítica da Aprendizagem",
    "Inteligência Artificial Generativa",
    "RAG",
    "Chatbots",
    "Mapa de Calor",
    "Dog or Cat: Reconhecimento de Imagens",
]

ALIASES = {
    "aprendizagem baseada em problemas": [
        "aprendizagem baseada em problemas (pbl)",
        "pbl",
        "abp",
    ],
    "world cafe": ["world café"],
    "aprendizagem baseada em equipes": ["team-based learning", "tbl"],
    "discurso de elevador": ["elevator pitch"],
    "hackathons": ["hackathon"],
    "simulacoes": ["simulacao"],
    "escape room": ["escape room educacional"],
    "vivencia metodologia imersiva multissensorial": [
        "vivencia imersiva multissensorial",
        "vivencia metodologia imersiva multissensorial",
    ],
    "metodologia analitica da aprendizagem": [
        "analitica da aprendizagem",
        "analitica da aprendizagem",
    ],
    "chatbots": ["bots personalizaveis"],
    "gamificacao estrutural": ["gamificação estrutural"],
    "gamificacao de conteudo": ["gamificação de conteúdo"],
}


def chave(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def parse_steps(bloco: str) -> list[dict]:
    # Aceita "1.\t", "1. ", e bullet "•" / "-" como passo (Simulações)
    bloco = bloco.replace("\r\n", "\n").replace("\r", "\n")
    # Normaliza bullet final de Simulações para passo numerado
    bloco = re.sub(r"(?m)^\s*[•\-]\s*Faça a síntese", "7. Faça a síntese", bloco)

    matches = list(
        re.finditer(
            r"(?m)^\s*(\d+)\.\s*(.+?)(?=^\s*\d+\.\s|\Z)",
            bloco,
            flags=re.DOTALL,
        )
    )
    passos = []
    esperado = 1
    for m in matches:
        num = int(m.group(1))
        # Nova lista recomeçando em 1 => fim do bloco desta metodologia
        if num == 1 and esperado > 1:
            break
        if num != esperado:
            continue
        corpo = re.sub(r"\s+", " ", m.group(2)).strip()
        if not corpo:
            continue
        # Primeira sentença = imperativo
        m2 = re.match(r"(.+?\.)\s+(.*)", corpo)
        if m2:
            imperativo = m2.group(1).rstrip(".").strip()
            descricao = m2.group(2).strip()
        else:
            imperativo = corpo.rstrip(".").strip()
            descricao = ""
        if imperativo:
            passos.append({"imperativo": imperativo, "descricao_base": descricao})
            esperado += 1
    return passos


def find_step_block(text: str, nome: str) -> str | None:
    """Localiza o bloco 'Passo a passo...' associado à metodologia."""
    k = chave(nome)

    # Casos especiais de título no texto da Andrea
    titulos_alt = {
        "vivencia metodologia imersiva multissensorial": [
            "vivencia imersiva multissensorial",
            "vivência imersiva multissensorial",
        ],
        "metodologia analitica da aprendizagem": [
            "analitica da aprendizagem",
            "analítica da aprendizagem",
        ],
        "gamificacao estrutural": [
            "passo a passo para a implementação da gamificação estrutural"
        ],
        "gamificacao de conteudo": [
            "passo a passo para a implementação da gamificação de conteúdo"
        ],
        "dog or cat: reconhecimento de imagens": [
            "dog or cat: reconhecimento de imagens"
        ],
        "jogos serios com blocos 3d": [
            "jogos sérios com blocos 3d",
            "jogos serios com blocos 3d",
        ],
        "narrativas transmidia em rotacao por estacoes": [
            "narrativas transmídia em rotação por estações",
        ],
        "rotina veja-pense-pergunte-crie": [
            "veja-pense-pergunte-crie",
            "rotina veja-pense-pergunte-crie",
        ],
        "aprendizagem baseada em jogos": [
            "aprendizagem baseada em jogos",
        ],
        "simulacoes": ["simulação", "simulacoes", "simulações"],
        "hackathons": ["hackathon"],
        "mapeamento mental": ["mapeamento mental"],
        "escape room": ["escape room educacional", "escape room"],
    }

    candidatos = [nome] + titulos_alt.get(k, [])
    text_l = text
    text_norm = chave(text)

    # Estratégia: achar "Passo a passo ... <nome>" e capturar até o próximo heading
    for cand in candidatos:
        ck = chave(cand)
        # procura "Passo a passo ... implementação ... <cand>"
        pattern = re.compile(
            rf"Passo a passo[^\n]{{0,120}}{re.escape(cand)}[^\n]*\n(.+?)(?=\n(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{{2,80}})\n|\nMetodologias |\nGamificação\n|\Z)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(text_l)
        if m:
            return m.group(1)

        # fallback: procurar linha de título da metodologia e depois o passo a passo
        # (para seções onde o título vem antes do passo a passo)
        idx = text_norm.find(ck)
        if idx < 0:
            continue
        # map approx index back is hard on normalized text; search original with flexible regex
        flex = re.compile(
            rf"(?is)(?:^|\n)[^\n]*{re.escape(cand)}[^\n]*\n.+?Passo a passo[^\n]*\n(.+?)(?=\n(?:Abordagem |Aprendizagem |Design |Sala |World |Mapa |Narrativas |Painel |Rotina |Coaching |Pedagogia |EduScrum|Discurso |Hackathons|Mapeamento |Minute |Pecha |Canvas |Gamifica|Simula|Roleplay|Jogos |Escape |Vivência |Diagnóstico |Extrato |Trilhas |Analítica |Inteligência |RAG\n|Chatbots|Dog or Cat|Metodologias |\Z))",
        )
        m2 = flex.search(text_l)
        if m2:
            return m2.group(1)

    # Último recurso: qualquer "Passo a passo" contendo pedaço do nome
    trecho = re.escape(nome.split()[0])
    m3 = re.search(
        rf"(?is)Passo a passo[^\n]*{trecho}[^\n]*\n(.+?)(?=\nPasso a passo|\n[A-ZÁÉÍÓÚ][^\n]{{8,60}}\n[A-ZÁ]|\Z)",
        text_l,
    )
    if m3 and chave(nome.split()[0]) in chave(m3.group(0)[:200]):
        return m3.group(1)
    return None


def extract_by_patterns(text: str, nome: str) -> str | None:
    """Extrai bloco com regexes explícitos (fonte de verdade por metodologia)."""
    patterns = {
        "Abordagem Problematizadora": r"(?is)Passo a passo para a implementação da Abordagem Problematizadora\n(.+?)(?=\nAprendizagem Baseada em Problemas\n|\Z)",
        "Aprendizagem Baseada em Problemas": r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Problemas\n(.+?)(?=\nAprendizagem Baseada em Projetos\n|\Z)",
        "Aprendizagem Baseada em Projetos": r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Projetos\n(.+?)(?=\nAprendizagem Baseada em Casos\n|\Z)",
        "Aprendizagem Baseada em Casos": r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Casos\n(.+?)(?=\nDesign Thinking\n|\Z)",
        "Design Thinking": r"(?is)Passo a passo para a implementação do Design Thinking\n(.+?)(?=\nAprendizagem Maker\n|\Z)",
        "Aprendizagem Maker": r"(?is)Passo a passo para a implementação da Aprendizagem Maker\n(.+?)(?=\nSala de Aula Invertida\n|\Z)",
        "Sala de Aula Invertida": r"(?is)Passo a passo para a implementação da Sala de Aula Invertida\s*\n(.+?)(?=\nWorld Café\n|\Z)",
        "World Café": r"(?is)Passo a passo para a implementação do World Café\n(.+?)(?=\nMapa de Polaridades\n|\Z)",
        "Mapa de Polaridades": r"(?is)Passo a passo para a implementação do Mapa de Polaridades\n(.+?)(?=\nAprendizagem Baseada em Equipes\n|\Z)",
        "Aprendizagem Baseada em Equipes": r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Equipes\n(.+?)(?=\nNarrativas Transmídia|\Z)",
        "Narrativas Transmídia em Rotação por Estações": r"(?is)Passo a passo para a implementação das Narrativas Transmídia em Rotação por Estações\n(.+?)(?=\nPainel da Diversidade|\Z)",
        "Painel da Diversidade de Perspectivas": r"(?is)Passo a passo para a implementação do Painel da Diversidade de Perspectivas\n(.+?)(?=\nRotina Veja-Pense-Pergunte-Crie\n|\nVeja-Pense|\Z)",
        "Rotina Veja-Pense-Pergunte-Crie": r"(?is)Passo a passo para a implementação do Veja-Pense-Pergunte-Crie\n(.+?)(?=\nCoaching Reverso\n|\Z)",
        "Coaching Reverso": r"(?is)Passo a passo para a implementação do Coaching Reverso\n(.+?)(?=\nMetodologias ágeis|\Z)",
        "Pedagogia Extrema": r"(?is)Passo a passo para a implementação da Pedagogia Extrema\n(.+?)(?=\nEduScrum\n|\Z)",
        "EduScrum": r"(?is)Passo a passo para a implementação do EduScrum\n(.+?)(?=\nDiscurso de Elevador\n|\Z)",
        "Discurso de Elevador": r"(?is)Passo a passo para a implementação do Discurso de Elevador\n(.+?)(?=\nHackathons\n|\Z)",
        "Hackathons": r"(?is)Passo a passo para a implementação de Hackathon\n(.+?)(?=\nMapeamento mental\n|\Z)",
        "Mapeamento mental": r"(?is)Passo a passo para a implementação do Mapeamento Mental\n(.+?)(?=\nMinute Paper\n|\Z)",
        "Minute Paper": r"(?is)Passo a passo para a implementação do Minute Paper\n(.+?)(?=\nPecha Kucha\n|\Z)",
        "Pecha Kucha": r"(?is)Passo a passo para a implementação da Pecha Kucha\n(.+?)(?=\nCanvas Mania\n|\Z)",
        "Canvas Mania": r"(?is)Passo a passo para a implementação da Canvas Mania\n(.+?)(?=\nMetodologias imersivas|\Z)",
        "Aprendizagem Baseada em Jogos": r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Jogos\n(.+?)(?=\nGamificação\n|\Z)",
        "Gamificação Estrutural": r"(?is)Passo a passo para a implementação da Gamificação Estrutural\n(.+?)(?=\nPasso a passo para a implementação da Gamificação de Conteúdo|\Z)",
        "Gamificação de Conteúdo": r"(?is)Passo a passo para a implementação da Gamificação de Conteúdo\n(.+?)(?=\nSimulações\n|\Z)",
        "Simulações": r"(?is)Passo a passo para a implementação de Simulação\n(.+?)(?=\nRoleplay\n|\Z)",
        "Roleplay": r"(?is)Passo a passo para a implementação do Roleplay\n(.+?)(?=\nJogos Sérios|\Z)",
        "Jogos Sérios com Blocos 3D": r"(?is)Passo a passo para a implementação dos Jogos Sérios com Blocos 3D\n(.+?)(?=\nEscape Room\n|\Z)",
        "Escape Room": r"(?is)Passo a passo para a implementação do Escape Room Educacional\n(.+?)(?=\nVivência|\Z)",
        "Vivência Metodologia imersiva Multissensorial": r"(?is)Passo a passo para a implementação da Vivência Imersiva Multissensorial\n(.+?)(?=\nMetodologias analíticas|\nDiagnóstico Coletivo\n|\Z)",
        "Diagnóstico Coletivo": r"(?is)Passo a passo para a implementação do Diagnóstico Coletivo\n(.+?)(?=\nExtrato de Participação\n|\Z)",
        "Extrato de Participação": r"(?is)Passo a passo para a implementação do Extrato de Participação\n(.+?)(?=\nTrilhas de Aprendizagem\n|\Z)",
        "Trilhas de Aprendizagem": r"(?is)Passo a passo para a implementação das Trilhas de Aprendizagem\n(.+?)(?=\nAnalítica da Aprendizagem\n|\Z)",
        "Metodologia analítica da Aprendizagem": r"(?is)Passo a passo para a implementação da Analítica da Aprendizagem\n(.+?)(?=\nInteligência Artificial Generativa\n|\Z)",
        "Inteligência Artificial Generativa": r"(?is)Passo a passo para a implementação da Inteligência Artificial Generativa\n(.+?)(?=\nRAG\n|\Z)",
        "RAG": r"(?is)Passo a passo para a implementação da RAG\n(.+?)(?=\nChatbots\n|\Z)",
        "Chatbots": r"(?is)Passo a passo para a implementação de Chatbots[^\n]*\n(.+?)(?=\nMapa de Calor\n|\Z)",
        "Mapa de Calor": r"(?is)Passo a passo para a implementação do Mapa de Calor\n(.+?)(?=\nDog or Cat|\Z)",
        "Dog or Cat: Reconhecimento de Imagens": r"(?is)Passo a passo para a implementação do Dog or Cat: Reconhecimento de Imagens\n(.+?)(?=\Z)",
    }
    pat = patterns.get(nome)
    if not pat:
        return None
    m = re.search(pat, text)
    return m.group(1) if m else None


def main() -> None:
    text = FONTE.read_text(encoding="utf-8")
    # Remove possível prefixo da mensagem do usuário ("seguem....")
    marker = "Metodologias (cri)ativas"
    if marker in text:
        text = text[text.index(marker) :]

    biblioteca: dict[str, list[dict]] = {}
    faltando = []
    contagens = {}

    for nome in METODOLOGIAS:
        bloco = extract_by_patterns(text, nome)
        if not bloco:
            bloco = find_step_block(text, nome)
        if not bloco:
            # Tentativas específicas extras
            if nome == "Simulações":
                bloco = find_step_block(text, "Passo a passo para a implementação de Simulação")
            if nome == "Hackathons":
                m = re.search(
                    r"(?is)Passo a passo para a implementação de Hackathon\n(.+?)(?=\nMapeamento mental|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Gamificação Estrutural":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Gamificação Estrutural\n(.+?)(?=\nPasso a passo para a implementação da Gamificação de Conteúdo|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Gamificação de Conteúdo":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Gamificação de Conteúdo\n(.+?)(?=\nSimulações|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Metodologia analítica da Aprendizagem":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Analítica da Aprendizagem\n(.+?)(?=\nInteligência Artificial Generativa|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Vivência Metodologia imersiva Multissensorial":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Vivência Imersiva Multissensorial\n(.+?)(?=\nMetodologias analíticas|\nDiagnóstico Coletivo|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Aprendizagem Baseada em Jogos":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Jogos\n(.+?)(?=\nGamificação|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Escape Room":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Escape Room Educacional\n(.+?)(?=\nVivência|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Jogos Sérios com Blocos 3D":
                m = re.search(
                    r"(?is)Passo a passo para a implementação dos Jogos Sérios com Blocos 3D\n(.+?)(?=\nEscape Room|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Dog or Cat: Reconhecimento de Imagens":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Dog or Cat: Reconhecimento de Imagens\n(.+?)(?=\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "RAG":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da RAG\n(.+?)(?=\nChatbots|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Inteligência Artificial Generativa":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Inteligência Artificial Generativa\n(.+?)(?=\nRAG\n|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Chatbots":
                m = re.search(
                    r"(?is)Passo a passo para a implementação de Chatbots[^\n]*\n(.+?)(?=\nMapa de Calor|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Rotina Veja-Pense-Pergunte-Crie":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Veja-Pense-Pergunte-Crie\n(.+?)(?=\nCoaching Reverso|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Narrativas Transmídia em Rotação por Estações":
                m = re.search(
                    r"(?is)Passo a passo para a implementação das Narrativas Transmídia em Rotação por Estações\n(.+?)(?=\nPainel da Diversidade|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "World Café":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do World Café\n(.+?)(?=\nMapa de Polaridades|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Discurso de Elevador":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Discurso de Elevador\n(.+?)(?=\nHackathons|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Roleplay":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Roleplay\n(.+?)(?=\nJogos Sérios|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Pedagogia Extrema":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Pedagogia Extrema\n(.+?)(?=\nEduScrum|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "EduScrum":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do EduScrum\n(.+?)(?=\nDiscurso de Elevador|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Minute Paper":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Minute Paper\n(.+?)(?=\nPecha Kucha|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Pecha Kucha":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Pecha Kucha\n(.+?)(?=\nCanvas Mania|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Canvas Mania":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Canvas Mania\n(.+?)(?=\nMetodologias imersivas|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Mapeamento mental":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Mapeamento Mental\n(.+?)(?=\nMinute Paper|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Aprendizagem Baseada em Equipes":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Equipes\n(.+?)(?=\nNarrativas Transmídia|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Mapa de Polaridades":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Mapa de Polaridades\n(.+?)(?=\nAprendizagem Baseada em Equipes|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Painel da Diversidade de Perspectivas":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Painel da Diversidade de Perspectivas\n(.+?)(?=\nRotina Veja-Pense-Pergunte-Crie|\nVeja-Pense|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Coaching Reverso":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Coaching Reverso\n(.+?)(?=\nMetodologias ágeis|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Diagnóstico Coletivo":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Diagnóstico Coletivo\n(.+?)(?=\nExtrato de Participação|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Extrato de Participação":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Extrato de Participação\n(.+?)(?=\nTrilhas de Aprendizagem|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Trilhas de Aprendizagem":
                m = re.search(
                    r"(?is)Passo a passo para a implementação das Trilhas de Aprendizagem\n(.+?)(?=\nAnalítica da Aprendizagem|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Mapa de Calor":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Mapa de Calor\n(.+?)(?=\nDog or Cat|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Design Thinking":
                m = re.search(
                    r"(?is)Passo a passo para a implementação do Design Thinking\n(.+?)(?=\nAprendizagem Maker|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Aprendizagem Maker":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Aprendizagem Maker\n(.+?)(?=\nSala de Aula Invertida|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Sala de Aula Invertida":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Sala de Aula Invertida\s*\n(.+?)(?=\nWorld Café|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Aprendizagem Baseada em Projetos":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Projetos\n(.+?)(?=\nAprendizagem Baseada em Casos|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Aprendizagem Baseada em Casos":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Casos\n(.+?)(?=\nDesign Thinking|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Aprendizagem Baseada em Problemas":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Aprendizagem Baseada em Problemas\n(.+?)(?=\nAprendizagem Baseada em Projetos|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Abordagem Problematizadora":
                m = re.search(
                    r"(?is)Passo a passo para a implementação da Abordagem Problematizadora\n(.+?)(?=\nAprendizagem Baseada em Problemas|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None
            if nome == "Simulações":
                m = re.search(
                    r"(?is)Passo a passo para a implementação de Simulação\n(.+?)(?=\nRoleplay|\Z)",
                    text,
                )
                bloco = m.group(1) if m else None

        if not bloco:
            faltando.append(nome)
            continue

        passos = parse_steps(bloco)
        if not passos:
            faltando.append(nome + " (sem passos parseados)")
            continue

        k = chave(nome)
        biblioteca[k] = passos
        contagens[nome] = len(passos)

        for alias in ALIASES.get(k, []):
            biblioteca[chave(alias)] = passos

    OUT.write_text(
        json.dumps(biblioteca, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"wrote {OUT}")
    print(f"keys={len(biblioteca)} metodologias_ok={len(contagens)}")
    for nome, n in sorted(contagens.items(), key=lambda x: x[0].lower()):
        print(f"  {n:2d}  {nome}")
    if faltando:
        print("FALTANDO:")
        for f in faltando:
            print(" -", f)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
