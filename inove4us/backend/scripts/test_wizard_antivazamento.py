"""Regressão: barreira final + expressões + anti-Recanto + anti-debug."""
from wizard_qualidade import (
    aplicar_barreira_final_payload,
    avaliar_qualidade,
    causas_somente_do_relato,
    contem_termo_do_relato,
    contexto_seguro_para_ui,
    estimate_tokens,
    expressoes_do_relato,
    extrair_trecho_relato,
    forcar_ancoragem_payload,
    montar_user_content_estruturar,
    parece_causa_enlatada,
    parece_lista_tokens_soltos,
    parece_texto_debug_ui,
    relato_insufficiente,
    sanitizar_causas_ia,
    texto_professor_limpo,
    vaza_contra_corpus,
)
from prompts.inov_ativas import build_estruturar_system_prompt

PROIBIDOS_UI = (
    "título sugerido",
    "titulo sugerido",
    "elementos concretos a preservar",
    "dor central do seu relato",
    "relato:",
    "escola recanto",
)

REF_RECANTO = (
    "Na Escola Recanto, 8º ano do Fundamental II, turno Manhã, "
    "alunos usam smartphones ou notebooks para fins não acadêmicos durante a aula."
)
REF_ABSENTEISMO = (
    "Alunos faltam às aulas frequentemente. Percepção de que o conteúdo "
    "da aula apenas replica as leituras obrigatórias de forma monótona."
)
CORPUS = [REF_RECANTO, REF_ABSENTEISMO]

# --- Caso legado smartphones ---
relato_disp = (
    "sou professor no ensino secundario da Escola Nossa Senhora das Gracas "
    "e tem uma turma de 35 alunos que e muito dispersa que nao se concentra "
    "nas atividades gera"
)
assert relato_insufficiente("curto") is not None
assert relato_insufficiente(relato_disp) is None

causas = causas_somente_do_relato(relato_disp, "Escola X, 8o ano", CORPUS)
blob = " ".join(c["descricao"].lower() for c in causas)
assert "smartphone" not in blob
assert "notebook" not in blob
assert "recanto" not in blob
assert all(not parece_texto_debug_ui(c["descricao"]) for c in causas)

# --- Caso córrego + contexto stale Recanto ---
relato_sabia = (
    "Sou professora de Ciências na Escola Municipal Vale Verde. "
    "Temos um projeto sobre o córrego do Sabiá: a água está escura, com cheiro "
    "e lixo acumulado. A escola se inscreveu no Concurso Municipal Escola Sustentável 2026 "
    "(prazo 28/11). Três turmas em cadeia: 6º ano B faz diagnóstico de campo; "
    "8º ano A propõe intervenção; 3º ano EM monta dossiê e mensuração. "
    "Preciso de hipóteses testáveis sobre a causa (esgoto clandestino, coleta irregular, "
    "bueiro entupido) e de um plano que engaje as turmas."
)
contexto_stale = "Escola Recanto, 8º ano do Fundamental II, turno Manhã."

exprs = expressoes_do_relato(relato_sabia)
assert any("córrego" in e.lower() or "corrego" in e.lower() or "sabiá" in e.lower() or "sabia" in e.lower() for e in exprs), exprs
assert any("vale verde" in e.lower() for e in exprs), exprs

ctx_safe = contexto_seguro_para_ui(contexto_stale, relato_sabia, CORPUS)
assert "recanto" not in ctx_safe.lower(), ctx_safe
assert "vale" in ctx_safe.lower() or "escola" in ctx_safe.lower(), ctx_safe
assert "para atuar" not in ctx_safe.lower(), ctx_safe

# --- Contexto seguro: prioridade do request + anti falso-positivo «escola para atuar» ---
caso1_problema = (
    "Os alunos irão investigar os focos de dengue no entorno da escola."
)
caso1_contexto = "Escola municipal no bairro Aldeota, Fortaleza"
ctx1 = contexto_seguro_para_ui(caso1_contexto, caso1_problema, CORPUS)
assert "aldeota" in ctx1.lower(), ctx1
assert "fortaleza" in ctx1.lower(), ctx1

caso2_problema = (
    "A prefeitura convocou a sua escola para atuar como um Polo de "
    "Inteligência e Intervenção para o bairro."
)
ctx2 = contexto_seguro_para_ui("", caso2_problema, CORPUS)
assert "para atuar" not in ctx2.lower(), ctx2
assert ctx2.lower() != "escola para atuar como um"
assert "atuar como" not in ctx2.lower(), ctx2

