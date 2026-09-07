"""Geração única do card AEE × metodologia (terceiro artefato).

Os dois canônicos — catálogo das 39 e `school_aee_matrizes` / `aee_canonico` —
são só leitura. O resultado vive em `school_aee_metodologias_canonico` (nível
canônico) e, se a escola customizar de verdade, em `school_aee_metodologias_org`.

Não é geração em tempo real no B2C. Lote: `scripts/gerar-aee-metodologias-canonico.py`.
"""
from __future__ import annotations

import re
from typing import Any

STATUS_PENDENTE = "pendente_revisao"
STATUS_APROVADO = "aprovado"
STATUS_REJEITADO = "rejeitado"

ORIGEM_ESCOLA = "escola"
ORIGEM_ADAPTACAO = "adaptacao_canonica"
ORIGEM_CATALOGO = "catalogo"

# Padrão validado (prompt 79) — few-shot obrigatório.
FEW_SHOT_ORIGINAL = (
    "O aluno da estação X deve ler em voz alta o que foi escrito pela turma."
)
FEW_SHOT_AEE_TEA = (
    "ferramentas visuais devem ser complementadas por alternativas audíveis e/ou táteis."
)
FEW_SHOT_ADAPTADO = (
    "O aluno da estação X apresenta o que foi escrito pela turma em voz alta e "
    "aponta/percorre com o dedo o texto no mapa enquanto fala (ou usa recurso tátil "
    "equivalente), garantindo acesso a quem depende de leitura labial, apoio tátil "
    "ou processamento auditivo."
)

SYSTEM_PROMPT = (
    "Você é um Psicopedagogo Sênior especializado em AEE e DUA.\n"
    "Tarefa: reescrever os PASSOS de uma metodologia escolar incorporando, "
    "IN-PLACE, as diretrizes AEE de uma condição específica.\n"
    "O resultado é um TERCEIRO artefato: o card modificado da combinação "
    "condição × metodologia. Não é o texto canônico da metodologia nem o "
    "texto canônico do AEE — é o cruzamento dos dois.\n\n"
    "REGRAS INVIOLÁVEIS:\n"
    "1. Reescreva cada passo no próprio enunciado. NÃO anexe nota lateral "
    "do tipo 'Alternativa AEE:', 'Adaptação:', 'Observação inclusiva:' ou "
    "parágrafo extra depois do passo original.\n"
    "2. Mantenha a intenção pedagógica original: é a mesma atividade, agora "
    "acessível. Não troque a metodologia por outra.\n"
    "3. Preserve a ordem e os TÍTULOS dos passos. Não omita nem invente passos.\n"
    "4. Não copie o canônico da metodologia sem alteração. Cada passo deve "
    "incorporar a diretriz da condição (previsibilidade, canal sensorial, "
    "tempo, papéis, materiais, transições — o que a diretriz pedir).\n"
    "5. Não copie o texto AEE como bloco isolado. Dissolva a diretriz dentro "
    "da mecânica do passo.\n"
    "6. Português do Brasil, linguagem acionável para o professor em aula.\n"
    "7. Retorne APENAS o roteiro. Formato de cada passo:\n"
    "Título do passo: mecânica reescrita em uma ou duas frases.\n"
    "Passos separados por uma linha em branco.\n"
    "Não coloque título geral, nome da metodologia, nome da condição, "
    "separadores '---' nem cabeçalho Markdown no topo — comece no primeiro passo.\n\n"
    "EXEMPLO DO PADRÃO DE TRANSFORMAÇÃO (siga este tipo de reescrita):\n"
    f"- Original: {FEW_SHOT_ORIGINAL}\n"
    f"- Diretriz AEE (TEA): {FEW_SHOT_AEE_TEA}\n"
    f"- Adaptado: {FEW_SHOT_ADAPTADO}\n"
)


def passos_to_text(passos: Any) -> str:
    """Serializa `passos_execucao` do catálogo no mesmo formato da API do Editor."""
    if passos is None:
        return ""
    if isinstance(passos, str):
        return passos.strip()
    if not isinstance(passos, list):
        return str(passos).strip()
    lines: list[str] = []
    for p in passos:
        if isinstance(p, str):
            if p.strip():
                lines.append(p.strip())
            continue
        if not isinstance(p, dict):
            continue
        titulo = str(p.get("titulo") or "").strip()
        mec = str(
            p.get("mecanica_passo_a_passo") or p.get("como_executar_detalhado") or ""
        ).strip()
        if titulo and mec and titulo != mec:
            lines.append(f"{titulo}: {mec}")
        else:
            line = titulo or mec
            if line:
                lines.append(line)
    return "\n".join(lines)


def normalizar_para_comparacao(texto: str) -> str:
    raw = (texto or "").strip().lower()
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw


