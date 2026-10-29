#!/usr/bin/env python3
"""127 — Dia a Dia + Desafios reais (Escola Teste). Não limpa."""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"
OUT = Path("/tmp/prompt-127-b2c.json") if sys.platform != "win32" else Path(
    r"C:\Projetos\inove4us\scripts\_prompt-127-b2c.json"
)

MISSAO_CAMPUS = (
    'A "Operação Campus 2.0" é um desafio de longa duração onde cinco turmas de '
    "matemática atuarão como consórcios complementares para entregar o Projeto "
    "Executivo da nova infraestrutura escolar, orquestrando a execução do semestre "
    "em oito etapas estratégicas. No Passo 1 (Mapeamento Espacial e Topografia), "
    "a primeira turma inicia o levantamento físico da escola, calculando áreas "
    "tridimensionais, descontando vãos e analisando ângulos de inclinação para "
    "rampas de acessibilidade, sendo este o momento ideal para engajar alunos com "
    "TDAH em funções de exploração física, permitindo que mapeiem os fluxos em "
    "movimento pela escola. Avançando para o Passo 2 (Engenharia de Insumos), a "
    "segunda turma recebe as medidas originais e utiliza proporções e geometria "
    "plana para converter áreas em materiais de construção precisos, desenhando "
    "a paginação de pisos e revestimentos para manter o desperdício abaixo de 5%. "
    "No Passo 3 (Matemática Financeira e Orçamento), a terceira equipe entra em cena "
    "para precificar a lista de compras, analisando o índice de inflação da "
    "construção civil e calculando juros compostos para blindar o fluxo de caixa "
    "da instituição. Durante esta fase, alunos com discalculia podem focar na "
    "pesquisa qualitativa de fornecedores e estruturação visual do orçamento "
    "enquanto os colegas parametrizam as fórmulas pesadas. Durante o Passo 4 "
    "(Logística e PERT/CPM), a quarta turma desenha o Caminho Crítico da obra "
    "utilizando teoria dos grafos e análise combinatória, calculando probabilidades "
    "de atraso e dimensionando os turnos de trabalho para que a reforma não "
    "paralise as aulas, incorporando na modelagem o ciclo de chuvas "
    "característico de Fortaleza. No Passo 5 (Sustentabilidade e ROI), a quinta "
    "equipe realiza os cálculos de eficiência, aplicando trigonometria para "
    "calcular o ângulo ideal de inclinação das placas solares considerando a "
    "incidência solar local, além de modelar funções exponenciais para provar à "
    "diretoria em quantos meses a economia gerada pagará o investimento da "
    "reforma. Com as fases setoriais superadas, o Passo 6 (Integração dos "
    "Consórcios) exige que representantes de cada turma se reúnam para uma "
    "validação cruzada de dados, auditando se o cronograma logístico é compatível "
    "com o orçamento financeiro e a topografia levantada. O Passo 7 (Preparação "
    "de Dashboards) é dedicado à tradução de todos os sistemas de equações e "
    "orçamentos em painéis executivos visuais e relatórios de viabilidade "
    "compreensíveis para não-engenheiros. Finalmente, o Passo 8 (A Grande Defesa "
    "Executiva) culmina em um Pitch formal onde o comitê integrado dos alunos "
    "apresenta o Masterplan financeiro e estrutural definitivo para a diretoria da "
    "escola, entregando um projeto sustentável e matemático pronto para ser "
    "executado. Complemento do professor: Já temos a planta baixa arquitetônica "
    "original da escola (que está desatualizada) e o histórico das faturas de "
    "energia e água dos últimos 12 meses. A primeira evidência de campo que quero "
    "coletar com os alunos é uma Auditoria de Divergência na área externa. Quero "
    "que a Turma 1 faça a medição real a trena e laser para comparar com o "
    "documento antigo, enquanto a Turma 5 mapeia as zonas de calor e a incidência "
    "do sol característico de Fortaleza nesse mesmo espaço. O objetivo é criar "
    "um choque de realidade imediato entre o que está no papel e o espaço físico real."
)

MET_DAILY = "agil_minute_paper"
MET_DESAFIO = "criativa_abordagem_problematizadora"
HOJE = date.today().isoformat()
ENC1 = (date.today() - timedelta(days=3)).isoformat()
ENC2 = (date.today() - timedelta(days=2)).isoformat()


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=30)
    data = r.json() if r.content else {}
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise SystemExit(f"login {email}: {data}")
    return s


