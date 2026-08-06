"""One-shot builder: merge c4–c5 + new c6–c10 questions into versioned catalog."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "catalog_iso9001_c4c5_v1.json"
DST = ROOT / "catalog_iso9001_c4c10_v1.json"

YES_PARTIAL = ["yes", "partial"]
YES_ONLY = ["yes"]


def q(
    id: str,
    theme: str,
    clause_ref: str,
    question: str,
    explanation: str,
    practice: list[str],
    evidence: list[str],
    show_when: dict | None = None,
) -> dict:
    return {
        "id": id,
        "version": "1",
        "theme": theme,
        "clause_ref": clause_ref,
        "question": question,
        "explanation": explanation,
        "practice_examples": practice,
        "evidence_examples": evidence,
        "answer_type": "choice_with_description",
        "required": True,
        "show_when": show_when,
    }


def when_answer(qid: str, values: list[str]) -> dict:
    return {"answer": qid, "in": values}


NEW: list[dict] = [
    # —— 6 Planejamento ——
    q(
        "c6-rsk-01",
        "Riscos e oportunidades",
        "6.1",
        "A empresa identifica riscos e oportunidades que afetam a qualidade do que entrega?",
        "Riscos e oportunidades orientam o que prevenir, melhorar ou explorar — não são só uma lista formal.",
        ["Mapa de riscos do negócio e da qualidade", "Discussão de riscos em reuniões de gestão"],
        ["Registro de riscos e oportunidades vigentes", "Ata que decide tratamentos"],
    ),
    q(
        "c6-rsk-02",
        "Riscos e oportunidades",
        "6.1",
        "Esses riscos e oportunidades geram ações concretas (tratar, monitorar ou aproveitar), e não ficam só documentados?",
        "O valor está no tratamento: quem faz o quê, até quando, e como se sabe se funcionou.",
        ["Plano de tratamento com responsáveis e prazos", "Acompanhamento em painel ou reunião"],
        ["Plano de ação vinculado aos riscos", "Evidência de acompanhamento"],
        when_answer("c6-rsk-01", YES_PARTIAL),
    ),
    q(
        "c6-obj-01",
        "Objetivos da qualidade",
        "6.2",
        "Existem objetivos de qualidade mensuráveis, alinhados ao que a empresa promete ao cliente?",
        "Objetivos bons são específicos, acompanháveis e ligados ao negócio — não slogans genéricos.",
        ["Metas anuais de qualidade e prazo", "Indicadores por processo crítico"],
        ["Lista de objetivos vigentes", "Painel ou relatório de acompanhamento"],
    ),
    q(
        "c6-obj-02",
        "Objetivos da qualidade",
        "6.2",
        "Há um plano claro para alcançar esses objetivos (recursos, responsáveis e prazos)?",
        "Objetivo sem plano vira desejo. O plano mostra como a organização pretende chegar lá.",
        ["Plano por objetivo com marcos", "Orçamento ou capacidade alocada"],
        ["Planos de ação dos objetivos", "Revisão periódica de progresso"],
        when_answer("c6-obj-01", YES_PARTIAL),
    ),
    q(
        "c6-chg-01",
        "Mudanças no sistema",
        "6.3",
        "Quando o sistema de qualidade muda (novo processo, novo produto, nova estrutura), a mudança é planejada e comunicada?",
        "Mudança descontrolada gera falha. Planejar reduz surpresa para equipe e cliente.",
        ["Checklist de mudança", "Comunicado e treinamento na mudança"],
        ["Registro de mudança planejada", "Evidência de comunicação"],
    ),
    # —— 7 Apoio ——
    q(
        "c7-res-01",
        "Recursos",
        "7.1",
        "A empresa disponibiliza pessoas, infraestrutura e ambiente adequados para entregar com qualidade?",
        "Sem capacidade adequada, processos e objetivos não se sustentam no dia a dia.",
        ["Planejamento de capacidade", "Manutenção de equipamentos e ambiente de trabalho"],
        ["Plano de recursos", "Registros de manutenção ou adequação"],
    ),
    q(
        "c7-cmp-01",
        "Competência",
        "7.2",
        "As pessoas que afetam a qualidade têm a competência necessária (e isso é verificado)?",
        "Competência é combinação de educação, treinamento e experiência — e precisa ser comprovável onde importa.",
        ["Matriz de competências", "Treinamentos ligados a funções críticas"],
        ["Registros de capacitação", "Avaliação de eficácia do treinamento"],
    ),
    q(
        "c7-awr-01",
        "Conscientização",
        "7.3",
        "As pessoas entendem a política, os objetivos relevantes e o impacto do seu trabalho na qualidade?",
        "Conscientização não é cartaz na parede: é a pessoa saber por que seu trabalho importa.",
        ["Integração de novos colaboradores", "Conversas de time sobre qualidade"],
        ["Registro de integração", "Evidência de comunicação da política"],
    ),
    q(
        "c7-com-01",
        "Comunicação",
        "7.4",
        "Há comunicação interna e externa definida sobre assuntos de qualidade (o que, quando, para quem)?",
        "Comunicação confusa gera retrabalho e risco com cliente e órgãos.",
        ["Matriz de comunicação", "Canais e rotinas de reporte"],
        ["Procedimento ou matriz de comunicação", "Exemplos de comunicados"],
    ),
    q(
        "c7-doc-01",
        "Informação documentada",
        "7.5",
        "Documentos e registros necessários estão controlados (versão, acesso, retenção) na prática?",
        "O essencial é achar a versão correta na hora certa — e não perder o histórico relevante.",
        ["Controle de documentos e registros", "Pastas ou sistema com versão vigente"],
        ["Lista mestra de documentos", "Exemplos de registros controlados"],
    ),
    # —— 8 Operação ——
    q(
        "c8-pln-01",
        "Planejamento operacional",
        "8.1",
        "A entrega ao cliente é planejada (critérios, controles e recursos) antes de executar?",
        "Planejar a operação evita improvisar qualidade na última hora.",
        ["Plano de produção ou prestação de serviço", "Critérios de aceitação definidos"],
        ["Ordens/planos de trabalho", "Critérios de qualidade do pedido"],
    ),
    q(
        "c8-req-01",
        "Requisitos do cliente",
        "8.2",
        "Os requisitos do cliente (e legais aplicáveis) são entendidos e confirmados antes de aceitar o pedido?",
        "Aceitar o que não se entende gera não conformidade e conflito.",
        ["Revisão de pedido / contrato", "Checklist de requisitos antes da aceitação"],
        ["Registro de revisão de pedido", "Confirmação ao cliente"],
    ),
    q(
        "c8-des-01",
        "Projeto e desenvolvimento",
        "8.3",
        "A empresa projeta ou desenvolve produtos/serviços (ou partes deles)?",
        "Pergunta-porta: se não há projeto, as perguntas seguintes de desenvolvimento não se aplicam.",
        ["Equipe de desenvolvimento", "Ciclo de criação de produto/serviço"],
        ["Portfólio de projetos", "Descrição do processo de desenvolvimento"],
    ),
    q(
        "c8-des-02",
        "Projeto e desenvolvimento",
        "8.3",
        "O desenvolvimento segue etapas com revisões, verificações e validações adequadas?",
        "Etapas e controles evitam descobrir falha só na entrega ao cliente.",
        ["Fases de projeto com gates", "Testes e validação com usuário/cliente"],
        ["Planos de projeto", "Registros de revisão/verificação/validação"],
        when_answer("c8-des-01", YES_PARTIAL),
    ),
    q(
        "c8-ext-01",
        "Fornecedores externos",
        "8.4",
        "A empresa usa fornecedores ou parceiros externos que afetam a qualidade do que entrega?",
        "Pergunta-porta para controle de fornecedores externos.",
        ["Lista de fornecedores críticos", "Contratos com requisitos de qualidade"],
        ["Cadastro de fornecedores", "Contratos ou pedidos com requisitos"],
    ),
    q(
        "c8-ext-02",
        "Fornecedores externos",
        "8.4",
        "Esses fornecedores são selecionados, avaliados e acompanhados com critérios claros?",
        "Dependência externa sem critério vira risco invisível.",
        ["Critérios de homologação", "Avaliação periódica de desempenho"],
        ["Registros de avaliação de fornecedor", "Ações com fornecedores críticos"],
        when_answer("c8-ext-01", YES_PARTIAL),
    ),
    q(
        "c8-prd-01",
        "Produção e prestação do serviço",
        "8.5",
        "A execução (produção ou serviço) tem controles suficientes para manter a qualidade combinada?",
        "Controles no chão de fábrica ou na operação do serviço são o que o cliente sente.",
        ["Instruções de trabalho", "Pontos de verificação na operação"],
        ["Registros de produção/serviço", "Controles e inspeções"],
    ),
    q(
        "c8-rel-01",
        "Liberação e não conformidade",
        "8.6",
        "Só se libera para o cliente o que atende aos critérios acordados?",
        "Liberação sem critério vira entrega arriscada.",
        ["Inspeção final / checklist de liberação", "Autoridade clara para liberar"],
        ["Registros de liberação", "Critérios de aceitação usados"],
    ),
    q(
        "c8-nc-01",
        "Saídas não conformes",
        "8.7",
        "Quando algo sai fora do padrão, isso é identificado, tratado e registrado (incluindo o que fazer com o item)?",
        "Tratar não conformidade operacional evita que o problema chegue — ou volte — ao cliente.",
        ["Segregação e decisão sobre o item", "Registro de não conformidade operacional"],
        ["Registros de NC / retrabalho / descarte", "Autorizações de concessão"],
    ),
    # —— 9 Avaliação de desempenho ——
    q(
        "c9-mon-01",
        "Monitoramento e medição",
        "9.1",
        "A empresa monitora indicadores que mostram se a qualidade e a satisfação do cliente estão sob controle?",
        "Sem medição útil, a gestão opera no escuro.",
        ["Indicadores de processo e de cliente", "Pesquisa ou feedback de satisfação"],
        ["Painéis ou relatórios de indicadores", "Registros de satisfação/reclamações"],
    ),
    q(
        "c9-aud-01",
        "Avaliação interna",
        "9.2",
        "Há avaliações internas planejadas que verificam se o sistema funciona de verdade?",
        "Avaliação interna bem feita revela gaps antes que o cliente ou um avaliador externo os veja.",
        ["Programa anual de avaliação interna", "Equipe treinada e imparcial o suficiente"],
        ["Programa e relatórios de avaliação interna", "Ações decorrentes"],
    ),
    q(
        "c9-mgt-01",
        "Análise crítica da direção",
        "9.3",
        "A direção analisa periodicamente o desempenho do sistema de qualidade e decide o que mudar?",
        "A análise crítica é o momento em que a direção governa o sistema — não só a operação.",
        ["Reunião periódica de análise crítica", "Pauta com dados, riscos e melhorias"],
        ["Atas de análise crítica", "Decisões e ações da direção"],
    ),
    q(
        "c9-mgt-02",
        "Análise crítica da direção",
        "9.3",
        "As decisões dessa análise viram ações acompanhadas (não ficam só na ata)?",
        "Decisão sem acompanhamento não melhora o sistema.",
        ["Plano de ações da análise crítica", "Revisão do status na reunião seguinte"],
        ["Lista de ações com status", "Evidência de fechamento"],
        when_answer("c9-mgt-01", YES_PARTIAL),
    ),
    # —— 10 Melhoria ——
    q(
        "c10-imp-01",
        "Melhoria",
        "10.1",
        "A empresa busca melhorar produtos, serviços e o próprio sistema de qualidade de forma deliberada?",
        "Melhoria contínua não é slogan: é hábito de aprender com o que os dados e as pessoas mostram.",
        ["Programa de melhorias", "Kaizen / projetos priorizados"],
        ["Registro de melhorias", "Resultados antes/depois"],
    ),
    q(
        "c10-capa-01",
        "Não conformidade e ação corretiva",
        "10.2",
        "Quando um problema relevante ocorre, há correção imediata e investigação da causa para não repetir?",
        "Corrigir o sintoma sem tratar a causa faz o problema voltar.",
        ["Fluxo de ação corretiva", "Análise de causa com evidência"],
        ["Registros de ação corretiva", "Verificação de eficácia"],
    ),
    q(
        "c10-capa-02",
        "Não conformidade e ação corretiva",
        "10.2",
        "A eficácia das ações corretivas é verificada depois — e não só “fechada no papel”?",
        "Fechar ação sem verificar é autoengano. A eficácia mostra se o risco realmente caiu.",
        ["Prazo de verificação de eficácia", "Critério claro de “resolveu”"],
        ["Registros de verificação de eficácia", "Reabertura quando não resolveu"],
        when_answer("c10-capa-01", YES_PARTIAL),
    ),
    q(
        "c10-ci-01",
        "Melhoria contínua",
        "10.3",
        "Há evidência de que o sistema de qualidade evolui com o tempo (não só reage a crises)?",
        "Evolução deliberada diferencia organização madura de organização apagando incêndio.",
        ["Backlog de melhorias priorizado", "Revisões que mudam processos de propósito"],
        ["Histórico de melhorias implementadas", "Mudanças de processo documentadas"],
    ),
]


def main() -> None:
    base = json.loads(SRC.read_text(encoding="utf-8"))
    # Add a few real conditions on existing c4–c5 follow-ups
    for item in base["questions"]:
        if item["id"] == "c4-ctx-02":
            item["show_when"] = when_answer("c4-ctx-01", YES_PARTIAL)
        elif item["id"] == "c4-int-02":
            item["show_when"] = when_answer("c4-int-01", YES_PARTIAL)
        elif item["id"] == "c5-pol-02":
            item["show_when"] = when_answer("c5-pol-01", YES_PARTIAL)

    out = {
        "catalog_version": "iso9001-2015-c4c10-v1",
        "title": "Roteiro orientado — da organização à melhoria",
        "standard_label": "ISO 9001:2015 (cláusulas 4 a 10)",
        "disclaimer": (
            "Perguntas próprias do QMind em linguagem empresarial. "
            "Não reproduzem o texto da norma e não geram conformidade automática."
        ),
        "steps": base["steps"],
        "clause_groups": [
            {"id": "4", "label": "Contexto da organização", "refs": ["4.1", "4.2", "4.3", "4.4"]},
            {"id": "5", "label": "Liderança", "refs": ["5.1", "5.2", "5.3"]},
            {"id": "6", "label": "Planejamento", "refs": ["6.1", "6.2", "6.3"]},
            {"id": "7", "label": "Apoio", "refs": ["7.1", "7.2", "7.3", "7.4", "7.5"]},
            {"id": "8", "label": "Operação", "refs": ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7"]},
            {"id": "9", "label": "Avaliação de desempenho", "refs": ["9.1", "9.2", "9.3"]},
            {"id": "10", "label": "Melhoria", "refs": ["10.1", "10.2", "10.3"]},
        ],
        "questions": base["questions"] + NEW,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DST.name}: {len(out['questions'])} questions")


if __name__ == "__main__":
    main()