caso3_problema = (
    "Os alunos precisam investigar maneiras de reduzir o desperdício de água."
)
ctx3 = contexto_seguro_para_ui("", caso3_problema, CORPUS)
assert ctx3 == "", repr(ctx3)
assert "realidade descrita" not in ctx3.lower()

caso4_problema = "A escola irá desenvolver ações junto à comunidade."
caso4_contexto = "2º ano do Ensino Médio · escola pública de Fortaleza"
ctx4 = contexto_seguro_para_ui(caso4_contexto, caso4_problema, CORPUS)
assert "fortaleza" in ctx4.lower(), ctx4
assert "ensino" in ctx4.lower() or "2" in ctx4, ctx4

# --- user_content semântico (etapa 2: campos opcionais) ---
uc1 = montar_user_content_estruturar(
    problema_limpo="Os alunos precisam investigar o desperdício de água."
)
assert "PROBLEMA / DESAFIO DO PROFESSOR" in uc1
assert "desperdício de água" in uc1 or "desperdicio de agua" in uc1.lower()
assert "OBJETIVO" not in uc1
assert "TURMA" not in uc1
assert "DURAÇÃO" not in uc1 and "DURACAO" not in uc1.upper()
assert "CONTEXTO INFORMADO" not in uc1
assert "N/A" not in uc1
assert "não informado" not in uc1.lower()

uc2 = montar_user_content_estruturar(
    problema_limpo="Investigar focos de dengue no entorno da escola.",
    objetivo="Mapear focos e propor intervenção de baixo custo.",
    turma_nivel="8º ano",
    disciplina_area="Ciências",
    duracao="6 aulas",
    contexto_seguro="Escola municipal no bairro Aldeota, Fortaleza",
)
assert "OBJETIVO / RESULTADO ESPERADO" in uc2
assert "Mapear focos" in uc2
assert "TURMA / NÍVEL" in uc2 and "8º ano" in uc2
assert "DISCIPLINA / ÁREA" in uc2 and "Ciências" in uc2
assert "DURAÇÃO" in uc2 and "6 aulas" in uc2
assert "CONTEXTO INFORMADO" in uc2 and "Aldeota" in uc2
# Ordem dos blocos
assert uc2.index("PROBLEMA") < uc2.index("OBJETIVO") < uc2.index("TURMA")
assert uc2.index("TURMA") < uc2.index("DISCIPLINA") < uc2.index("DURAÇÃO")
assert uc2.index("DURAÇÃO") < uc2.index("CONTEXTO INFORMADO")

# Compatibilidade antiga: só problema + contexto
uc3 = montar_user_content_estruturar(
    problema_limpo="Turma dispersa precisa de papéis claros num projeto curto.",
    contexto_seguro="1º ano EM · escola pública",
)
assert "PROBLEMA / DESAFIO DO PROFESSOR" in uc3
assert "CONTEXTO INFORMADO" in uc3
assert "OBJETIVO" not in uc3
assert "não informado" not in uc3.lower()

# Opcionais vazios / whitespace → omitidos
uc4 = montar_user_content_estruturar(
    problema_limpo="Reduzir o desperdício de água na escola.",
    objetivo="   ",
    turma_nivel="",
    disciplina_area=None,
    duracao="  ",
    contexto_seguro="",
)
assert "OBJETIVO" not in uc4
assert "TURMA" not in uc4
assert "DISCIPLINA" not in uc4
assert "DURAÇÃO" not in uc4
assert "CONTEXTO INFORMADO" not in uc4
assert "N/A" not in uc4

pads = causas_somente_do_relato(relato_sabia, contexto_stale, CORPUS)
assert len(pads) == 3
for i, c in enumerate(pads):
    texto = f"{c['titulo']} {c['descricao']}".lower()
    for p in PROIBIDOS_UI:
        assert p not in texto, (i, p, texto)
    assert not parece_lista_tokens_soltos(c["descricao"]), c["descricao"]
    assert contem_termo_do_relato(c["descricao"], relato_sabia), (i, c)
# Pad legível: sem colagem de fragmentos nem meta-texto «quando o relato as mencionar»
blob_pads = " ".join(c["descricao"].lower() for c in pads)
assert "quando o relato as mencionar" not in blob_pads
assert "para atuar como um e" not in blob_pads
assert "em torno de escola para" not in blob_pads

