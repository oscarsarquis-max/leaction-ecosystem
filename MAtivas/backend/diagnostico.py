"""
MAtivas - Diagnóstico rápido de metodologia (sem IA)
=====================================================================
Faz a correspondência entre o desafio relatado pelo professor e a base
de conhecimento `problema_mativa` por sobreposição de palavras-chave
(normalizando acentos e removendo stopwords). Usado pelo endpoint
síncrono POST /api/diagnostico para exibir uma prévia da metodologia em
/resultado antes da geração completa do roteiro.

A metodologia escolhida aqui é "travada": é repassada ao worker, que
apenas elabora os passos para ela (sem reescolher).
"""

import re
import unicodedata

from psycopg2.extras import RealDictCursor

# Ruído de domínio: termos frequentes que não ajudam a diferenciar uma
# metodologia da outra (aparecem em quase todos os registros).
STOPWORDS = {
    "que", "com", "sem", "para", "por", "dos", "das", "nos", "nas", "uma", "uns",
    "umas", "como", "mais", "menos", "muito", "muita", "pouco", "seus", "suas",
    "meu", "minha", "meus", "minhas", "nao", "sim", "tem", "tum", "ter", "sao",
    "esta", "estao", "este", "esse", "essa", "isso", "aos", "ate", "ele", "ela",
    "eles", "elas", "lhe", "seu", "sua", "num", "numa", "pelo", "pela",
    "aluno", "alunos", "aluna", "alunas", "estudante", "estudantes",
    "professor", "professora", "professores", "sala", "aula", "aulas",
    "turma", "turmas", "curso", "conteudo", "conteudos", "dificuldade",
    "dificuldades", "precisam", "precisa", "demonstram", "demonstra",
    "conseguem", "consegue", "fazer", "maneira", "maneiras", "forma",
    "ano", "anos", "serie", "series", "grau",
}

_DEFAULT_FALLBACK = "Aprendizagem Baseada em Problemas"

GRUPO_TEXTOS = {
    "Metodologias (Cri)ativas": (
        "Priorizam a expressão, a experimentação e a produção autoral dos estudantes. "
        "Incentivam criação, prototipagem e narrativas que transformam ideias em "
        "aprendizagem significativa."
    ),
    "Metodologias Ágeis": (
        "Organizam o trabalho em ciclos curtos, com colaboração, feedback frequente "
        "e adaptação. São úteis quando é preciso envolver a turma de forma dinâmica."
    ),
    "Metodologias Imersivas": (
        "Colocam os estudantes em situações vividas, simuladas ou experienciais, "
        "aproximando o conteúdo de contextos reais, jogos ou ambientes digitais."
    ),
    "Metodologias Analíticas": (
        "Estruturam a investigação, a argumentação e a resolução de problemas, "
        "fortalecendo o pensamento crítico e a tomada de decisão."
    ),
}

_NIVEL_PATTERNS = [
    ("Educação Infantil", r"\b(educacao infantil|infantil|creche|pre[- ]?escola)\b"),
    ("Fundamental I", r"\b(fundamental i|anos iniciais|1o ao 5o|1º ao 5º)\b"),
    ("Fundamental II", r"\b(fundamental ii|anos finais|6o ao 9o|6º ao 9º)\b"),
    ("Ensino Médio", r"\b(ensino medio|medio|1a serie|2a serie|3a serie)\b"),
    (
        "Educação Profissional e Tecnológica",
        r"\b(educacao profissional|tecnologica|etec|senai|curso tecnico)\b",
    ),
    ("Educação Corporativa", r"\b(educacao corporativa|treinamento corporativo|empresa)\b"),
    ("Educação Continuada", r"\b(educacao continuada|pos[- ]?graduacao|extensao)\b"),
]

_FORMATO_PATTERNS = [
    ("Online", r"\b(online|remot[oa]|ead|virtual|plataforma|zoom|teams)\b"),
    ("Híbrido", r"\b(hibrid[oa]|semipresencial|mist[oa])\b"),
    ("Presencial", r"\b(presencial|sala de aula|em sala)\b"),
]


def _normalizar(texto):
    texto = texto or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def _tokens(texto):
    norm = _normalizar(texto)
    brutos = re.findall(r"[a-z0-9]+", norm)
    return [t for t in brutos if len(t) > 2 and t not in STOPWORDS]


def _frases(problemas_combinados):
    return [f.strip() for f in (problemas_combinados or "").split(";") if f.strip()]


def _limpar_observacao(observacao):
    """Remove o prefixo 'Acionar quando ' para encaixar a observação numa
    frase corrida da justificativa."""
    obs = (observacao or "").strip()
    obs = re.sub(r"^acionar\s+quando\s+", "", obs, flags=re.IGNORECASE)
    return obs[0].lower() + obs[1:] if obs else obs


def _normalizar_grupo(nome):
    if not nome:
        return None
    norm = _normalizar(nome)
    if "cri" in norm and "ativa" in norm:
        return "Metodologias (Cri)ativas"
    if "agil" in norm:
        return "Metodologias Ágeis"
    if "imers" in norm:
        return "Metodologias Imersivas"
    if "analit" in norm:
        return "Metodologias Analíticas"
    return nome.strip() if nome else None


def _texto_grupo(grupo):
    grupo_norm = _normalizar_grupo(grupo)
    return GRUPO_TEXTOS.get(grupo_norm, GRUPO_TEXTOS["Metodologias Analíticas"])


