"""Versioned advisory rule catalog for the Evolution Map (deterministic, no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.schemas.enums import (
    EvolutionCategory,
    EvolutionConfidence,
    EvolutionEffort,
    EvolutionImpact,
    EvolutionPriority,
)

CATALOG_VERSION = "1.0.0"

ConditionKind = Literal[
    "guided_answer_value",
    "evidence_pending",
    "evidence_rejected",
    "context_objectives_incomplete",
    "context_risks_without_action",
    "context_processes_untracked",
    "competence_undemonstrated",
    "documented_info_uncontrolled",
    "supplier_unevaluated",
    "customer_satisfaction_untracked",
    "internal_audit_ineffective",
    "finding_cause_missing",
    "action_efficacy_unverified",
    "maturity_low_dimension",
]


@dataclass(frozen=True, slots=True)
class EvolutionRule:
    rule_id: str
    version: str
    category: EvolutionCategory
    conditions: dict[str, Any]
    title: str
    observation: str
    business_rationale: str
    suggested_evolution: str
    expected_benefit: str
    first_step: str
    impact: EvolutionImpact
    effort: EvolutionEffort
    base_priority: EvolutionPriority
    expected_sources: tuple[str, ...] = field(default_factory=tuple)
    related_clauses: tuple[str, ...] = field(default_factory=tuple)
    # Optional theme tags to match question codes (e.g. CTX, LDR, OPS)
    question_themes: tuple[str, ...] = field(default_factory=tuple)


def _rule(
    rule_id: str,
    *,
    category: EvolutionCategory,
    conditions: dict[str, Any],
    title: str,
    observation: str,
    business_rationale: str,
    suggested_evolution: str,
    expected_benefit: str,
    first_step: str,
    impact: EvolutionImpact = EvolutionImpact.medium,
    effort: EvolutionEffort = EvolutionEffort.medium,
    base_priority: EvolutionPriority = EvolutionPriority.next_cycle,
    expected_sources: tuple[str, ...] = (),
    related_clauses: tuple[str, ...] = (),
    question_themes: tuple[str, ...] = (),
    version: str = "1.0.0",
) -> EvolutionRule:
    return EvolutionRule(
        rule_id=rule_id,
        version=version,
        category=category,
        conditions=conditions,
        title=title,
        observation=observation,
        business_rationale=business_rationale,
        suggested_evolution=suggested_evolution,
        expected_benefit=expected_benefit,
        first_step=first_step,
        impact=impact,
        effort=effort,
        base_priority=base_priority,
        expected_sources=expected_sources,
        related_clauses=related_clauses,
        question_themes=question_themes,
    )


RULES: tuple[EvolutionRule, ...] = (
    _rule(
        "EVO-ANS-PARTIAL-OPS",
        category=EvolutionCategory.operations_customers,
        conditions={"kind": "guided_answer_value", "answer_values": ["partial"]},
        question_themes=("OPS", "PRD", "SVC", "CUS"),
        title="Prática operacional ainda inconsistente",
        observation="Há respostas parciais sobre como o trabalho do dia a dia é conduzido.",
        business_rationale=(
            "Quando o fluxo funciona 'às vezes', o cliente sente variação de prazo e qualidade "
            "e a equipe gasta energia apagando incêndio."
        ),
        suggested_evolution=(
            "Padronizar o fluxo crítico em um roteiro simples, com quem faz o quê e quando "
            "escalar exceção."
        ),
        expected_benefit="Menos retrabalho e entrega mais previsível para o cliente.",
        first_step="Escolher um processo crítico e descrever o caminho feliz em uma página.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.now,
        expected_sources=("guided_answer", "evidence"),
        related_clauses=("8",),
    ),
    _rule(
        "EVO-ANS-NO-GOV",
        category=EvolutionCategory.direction_governance,
        conditions={"kind": "guided_answer_value", "answer_values": ["no"]},
        question_themes=("LDR", "GOV", "POL", "CTX"),
        title="Direção ainda sem prática explícita",
        observation="Há respostas negativas sobre direção, papéis ou intenção da qualidade.",
        business_rationale=(
            "Sem direção clara, decisões competem entre si e a equipe interpreta prioridades "
            "de formas diferentes."
        ),
        suggested_evolution=(
            "Explicitar em linguagem da empresa o que qualidade significa aqui, quem decide "
            "e como isso aparece nas reuniões."
        ),
        expected_benefit="Alinhamento mais rápido e menos conflito de prioridades.",
        first_step="Escrever em 5 linhas a intenção de qualidade da organização e quem patrocina.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.low,
        base_priority=EvolutionPriority.now,
        expected_sources=("guided_answer",),
        related_clauses=("5",),
    ),
    _rule(
        "EVO-ANS-UNKNOWN-PLAN",
        category=EvolutionCategory.planning_risks,
        conditions={"kind": "guided_answer_value", "answer_values": ["unknown"]},
        question_themes=("RSK", "PLN", "OBJ", "CHG"),
        title="Lacuna de informação no planejamento",
        observation="Há respostas 'não sei' em temas de planejamento ou risco.",
        business_rationale=(
            "Não saber é um sinal de que a informação não circula — não é julgamento de culpa. "
            "Sem clareza, o plano vira lista de desejos."
        ),
        suggested_evolution=(
            "Mapear quem detém a informação faltante e agendar uma conversa curta para fechar "
            "o entendimento."
        ),
        expected_benefit="Planejamento com premissas explícitas e menos surpresa operacional.",
        first_step="Listar as três dúvidas e o nome de quem pode respondê-las nesta semana.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.low,
        base_priority=EvolutionPriority.investigate,
        expected_sources=("guided_answer",),
        related_clauses=("6",),
    ),
    _rule(
        "EVO-EVID-PENDING",
        category=EvolutionCategory.measurement_decisions,
        conditions={"kind": "evidence_pending"},
        title="Evidência prometida ainda não disponível",
        observation="Existem evidências em espera de envio, análise ou promessa de entrega posterior.",
        business_rationale=(
            "Decisões baseadas em 'vamos anexar depois' aumentam o risco de concluir cedo "
            "demais e reabrir o assunto sob pressão."
        ),
        suggested_evolution=(
            "Fechar o ciclo das evidências pendentes antes de tratar o tema como resolvido."
        ),
        expected_benefit="Base factual mais confiável para priorizar melhorias.",
        first_step="Revisar a lista de evidências pendentes e definir data de entrega por item.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.low,
        base_priority=EvolutionPriority.now,
        expected_sources=("evidence", "guided_answer"),
        related_clauses=("7", "9"),
    ),
    _rule(
        "EVO-EVID-REJECTED",
        category=EvolutionCategory.measurement_decisions,
        conditions={"kind": "evidence_rejected"},
        title="Evidência rejeitada precisa de substituição",
        observation="Há evidências rejeitadas vinculadas à avaliação.",
        business_rationale=(
            "Manter rejeições sem substituto deixa um buraco na narrativa do diagnóstico "
            "e enfraquece qualquer plano posterior."
        ),
        suggested_evolution=(
            "Substituir ou complementar o material rejeitado com um registro que realmente "
            "mostre a prática atual."
        ),
        expected_benefit="Histórico utilizável sem ambiguidade sobre o que foi observado.",
        first_step="Abrir cada evidência rejeitada e decidir: substituir, complementar ou justificar.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.now,
        expected_sources=("evidence",),
        related_clauses=("7",),
    ),
    _rule(
        "EVO-CTX-OBJECTIVES",
        category=EvolutionCategory.direction_governance,
        conditions={"kind": "context_objectives_incomplete"},
        title="Objetivos sem dono ou prazo claro",
        observation="O contexto descreve intenção, mas faltam responsável e/ou prazo operacional.",
        business_rationale=(
            "Objetivo sem dono vira cartaz. Sem prazo, a prioridade compete com o urgente do dia."
        ),
        suggested_evolution=(
            "Associar a cada objetivo um responsável nomeado e uma data de revisão realista."
        ),
        expected_benefit="Foco mensurável e cobrança justa entre áreas.",
        first_step="Pegar o objetivo mais importante e preencher responsável + data de revisão.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.low,
        base_priority=EvolutionPriority.now,
        expected_sources=("wizard_context",),
        related_clauses=("6",),
    ),
    _rule(
        "EVO-CTX-RISKS",
        category=EvolutionCategory.planning_risks,
        conditions={"kind": "context_risks_without_action"},
        title="Riscos citados sem ação associada",
        observation="Riscos aparecem no contexto, mas não há ação ou tratamento correspondente.",
        business_rationale=(
            "Nomear risco sem tratamento cria falsa segurança — o problema só fica visível "
            "quando já custou caro."
        ),
        suggested_evolution=(
            "Para cada risco relevante, definir prevenção simples ou plano de contingência."
        ),
        expected_benefit="Menos surpresa operacional e resposta mais rápida quando algo falha.",
        first_step="Escolher o risco de maior impacto e escrever uma ação preventiva em uma frase.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("wizard_context", "guided_answer"),
        related_clauses=("6",),
    ),
    _rule(
        "EVO-CTX-PROCESSES",
        category=EvolutionCategory.operations_customers,
        conditions={"kind": "context_processes_untracked"},
        title="Processos sem acompanhamento",
        observation="Há processos listados sem indício de acompanhamento (indicador, rotina ou evidência).",
        business_rationale=(
            "Processo sem olhar periódico degrada em silêncio até o cliente ou a equipe reclamar."
        ),
        suggested_evolution=(
            "Definir um sinal simples de saúde por processo crítico (prazo, retrabalho ou fila)."
        ),
        expected_benefit="Detecção precoce de gargalos antes de virar crise.",
        first_step="Escolher um processo e um número que a equipe já olhe toda semana.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("wizard_context", "guided_answer"),
        related_clauses=("4", "8"),
    ),
    _rule(
        "EVO-PEOPLE-COMPETENCE",
        category=EvolutionCategory.people_resources,
        conditions={"kind": "competence_undemonstrated"},
        question_themes=("HR", "CMP", "TRN", "PPL"),
        title="Competências ainda sem demonstração",
        observation="Respostas sobre pessoas/competência vieram parciais, negativas ou sem evidência.",
        business_rationale=(
            "Assumir que 'todo mundo sabe' esconde dependência de poucas pessoas e risco "
            "quando alguém falta."
        ),
        suggested_evolution=(
            "Tornar explícito o que cada papel crítico precisa saber fazer e como isso é "
            "demonstrado no trabalho."
        ),
        expected_benefit="Menos dependência crítica e onboarding mais rápido.",
        first_step="Listar três habilidades críticas do processo e quem as demonstra hoje.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("guided_answer", "evidence"),
        related_clauses=("7",),
    ),
    _rule(
        "EVO-DOC-CONTROL",
        category=EvolutionCategory.people_resources,
        conditions={"kind": "documented_info_uncontrolled"},
        question_themes=("DOC", "INF", "REC"),
        title="Informação documentada sem controle prático",
        observation="Há indícios de documentos ou registros sem versão, dono ou local confiável.",
        business_rationale=(
            "Quando cada um usa uma versão diferente, a operação diverge e a discussão "
            "vira 'quem está certo?'."
        ),
        suggested_evolution=(
            "Definir um lugar oficial para o que é crítico e uma regra simples de atualização."
        ),
        expected_benefit="Menos erro por informação desatualizada.",
        first_step="Escolher o documento mais usado e garantir uma única versão oficial visível.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("guided_answer", "evidence"),
        related_clauses=("7",),
    ),
    _rule(
        "EVO-SUPPLIER",
        category=EvolutionCategory.operations_customers,
        conditions={"kind": "supplier_unevaluated"},
        question_themes=("SUP", "PUR", "EXT"),
        title="Fornecedores sem avaliação prática",
        observation="Respostas sobre fornecedores externos indicam ausência ou fragilidade de avaliação.",
        business_rationale=(
            "Fornecedor sem critério vira loteria de custo, prazo e qualidade — o cliente "
            "sente o efeito depois."
        ),
        suggested_evolution=(
            "Definir critérios mínimos (prazo, qualidade, comunicação) e revisar periodicamente."
        ),
        expected_benefit="Menos interrupção de fornecimento e menos surpresa de custo.",
        first_step="Listar os três fornecedores críticos e o critério que mais importa para cada um.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("guided_answer",),
        related_clauses=("8",),
    ),
    _rule(
        "EVO-CUSTOMER-SAT",
        category=EvolutionCategory.operations_customers,
        conditions={"kind": "customer_satisfaction_untracked"},
        question_themes=("CUS", "SAT", "FBK", "NPS"),
        title="Satisfação do cliente sem acompanhamento",
        observation="Não há indício claro de escuta contínua da percepção do cliente.",
        business_rationale=(
            "Sem escuta estruturada, a empresa só descobre insatisfação quando já perdeu "
            "renovação ou reputação."
        ),
        suggested_evolution=(
            "Instalar um canal simples de feedback e uma rotina mensal de leitura dos sinais."
        ),
        expected_benefit="Ajustes de oferta e atendimento com base em fatos, não em achismo.",
        first_step="Definir uma pergunta curta pós-entrega e quem lê as respostas toda semana.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.low,
        base_priority=EvolutionPriority.now,
        expected_sources=("guided_answer", "wizard_context"),
        related_clauses=("9",),
    ),
    _rule(
        "EVO-INTERNAL-AUDIT",
        category=EvolutionCategory.measurement_decisions,
        conditions={"kind": "internal_audit_ineffective"},
        question_themes=("AUD", "INT", "CHK"),
        title="Verificação interna ainda pouco efetiva",
        observation="Há sinais de que a verificação interna não gera aprendizado acionável.",
        business_rationale=(
            "Verificação que só 'cumpre calendário' consome tempo sem mudar o resultado "
            "para o cliente ou a operação."
        ),
        suggested_evolution=(
            "Transformar cada verificação em perguntas sobre risco real e ações com dono."
        ),
        expected_benefit="Aprendizado interno mais útil e menos formalismo vazio.",
        first_step="Revisar a última verificação e extrair uma melhoria concreta com responsável.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("guided_answer", "finding"),
        related_clauses=("9",),
    ),
    _rule(
        "EVO-FINDING-CAUSE",
        category=EvolutionCategory.correction_improvement,
        conditions={"kind": "finding_cause_missing"},
        title="Constatação sem análise de causa",
        observation="Há constatações revisadas sem indício de causa compreendida.",
        business_rationale=(
            "Corrigir só o sintoma faz o problema voltar — e a equipe perde confiança no processo."
        ),
        suggested_evolution=(
            "Para cada constatação relevante, registrar a causa mais provável em linguagem simples."
        ),
        expected_benefit="Ações que atacam a raiz e reduzem reincidência.",
        first_step="Escolher uma constatação e responder: 'por que isso aconteceu de verdade?'.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.now,
        expected_sources=("finding",),
        related_clauses=("10",),
    ),
    _rule(
        "EVO-ACTION-EFFICACY",
        category=EvolutionCategory.correction_improvement,
        conditions={"kind": "action_efficacy_unverified"},
        title="Ação sem verificação de eficácia",
        observation="Existem itens de ação implementados sem validação de eficácia.",
        business_rationale=(
            "Marcar como feito sem checar resultado cria ilusão de progresso e reabre o "
            "mesmo problema no próximo ciclo."
        ),
        suggested_evolution=(
            "Definir evidência de eficácia e data de verificação antes de encerrar a ação."
        ),
        expected_benefit="Ciclo de melhoria que realmente fecha.",
        first_step="Para cada ação 'implementada', definir o que prova que melhorou e quando checar.",
        impact=EvolutionImpact.high,
        effort=EvolutionEffort.low,
        base_priority=EvolutionPriority.now,
        expected_sources=("action_item", "finding"),
        related_clauses=("10",),
    ),
    _rule(
        "EVO-MATURITY-LOW",
        category=EvolutionCategory.measurement_decisions,
        conditions={"kind": "maturity_low_dimension", "max_level": 2},
        title="Dimensão de maturidade ainda inicial",
        observation="Há dimensão de maturidade aprovada com nível baixo (1–2).",
        business_rationale=(
            "Nível inicial não é fracasso — é mapa. Ignorar a dimensão frágil concentra "
            "risco onde a operação menos aguenta pressão."
        ),
        suggested_evolution=(
            "Escolher uma prática concreta que eleve a dimensão frágil no próximo ciclo."
        ),
        expected_benefit="Evolução visível e priorizada, sem dispersão.",
        first_step="Abrir a dimensão mais baixa e escolher um único hábito semanal para fortalecer.",
        impact=EvolutionImpact.medium,
        effort=EvolutionEffort.medium,
        base_priority=EvolutionPriority.next_cycle,
        expected_sources=("maturity_score",),
        related_clauses=("4", "5", "6", "7", "8", "9", "10"),
    ),
)


def rules_by_id() -> dict[str, EvolutionRule]:
    return {r.rule_id: r for r in RULES}


def default_confidence_for_rule(rule: EvolutionRule, *, has_evidence: bool, has_finding: bool) -> EvolutionConfidence:
    kind = str(rule.conditions.get("kind", ""))
    if kind == "guided_answer_value" and rule.conditions.get("answer_values") == ["unknown"]:
        return EvolutionConfidence.low
    if has_evidence and has_finding:
        return EvolutionConfidence.high
    if has_evidence or has_finding:
        return EvolutionConfidence.medium
    if kind in ("evidence_pending", "evidence_rejected", "action_efficacy_unverified"):
        return EvolutionConfidence.medium
    return EvolutionConfidence.medium