def j(r: requests.Response):
    if not r.content:
        return {}
    try:
        body = r.json()
    except Exception:
        return {"raw": (r.text or "")[:600]}
    return body


def cred(s: requests.Session):
    me = j(s.get(f"{BASE}/api/auth/me", timeout=20))
    u = me.get("user") or me
    return u.get("creditos_ia"), u


def slim_err(r: requests.Response) -> dict:
    b = j(r)
    return {
        "http": r.status_code,
        "error": b.get("error") or b.get("code"),
        "code": b.get("code"),
        "ok": r.ok,
    }


def cards_from_plano(plano: dict) -> list[dict]:
    raw = (plano or {}).get("tarefas_kanban") or []
    out = []
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or f"t{i + 1}")
        item = dict(c)
        item["id"] = cid
        item["coluna"] = item.get("coluna") or "para_fazer"
        item["origem_card"] = item.get("origem_card") or "catalogo"
        out.append(item)
    return out


def entidades_campus(textos: list[str]) -> dict:
    blob = " ".join(textos).lower()
    return {
        "consorcio_ou_turma": any(x in blob for x in ("turma", "consórcio", "consorcio")),
        "passo": "passo" in blob or "pert" in blob,
        "cinco_pct": "5%" in blob or "5 %" in blob or "desperdício" in blob or "desperdicio" in blob,
        "material": any(x in blob for x in ("planta", "fatura", "trena", "laser")),
        "fortaleza": "fortaleza" in blob,
        "prefixo_adaptando": any("adaptando para sua aula" in t.lower() for t in textos),
    }