def _justificativa_usuario(grupo):
    """Fallback genérico quando não há frase de problemas_combinados."""
    grupo_norm = _normalizar_grupo(grupo) or "Metodologias Inov-ativas"
    return (
        f"As metodologias do grupo {grupo_norm} podem apoiar sua prática. "
        "Ao gerar o roteiro, selecionaremos a mais adequada para a sua turma."
    )


def _montar_justificativa(metodologia, grupo, melhor_frase=None, observacao=None):
    """Formato padrão do roteiro: metodologia + grupo + indicação pedagógica."""
    grupo_norm = _normalizar_grupo(grupo) or "Metodologias Inov-ativas"
    if melhor_frase and melhor_frase.strip():
        indicacao = melhor_frase.strip().rstrip(".")
        indicacao = indicacao[0].lower() + indicacao[1:] if indicacao else indicacao
    elif observacao:
        indicacao = _limpar_observacao(observacao)
    else:
        indicacao = "o desafio descrito apresenta características alinhadas a esta abordagem"

    return (
        f"A {metodologia} faz parte das {grupo_norm} e é indicada quando "
        f"{indicacao}."
    )


def extrair_contexto(texto):
    """Extrai nível, modalidade e participantes do relato, quando possível."""
    norm = _normalizar(texto)
    resultado = {"nivel": None, "formato": None, "participantes": None}

    for label, pattern in _NIVEL_PATTERNS:
        if re.search(pattern, norm):
            resultado["nivel"] = label
            break

    for label, pattern in _FORMATO_PATTERNS:
        if re.search(pattern, norm):
            resultado["formato"] = label
            break

    match_qtd = re.search(
        r"\b(\d{1,4})\s*(alunos?|estudantes?|participantes?|pessoas?|criancas?)\b",
        norm,
    )
    if match_qtd:
        resultado["participantes"] = int(match_qtd.group(1))
    else:
        match_turma = re.search(r"\bturma de\s+(\d{1,4})\b", norm)
        if match_turma:
            resultado["participantes"] = int(match_turma.group(1))

    return resultado


def buscar_base_conhecimento(conn):
    """Lê todos os registros de problema_mativa."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, metodologia, grupo, problemas_combinados,
                      observacao_automatizacao, publico_preferencial,
                      publico_complementar, modalidade_preferencial,
                      modalidades_alternativas
                 FROM problema_mativa
             ORDER BY id ASC"""
        )
        return cur.fetchall()


def diagnosticar(texto_usuario, registros, nivel=None, formato=None):
    """Retorna a metodologia mais aderente ao texto do usuário e uma
    justificativa construída a partir da base de conhecimento.

    Retorno: {metodologia, justificativa, grupo, publico_preferencial,
              modalidade_preferencial, score}
    """
    tokens_user = set(_tokens(texto_usuario))

    melhor = None
    melhor_score = -1.0
    melhor_frase = None

    for r in registros or []:
        frases = _frases(r.get("problemas_combinados"))
        tokens_obs = set(_tokens(r.get("observacao_automatizacao")))

        # Pontuação base: sobreposição de palavras com problemas + observação.
        tokens_problemas = set(_tokens(r.get("problemas_combinados")))
        score = float(len(tokens_user & tokens_problemas))
        score += 0.5 * float(len(tokens_user & tokens_obs))

        # Bônus leve por aderência de público/modalidade (desempate).
        if nivel and (set(_tokens(nivel)) & set(_tokens(r.get("publico_preferencial")))):
            score += 0.5
        if formato and (set(_tokens(formato)) & set(_tokens(r.get("modalidade_preferencial")))):
            score += 0.25

        # Frase de 'problemas_combinados' com maior aderência ao relato.
        frase_local = None
        frase_local_score = -1
        for frase in frases:
            ov = len(tokens_user & set(_tokens(frase)))
            if ov > frase_local_score:
                frase_local_score = ov
                frase_local = frase

        if score > melhor_score:
            melhor_score = score
            melhor = r
            melhor_frase = frase_local if frase_local_score > 0 else None

    if melhor is None:
        grupo_fb = "Metodologias Analíticas"
        met_fb = _DEFAULT_FALLBACK
        return {
            "metodologia": met_fb,
            "justificativa": _montar_justificativa(met_fb, grupo_fb),
            "grupo": grupo_fb,
            "grupo_titulo": grupo_fb,
            "grupo_descricao": _texto_grupo(grupo_fb),
            "publico_preferencial": None,
            "modalidade_preferencial": None,
            "score": 0,
            "contexto": extrair_contexto(texto_usuario),
            "problema_indicador": None,
        }

    metodologia = melhor.get("metodologia") or _DEFAULT_FALLBACK
    grupo = _normalizar_grupo(melhor.get("grupo")) or "Metodologias Analíticas"
    justificativa = _montar_justificativa(
        metodologia,
        grupo,
        melhor_frase=melhor_frase,
        observacao=melhor.get("observacao_automatizacao"),
    )

    return {
        "metodologia": metodologia,
        "justificativa": justificativa,
        "grupo": grupo,
        "grupo_titulo": grupo,
        "grupo_descricao": _texto_grupo(grupo),
        "publico_preferencial": melhor.get("publico_preferencial"),
        "modalidade_preferencial": melhor.get("modalidade_preferencial"),
        "score": melhor_score,
        "contexto": extrair_contexto(texto_usuario),
        "problema_indicador": melhor_frase,
    }
