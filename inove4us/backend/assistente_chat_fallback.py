"""Árvore mínima local do Assistente (fallback se o Hub CMS falhar).

Nomenclatura alinhada ao produto real (2026-07):
- Dia a Dia: 4 estações — Alinhamento, Entrega do dia, Atividade em campo, Retro do ciclo
- Desafios: Wizard → plano EduScrum + Kanban (Para Fazer / Fazendo / Pronto)
- Freemium: valores injetados em runtime a partir de db.FREEMIUM_*
"""

from __future__ import annotations

from typing import Any


def build_fallback_tree(
    *,
    aulas_mes: int = 5,
    desafios_gratis: int = 1,
) -> dict[str, Any]:
    """Árvore completa usada como plano B e como conteúdo inicial até o Hub publicar."""
    return {
        "avatar_name": "Nina",
        "avatar_tagline": "Guia do inovador",
        "avatar_candidates": ["Nina"],
        "root_id": "inicio",
        "nodes": {
            "inicio": {
                "message": (
                    "Olá! Sou a Nina, sua guia no inove4us. "
                    "Escolha um tema abaixo — ou deixe uma sugestão no campo acima."
                ),
                "options": [
                    {"label": "Aulas do Dia a Dia (rápido)", "next": "dia_a_dia"},
                    {"label": "Desafios e Projetos", "next": "desafios"},
                    {"label": "Como usar o Kanban", "next": "kanban"},
                    {"label": "Planos, pagamentos e conta", "next": "planos"},
                ],
            },
            "dia_a_dia": {
                "message": (
                    "O Dia a Dia é o ciclo rápido (~50 min) para planejar e executar "
                    "uma aula. Você preenche as 4 estações e move o trabalho no Kanban "
                    "(Para Fazer → Fazendo → Pronto)."
                ),
                "options": [
                    {"label": "O que são as 4 estações?", "next": "dia_estacoes"},
                    {"label": "Como escolher a atividade em campo?", "next": "dia_dinamica"},
                    {"label": "Abrir o Dia a Dia", "next": "dia_a_dia", "href": "/dia-a-dia"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "dia_estacoes": {
                "message": (
                    "As 4 estações do ciclo são:\n"
                    "1 · Alinhamento (abertura)\n"
                    "2 · Entrega do dia\n"
                    "3 · Atividade em campo (dinâmica ativa)\n"
                    "4 · Retro do ciclo (fechamento)\n\n"
                    "Isso aparece exatamente assim na tela de planejar aula."
                ),
                "options": [
                    {"label": "Como escolher a atividade em campo?", "next": "dia_dinamica"},
                    {"label": "Ir para nova aula", "next": "dia_estacoes", "href": "/dia-a-dia/nova"},
                    {"label": "Voltar ao Dia a Dia", "next": "dia_a_dia"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "dia_dinamica": {
                "message": (
                    "Na estação 3 · Atividade em campo você pode escolher uma dinâmica "
                    "sugerida do catálogo ou descrever a sua. A sugestão é um atalho — "
                    "não substitui o seu julgamento pedagógico."
                ),
                "options": [
                    {"label": "Abrir nova aula", "next": "dia_dinamica", "href": "/dia-a-dia/nova"},
                    {"label": "Voltar ao Dia a Dia", "next": "dia_a_dia"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "desafios": {
                "message": (
                    "Em Desafios você descreve a dor real da turma; a inove4us estrutura "
                    "causas e caminhos metodológicos e gera um plano EduScrum com Kanban. "
                    "Cada geração bem-sucedida consome 1 crédito de desafio."
                ),
                "options": [
                    {"label": "Como escrever um bom desafio?", "next": "desafio_escrever"},
                    {"label": "A geração consome crédito?", "next": "desafio_credito"},
                    {"label": "Abrir Desafio", "next": "desafios", "href": "/desafio"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "desafio_escrever": {
                "message": (
                    "Seja específico: turma, tema e a dor real (o que trava a aprendizagem). "
                    "Cite nomes concretos (projeto, prazo, hipóteses dos alunos). "
                    "Evite só dizer “a turma está dispersa” — quanto mais contexto, "
                    "melhor a hipótese e o plano."
                ),
                "options": [
                    {"label": "Ir para Desafio", "next": "desafio_escrever", "href": "/desafio"},
                    {"label": "Voltar a Desafios", "next": "desafios"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "desafio_credito": {
                "message": (
                    f"Sim. Cada estruturação com IA consome 1 crédito de desafio. "
                    f"No plano gratuito você começa com {desafios_gratis} desafio"
                    f"{'' if desafios_gratis == 1 else 's'}. "
                    "Aulas do Dia a Dia usam outro limite (aulas/mês), não esse crédito."
                ),
                "options": [
                    {"label": "Ver planos e créditos", "next": "planos"},
                    {"label": "Voltar a Desafios", "next": "desafios"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "kanban": {
                "message": (
                    "O Kanban acompanha a execução da aula ou do plano EduScrum. "
                    "As colunas são: Para Fazer → Fazendo → Pronto. "
                    "Ao mover um card, você registra uma observação curta do que mudou."
                ),
                "options": [
                    {"label": "Como mover os cards?", "next": "kanban_mover"},
                    {"label": "Onde vejo o Kanban?", "next": "kanban_onde"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "kanban_mover": {
                "message": (
                    "Clique no card e escolha a coluna de destino (Para Fazer, Fazendo ou Pronto). "
                    "É pedido um registro breve do que foi feito — isso alimenta o histórico "
                    "da aula. Não usamos o termo “Sprint” aqui: o ciclo é a própria aula "
                    "ou a continuidade/reinício no EduScrum."
                ),
                "options": [
                    {"label": "Abrir Mesa (agenda e mapa)", "next": "kanban_mover", "href": "/mesa-do-inovador"},
                    {"label": "Voltar ao Kanban", "next": "kanban"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "kanban_onde": {
                "message": (
                    "No Dia a Dia, o Kanban fica ao lado do planejamento do ciclo. "
                    "Nos Desafios, depois de gerar o plano EduScrum, o quadro aparece "
                    "na etapa de execução da aula registrada na agenda."
                ),
                "options": [
                    {"label": "Ir ao Dia a Dia", "next": "kanban_onde", "href": "/dia-a-dia"},
                    {"label": "Ir a Desafios", "next": "kanban_onde", "href": "/desafio"},
                    {"label": "Voltar ao Kanban", "next": "kanban"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "planos": {
                "message": (
                    f"No plano gratuito: até {aulas_mes} aulas do Dia a Dia por mês e "
                    f"{desafios_gratis} desafio ativo (crédito de IA). "
                    "Para mais liberdade, veja Profissional, Mentor ou pacotes avulsos."
                ),
                "options": [
                    {"label": "Limites do plano grátis", "next": "planos_limites"},
                    {"label": "Como assinar / comprar créditos?", "next": "planos_assinar"},
                    {"label": "Renovação e cancelamento", "next": "planos_cancelar"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "planos_limites": {
                "message": (
                    f"Gratuito: {aulas_mes} aulas do Dia a Dia / mês e "
                    f"{desafios_gratis} crédito de desafio. "
                    "Quando o crédito acaba, a estruturação com IA fica bloqueada até "
                    "você escolher um plano ou pacote."
                ),
                "options": [
                    {"label": "Como assinar?", "next": "planos_assinar"},
                    {"label": "Voltar a Planos", "next": "planos"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "planos_assinar": {
                "message": (
                    "Use o botão Ver planos (no topo ou quando os créditos acabam). "
                    "Você escolhe o plano no Action Hub e paga com Mercado Pago "
                    "(cartão e demais meios disponíveis no checkout). "
                    "Profissional R$ 24,90 · Mentor R$ 49,90 · pacote avulso de 3 desafios."
                ),
                "options": [
                    {
                        "label": "Abrir planos (upgrade)",
                        "next": "planos_assinar",
                        "action": "open_upgrade",
                    },
                    {"label": "Voltar a Planos", "next": "planos"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
            "planos_cancelar": {
                "message": (
                    "Assinaturas e cobranças ficam no Action Hub / Mercado Pago. "
                    "Para alterar ou cancelar, use o fluxo de planos/conta do Hub "
                    "ou o suporte indicado na página de pagamento. "
                    "Pacotes avulsos de créditos não renovam automaticamente."
                ),
                "options": [
                    {"label": "Voltar a Planos", "next": "planos"},
                    {"label": "Voltar ao início", "next": "inicio"},
                ],
            },
        },
    }


def normalize_tree_payload(raw: object, *, aulas_mes: int, desafios_gratis: int) -> dict[str, Any] | None:
    """Valida JSON do Hub; devolve None se inválido."""
    if not isinstance(raw, dict):
        return None
    nodes = raw.get("nodes")
    root_id = str(raw.get("root_id") or "").strip()
    if not isinstance(nodes, dict) or not root_id or root_id not in nodes:
        return None
    # Cópia rasa + placeholders
    out = {
        "avatar_name": str(raw.get("avatar_name") or "Nina").strip()[:40] or "Nina",
        "avatar_tagline": str(raw.get("avatar_tagline") or "Guia do inovador").strip()[:80],
        "avatar_candidates": raw.get("avatar_candidates")
        if isinstance(raw.get("avatar_candidates"), list)
        else ["Nina"],
        "root_id": root_id,
        "nodes": {},
        "source": "hub",
    }
    for nid, node in nodes.items():
        if not isinstance(node, dict):
            continue
        msg = str(node.get("message") or "")
        msg = msg.replace("{{FREEMIUM_AULAS}}", str(aulas_mes))
        msg = msg.replace("{{FREEMIUM_DESAFIOS}}", str(desafios_gratis))
        options = []
        for opt in node.get("options") or []:
            if not isinstance(opt, dict):
                continue
            label = str(opt.get("label") or "").strip()
            nxt = str(opt.get("next") or "").strip()
            if not label:
                continue
            item: dict[str, Any] = {"label": label[:120]}
            if nxt:
                item["next"] = nxt
            href = str(opt.get("href") or "").strip()
            if href.startswith("/"):
                item["href"] = href[:200]
            action = str(opt.get("action") or "").strip()
            if action:
                item["action"] = action[:64]
            options.append(item)
        out["nodes"][str(nid)] = {"message": msg[:2000], "options": options}
    if root_id not in out["nodes"]:
        return None
    return out
