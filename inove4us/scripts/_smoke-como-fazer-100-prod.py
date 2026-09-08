#!/usr/bin/env python3
"""Smoke 100: 2ª chamada Como fazer (Campus 2.0 + desafio curto). Consome 2 créditos por caso."""
from __future__ import annotations

import json
import sys

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"

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

MISSAO_CURTA = (
    "Turma do 6º ano tem dificuldade em somar frações com denominadores diferentes. "
    "Quero uma aula de 50 minutos, em sala, com evidência clara do que cada aluno "
    "conseguiu calcular no fim do encontro."
)

MAGUEREZ = [
    "Observação da Realidade",
    "Levantamento de Pontos-Chave",
    "Teorização",
    "Hipóteses de Solução",
    "Aplicação à Realidade",
]


def login(email: str) -> tuple[requests.Session, dict]:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    data = r.json() if r.content else {}
    if data.get("status") != "granted":
        raise SystemExit(f"login {email}: {data.get('status')}")
    return s, data.get("user") or {}


def titulos(plano: dict) -> list[str]:
    cards = (plano or {}).get("tarefas_kanban") or []
    return [str(c.get("titulo") or c.get("titulo_do_card") or "") for c in cards]


def comos(plano: dict) -> list[str]:
    cards = (plano or {}).get("tarefas_kanban") or []
    return [
        str(c.get("como_executar_detalhado") or c.get("mecanica_passo_a_passo") or "")
        for c in cards
    ]


def entidades_campus(textos: list[str]) -> dict:
    blob = " ".join(textos).lower()
    return {
        "consorcio_ou_turma": any(x in blob for x in ("turma", "consórcio", "consorcio")),
        "passo": "passo" in blob or "pert" in blob,
        "cinco_pct": "5%" in blob or "5 %" in blob or "desperdício" in blob,
        "material": any(x in blob for x in ("planta", "fatura", "trena", "laser")),
        "tdah_ou_disc": "tdah" in blob or "discalcul" in blob,
        "fortaleza": "fortaleza" in blob,
        "prefixo_adaptando": any("adaptando para sua aula" in t.lower() for t in textos),
    }


def rodar_caso(s: requests.Session, problema: str, met_id: str | None) -> dict:
    me0 = s.get(f"{BASE}/api/auth/me", timeout=20).json()
    u0 = me0.get("user") or me0
    cred0 = u0.get("creditos_ia")
    body = {"problema": problema, "contexto": ""}
    if met_id:
        body["metodologia_desejada_id"] = met_id
    r1 = s.post(f"{BASE}/api/wizard/estruturar", json=body, timeout=90)
    d1 = r1.json() if r1.content else {}
    caminhos = d1.get("caminhos") or []
    caminho = next((c for c in caminhos if c.get("id") == "A"), caminhos[0] if caminhos else None)
    tit_antes = titulos((caminho or {}).get("plano_eduscrum") or {})
    r2 = None
    d2 = {}
    if caminho:
        r2 = s.post(
            f"{BASE}/api/wizard/selecionar-caminho",
            json={"caminho": caminho, "problema": problema},
            timeout=90,
        )
        d2 = r2.json() if r2.content else {}
    plano = d2.get("plano_eduscrum") or {}
    me1 = s.get(f"{BASE}/api/auth/me", timeout=20).json()
    u1 = me1.get("user") or me1
    return {
        "estruturar_http": r1.status_code,
        "estruturar_fallback": d1.get("fallback"),
        "creditos_antes": cred0,
        "creditos_depois_estruturar": d1.get("creditos_ia"),
        "selecionar_http": r2.status_code if r2 is not None else None,
        "como_fazer_reescrito": d2.get("como_fazer_reescrito"),
        "como_fazer_meta": d2.get("como_fazer_meta"),
        "creditos_depois": d2.get("creditos_ia") if d2 else u1.get("creditos_ia"),
        "creditos_me": u1.get("creditos_ia"),
        "titulos_antes": tit_antes,
        "titulos_depois": titulos(plano),
        "como_fazer": [t[:280] for t in comos(plano)],
        "entidades": entidades_campus(comos(plano)),
        "metodologia_a": (caminho or {}).get("metodologia"),
        "id_metodologia_a": (caminho or {}).get("id_metodologia"),
    }


def main() -> int:
    health = requests.get(f"{BASE}/api/health", timeout=15).json()
    s, user = login(HOMOLOG)
    campus = rodar_caso(s, MISSAO_CAMPUS, "criativa_abordagem_problematizadora")
    curto = rodar_caso(s, MISSAO_CURTA, None)
    out = {
        "health": {"git_sha": health.get("git_sha"), "ok": health.get("ok")},
        "user": {
            "id_clie": user.get("id_clie"),
            "is_institutional": user.get("is_institutional"),
        },
        "campus": campus,
        "curto": curto,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    mag = campus.get("titulos_depois") == MAGUEREZ
    ents = campus.get("entidades") or {}
    ok = (
        campus.get("estruturar_http") == 200
        and campus.get("selecionar_http") == 200
        and mag
        and campus.get("como_fazer_reescrito") is True
        and not ents.get("prefixo_adaptando")
        and ents.get("consorcio_ou_turma")
        and curto.get("selecionar_http") == 200
        and curto.get("titulos_depois") == curto.get("titulos_antes")
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
