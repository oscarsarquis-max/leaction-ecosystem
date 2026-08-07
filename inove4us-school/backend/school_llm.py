"""LLM / Bedrock no School (mesmo padrão do inove4us B2C — boto3 Bedrock Runtime).

Isolado: não importa código do B2C. Usa BEDROCK_* / PEI_BEDROCK_* do .env.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any


BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = (
    os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
)
PEI_BEDROCK_MODEL_ID = (os.environ.get("PEI_BEDROCK_MODEL_ID") or "").strip()
PEI_MAX_TOKENS = int(os.environ.get("PEI_BEDROCK_MAX_TOKENS") or "1024")


def _ssl_verify() -> bool:
    return os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def invoke_text(*, system_prompt: str, user_content: str, max_tokens: int | None = None) -> str:
    """Chama Bedrock (Anthropic Messages API) e devolve texto plano."""
    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        return (
            f"[stub IA] Adapte a metodologia com passos curtos, apoios sensoriais "
            f"e checagens de compreensão. Perfil: {user_content[:240]}"
        )

    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError(
            "boto3 não instalado no School — pip install boto3 botocore"
        ) from exc

    verify = _ssl_verify()
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    model_id = PEI_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
    bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        config=Config(connect_timeout=8, read_timeout=60, retries={"max_attempts": 1}),
    )
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": int(max_tokens or PEI_MAX_TOKENS),
            "temperature": 0.35,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }
    )
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    raw = response.get("body")
    payload = json.loads(raw.read() if hasattr(raw, "read") else raw)
    parts = payload.get("content") or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text") or ""))
    text = "\n".join(t.strip() for t in texts if t.strip()).strip()
    if not text:
        raise RuntimeError("Bedrock retornou resposta vazia")
    return text


def gerar_adaptacao_metodologia_pei(
    *,
    metodologia_nome: str,
    necessidades_especificas: str,
) -> str:
    met = (metodologia_nome or "").strip() or "Metodologia"
    necessidades = (necessidades_especificas or "").strip() or "(sem perfil detalhado)"
    system = (
        "Você é um Psicopedagogo Especialista em Educação Inclusiva e DUA. "
        "Gere passos práticos e acionáveis para adaptar uma metodologia escolar "
        "ao perfil de um aluno com PEI. Responda em português, em tópicos claros, "
        "sem prefácio longo."
    )
    user = (
        f"Como adaptar a metodologia {met} para um aluno com o seguinte "
        f"perfil/PEI: {necessidades}?"
    )
    try:
        return invoke_text(system_prompt=system, user_content=user)
    except Exception as exc:
        print(f"[school-llm] falha gerar PEI×metodologia: {exc}", file=sys.stderr, flush=True)
        raise


def mesclar_metodologia_com_sugestao(
    *,
    texto_canonico: str,
    sugestao_professor: str,
) -> str:
    """Mescla canônico + sugestão do professor em texto unificado (curadoria IA)."""
    return sintetizar_versao_escola(
        texto_canonico=texto_canonico,
        observacoes_coordenacao="",
        sugestoes_aceitas=[sugestao_professor] if sugestao_professor else [],
    )


_SYSTEM_ROTEIRO_INTEGRADO = (
    "Você é um Designer Pedagógico Sênior. Sua tarefa é criar um roteiro de aula "
    "ÚNICO, fluido e coerente, mesclando a base metodológica com as regras da escola "
    "e as dicas dos professores.\n"
    "NÃO crie seções separadas como 'Observações da coordenação' ou 'Sugestões'. "
    "Em vez disso, embuta organicamente essas diretrizes dentro dos passos da metodologia.\n\n"
    "DIRETRIZES DE SAÍDA:\n"
    "1. Retorne APENAS o roteiro passo a passo consolidado.\n"
    "2. Formate em Markdown usando bullet points ou listas numeradas.\n"
    "3. Se houver uma regra da coordenação (ex: 'todos devem falar'), insira-a no "
    "passo correspondente (ex: no passo de Apresentação).\n"
    "4. Se houver uma dica prática (ex: 'checagem em duplas'), insira-a como uma "
    "'Dica:' ou 'Nota:' no passo onde ela faz mais sentido.\n"
    "5. O texto deve ser direto, acionável e fácil de ler durante uma aula.\n"
    "6. Não use títulos de bloco como 'Canônico', 'Coordenação', 'Sugestões', "
    "'Texto integrado' ou separadores '— … —'."
)


def _format_sugestoes_para_prompt(sugestoes: list[str]) -> str:
    if not sugestoes:
        return "(nenhuma dica da trincheira informada)"
    return "\n".join(f"- {s}" for s in sugestoes)


def _stub_roteiro_unificado(
    *,
    canonico: str,
    coord: str,
    sugestoes: list[str],
) -> str:
    """Rascunho local fluido (PEI_LLM_STUB) — sem seções fragmentadas."""
    linhas_base = [ln.strip() for ln in canonico.splitlines() if ln.strip()]
    if not linhas_base:
        linhas_base = [
            "Abrir a aula com o propósito da metodologia",
            "Desenvolver a atividade principal",
            "Fechar e registrar evidências de aprendizagem",
        ]

    passos: list[str] = []
    for i, linha in enumerate(linhas_base):
        if ": " in linha and len(linha.split(": ", 1)[0]) < 80:
            titulo, resto = linha.split(": ", 1)
            bloco = f"{i + 1}. **{titulo.strip()}** — {resto.strip()}"
        else:
            bloco = f"{i + 1}. {linha}"
        notas: list[str] = []
        if coord and i == 0:
            notas.append(f"   - Nota: {coord}")
        if i < len(sugestoes) and i < len(linhas_base) - 1:
            notas.append(f"   - Dica: {sugestoes[i]}")
        if i == len(linhas_base) - 1:
            for tip in sugestoes[max(0, len(linhas_base) - 1) :]:
                notas.append(f"   - Dica: {tip}")
        if notas:
            bloco = f"{bloco}\n" + "\n".join(notas)
        passos.append(bloco)

    return "\n\n".join(passos)


def _limpar_roteiro_ia(texto: str) -> str:
    """Remove prefácios/seções acidentais; devolve só o roteiro fluido."""
    raw = (texto or "").strip()
    if not raw:
        return ""
    # Corta blocos de cabeçalho fragmentado se o modelo (ou stub antigo) ainda emitir
    ban = (
        "— observações da coordenação —",
        "— sugestões dos professores",
        "— texto integrado da escola",
        "[canônico",
        "[observações da coordenação]",
        "[sugestões dos professores",
        "dados de entrada:",
    )
    lines = raw.splitlines()
    out: list[str] = []
    skip_until_blank = False
    for ln in lines:
        low = ln.strip().lower()
        if any(low.startswith(b) or b in low for b in ban):
            skip_until_blank = True
            continue
        if skip_until_blank:
            if not ln.strip():
                skip_until_blank = False
            continue
        out.append(ln)
    cleaned = "\n".join(out).strip()
    return cleaned or raw


def sintetizar_versao_escola(
    *,
    texto_canonico: str,
    observacoes_coordenacao: str = "",
    sugestoes_aceitas: list[str] | None = None,
) -> str:
    """Roteiro único fluido: canônico + coordenação + dicas embutidas nos passos."""
    canonico = (texto_canonico or "").strip() or "(metodologia padrão vazia)"
    coord = (observacoes_coordenacao or "").strip()
    sugestoes = [
        str(s).strip()
        for s in (sugestoes_aceitas or [])
        if str(s or "").strip()
    ]

    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        return _limpar_roteiro_ia(
            _stub_roteiro_unificado(
                canonico=canonico,
                coord=coord,
                sugestoes=sugestoes,
            )
        )

    user = (
        "DADOS DE ENTRADA:\n"
        f"- Metodologia Base (Canônica): {canonico}\n"
        f"- Regras da Coordenação: {coord or '(nenhuma regra adicional)'}\n"
        f"- Dicas da Trincheira (Professores): {_format_sugestoes_para_prompt(sugestoes)}\n\n"
        "Gere agora o roteiro consolidado conforme as diretrizes."
    )
    try:
        bruto = invoke_text(
            system_prompt=_SYSTEM_ROTEIRO_INTEGRADO,
            user_content=user,
            max_tokens=2048,
        )
        return _limpar_roteiro_ia(bruto)
    except Exception as exc:
        print(f"[school-llm] falha sintetizar versão escola: {exc}", file=sys.stderr, flush=True)
        raise


def adaptar_pei_metodologia_com_ia(
    *,
    metodologia_canonica: str,
    aee_texto_escola: str = "",
    aee_campos_experiencia: str = "",
    pei_experiencias_individuais: str = "",
    sugestao_professor: str = "",
    sugestoes_aceitas: list[str] | None = None,
    adaptacao_pei_escola: str = "",
    condicao_categoria: str = "",
    # retrocompat
    matriz_pei_ativa: str = "",
) -> str:
    """Cruza base + AEE + PEI + Adaptação PEI da Escola + sugestões → roteiro único."""
    canonico = (metodologia_canonica or "").strip() or "(metodologia vazia)"
    aee_txt = (aee_texto_escola or matriz_pei_ativa or "").strip() or "(diretriz AEE ausente)"
    aee_campos = (aee_campos_experiencia or "").strip() or "(campos de experiência ausentes)"
    pei_exp = (pei_experiencias_individuais or "").strip() or "(sem adaptação individual informada)"
    adaptacao = (adaptacao_pei_escola or "").strip()
    sugestoes = [str(s).strip() for s in (sugestoes_aceitas or []) if str(s or "").strip()]
    if sugestao_professor and str(sugestao_professor).strip():
        t = str(sugestao_professor).strip()
        if t not in sugestoes:
            sugestoes.append(t)
    if not sugestoes:
        sugestoes = ["(sem sugestão)"]
    cond = (condicao_categoria or "").strip() or "condição não especificada"

    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        blocos = [
            f"Adaptação de plano de aula (rascunho IA) — {cond}",
            f"Base metodológica:\n{canonico[:400]}",
            f"Adaptação PEI da Escola:\n{adaptacao[:300] or '(nenhuma)'}",
            f"Diretriz AEE:\n{aee_txt[:300]}",
            f"Campos de experiência AEE:\n{aee_campos[:300]}",
            f"PEI — experiências individuais:\n{pei_exp[:300]}",
            "Sugestões dos professores:\n"
            + "\n---\n".join(s[:300] for s in sugestoes),
        ]
        return _limpar_roteiro_ia("\n\n".join(blocos))

    system = (
        "Aja como psicopedagogo. Produza UM único roteiro fluido de adaptação "
        "metodológica na prática (Markdown), em português, objetivo e acionável. "
        "Parta da metodologia base, aplique a Adaptação PEI da Escola, cruze com "
        "a diretriz AEE (texto + campos de experiência) e as necessidades do aluno "
        "(experiências adaptadas individuais). Embutir as dicas dos professores "
        "nos passos — não liste seções separadas como 'sugestões' ou 'canônico'. "
        "Sem prefácio longo."
    )
    user = (
        "DADOS DE ENTRADA:\n"
        f"- Metodologia Base: {canonico}\n"
        f"- Adaptação PEI da Escola: {adaptacao or '(nenhuma orientação adicional)'}\n"
        f"- Condição / AEE: {cond}\n"
        f"- AEE.texto_escola: {aee_txt}\n"
        f"- AEE.campos_experiencia_metodologica: {aee_campos}\n"
        f"- PEI.experiencias_adaptadas_individuais: {pei_exp}\n"
        f"- Dicas da Trincheira (Professores): {_format_sugestoes_para_prompt(sugestoes)}\n\n"
        "Gere agora o roteiro consolidado conforme as diretrizes."
    )
    try:
        bruto = invoke_text(system_prompt=system, user_content=user, max_tokens=2048)
        return _limpar_roteiro_ia(bruto)
    except Exception as exc:
        print(f"[school-llm] falha adaptar PEI×metodologia: {exc}", file=sys.stderr, flush=True)
        raise


_SYSTEM_AEE_METODOLOGIA = (
    "Você é um Psicopedagogo Sênior. Crie um roteiro de aula ÚNICO e passo a passo, "
    "adaptando uma metodologia para uma deficiência específica.\n"
    "DIRETRIZ:\n"
    "Mescle tudo organicamente. Se o AEE pede rotinas visuais, insira isso nos passos. "
    "Se o professor deu uma dica, coloque como 'Dica Prática' no passo adequado. "
    "Não crie cabeçalhos isolados para sugestões. O retorno deve ser exclusivamente "
    "o texto final em Markdown."
)


def sintetizar_adaptacao_aee_metodologia(
    *,
    texto_canonico_metodologia: str,
    texto_campos_experiencia_aee: str,
    sugestoes_professores: list[str] | None = None,
    condicao_categoria: str = "",
) -> str:
    """Roteiro único: metodologia canônica + campos AEE + sugestões (por condição)."""
    canonico = (texto_canonico_metodologia or "").strip() or "(metodologia vazia)"
    campos = (texto_campos_experiencia_aee or "").strip() or "(campos de experiência ausentes)"
    sugestoes = [
        str(s).strip() for s in (sugestoes_professores or []) if str(s or "").strip()
    ]
    cond = (condicao_categoria or "").strip() or "condição não especificada"

    if os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes"):
        blocos = [
            f"Roteiro adaptado — {cond}",
            canonico[:500],
            f"Aplicando campos de experiência: {campos[:400]}",
        ]
        if sugestoes:
            blocos.append(
                "Dica Prática: " + " | ".join(s[:200] for s in sugestoes[:3])
            )
        return _limpar_roteiro_ia("\n\n".join(blocos))

    user = (
        "ENTRADAS:\n"
        f"- Metodologia Original: {canonico}\n"
        f"- Diretrizes e Campos de Experiência da Deficiência ({cond}): {campos}\n"
        f"- Sugestões dos Professores (se houver): "
        f"{_format_sugestoes_para_prompt(sugestoes) if sugestoes else '(nenhuma)'}\n\n"
        "Gere agora exclusivamente o texto final do roteiro em Markdown."
    )
    try:
        bruto = invoke_text(
            system_prompt=_SYSTEM_AEE_METODOLOGIA,
            user_content=user,
            max_tokens=2048,
        )
        return _limpar_roteiro_ia(bruto)
    except Exception as exc:
        print(
            f"[school-llm] falha sintetizar adaptação AEE×metodologia: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