def eh_copia_identica(
    texto_org: str,
    texto_catalogo: str,
    texto_aee: str = "",
) -> bool:
    """True se o registro da escola está vazio ou é cópia do canônico (não é customização)."""
    org = normalizar_para_comparacao(texto_org)
    if not org:
        return True
    cat = normalizar_para_comparacao(texto_catalogo)
    if cat and org == cat:
        return True
    aee = normalizar_para_comparacao(texto_aee)
    if aee and org == aee:
        return True
    return False


def montar_user_prompt(
    *,
    metodologia_nome: str,
    condicao_categoria: str,
    texto_passos_catalogo: str,
    campos_experiencia_aee: str,
    descricao_base_aee: str = "",
    sugestoes_professores: list[str] | None = None,
) -> str:
    sugestoes = [
        str(s).strip() for s in (sugestoes_professores or []) if str(s or "").strip()
    ]
    bloco_sug = (
        "\n".join(f"- {s}" for s in sugestoes)
        if sugestoes
        else "(nenhuma — este lote canônico não incorpora dicas de professor)"
    )
    desc = (descricao_base_aee or "").strip() or "(sem descrição-base adicional)"
    campos = (campos_experiencia_aee or "").strip() or "(campos de experiência ausentes)"
    passos = (texto_passos_catalogo or "").strip() or "(metodologia sem passos)"
    return (
        "INSUMOS (somente leitura — não os reproduza como saída):\n\n"
        f"Metodologia: {metodologia_nome}\n"
        f"Condição AEE: {condicao_categoria}\n\n"
        "=== PASSOS CANÔNICOS DA METODOLOGIA (catálogo, intacto) ===\n"
        f"{passos}\n\n"
        "=== DIRETRIZ-BASE AEE (canônico da condição, intacto) ===\n"
        f"{desc}\n\n"
        "=== CAMPOS DE EXPERIÊNCIA METODOLÓGICA AEE (canônico da condição, intacto) ===\n"
        f"{campos}\n\n"
        "=== SUGESTÕES DE PROFESSORES (opcional; lote canônico normalmente vazio) ===\n"
        f"{bloco_sug}\n\n"
        "Gere agora o CARD MODIFICADO: os mesmos passos, reescritos in-place, "
        "incorporando a diretriz desta condição. Não devolva os originais."
    )


def gerar_card_adaptado(
    *,
    metodologia_nome: str,
    condicao_categoria: str,
    texto_passos_catalogo: str,
    campos_experiencia_aee: str,
    descricao_base_aee: str = "",
    sugestoes_professores: list[str] | None = None,
    max_tokens: int = 4096,
) -> str:
    """Chama o LLM do School e devolve o terceiro artefato (texto adaptado)."""
    from school_llm import _limpar_roteiro_ia, invoke_text

    user = montar_user_prompt(
        metodologia_nome=metodologia_nome,
        condicao_categoria=condicao_categoria,
        texto_passos_catalogo=texto_passos_catalogo,
        campos_experiencia_aee=campos_experiencia_aee,
        descricao_base_aee=descricao_base_aee,
        sugestoes_professores=sugestoes_professores,
    )
    bruto = invoke_text(
        system_prompt=SYSTEM_PROMPT,
        user_content=user,
        max_tokens=max_tokens,
    )
    return _limpar_roteiro_ia(bruto)


def ddl_tabela_canonico() -> str:
    return """
            CREATE TABLE IF NOT EXISTS public.school_aee_metodologias_canonico (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                condicao_categoria   VARCHAR(80) NOT NULL,
                metodologia_codigo   VARCHAR(120) NOT NULL,
                metodologia_nome     VARCHAR(255) NOT NULL,
                passos_adaptados     TEXT NOT NULL,
                status               VARCHAR(32) NOT NULL DEFAULT 'pendente_revisao',
                origem               VARCHAR(80) NOT NULL DEFAULT 'ia_lote',
                gerado_em            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                aprovado_em          TIMESTAMPTZ,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_school_aee_met_canonico_cond_cod
                    UNIQUE (condicao_categoria, metodologia_codigo),
                CONSTRAINT ck_school_aee_met_canonico_status
                    CHECK (status IN ('pendente_revisao', 'aprovado', 'rejeitado'))
            )
            """


def ensure_canonico_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(ddl_tabela_canonico())
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_school_aee_met_canonico_cond
                ON public.school_aee_metodologias_canonico (condicao_categoria)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_school_aee_met_canonico_status
                ON public.school_aee_metodologias_canonico (status)
            """
        )
        cur.execute(
            """
            COMMENT ON TABLE public.school_aee_metodologias_canonico IS
              'Terceiro artefato: passos da metodologia reescritos para uma condição AEE. '
              'Não substitui o catálogo das 39 nem school_aee_matrizes. Servir só se status=aprovado.'
            """
        )
