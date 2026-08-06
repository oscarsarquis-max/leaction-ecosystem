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


def when_context_not_empty(path: str) -> dict:
    return {"context": path, "not_empty": True}


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
    q(
        "c6-rsk-03",
        "Riscos e oportunidades",
        "6.1",
        "A empresa revisita riscos e oportunidades quando o contexto muda (novo cliente, novo produto, crise, sazonalidade)?",
        "Lista estática perde valor. Revisar nos momentos certos evita surpresa operacional.",
        ["Revisão de riscos na mudança de portfólio", "Pauta fixa de riscos na reunião mensal"],
        ["Histórico de revisões de risco", "Ata que registra inclusão/baixa de riscos"],
        when_answer("c6-rsk-01", YES_PARTIAL),
    ),
    q(
        "c6-obj-03",
        "Objetivos da qualidade",
        "6.2",
        "Os objetivos de qualidade são comunicados às pessoas que precisam agir sobre eles?",
        "Objetivo só na direção não move o chão de fábrica nem o atendimento.",
        ["Desdobramento de metas por área", "Quadro ou painel visível ao time"],
        ["Comunicado de metas", "Evidência de alinhamento com equipes"],
        when_answer("c6-obj-01", YES_PARTIAL),
    ),
    q(
        "c6-chg-02",
        "Mudanças no sistema",
        "6.3",
        "Antes de mudar algo relevante, a empresa avalia impacto em cliente, processos, pessoas e riscos?",
        "Mudança sem leitura de impacto costuma gerar retrabalho e reclamação.",
        ["Análise simples de impacto", "Go/no-go com responsáveis do processo"],
        ["Registro de análise de impacto", "Aprovação da mudança"],
        when_answer("c6-chg-01", YES_PARTIAL),
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
    q(
        "c7-msr-01",
        "Medição e calibração",
        "7.1",
        "A operação depende de medições ou instrumentos de verificação para decidir se o produto/serviço está ok?",
        "Pergunta-porta: só faz sentido falar de calibração quando a qualidade depende de medir.",
        ["Balança, paquímetro, manômetro, sensores", "Checklist com critérios numéricos"],
        ["Lista de pontos de medição críticos", "Descrição do que é medido na operação"],
    ),
    q(
        "c7-res-02",
        "Medição e calibração",
        "7.1",
        "Esses equipamentos de medição ou verificação estão adequados e confiáveis para a decisão que suportam?",
        "Medir errado é pior do que não medir: a decisão parece fundamentada, mas não está.",
        ["Calibração ou verificação periódica", "Critério claro de o que medir e com o quê"],
        ["Certificados ou registros de verificação", "Lista de instrumentos críticos"],
        when_answer("c7-msr-01", YES_PARTIAL),
    ),
    q(
        "c7-cmp-02",
        "Competência",
        "7.2",
        "Quando alguém assume função crítica sem a competência completa, há supervisão, treino ou restrição temporária?",
        "Colocar pessoa nova em posto crítico sem rede de proteção é risco previsível.",
        ["Período de capacitação com acompanhante", "Liberação formal para operar sozinho"],
        ["Registro de liberação de função", "Plano de treino on-the-job"],
        when_answer("c7-cmp-01", YES_PARTIAL),
    ),
    q(
        "c7-knw-01",
        "Conhecimento da organização",
        "7.1",
        "O conhecimento crítico do negócio (como fazer certo o que o cliente valoriza) está acessível — não só na cabeça de poucas pessoas?",
        "Conhecimento preso em poucas pessoas vira risco de continuidade e de qualidade.",
        ["Procedimentos vivos ou playbooks", "Handover e lições aprendidas"],
        ["Base de conhecimento / procedimentos", "Registro de lições aprendidas"],
    ),
    q(
        "c7-doc-02",
        "Informação documentada",
        "7.5",
        "Quando um documento muda, a versão antiga deixa de ser usada no dia a dia?",
        "Versão velha na bancada é uma das causas clássicas de erro repetido.",
        ["Retirada ou marca d'água de obsoleto", "Aviso de nova versão aos usuários"],
        ["Controle de versão com histórico", "Evidência de comunicação da mudança"],
        when_answer("c7-doc-01", YES_PARTIAL),
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
    q(
        "c8-req-02",
        "Requisitos do cliente",
        "8.2",
        "Mudanças de pedido ou de escopo pedidas pelo cliente são registradas e repassadas a quem executa?",
        "Pedido mudou e a operação não soube: receita clássica de retrabalho e atrito.",
        ["Controle de alteração de pedido", "Comunicação obrigatória para produção/serviço"],
        ["Registro de alteração", "Confirmação ao cliente e ao time interno"],
        when_answer("c8-req-01", YES_PARTIAL),
    ),
    q(
        "c8-prd-02",
        "Produção e prestação do serviço",
        "8.5",
        "Dá para saber, quando preciso, o que foi feito, por quem e com quais insumos (rastreabilidade útil ao negócio)?",
        "Rastreabilidade boa resolve disputa e acelera contenção quando algo dá errado.",
        ["Lotes, ordens ou tickets com histórico", "Identificação em processo"],
        ["Registros de lote/ordem", "Exemplos de rastreio ponta a ponta"],
    ),
    q(
        "c8-prop-01",
        "Propriedade de cliente ou fornecedor",
        "8.5",
        "A empresa recebe bens, materiais ou dados de clientes ou fornecedores para usar na entrega?",
        "Pergunta-porta: só então faz sentido controlar propriedade de terceiros.",
        ["Ferramentas ou moldes do cliente", "Arquivos, dados ou amostras fornecidas"],
        ["Lista do que é recebido de terceiros", "Contrato que menciona bens/dados do cliente"],
    ),
    q(
        "c8-prd-03",
        "Propriedade de cliente ou fornecedor",
        "8.5",
        "Esses bens, materiais ou dados de terceiros são protegidos e tratados com cuidado?",
        "Perder, danificar ou expor o que é do cliente ou fornecedor destrói confiança rápido.",
        ["Controle de propriedade do cliente/fornecedor", "Regras de sigilo e guarda"],
        ["Registro de recebimento/devolução", "Tratativa quando há dano ou perda"],
        when_answer("c8-prop-01", YES_PARTIAL),
    ),
    q(
        "c8-rel-02",
        "Liberação e não conformidade",
        "8.6",
        "Depois da entrega, a empresa acompanha o que combinou (suporte, garantia, instalação) quando isso faz parte do acordo?",
        "A qualidade não termina na porta de saída se o contrato inclui pós-entrega.",
        ["Checklist de pós-venda", "SLA de suporte ou garantia"],
        ["Registros de atendimento pós-entrega", "Acordo comercial com obrigações claras"],
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
    q(
        "c9-sat-01",
        "Satisfação do cliente",
        "9.1",
        "A empresa escuta a satisfação (e a insatisfação) do cliente de forma útil para decidir — não só para arquivar?",
        "Pesquisa sem uso é teatro. O valor está em agir sobre o que se ouve.",
        ["Pesquisa, NPS ou entrevistas", "Análise de reclamações e elogios"],
        ["Resultados de satisfação", "Ações derivadas do feedback"],
    ),
    q(
        "c9-aud-02",
        "Avaliação interna",
        "9.2",
        "Os achados da avaliação interna geram ações com prazo e responsável — e alguém confere se fecharam?",
        "Relatório sem ação é custo sem retorno.",
        ["Plano de ações pós-avaliação", "Verificação de fechamento"],
        ["Lista de achados com status", "Evidência de verificação"],
        when_answer("c9-aud-01", YES_PARTIAL),
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
    q(
        "c10-capa-03",
        "Não conformidade e ação corretiva",
        "10.2",
        "Problemas parecidos que se repetem em áreas diferentes são tratados como padrão — não como casos isolados?",
        "Tratar cada ocorrência como única esconde causa sistêmica.",
        ["Agrupamento de reclamações/NCs por tema", "Ação corretiva de processo, não só de lote"],
        ["Análise de recorrência", "Ação que muda o processo"],
        when_answer("c10-capa-01", YES_PARTIAL),
    ),
    q(
        "c10-imp-02",
        "Melhoria",
        "10.1",
        "Ideias e problemas levantados por quem executa chegam a alguém com poder de priorizar melhoria?",
        "Quem faz o trabalho vê o atrito primeiro. Sem canal, a melhoria fica só no discurso.",
        ["Canal simples de sugestões/problemas", "Ritual de priorização com a gestão"],
        ["Registro de sugestões", "Exemplos de melhorias originadas do time"],
    ),
]


def main() -> None:
    base = json.loads(SRC.read_text(encoding="utf-8"))
    # Condições reais + follow-ups c4–c5
    for item in base["questions"]:
        if item["id"] == "c4-ctx-02":
            item["show_when"] = when_answer("c4-ctx-01", YES_PARTIAL)
        elif item["id"] == "c4-int-02":
            item["show_when"] = when_answer("c4-int-01", YES_PARTIAL)
        elif item["id"] == "c4-scp-02":
            # Justificativa de exclusão só quando há exclusões no contexto.
            item["show_when"] = when_context_not_empty("qms_scope.exclusions")
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
            {"id": "4", "label": "Compreender a organização", "refs": ["4.1", "4.2", "4.3", "4.4"]},
            {"id": "5", "label": "Liderança e direção", "refs": ["5.1", "5.2", "5.3"]},
            {"id": "6", "label": "Planejar resultados", "refs": ["6.1", "6.2", "6.3"]},
            {"id": "7", "label": "Criar capacidade para entregar", "refs": ["7.1", "7.2", "7.3", "7.4", "7.5"]},
            {"id": "8", "label": "Entregar ao cliente com controle", "refs": ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7"]},
            {"id": "9", "label": "Medir, analisar e decidir", "refs": ["9.1", "9.2", "9.3"]},
            {"id": "10", "label": "Corrigir e melhorar", "refs": ["10.1", "10.2", "10.3"]},
        ],
        "questions": base["questions"] + NEW,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DST.name}: {len(out['questions'])} questions")


if __name__ == "__main__":
    main()