# 3ª com flag de complemento
assert pads[2].get("precisa_complemento") is True
assert pads[2].get("pergunta_complemento")

# Tokens soltos no template antigo devem ser rejeitados
assert parece_lista_tokens_soltos(
    "O desafio central envolve ciências, municipal e vale, conforme o que você relatou."
)

# --- Barreira final: injeta de propósito texto da base ---
payload_injetado = {
    "causas_raiz": [
        {
            "titulo": "Causa vazada",
            "descricao": REF_RECANTO,
            "origem": "ia_relato",
        },
        {
            "titulo": "Absenteísmo",
            "descricao": REF_ABSENTEISMO,
            "origem": "ia_relato",
        },
        {
            "titulo": "Ok",
            "descricao": "O córrego do Sabiá pede diagnóstico com o 6º ano B.",
            "origem": "ia_relato",
        },
    ],
    "caminhos": [
        {
            "id": "A",
            "metodologia": "Diagnóstico Coletivo",
            "hipotese_teste": REF_RECANTO,
            "resumo": REF_ABSENTEISMO,
        }
    ],
    "qualidade": {},
}
assert vaza_contra_corpus(REF_RECANTO, CORPUS, relato_sabia)[0] is True

bloqueado = aplicar_barreira_final_payload(
    payload_injetado,
    problema=relato_sabia,
    contexto=contexto_stale,
    corpus_refs=CORPUS,
)
assert (bloqueado.get("qualidade") or {}).get("barreira_final_bloqueios", 0) >= 1
final_blob = " ".join(
    f"{c.get('titulo')} {c.get('descricao')}".lower()
    for c in bloqueado["causas_raiz"]
)
assert "recanto" not in final_blob, final_blob
assert "faltam" not in final_blob, final_blob
assert "leituras" not in final_blob, final_blob
for i, c in enumerate(bloqueado["causas_raiz"]):
    assert contem_termo_do_relato(c["descricao"], relato_sabia), (i, c)
    assert not parece_lista_tokens_soltos(c["descricao"])
hip = bloqueado["caminhos"][0]["hipotese_teste"].lower()
assert "recanto" not in hip
assert contem_termo_do_relato(bloqueado["caminhos"][0]["hipotese_teste"], relato_sabia)

# forcar com Recanto no contexto
payload_ok = forcar_ancoragem_payload(
    {
        "causas_raiz": [
            {
                "titulo": "Seu contexto",
                "descricao": f"No contexto «{contexto_stale}», a intervenção precisa responder.",
            }
        ],
        "caminhos": [
            {
                "id": "A",
                "metodologia": "Diagnóstico Coletivo",
                "hipotese_teste": "Os alunos faltam menos.",
            }
        ],
    },
    problema=relato_sabia,
    contexto=contexto_stale,
    corpus_refs=CORPUS,
)
for c in payload_ok["causas_raiz"]:
    assert "recanto" not in f"{c['titulo']} {c['descricao']}".lower()

# Form labels
relato_form = (
    "Título sugerido: Córrego do Sabiá — concurso "
    f"Relato: {relato_sabia}"
)
limpo = texto_professor_limpo(relato_form)
assert "título sugerido" not in limpo.lower()
assert "…" not in extrair_trecho_relato(relato_form)

enlatadas = [
    {
        "titulo": "Causa estrutural",
        "descricao": "Percepção de que o conteúdo da aula apenas replica as leituras obrigatórias de forma monótona.",
    },
    {
        "titulo": "Contexto da turma",
        "descricao": (
            "No contexto «sala de aula», o sintoma «Alunos faltam às aulas frequentemente.» "
            "se manifesta de forma recorrente e precisa de intervenção prática."
        ),
    },
]
assert all(parece_causa_enlatada(c["titulo"], c["descricao"]) for c in enlatadas)

san = sanitizar_causas_ia(
    enlatadas,
    problema=relato_sabia,
    contexto=contexto_stale,
    refs_no_prompt=[{"desc_prob": REF_RECANTO, "razoes_prob": REF_ABSENTEISMO}],
    corpus_refs=CORPUS,
)
for c in san:
    t = f"{c['titulo']} {c['descricao']}".lower()
    assert "recanto" not in t
    assert "faltam" not in t