def main() -> int:
    out: dict = {"prompt": 127, "hoje": HOJE, "bugs": []}
    h = requests.get(f"{BASE}/api/health", timeout=20)
    out["health"] = {"http": h.status_code, **(j(h) if h.ok else {})}
    s = login(HOMOLOG)
    cred0, user0 = cred(s)
    out["user"] = {
        "id_clie": user0.get("id_clie"),
        "is_institutional": user0.get("is_institutional"),
        "creditos_antes": cred0,
    }

    # --- 5. Dia a Dia ---
    temas = j(s.get(f"{BASE}/api/daily/bncc-temas", params={"disciplina": "Matemática", "curso_ano": "6º ano"}, timeout=30))
    items = temas.get("items") or []
    tema = next((t for t in items if isinstance(t, dict) and (t.get("codigo") or t.get("habilidade_codigo"))), None)
    if not tema and items:
        tema = items[0] if isinstance(items[0], dict) else {}
    codigo = str((tema or {}).get("codigo") or (tema or {}).get("habilidade_codigo") or "EF06MA01")
    nome_tema = str((tema or {}).get("tema") or (tema or {}).get("titulo") or "Sistema de numeração decimal")
    texto_oficial = str((tema or {}).get("texto_oficial") or (tema or {}).get("descricao") or (
        "Comparar, ordenar, ler e escrever números naturais e números racionais "
        "cuja representação decimal é finita, fazendo uso da reta numérica."
    ))
    r_cont = s.post(
        f"{BASE}/api/daily/conteudo-sugerido",
        json={
            "fonte": "bncc",
            "tema": nome_tema,
            "nivel_turma": "6º ano",
            "habilidade_codigo": codigo,
            "disciplina": "Matemática",
            "texto_oficial": texto_oficial,
        },
        timeout=90,
    )
    d_cont = j(r_cont)
    r_met = s.get(
        f"{BASE}/api/daily/metodologia",
        params={"id": MET_DAILY, "turma_nome": "6º Ano A", "anexar_conteudo": "0"},
        timeout=30,
    )
    d_met = j(r_met)
    texto = (d_cont.get("texto_montado") or "")[:1800]
    r_plan = s.post(
        f"{BASE}/api/daily/planejar",
        json={
            "data_planejada": HOJE,
            "turma_nome": "6º Ano A",
            "tema_aula": f"{codigo} — {nome_tema}",
            "ementa_topico": nome_tema,
            "habilidades_bncc": [codigo],
            "objetivo_aprendizagem": "Ler, comparar e localizar números naturais e racionais na reta numérica, com evidência escrita ao fim da aula.",
            "acolhida": "Minute Paper: cada aluno registra em 2 minutos o que já sabe sobre a reta numérica.",
            "conteudo_essencial": texto or texto_oficial,
            "fechamento_checkout": "Minute Paper de saída: um número que o aluno posicionou na reta e por quê.",
            "dinamica_ativa_id": MET_DAILY,
            "dinamica_ativa_fonte": "inove_local",
            "tipo_registro": "aula",
            "origem": "manual",
        },
        timeout=40,
    )
    d_plan = j(r_plan)
    aula = d_plan.get("aula") or {}
    aula_id = d_plan.get("id") or aula.get("id")
    if aula_id:
        s.put(f"{BASE}/api/daily/{aula_id}", json={"status": "planejado"}, timeout=20)
    ov = ((d_met.get("dinamica") or {}).get("escola_override") or {})
    out["dia_a_dia"] = {
        "bncc": {"http": temas.get("success") and 200 or r_cont.status_code, "n_temas": len(items), "codigo": codigo, "tema": nome_tema[:120]},
        "conteudo": {
            "http": r_cont.status_code,
            "cached": d_cont.get("cached"),
            "ia_called": d_cont.get("ia_called"),
            "has_texto": bool(d_cont.get("texto_montado")),
        },
        "metodologia": {
            "http": r_met.status_code,
            "ia_called": d_met.get("ia_called"),
            "fonte": d_met.get("fonte"),
            "nome": (d_met.get("dinamica") or {}).get("nome"),
            "escola_override": bool(ov.get("ativa") or ov),
            "versao": ov.get("versao"),
        },
        "planejar": {
            **slim_err(r_plan),
            "aula_id": aula_id,
            "id_evento": aula.get("id_evento_agenda"),
            "status": aula.get("status"),
            "override_kanban": ((aula.get("kanban_state") or {}).get("escola_override") or {}),
        },
    }
    if not r_plan.ok:
        out["bugs"].append({"secao": "5_dia_a_dia", **slim_err(r_plan), "body": d_plan})

    # --- 6. Desafio rico ---
    cred_pre_wiz, _ = cred(s)
    r1 = s.post(
        f"{BASE}/api/wizard/estruturar",
        json={"problema": MISSAO_CAMPUS, "contexto": "", "metodologia_desejada_id": MET_DESAFIO},
        timeout=120,
    )
    d1 = j(r1)
    caminhos = d1.get("caminhos") or []
    caminho = next((c for c in caminhos if c.get("id") == "A"), caminhos[0] if caminhos else None)
    r2 = None
    d2 = {}
    if caminho:
        r2 = s.post(
            f"{BASE}/api/wizard/selecionar-caminho",
            json={"caminho": caminho, "problema": MISSAO_CAMPUS},
            timeout=120,
        )
        d2 = j(r2)
    plano = d2.get("plano_eduscrum") or {}
    cards = cards_from_plano(plano)
    comos = [str(c.get("como_executar_detalhado") or c.get("mecanica_passo_a_passo") or "") for c in cards]
    cred_pos_wiz, _ = cred(s)
    id_met = (caminho or {}).get("id_metodologia") or plano.get("id_metodologia") or MET_DESAFIO
    plan_data = {
        "problema": MISSAO_CAMPUS[:500],
        "hipotese": d1.get("hipotese_teste") or "Consórcios de matemática entregam o masterplan do Campus 2.0 com evidência de campo.",
        "causas": d1.get("causas_raiz") or [{"titulo": "Planta desatualizada", "descricao": "Divergência entre papel e espaço real"}],
        "plano": {**plano, "id_metodologia": id_met, "tarefas_kanban": cards},
        "plano_eduscrum": plano,
    }
    titulo_ativo = "Operação Campus 2.0 — Projeto Executivo"
    r_des = s.post(
        f"{BASE}/api/desafios",
        json={"titulo": titulo_ativo, "tema": titulo_ativo, "plan_data": plan_data},
        timeout=40,
    )
    d_des = j(r_des)
    did = d_des.get("desafio_id") or (d_des.get("desafio") or {}).get("id")
    kanban = [{"id": c["id"], "titulo": c.get("titulo"), "coluna": c.get("coluna") or "para_fazer", "origem_card": "catalogo", "editado": False} for c in cards]
    r_put_k = s.put(f"{BASE}/api/desafios/{did}", json={"kanban_state": {"tarefas": kanban}}, timeout=30) if did else None
    cid0 = cards[0]["id"] if cards else "t1"
    r_pei = s.post(
        f"{BASE}/api/kanban/adaptar-pei",
        json={
            "card_id": cid0,
            "titulo_card": cards[0].get("titulo") if cards else "Observação da Realidade",
            "descricao_card": (comos[0] if comos else "")[:800],
            "perfil_selecionado": "TEA",
            "aluno_nome": "Lucas Mendes",
            "metodologia_id": id_met,
            "desafio_id": did,
            "coluna": "para_fazer",
        },
        timeout=90,
    ) if did else None
    moved = []
    for i, c in enumerate(kanban):
        if i == 0:
            c["coluna"] = "fazendo"
        elif i == 1:
            c["coluna"] = "pronto"
        else:
            c["coluna"] = "para_fazer"
        moved.append(dict(c))
    r_move = s.put(f"{BASE}/api/desafios/{did}", json={"kanban_state": {"tarefas": moved}}, timeout=30) if did else None
    sess = str(uuid.uuid4())
    aulas_ativas = [
        {
            "data": HOJE,
            "turma": "6º Ano A",
            "turno": "manha",
            "modo_execucao": "reinicio",
            "card_ids": [c["id"] for c in cards[:2]] or [cid0],
            "escopos": {c["id"]: f"Aula manhã — {c.get('titulo')}" for c in cards[:2]},
        },
        {
            "data": HOJE,
            "turma": "1ª Série A",
            "turno": "tarde",
            "modo_execucao": "reinicio",
            "card_ids": [c["id"] for c in cards[2:4]] or [cid0],
            "escopos": {c["id"]: f"Aula tarde — {c.get('titulo')}" for c in cards[2:4]},
        },
        {
            "data": HOJE,
            "turma": "9º Ano A",
            "turno": "noite",
            "modo_execucao": "reinicio",
            "card_ids": [c["id"] for c in cards[4:5]] or [cid0],
            "escopos": {c["id"]: f"Aula noite — {c.get('titulo')}" for c in cards[4:5]},
        },
    ]
    r_reg = s.post(
        f"{BASE}/api/agenda-eventos/registrar-aulas",
        json={
            "titulo": titulo_ativo,
            "tema": titulo_ativo,
            "desafio_id": did,
            "plano_session": sess,
            "plan_data": plan_data,
            "kanban_state": {"tarefas": moved},
            "causas": plan_data["causas"],
            "aulas": aulas_ativas,
        },
        timeout=50,
    ) if did else None
    rb_reg = j(r_reg) if r_reg else {}
    evs = rb_reg.get("eventos") or []
    eids = [e.get("id_evento") for e in evs]
    out["desafio_ativo"] = {
        "estruturar": {"http": r1.status_code, "fallback": d1.get("fallback"), "n_caminhos": len(caminhos), "creditos": d1.get("creditos_ia")},
        "selecionar": {
            "http": r2.status_code if r2 is not None else None,
            "como_fazer_reescrito": d2.get("como_fazer_reescrito"),
            "como_fazer_meta": d2.get("como_fazer_meta"),
            "n_cards": len(cards),
            "titulos": [c.get("titulo") for c in cards],
            "entidades": entidades_campus(comos),
            "como_fazer_amostra": [t[:220] for t in comos[:3]],
        },
        "creditos_pre_wizard": cred_pre_wiz,
        "creditos_pos_wizard": cred_pos_wiz,
        "criar": slim_err(r_des) | {"desafio_id": did},
        "kanban_put": slim_err(r_put_k) if r_put_k else None,
        "pei": slim_err(r_pei) | {"fonte": j(r_pei).get("fonte"), "ia_called": j(r_pei).get("ia_called"), "aluno": "Lucas Mendes", "condicao": "TEA"} if r_pei else None,
        "kanban_move": slim_err(r_move) if r_move else None,
        "registrar": ({**slim_err(r_reg), "eventos": [{"id": e.get("id_evento"), "turma": e.get("turma"), "turno": e.get("turno"), "data": e.get("data_evento")} for e in evs]} if r_reg else {"skipped": True}),
        "id_metodologia": id_met,
    }
    if r_reg and not r_reg.ok:
        out["bugs"].append({"secao": "6_registrar", **slim_err(r_reg), "body": rb_reg})
    if r1.status_code != 200:
        out["bugs"].append({"secao": "6_wizard_estruturar", **slim_err(r1)})
    if r2 is not None and r2.status_code != 200:
        out["bugs"].append({"secao": "6_wizard_selecionar", **slim_err(r2)})

    # --- 8. Curadoria no desafio ATIVO (fecha só a 1ª aula da cadeia) ---
    sugestao = (
        "Na Auditoria de Divergência, o Minute Paper de saída funcionou melhor em duplas "
        "heterogêneas: um aluno mede, o outro registra na planta. Sugiro formalizar esse "
        "pareamento na diretriz da escola para a Abordagem Problematizadora."
    )
    r_conc = None
    if eids and eids[0]:
        r_conc = s.post(
            f"{BASE}/api/agenda-eventos/{eids[0]}/concluir-aula",
            json={
                "relato_sala": (
                    "Turma 6º Ano A iniciou o mapeamento da área externa com trena. "
                    "Lucas Mendes (TEA) usou o roteiro visual do subcard PEI e concluiu "
                    "o registro das medidas do pátio com apoio de um par."
                ),
                "participantes": "6º Ano A — 6 alunos presentes, incluindo Lucas Mendes",
                "has_teacher_adaptations": True,
                "sugestao_coordenacao": sugestao,
                "metodologia_usada": (caminho or {}).get("metodologia") or "Abordagem Problematizadora",
                "aula_contexto": "Operação Campus 2.0 — Passo 1, manhã, 6º Ano A",
            },
            timeout=40,
        )
    out["curadoria_envio"] = slim_err(r_conc) if r_conc else {"skipped": True, "reason": "sem evento"}
    if r_conc and not r_conc.ok:
        out["bugs"].append({"secao": "8_concluir_sugestao", **slim_err(r_conc), "body": j(r_conc)})

    # --- 7. Desafio simples ENCERRADO ---
    cid_e = f"c127-enc-{uuid.uuid4().hex[:6]}"
    titulo_enc = "Fechamento — síntese da reta numérica"
    plan_enc = {
        "problema": "Consolidar a leitura da reta numérica em duas aulas curtas, com evidência escrita.",
        "hipotese": "Dois encontros bastam para cada aluno posicionar um número racional na reta.",
        "causas": [{"titulo": "Síntese", "descricao": "Encerrar ciclo demonstrável"}],
        "plano": {
            "missao": titulo_enc,
            "id_metodologia": "agil_mapeamento_mental",
            "tarefas_kanban": [{"id": cid_e, "titulo": "Síntese na reta numérica", "coluna": "para_fazer"}],
        },
    }
    r_de = s.post(f"{BASE}/api/desafios", json={"titulo": titulo_enc, "tema": titulo_enc, "plan_data": plan_enc}, timeout=30)
    did_e = j(r_de).get("desafio_id") or (j(r_de).get("desafio") or {}).get("id")
    s.put(f"{BASE}/api/desafios/{did_e}", json={"kanban_state": {"tarefas": [{"id": cid_e, "titulo": "Síntese na reta numérica", "coluna": "para_fazer"}]}}, timeout=20)
    r_re = s.post(
        f"{BASE}/api/agenda-eventos/registrar-aulas",
        json={
            "titulo": titulo_enc,
            "tema": titulo_enc,
            "desafio_id": did_e,
            "plano_session": str(uuid.uuid4()),
            "plan_data": plan_enc,
            "kanban_state": {"tarefas": [{"id": cid_e, "titulo": "Síntese na reta numérica", "coluna": "para_fazer"}]},
            "causas": plan_enc["causas"],
            "aulas": [
                {"data": ENC1, "turma": "6º Ano A", "turno": "tarde", "modo_execucao": "reinicio", "card_ids": [cid_e], "escopos": {cid_e: "Aula 1 síntese"}},
                {"data": ENC2, "turma": "6º Ano A", "turno": "tarde", "modo_execucao": "continuidade", "card_ids": [cid_e], "escopos": {cid_e: "Aula 2 síntese"}},
            ],
        },
        timeout=40,
    )
    ev_e = j(r_re).get("eventos") or []
    eids_e = [e.get("id_evento") for e in ev_e]
    concs = []
    for i, eid in enumerate(eids_e):
        rc = s.post(
            f"{BASE}/api/agenda-eventos/{eid}/concluir-aula",
            json={
                "relato_sala": f"Aula {i + 1} de síntese concluída. Alunos posicionaram números na reta.",
                "participantes": "6º Ano A",
            },
            timeout=30,
        )
        concs.append(slim_err(rc))
    g_end = s.get(f"{BASE}/api/desafios/{did_e}", timeout=30)
    dend = j(g_end).get("desafio") or {}
    put_end = s.put(
        f"{BASE}/api/desafios/{did_e}",
        json={"kanban_state": {"tarefas": [{"id": cid_e, "titulo": "NÃO DEVE PERSISTIR"}]}},
        timeout=30,
    )
    put_b = j(put_end)
    out["desafio_encerrado"] = {
        "criar": slim_err(r_de) | {"desafio_id": did_e},
        "registrar": slim_err(r_re) | {"eventos": eids_e},
        "concluir": concs,
        "encerrado": dend.get("encerrado"),
        "put_http": put_end.status_code,
        "put_code": put_b.get("code"),
        "ok_120": dend.get("encerrado") is True and put_end.status_code == 403,
    }
    if not out["desafio_encerrado"]["ok_120"]:
        out["bugs"].append({"secao": "7_encerramento", **out["desafio_encerrado"]})

    # --- 9. Checagens (antes da curadoria School; avisos reabertos depois) ---
    cred1, user1 = cred(s)
    aloc = s.get(f"{BASE}/api/me/alocacoes-escola", timeout=20)
    mural = s.get(f"{BASE}/api/mural", timeout=20)
    agenda = s.get(f"{BASE}/api/agenda-eventos", params={"mes": HOJE[:7]}, timeout=20)
    grafo = s.get(f"{BASE}/api/agenda-eventos/grafo", timeout=20)
    avisos = s.get(f"{BASE}/api/avisos-mesa", timeout=20)
    mesa = s.get(f"{BASE}/api/desafios/{did}/mesa", timeout=20) if did else None
    daily_list = s.get(f"{BASE}/api/daily", timeout=20)
    g_ativo = s.get(f"{BASE}/api/desafios/{did}", timeout=20) if did else None
    d_ativo = (j(g_ativo).get("desafio") or {}) if g_ativo else {}

    ev_ag = j(agenda).get("eventos") or []
    hoje_ev = []
    for e in ev_ag:
        de = str(e.get("data_evento") or "")
        if de.startswith(HOJE):
            hoje_ev.append({"id": e.get("id_evento"), "hora": de[11:19], "turma": e.get("turma"), "turno": e.get("turno"), "tipo": e.get("tipo"), "titulo": (e.get("titulo") or "")[:80]})
    horas = sorted({h["hora"] for h in hoje_ev if h.get("hora")})
    nos = (j(grafo).get("nos") or j(grafo).get("nodes") or [])
    out["checagem"] = {
        "creditos_depois": cred1,
        "alocacoes": {"http": aloc.status_code, "n": len(j(aloc).get("alocacoes") or j(aloc).get("items") or []), "body_keys": list(j(aloc).keys())[:8]},
        "mural": {"http": mural.status_code, "n": len(j(mural).get("itens") or j(mural).get("comunicados") or j(mural).get("items") or [])},
        "agenda": {"http": agenda.status_code, "n_mes": len(ev_ag), "hoje": hoje_ev, "horarios_distintos_hoje": horas},
        "grafo": {"http": grafo.status_code, "n_nos": len(nos), "ok": grafo.ok},
        "avisos_mesa": {"http": avisos.status_code, "n": len(j(avisos).get("avisos") or []), "tipos": [a.get("tipo") for a in (j(avisos).get("avisos") or [])]},
        "daily_list": {"http": daily_list.status_code, "n": len(j(daily_list).get("aulas") or j(daily_list).get("items") or [])},
        "desafio_ativo_persistiu": {
            "http": g_ativo.status_code if g_ativo else None,
            "encerrado": d_ativo.get("encerrado"),
            "titulo": d_ativo.get("titulo"),
        },
        "mesa_ativo": {
            "http": mesa.status_code if mesa else None,
            "n_cards": len(j(mesa).get("cards") or []) if mesa else 0,
            "pei_subcards": sum(1 for c in (j(mesa).get("cards") or []) if c.get("parent_card_id") or c.get("tipo") == "pei") if mesa else 0,
        },
    }
    # persistência: reabrir
    aloc2 = s.get(f"{BASE}/api/me/alocacoes-escola", timeout=20)
    mural2 = s.get(f"{BASE}/api/mural", timeout=20)
    g2 = s.get(f"{BASE}/api/desafios/{did}", timeout=20) if did else None
    out["persistencia"] = {
        "alocacoes_igual": (j(aloc2).get("alocacoes") or j(aloc2).get("items")) == (j(aloc).get("alocacoes") or j(aloc).get("items")),
        "mural_n": len(j(mural2).get("itens") or j(mural2).get("comunicados") or j(mural2).get("items") or []),
        "desafio_titulo": ((j(g2).get("desafio") or {}).get("titulo") if g2 else None),
    }

    out["credito"] = {"antes": cred0, "depois": cred1, "delta": (cred1 - cred0) if isinstance(cred0, (int, float)) and isinstance(cred1, (int, float)) else None}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
