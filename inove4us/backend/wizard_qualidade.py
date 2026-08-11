"""Qualidade determinística do wizard — sem custo de IA.

Checagens locais: relato mínimo, vínculo com o relato do professor,
suspeita de vazamento a partir da base de referência, ancoragem por termos concretos.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


MIN_RELATO_CHARS = 80
MIN_RELATO_WORDS = 18
JACCARD_VINCULO_OK = 0.18
SIM_VAZAMENTO = 0.42
# Barreira final: limiar alto o bastante para pegar cópia/paráfrase da base inteira.
SIM_BARREIRA_FINAL = 0.40
JACCARD_CONTEXTO_OK = 0.08

# Títulos do fallback legado — se aparecerem, o payload é lixo enlatado.
TITULOS_CAUSA_ENLATADA = {
    "causa estrutural",
    "lacuna de protagonismo",
}

# Expressões multipalavra típicas de relatos escolares (entidades, não tokens soltos).
_EXPR_PATTERNS = [
    re.compile(
        r"(?i)\bc[oó]rrego\s+(?:do|da|de)\s+[A-ZÁÉÍÓÚÂÊÔÃÕÀ][\wÀ-ÿ'-]{2,}",
    ),
    re.compile(
        r"(?i)\bescola\s+(?:municipal\s+|estadual\s+|particular\s+)?"
        r"[A-ZÁÉÍÓÚÂÊÔÃÕÀ][\wÀ-ÿ' -]{2,45}",
    ),
    re.compile(
        r"(?i)\bconcurso\s+(?:municipal\s+|estadual\s+)?"
        r"[A-ZÁÉÍÓÚÂÊÔÃÕÀ][\wÀ-ÿ' -]{2,55}",
    ),
    re.compile(
        r"(?i)\bbairro\s+[A-ZÁÉÍÓÚÂÊÔÃÕÀ][\wÀ-ÿ' -]{2,40}",
    ),
    re.compile(
        r"(?i)\b\d+[ºoª]\s*ano(?:\s+(?:do\s+)?(?:ensino\s+)?(?:fundamental|m[eé]dio|em))?"
        r"(?:\s+[A-Z]\b)?",
    ),
    re.compile(
        r"(?i)\b(?:esgoto\s+clandestino|bueiro\s+entupido|coleta\s+irregular|"
        r"lixo\s+acumulado|diagn[oó]stico\s+de\s+campo)",
    ),
]

STOP_TERMOS = {
    "para",
    "como",
    "mais",
    "menos",
    "muito",
    "muita",
    "sobre",
    "entre",
    "quando",
    "onde",
    "qual",
    "quais",
    "essa",
    "esse",
    "isso",
    "aqui",
    "ainda",
    "também",
    "tambem",
    "depois",
    "antes",
    "aluno",
    "alunos",
    "aluna",
    "alunas",
    "turma",
    "turmas",
    "aula",
    "aulas",
    "sala",
    "professor",
    "professora",
    "escola",
    "projeto",
    "preciso",
    "precisa",
    "podem",
    "fazer",
    "anos",
    "ano",
    # Ruído de rótulos de formulário / templates internos
    "titulo",
    "título",
    "sugerido",
    "sugerida",
    "relato",
    "elementos",
    "concretos",
    "preservar",
    "central",
    "declaracao",
    "declaração",
}

# Rótulos estruturais que nunca devem ecoar na UI como conteúdo do professor.
_ROTULO_FORM_RE = re.compile(
    r"(?is)\b(?:"
    r"t[ií]tulo\s+sugerido|"
    r"declara[cç][aã]o\s+do\s+problema|"
    r"o\s+desafio\s+da\s+turma|"
    r"a\s+dor\s+do\s+professor(?:\s*\([^)]*\))?|"
    r"meu\s+problema|"
    r"localiza[cç][aã]o\s*/?\s*contexto|"
    r"contexto|"
    r"relato"
    r")\s*:\s*"
)
_TITULO_SUGERIDO_RE = re.compile(
    r"(?is)t[ií]tulo\s+sugerido\s*:\s*(.+?)(?=\brelato\s*:|$)"
)
_APOS_RELATO_RE = re.compile(r"(?is)\brelato\s*:\s*(.+)$")


def _norm_words(texto: str) -> list[str]:
    return re.findall(r"[a-zà-ÿ0-9]{3,}", (texto or "").lower())


def estimate_tokens(texto: str) -> int:
    s = texto or ""
    return max(1, (len(s) + 3) // 4) if s else 0


def relato_insufficiente(problema: str) -> str | None:
    limpo = texto_professor_limpo(problema)
    if len(limpo) < MIN_RELATO_CHARS:
        return (
            "Conte um pouco mais sobre a turma e o desafio "
            f"(mínimo ~{MIN_RELATO_CHARS} caracteres). Assim a hipótese fica fiel ao seu relato."
        )
    words = _norm_words(limpo)
    if len(words) < MIN_RELATO_WORDS:
        return (
            "Descreva com mais detalhes o que acontece na sala "
            f"(cerca de {MIN_RELATO_WORDS} palavras). Evitamos gastar IA com relatos incompletos."
        )
    return None


def jaccard_words(a: str, b: str) -> float:
    wa, wb = set(_norm_words(a)), set(_norm_words(b))
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    union = len(wa | wb)
    return inter / union if union else 0.0


def similaridade_texto(a: str, b: str) -> float:
    aa = " ".join(str(a or "").split()).lower()
    bb = " ".join(str(b or "").split()).lower()
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb).ratio()


def texto_professor_limpo(problema: str) -> str:
    """
    Conteúdo que o professor escreveu — sem rótulos de formulário
    («Título sugerido:», «Relato:», etc.).
    """
    bruto = str(problema or "")
    m_relato = _APOS_RELATO_RE.search(bruto)
    if m_relato:
        bruto = m_relato.group(1)
    limpo = _ROTULO_FORM_RE.sub(" ", bruto)
    return " ".join(limpo.split()).strip()


def extrair_titulo_sugerido(problema: str) -> str | None:
    m = _TITULO_SUGERIDO_RE.search(str(problema or ""))
    if not m:
        return None
    tit = _ROTULO_FORM_RE.sub(" ", m.group(1))
    tit = " ".join(tit.split()).strip()
    return tit[:120] if len(tit) >= 8 else None


def _cortar_em_limite_legivel(texto: str, max_chars: int) -> str:
    """Corta em limite de palavra/frase — nunca no meio com «…» solto no eco."""
    limpo = " ".join(str(texto or "").split()).strip()
    if not limpo or len(limpo) <= max_chars:
        return limpo
    corte = limpo[:max_chars].rstrip()
    # Preferir fim de frase
    for sep in (". ", "! ", "? ", "; "):
        idx = corte.rfind(sep)
        if idx >= max(40, max_chars // 3):
            return corte[: idx + 1].strip()
    idx = corte.rfind(" ")
    if idx >= 40:
        return corte[:idx].rstrip(",;:") + "."
    return corte.rstrip(",;:") + "."


def extrair_trecho_relato(problema: str, max_chars: int = 160) -> str:
    limpo = texto_professor_limpo(problema)
    if not limpo:
        tit = extrair_titulo_sugerido(problema)
        return tit or ""
    return _cortar_em_limite_legivel(limpo, max_chars)


def expressoes_do_relato(problema: str, *, limite: int = 8) -> list[str]:
    """
    Entidades/frases do relato (não palavras soltas).
    Preferidas nos templates sem IA para soar naturais.
    """
    base = texto_professor_limpo(problema)
    tit = extrair_titulo_sugerido(problema)
    fonte = f"{tit}. {base}" if tit else base
    out: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        e = " ".join(str(raw or "").split()).strip(" .,;:-")
        if len(e) < 5:
            return
        key = e.lower()
        if key in seen:
            return
        # Evitar eco de rótulo
        if "sugerido" in key or key.startswith("relato"):
            return
        seen.add(key)
        out.append(e)

    if tit:
        _add(tit)
    for pat in _EXPR_PATTERNS:
        for m in pat.finditer(fonte):
            _add(m.group(0))
            if len(out) >= limite:
                return out[:limite]
    # Fallback: bigramas/trigramas com iniciais maiúsculas
    for m in re.finditer(
        r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÀ][\wÀ-ÿ'-]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÀ][\wÀ-ÿ'-]+){1,4}\b",
        fonte,
    ):
        _add(m.group(0))
        if len(out) >= limite:
            break
    return out[:limite]


def _ancora_legivel(texto: str, *, max_chars: int = 56, max_words: int = 8) -> str | None:
    """
    Âncora curta para UI/perguntas. Rejeita cláusulas longas do relato
    (ex.: «Fomos escolhidos para a realização de um projeto…»).
    """
    e = " ".join(str(texto or "").split()).strip(" .,;:-«»\"'")
    if len(e) < 4:
        return None
    words = e.split()
    if len(words) > max_words or len(e) > max_chars:
        return None
    # Verbos/cláusulas de abertura — não são entidades
    if re.match(
        r"(?i)^(fomos|somos|temos|quero|queremos|precisamos|preciso|"
        r"n[oó]s|eu|eles|elas|foi|ser[aá]|estamos|para|como|com|sem|"
        r"entre|sobre|em|na|no|nas|nos)\b",
        e,
    ):
        return None
    # Fragmentos de oração (eco ruim na UI)
    if re.search(
        r"(?i)\b(para atuar|atuar como|como um e|e nas casas|"
        r"realiza[cç][aã]o de|fomos escolhidos|que voc[eê]|"
        r"do relato|em torno de)\b",
        e,
    ):
        return None
    return e


def frase_tema_do_relato(problema: str) -> str:
    """Tema curto e legível — uma âncora boa, sem colar fragmentos com «e»."""
    exprs = expressoes_do_relato(problema, limite=6)
    curtas = [e for e in (_ancora_legivel(x) for x in exprs) if e]

    def _score(a: str) -> tuple[int, int]:
        # Prioriza entidades nomeadas / tema ambiental; evita gambiarras.
        s = 0
        if re.search(
            r"(?i)c[oó]rrego|escola|concurso|esgoto|bueiro|sustent|vale\s+\w+",
            a,
        ):
            s -= 20
        if re.search(r"(?i)\d+[ºoª]\s*ano|turma", a):
            s -= 8
        # Prefere âncoras compactas entre as priorizadas
        return (s, len(a))

    if curtas:
        return sorted(curtas, key=_score)[0]
    tit = _ancora_legivel(
        extrair_titulo_sugerido(problema) or "", max_chars=72, max_words=10
    )
    if tit:
        return tit
    # Sem entidade nomeada: tema genérico (não ecoar 1ª frase inteira do relato)
    corpo = texto_professor_limpo(problema).lower()
    if re.search(r"(?i)ambient|sustent|c[oó]rrego|lixo|esgoto|campo", corpo):
        return "o desafio ambiental do relato"
    if re.search(r"(?i)turma|ano|aluno", corpo):
        return "o desafio da turma"
    return "o desafio que você descreveu"


def termos_concretos_do_relato(problema: str, *, limite: int = 12) -> list[str]:
    """
    Termos distintivos do relato (checagem de ancoragem).
    Preferir tokens que pertençam a expressões extraídas.
    """
    exprs = expressoes_do_relato(problema, limite=6)
    out: list[str] = []
    seen: set[str] = set()
    for e in exprs:
        for w in _norm_words(e):
            if len(w) < 4 or w in STOP_TERMOS or w in seen:
                continue
            seen.add(w)
            out.append(w)
            if len(out) >= limite:
                return out
    base = texto_professor_limpo(problema)
    tit = extrair_titulo_sugerido(problema)
    if tit:
        base = f"{tit} {base}"
    for w in _norm_words(base):
        if len(w) < 4 or w in STOP_TERMOS or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= limite:
            break
    return out


def contexto_request_normalizado(contexto: str) -> str:
    ctx = " ".join(str(contexto or "").split()).strip()
    ctx = _ROTULO_FORM_RE.sub(" ", ctx)
    return " ".join(ctx.split()).strip()


def contexto_explicito_aceitavel(
    ctx: str,
    *,
    problema: str,
    corpus_refs: list[str] | None,
) -> bool:
    """Mesmas barreiras de vazamento/vínculo — sem inventar regras novas."""
    if not ctx or len(ctx) < 8:
        return False
    corpo = texto_professor_limpo(problema)
    vaza, _, _ = vaza_contra_corpus(ctx, corpus_refs or [], problema)
    if vaza:
        return False
    ligado = (
        jaccard_words(ctx, corpo) >= JACCARD_CONTEXTO_OK
        or any(t in ctx.lower() for t in termos_concretos_do_relato(problema, limite=6))
    )
    return ligado


def contexto_seguro_para_ui(
    contexto: str,
    problema: str,
    corpus_refs: list[str] | None = None,
) -> str:
    """
    Contexto exibível/seguro para prompt e pads.

    Prioridade: contexto explícito do request (se passar anti-vazamento/vínculo).
    Inferência a partir do relato só via `_ancora_legivel` — nunca devolver
    fragmentos crus (ex.: «escola para atuar como um»).
    Sem contexto confiável → string vazia (não inventar localização).
    """
    ctx = contexto_request_normalizado(contexto)
    if contexto_explicito_aceitavel(ctx, problema=problema, corpus_refs=corpus_refs):
        return ctx[:100]

    exprs = expressoes_do_relato(problema, limite=6)

    # Entidades «escola …» só se forem âncoras legíveis (nome/local), não cláusulas.
    for e in exprs:
        if re.match(r"(?i)^escola\b", e):
            ancora = _ancora_legivel(e, max_chars=100, max_words=12)
            if ancora:
                return ancora

    turmas_ok: list[str] = []
    for e in exprs:
        if re.search(r"(?i)\d+[ºoª]\s*ano|\bano\b", e):
            ancora = _ancora_legivel(e, max_chars=100, max_words=12)
            if ancora:
                turmas_ok.append(ancora)
    if turmas_ok:
        return ", ".join(turmas_ok[:3])[:100]

    for e in exprs:
        ancora = _ancora_legivel(e, max_chars=100, max_words=12)
        if ancora:
            return ancora

    return ""


def contem_termo_do_relato(texto: str, problema: str) -> bool:
    low = (texto or "").lower()
    for e in expressoes_do_relato(problema, limite=6):
        if e.lower() in low:
            return True
    termos = termos_concretos_do_relato(problema)
    corpo = texto_professor_limpo(problema)
    if not termos:
        return jaccard_words(texto, corpo) >= 0.12
    return any(t in low for t in termos)


def textos_ancorados_no_relato(textos: list[str], problema: str) -> bool:
    """True se AO MENOS um texto cita um termo/expressão concreto do relato."""
    return any(contem_termo_do_relato(t, problema) for t in textos if t)


def parece_texto_debug_ui(texto: str) -> bool:
    """Detecta eco de rótulo de formulário ou estado interno na UI."""
    t = texto or ""
    low = t.lower()
    if "elementos concretos a preservar" in low:
        return True
    if "dor central do seu relato" in low:
        return True
    if "título sugerido" in low or "titulo sugerido" in low:
        return True
    if re.search(r"(?i)\brelato\s*:", t):
        return True
    if "«" in t and "…" in t and len(t) > 120:
        if low.startswith("a dor") or "a partir de «" in low:
            return True
    return False


def parece_lista_tokens_soltos(texto: str) -> bool:
    """Ex.: 'ciências, municipal e vale' — molde com substantivos isolados."""
    m = re.search(
        r"(?i)envolve\s+([a-zà-ÿ]{4,}),\s*([a-zà-ÿ]{4,})\s+e\s+([a-zà-ÿ]{4,})\b",
        texto or "",
    )
    if not m:
        m = re.search(
            r"(?i)como\s+([a-zà-ÿ]{4,})\s+se\s+conecta\s+a\s+([a-zà-ÿ]{4,})\b",
            texto or "",
        )
        if m:
            return True
        return False
    parts = [m.group(1), m.group(2), m.group(3)]
    # Três tokens curtos sem espaço interno = lista solta
    return all(" " not in p and len(p) <= 12 for p in parts)


def parece_causa_enlatada(titulo: str, descricao: str) -> bool:
    tit = (titulo or "").strip().lower()
    desc = (descricao or "").lower()
    if tit in TITULOS_CAUSA_ENLATADA:
        return True
    if parece_texto_debug_ui(f"{titulo} {descricao}"):
        return True
    if parece_lista_tokens_soltos(descricao or ""):
        return True
    if "o sintoma" in desc and "se manifesta de forma recorrente" in desc:
        return True
    if "faltam às aulas" in desc or "faltam as aulas" in desc:
        return True
    if "leituras obrigatórias" in desc or "leituras obrigatorias" in desc:
        return True
    return False


def _ngramas(texto: str, n: int = 4) -> list[str]:
    words = _norm_words(texto)
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def vaza_contra_corpus(
    texto: str,
    corpus: list[str],
    problema: str,
) -> tuple[bool, float, str]:
    """
    True se o texto copia/paráfrase a base de referência e NÃO está no relato.
    """
    if not texto or not corpus:
        return False, 0.0, ""
    corpo = texto_professor_limpo(problema).lower()
    max_sim = 0.0
    hit = ""
    for ref in corpus:
        ref_s = " ".join(str(ref or "").split())
        if len(ref_s) < 20:
            continue
        # n-grama da ref presente na saída mas ausente no relato
        for ng in _ngramas(ref_s, 4)[:40]:
            if len(ng) < 16:
                continue
            if ng in (texto or "").lower() and ng not in corpo:
                return True, 0.99, ref_s[:120]
        sim = similaridade_texto(texto, ref_s)
        if sim > max_sim:
            max_sim = sim
            hit = ref_s[:120]
    if max_sim >= SIM_BARREIRA_FINAL:
        # Se o texto está fortemente ancorado no relato, pode ser coincidência fraca
        if contem_termo_do_relato(texto, problema) and max_sim < 0.55:
            if jaccard_words(texto, corpo) >= 0.2:
                return False, max_sim, hit
        return True, max_sim, hit
    return False, max_sim, hit


def corpus_textos_de_refs(refs: list[dict] | None) -> list[str]:
    out: list[str] = []
    for r in refs or []:
        for key in ("desc_prob", "razoes_prob", "solucoes_prob"):
            val = " ".join(str(r.get(key) or "").split())
            if len(val) >= 20:
                out.append(val)
    return out


def avaliar_qualidade(
    *,
    problema: str,
    trecho_relato_usado: str | None,
    textos_hipoteses: list[str],
    textos_causas: list[str] | None = None,
    refs_no_prompt: list[dict],
    n_causas_ia: int | None = None,
    corpus_refs: list[str] | None = None,
) -> dict[str, Any]:
    """
    Flags para telemetria / gate de retry.
    `precisa_retry` = resultado claramente desconectado, com vazamento,
    debug na UI, ou menos de 3 causas vindas da IA.
    """
    corpo = texto_professor_limpo(problema)
    trecho = " ".join(str(trecho_relato_usado or "").split())
    if not trecho or parece_texto_debug_ui(trecho):
        trecho = extrair_trecho_relato(problema)

    score_vinculo = jaccard_words(corpo or problema, trecho)
    vinculo_ok = score_vinculo >= JACCARD_VINCULO_OK and not parece_texto_debug_ui(trecho)

    corpus = list(corpus_refs or [])
    corpus.extend(corpus_textos_de_refs(refs_no_prompt))

    max_sim = 0.0
    hipotese_suspeita = ""
    ref_suspeita = ""
    todos = list(textos_hipoteses or []) + list(textos_causas or [])
    for hip in todos:
        vaza, sim, hit = vaza_contra_corpus(hip, corpus, problema)
        if sim > max_sim:
            max_sim = sim
            hipotese_suspeita = (hip or "")[:120]
            ref_suspeita = hit
        if vaza:
            max_sim = max(max_sim, sim)

    possivel_vazamento = any(
        vaza_contra_corpus(t, corpus, problema)[0] for t in todos if t
    )

    causas_enlatadas = any(
        parece_causa_enlatada("", t) for t in (textos_causas or []) if t
    )
    debug_ui = any(parece_texto_debug_ui(t) for t in todos if t)
    tokens_soltos = any(parece_lista_tokens_soltos(t) for t in (textos_causas or []) if t)
    ancoragem_ok = any(
        vinculo_minimo_com_relato(t, problema) for t in todos if t
    )
    causas_ia_insuficientes = n_causas_ia is not None and n_causas_ia < 3

    precisa_retry = (
        (not vinculo_ok)
        or possivel_vazamento
        or causas_enlatadas
        or debug_ui
        or tokens_soltos
        or (not ancoragem_ok)
        or causas_ia_insuficientes
    )

    return {
        "vinculo_relato_ok": vinculo_ok,
        "vinculo_relato_score": round(score_vinculo, 3),
        "possivel_vazamento": possivel_vazamento,
        "vazamento_score": round(max_sim, 3),
        "ancoragem_termos_ok": ancoragem_ok,
        "causas_enlatadas": causas_enlatadas,
        "debug_ui": debug_ui,
        "tokens_soltos": tokens_soltos,
        "causas_ia_insuficientes": causas_ia_insuficientes,
        "precisa_retry": precisa_retry,
        "trecho_relato_usado": trecho[:220],
        "termos_relato": termos_concretos_do_relato(problema, limite=8),
        "expressoes_relato": expressoes_do_relato(problema, limite=5),
        "detalhe": {
            "hipotese_amostra": hipotese_suspeita,
            "ref_amostra": ref_suspeita,
        },
    }


def causas_somente_do_relato(
    problema: str,
    contexto: str,
    corpus_refs: list[str] | None = None,
) -> list[dict]:
    """
    Causas determinísticas legíveis — ângulos distintos do relato.
    Só usado quando a IA falhou nas checagens (não como reescrita padrão).
    """
    exprs = expressoes_do_relato(problema, limite=8)
    tema = frase_tema_do_relato(problema)
    ctx = contexto_seguro_para_ui(contexto, problema, corpus_refs) or tema

    # Ângulos preferidos — sempre a forma já “legível”, nunca fragmento cru.
    ambientais: list[str] = []
    turmas: list[str] = []
    prazo: list[str] = []
    for e in exprs:
        a = _ancora_legivel(e)
        if not a:
            continue
        if re.search(
            r"(?i)esgoto|bueiro|coleta|lixo|c[oó]rrego|cheiro|água|agua|"
            r"ambient|sustent|campo|diagn[oó]stico",
            a,
        ):
            ambientais.append(a)
        if re.search(r"(?i)\d+[ºoª]\s*ano|turma|ensino", a):
            turmas.append(a)
        if re.search(r"(?i)concurso|prazo|sustent[aá]vel|dossi", a):
            prazo.append(a)

    e_amb = ambientais[0] if ambientais else tema
    e_turma = ", ".join(turmas[:2]) if turmas else "as turmas envolvidas"
    e_prazo = prazo[0] if prazo else tema
    # Focos curtos só — nunca embutir frase inteira do relato na pergunta.
    # Temas genéricos («o desafio ambiental…») não entram na pergunta.
    _tema_generico = re.compile(r"(?i)^o desafio\b|que voc[eê] descreveu")
    foco_a = None if _tema_generico.search(e_amb or "") else e_amb
    if foco_a and not _ancora_legivel(foco_a) and not ambientais:
        # tema genérico / longo demais para a pergunta
        foco_a = None
    foco_t = turmas[0] if turmas else None
    focos = [f for f in (foco_a, foco_t) if f]
    if focos:
        pergunta_comp = (
            f"Qual evidência de campo sobre {' / '.join(focos)} "
            f"você já tem ou quer coletar primeiro com as turmas?"
        )
    else:
        pergunta_comp = (
            "Qual evidência de campo você já tem — ou quer que as turmas "
            "coletem primeiro — para tornar essa hipótese testável?"
        )

    menciona_esgoto = bool(
        re.search(r"(?i)esgoto|bueiro|coleta\s+irregular|lixo", problema or "")
    )
    if menciona_esgoto:
        desc_causas = (
            f"No relato sobre {e_amb}, há causas concorrentes a investigar "
            f"(esgoto clandestino, coleta irregular ou bueiro entupido). "
            f"Com as turmas, vale estruturar evidências de campo para "
            f"confirmar ou descartar cada hipótese."
        )
    else:
        desc_causas = (
            f"O relato aponta hipóteses testáveis ligadas a {e_amb}. "
            f"Com as turmas, vale estruturar evidências para confirmar "
            f"ou descartar cada linha."
        )

    return [
        {
            "titulo": "Causas concorrentes",
            "descricao": desc_causas,
            "origem": "pad_deterministico",
            "precisa_complemento": False,
        },
        {
            "titulo": "Coordenação entre turmas",
            "descricao": (
                f"No cenário de {ctx}, o trabalho entre {e_turma} precisa "
                f"ficar articulado (diagnóstico → intervenção → dossiê). "
                f"Sem esse fio, o projeto em torno de {tema} se desconecta."
            ),
            "origem": "pad_deterministico",
            "precisa_complemento": False,
        },
        {
            "titulo": "Hipótese a aprofundar",
            "descricao": (
                f"Em relação a {e_prazo}, ainda falta tornar testável a "
                f"hipótese que a turma priorizar — com um detalhe observável "
                f"(o que medir, onde e com qual turma), o plano fica concreto."
            ),
            "origem": "pad_deterministico",
            "precisa_complemento": True,
            "pergunta_complemento": pergunta_comp,
        },
    ]


def _completar_causas_com_pad(
    out: list[dict],
    *,
    problema: str,
    contexto: str,
    corpus_refs: list[str] | None = None,
) -> list[dict]:
    pads = causas_somente_do_relato(problema, contexto, corpus_refs)
    used = {(c.get("titulo") or "").strip().lower() for c in out}
    for p in pads:
        if len(out) >= 3:
            break
        tit = (p.get("titulo") or "").strip().lower()
        if tit in used:
            continue
        out.append(dict(p))
        used.add(tit)
    while len(out) < 3:
        out.append(dict(pads[len(out) % len(pads)]))
    return out[:3]


def vinculo_minimo_com_relato(texto: str, problema: str) -> bool:
    """
    Vínculo suficiente para aceitar texto da IA.
    Mais permissivo que exigir substantivo próprio: evita matar hipóteses
    boas sobre turmas/método/cronograma que não repetem 'córrego'/'escola'.
    """
    if contem_termo_do_relato(texto, problema):
        return True
    corpo = texto_professor_limpo(problema)
    if jaccard_words(texto, corpo) >= 0.10:
        return True
    # Sobreposição de palavras significativas (não-stop) com o relato
    wa = {w for w in _norm_words(texto) if w not in STOP_TERMOS and len(w) >= 5}
    wb = {w for w in _norm_words(corpo) if w not in STOP_TERMOS and len(w) >= 5}
    if wa and wb and len(wa & wb) >= 2:
        return True
    return False


def causa_passa_checagens(
    titulo: str,
    descricao: str,
    *,
    problema: str,
    corpus: list[str],
) -> bool:
    """True se a causa pode ir à tela sem pad (sem vazamento / debug / desconexão)."""
    desc = (descricao or "").strip()
    if len(desc) < 36:
        return False
    if parece_causa_enlatada(titulo or "", desc):
        return False
    if parece_texto_debug_ui(desc) or parece_lista_tokens_soltos(desc):
        return False
    if vaza_contra_corpus(desc, corpus, problema)[0]:
        return False
    return vinculo_minimo_com_relato(desc, problema)


def sanitizar_causas_ia(
    raw_causas: object,
    *,
    problema: str,
    contexto: str,
    refs_no_prompt: list[dict],
    corpus_refs: list[str] | None = None,
) -> list[dict]:
    """
    Aceita causas da IA que passam nas checagens.
    Pad só completa slots faltantes — nunca reescreve as que já passaram.
    """
    corpus = list(corpus_refs or [])
    corpus.extend(corpus_textos_de_refs(refs_no_prompt))

    if not isinstance(raw_causas, list) or not raw_causas:
        return causas_somente_do_relato(problema, contexto, corpus)

    out: list[dict] = []
    for item in raw_causas[:5]:
        if not isinstance(item, dict):
            continue
        titulo = str(item.get("titulo") or "Causa").strip()
        if len(titulo) > 120:
            titulo = titulo[:120].rsplit(" ", 1)[0].strip() or titulo[:120]
        desc = str(item.get("descricao") or item.get("texto") or "").strip()
        if not causa_passa_checagens(
            titulo, desc, problema=problema, corpus=corpus
        ):
            continue
        out.append(
            {
                "titulo": titulo or "Causa",
                # Texto pedagógico completo — NÃO cortar no meio da frase.
                "descricao": desc,
                "origem": "ia_relato",
                "precisa_complemento": False,
            }
        )

    # 3 (ou mais) boas → intactas, sem pad
    if len(out) >= 3:
        return out[:3]
    # 2 boas → completa só o 3º slot
    if len(out) == 2:
        return _completar_causas_com_pad(
            out, problema=problema, contexto=contexto, corpus_refs=corpus
        )
    # 0–1 boa → pad total (IA insuficiente)
    return causas_somente_do_relato(problema, contexto, corpus)


def contar_causas_ia(causas: list[dict] | None) -> int:
    return sum(
        1
        for c in (causas or [])
        if isinstance(c, dict) and c.get("origem") == "ia_relato"
    )


def forcar_ancoragem_payload(
    payload: dict,
    *,
    problema: str,
    contexto: str,
    corpus_refs: list[str] | None = None,
) -> dict:
    """
    Defesa determinística CONDICIONAL.
    Causas/hipóteses da IA que já passam nas checagens NÃO são reescritas.
    Pad/template só substitui o slot que falhou.
    """
    tema = frase_tema_do_relato(problema)
    trecho = extrair_trecho_relato(problema)
    corpus = corpus_refs or []
    payload = dict(payload or {})
    causas = [c for c in (payload.get("causas_raiz") or []) if isinstance(c, dict)]

    if not causas:
        payload["causas_raiz"] = causas_somente_do_relato(problema, contexto, corpus)
    else:
        fixed: list[dict] = []
        pads = causas_somente_do_relato(problema, contexto, corpus)
        pad_i = 0
        for c in causas:
            if causa_passa_checagens(
                c.get("titulo", ""),
                c.get("descricao", ""),
                problema=problema,
                corpus=corpus,
            ):
                # Preserva IA intacta (inclui origem/flags)
                c2 = dict(c)
                c2.setdefault("origem", c.get("origem") or "ia_relato")
                c2["precisa_complemento"] = bool(c2.get("precisa_complemento"))
                fixed.append(c2)
            else:
                fixed.append(dict(pads[pad_i % len(pads)]))
                pad_i += 1
        if len(fixed) >= 3:
            # Já tem 3: não chama pad de novo (evita trocar IA boa por template)
            payload["causas_raiz"] = fixed[:3]
        elif len(fixed) == 2:
            payload["causas_raiz"] = _completar_causas_com_pad(
                fixed, problema=problema, contexto=contexto, corpus_refs=corpus
            )
        else:
            payload["causas_raiz"] = causas_somente_do_relato(
                problema, contexto, corpus
            )

    caminhos = []
    for c in payload.get("caminhos") or []:
        if not isinstance(c, dict):
            continue
        c2 = dict(c)
        hip = str(c2.get("hipotese_teste") or "")
        hip_ok = (
            bool(hip)
            and not parece_texto_debug_ui(hip)
            and not vaza_contra_corpus(hip, corpus, problema)[0]
            and vinculo_minimo_com_relato(hip, problema)
        )
        if not hip_ok:
            nome = c2.get("metodologia") or "esta metodologia"
            c2["hipotese_teste"] = (
                f"Se você conduzir {nome} com a turma em torno de {tema}, "
                f"os estudantes praticam a aprendizagem de forma ativa "
                f"e você observa evidências concretas do progresso."
            )
        # Trecho: só substitui se vazio/debug; senão preserva o da IA (limpo)
        trecho_card = str(c2.get("trecho_relato_usado") or "").strip()
        if not trecho_card or parece_texto_debug_ui(trecho_card):
            c2["trecho_relato_usado"] = trecho
        else:
            limpo_card = texto_professor_limpo(trecho_card)
            c2["trecho_relato_usado"] = limpo_card or trecho_card
        for campo in ("resumo", "por_que_usar", "dinamica_sala", "inspiracao_caso"):
            val = str(c2.get(campo) or "")
            if val and vaza_contra_corpus(val, corpus, problema)[0]:
                c2[campo] = (
                    f"Aplicação de {c2.get('metodologia') or 'metodologia'} "
                    f"ao desafio {tema}."
                )
        caminhos.append(c2)
    if caminhos:
        payload["caminhos"] = caminhos
    # Só força trecho raiz se estiver vazio/debug
    trecho_raiz = str(payload.get("trecho_relato_usado") or "").strip()
    if not trecho_raiz or parece_texto_debug_ui(trecho_raiz):
        payload["trecho_relato_usado"] = trecho
    return payload


def aplicar_barreira_final_payload(
    payload: dict,
    *,
    problema: str,
    contexto: str,
    corpus_refs: list[str],
) -> dict:
    """
    Rede de segurança: só substitui o texto que vazou da base.
    Itens limpos (IA boa) passam intactos.
    """
    payload = dict(payload or {})
    corpus = list(corpus_refs or [])
    bloqueios = 0
    amostras: list[str] = []

    pads = causas_somente_do_relato(problema, contexto, corpus)
    pad_i = 0
    causas_out: list[dict] = []
    for c in payload.get("causas_raiz") or []:
        if not isinstance(c, dict):
            continue
        c2 = dict(c)
        blob = f"{c2.get('titulo', '')} {c2.get('descricao', '')}"
        vaza, _, hit = vaza_contra_corpus(blob, corpus, problema)
        soltos = parece_lista_tokens_soltos(c2.get("descricao", ""))
        if vaza or soltos:
            bloqueios += 1
            amostras.append(hit or blob[:80])
            causas_out.append(dict(pads[pad_i % len(pads)]))
            pad_i += 1
        else:
            causas_out.append(c2)

    if not causas_out:
        causas_out = pads
    elif len(causas_out) < 3:
        causas_out = _completar_causas_com_pad(
            causas_out, problema=problema, contexto=contexto, corpus_refs=corpus
        )
    payload["causas_raiz"] = causas_out[:3]

    tema = frase_tema_do_relato(problema)
    caminhos = []
    for c in payload.get("caminhos") or []:
        if not isinstance(c, dict):
            continue
        c2 = dict(c)
        for campo in (
            "hipotese_teste",
            "resumo",
            "por_que_usar",
            "dinamica_sala",
            "inspiracao_caso",
            "trecho_relato_usado",
        ):
            val = str(c2.get(campo) or "")
            if not val:
                continue
            vaza, _, hit = vaza_contra_corpus(val, corpus, problema)
            if vaza:
                bloqueios += 1
                amostras.append(hit or val[:80])
                if campo == "hipotese_teste":
                    nome = c2.get("metodologia") or "esta metodologia"
                    c2[campo] = (
                        f"Se você conduzir {nome} com a turma em torno de {tema}, "
                        f"os estudantes praticam a aprendizagem de forma ativa "
                        f"e você observa evidências concretas do progresso."
                    )
                elif campo == "trecho_relato_usado":
                    c2[campo] = extrair_trecho_relato(problema)
                else:
                    c2[campo] = (
                        f"Aplicação de {c2.get('metodologia') or 'metodologia'} "
                        f"ao desafio {tema}."
                    )
        caminhos.append(c2)
    if caminhos:
        payload["caminhos"] = caminhos

    qualidade = dict(payload.get("qualidade") or {})
    qualidade["barreira_final_bloqueios"] = bloqueios
    if bloqueios:
        qualidade["barreira_final_amostra"] = (amostras[0] if amostras else "")[:120]
        print(
            f"[wizard] BARREIRA_FINAL bloqueios={bloqueios} "
            f"amostra={(amostras[0] if amostras else '')[:80]!r}",
            file=__import__("sys").stderr,
        )
    payload["qualidade"] = qualidade
    return payload