q_bad = avaliar_qualidade(
    problema=relato_sabia,
    trecho_relato_usado="sala de aula",
    textos_hipoteses=[REF_RECANTO],
    textos_causas=[REF_ABSENTEISMO],
    refs_no_prompt=[{"desc_prob": REF_RECANTO, "razoes_prob": REF_ABSENTEISMO}],
    corpus_refs=CORPUS,
)
assert q_bad["precisa_retry"] is True
assert q_bad["possivel_vazamento"] is True

# --- IA boa e diversificada deve chegar INTACTA (sem pad) ---
ia_diversa = [
    {
        "titulo": "Esgoto clandestino",
        "descricao": (
            "Os alunos levantaram que o escurecimento e o cheiro do córrego do Sabiá "
            "podem vir de esgoto clandestino; isso pede amostragem e rastreio de pontos "
            "de descarga antes de qualquer intervenção."
        ),
        "origem": "ia_relato",
    },
    {
        "titulo": "Desarticulação entre turmas",
        "descricao": (
            "Há risco de desarticulação entre as três turmas (6º ano B, 8º ano A e "
            "3º ano EM): diagnóstico, intervenção e dossiê precisam de handoff explícito "
            "senão o concurso Municipal Escola Sustentável fica incompleto."
        ),
        "origem": "ia_relato",
    },
    {
        "titulo": "Hipóteses sem teste empírico",
        "descricao": (
            "As hipóteses dos alunos (coleta irregular, bueiro entupido) ainda não estão "
            "estruturadas para teste empírico — falta definir evidência, indicador e "
            "prazo até 28/11 para mensuração no dossiê."
        ),
        "origem": "ia_relato",
    },
]
san_ia = sanitizar_causas_ia(
    ia_diversa,
    problema=relato_sabia,
    contexto=contexto_stale,
    refs_no_prompt=[],
    corpus_refs=CORPUS,
)
assert len(san_ia) == 3
for orig, got in zip(ia_diversa, san_ia):
    assert got["descricao"] == orig["descricao"], (orig["titulo"], got["descricao"])
    assert got["origem"] == "ia_relato"
    assert got.get("precisa_complemento") is False

payload_ia = {
    "causas_raiz": list(ia_diversa),
    "caminhos": [
        {
            "id": "A",
            "metodologia": "Diagnóstico Coletivo",
            "hipotese_teste": (
                "Se o 6º ano B mapear pontos de esgoto clandestino no córrego do Sabiá, "
                "a turma terá evidência para testar essa causa antes da intervenção."
            ),
            "trecho_relato_usado": "córrego do Sabiá com água escura e cheiro",
            "resumo": "Diagnóstico coletivo das causas ambientais levantadas pelos alunos.",
        }
    ],
    "trecho_relato_usado": "córrego do Sabiá com água escura e cheiro",
    "qualidade": {},
}
apos_forcar = forcar_ancoragem_payload(
    payload_ia,
    problema=relato_sabia,
    contexto=contexto_stale,
    corpus_refs=CORPUS,
)
apos_barreira = aplicar_barreira_final_payload(
    apos_forcar,
    problema=relato_sabia,
    contexto=contexto_stale,
    corpus_refs=CORPUS,
)
assert (apos_barreira.get("qualidade") or {}).get("barreira_final_bloqueios", 0) == 0
for orig, got in zip(ia_diversa, apos_barreira["causas_raiz"]):
    assert got["descricao"] == orig["descricao"], got["descricao"]
    assert "fio condutor" not in got["descricao"].lower()
    assert "pad_deterministico" != got.get("origem")
# Ângulos distintos preservados
blob_final = " ".join(c["descricao"].lower() for c in apos_barreira["causas_raiz"])
assert "esgoto" in blob_final
assert "desarticulação" in blob_final or "desarticulacao" in blob_final or "turmas" in blob_final
assert "teste empírico" in blob_final or "empirico" in blob_final or "evidência" in blob_final or "evidencia" in blob_final
assert apos_barreira["caminhos"][0]["hipotese_teste"] == payload_ia["caminhos"][0]["hipotese_teste"]

p = build_estruturar_system_prompt(
    "- (estilo) Engajamento: turma dispersa precisa de papeis claros."
)
assert "framework_obrigatorio" in p
assert "id_metodologia" in p
assert "ancoras_de_estilo" in p or "âncoras" in p.lower() or "ancoras" in p.lower()
print("system_tokens_est", estimate_tokens(p))
print("OK barreira + IA intacta + diversidade + contexto_seguro")
